"""
Proxy Handler - Transparent HTTP Relay for Internal Services
"""
import requests
from flask import Response, request, stream_with_context
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

# Hop-by-hop headers that should never be forwarded (RFC 7230)
HOP_BY_HOP_HEADERS = {
    'connection',
    'proxy-connection',  # Non-standard but some clients send it
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailer',  # Correct RFC name (singular, not trailers)
    'transfer-encoding',
    'upgrade',
    'content-length',  # Drop when streaming to let server chunk
}

# Headers that can legitimately repeat and should be preserved line-for-line
MULTI_VALUE_RESPONSE_HEADERS = {
    'set-cookie',
    'www-authenticate',
    'link',
    'warning',
}


def _connection_tokens(headers_obj) -> set:
    """
    Extract header names listed in Connection header.
    These are dynamic hop-by-hop headers that must also be stripped.
    """
    try:
        val = headers_obj.get('Connection') or headers_obj.get('connection')
    except Exception:
        val = None
    
    if not val:
        return set()
    
    # Parse comma-separated tokens and normalize to lowercase
    return {token.strip().lower() for token in val.split(',') if token.strip()}


class ProxyHandler:
    """Handle proxying requests to backend services"""
    
    def __init__(self, route_manager, verify_ssl: bool = False):
        self.route_manager = route_manager
        self._verify_ssl = verify_ssl
        
        # Use a session for connection pooling and optional retries
        self._session = requests.Session()
        try:
            from urllib3.util.retry import Retry
            from requests.adapters import HTTPAdapter
            # Retry safe methods on temporary failures
            retry = Retry(
                total=2,
                connect=2,
                read=2,
                status=2,
                allowed_methods={'GET', 'HEAD', 'OPTIONS'},
                status_forcelist={502, 503, 504},
                backoff_factor=0.2,
            )
            adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=64)
            self._session.mount('http://', adapter)
            self._session.mount('https://', adapter)
        except Exception:
            pass

        if not verify_ssl:
            try:
                from urllib3 import disable_warnings
                from urllib3.exceptions import InsecureRequestWarning
                disable_warnings(InsecureRequestWarning)
            except Exception:
                # Fallback quietly if urllib3 API changes
                pass
    
    def proxy_request(self, route_path: str, sub_path: str = '') -> Response:
        """
        Proxy a request to the target service
        
        Args:
            route_path: The route path (e.g., '/jellyfin')
            sub_path: Additional path after the route (e.g., '/dashboard')
        
        Returns:
            Flask Response object
        """
        # Get route configuration
        route = self.route_manager.get_route_by_path(route_path)
        
        if not route:
            return Response("Route not found", status=404)
        
        if not route.get('enabled', True):
            return Response("Route is disabled", status=503)
        
        # Build target URL
        target_url = self._build_target_url(route, sub_path)
        
        # Prepare headers
        headers = self._prepare_headers(route)
        
        # Get request data and method
        method = request.method
        # Preserve repeated query params (MultiDict → list of tuples)
        params = [(k, v) for k in request.args.keys() for v in request.args.getlist(k)]
        timeout = route.get('timeout', 30)
        
        # Buffer request body (avoid for large uploads in future)
        body = request.get_data(cache=False, as_text=False)
        
        try:
            logger.info(f"PROXY_REQUEST - Path: {route_path}{sub_path} | Target: {target_url} | Method: {method}")
            
            # Make the proxied request using session for connection pooling
            # Do NOT pass cookies= since Cookie header is already forwarded
            # Use separate connect/read timeouts for better control
            connect_timeout = min(5, timeout)
            resp = self._session.request(
                method=method,
                url=target_url,
                headers=headers,
                data=body,
                params=params,
                timeout=(connect_timeout, timeout),
                stream=True,  # Stream response
                allow_redirects=False,  # Handle redirects ourselves
                verify=self._verify_ssl
            )
            
            # Ensure compressed pass-through
            resp.raw.decode_content = False
            
            # Build Flask response. For HEAD or 204/304, do not stream a body.
            no_body = (method == 'HEAD') or (resp.status_code in (204, 304))
            
            if no_body:
                response = Response(status=resp.status_code, direct_passthrough=True)
            else:
                def generate():
                    # Stream raw bytes without decoding compression
                    for chunk in iter(lambda: resp.raw.read(8192), b''):
                        yield chunk
                
                response = Response(
                    stream_with_context(generate()),
                    status=resp.status_code,
                    direct_passthrough=True
                )
            
            # Close upstream when Flask closes the response (covers all code paths)
            response.call_on_close(resp.close)
            
            # Copy response headers, excluding hop-by-hop and those named by Connection
            resp_dynamic_hbh = _connection_tokens(resp.headers)
            for header, value in resp.headers.items():
                h = header.lower()
                if h in HOP_BY_HOP_HEADERS or h in resp_dynamic_hbh or h in MULTI_VALUE_RESPONSE_HEADERS:
                    continue
                response.headers[header] = value
            
            # Preserve multi-valued headers correctly
            raw_headers = getattr(resp.raw, 'headers', None)
            if raw_headers is not None:
                for name in MULTI_VALUE_RESPONSE_HEADERS:
                    for v in raw_headers.getlist(name.title()):
                        response.headers.add(name.title(), v)
            elif hasattr(resp.headers, 'get_all'):
                # Fallback for older requests versions
                for name in MULTI_VALUE_RESPONSE_HEADERS:
                    for v in resp.headers.get_all(name.title(), []):
                        response.headers.add(name.title(), v)
            
            # Preserve upstream Content-Length for HEAD (no body will be sent)
            if no_body and 'Content-Length' in resp.headers:
                response.headers['Content-Length'] = resp.headers['Content-Length']
            
            # Disable proxy buffering for real-time streaming (Nginx compatibility)
            response.headers['X-Accel-Buffering'] = 'no'
            
            # Add Via header for HTTP/1.1 proxy transparency
            response.headers.setdefault('Via', '1.1 shark-proxy')
            
            # Redirect rewrite using urllib.parse for safety
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get('Location')
                if loc:
                    new_loc = self._rewrite_location(loc, route, route_path)
                    if new_loc:
                        response.headers['Location'] = new_loc
                        logger.info(f"PROXY_REDIRECT - Rewrote: {loc} → {new_loc}")
            
            logger.info(f"PROXY_SUCCESS - Path: {route_path}{sub_path} | Status: {resp.status_code}")
            return response
            
        except requests.exceptions.Timeout:
            logger.error(f"PROXY_TIMEOUT - {target_url}")
            return Response("Service timeout", status=504)
        
        except requests.exceptions.ConnectionError:
            logger.error(f"PROXY_CONNECTION_ERROR - {target_url}")
            return Response("Service unavailable", status=503)
        
        except Exception as e:
            logger.error(f"PROXY_ERROR - {target_url} - {e}")
            return Response(f"Proxy error: {str(e)}", status=500)
    
    def _build_target_url(self, route: dict, sub_path: str) -> str:
        """Build the target URL from route config"""
        protocol = route.get('protocol', 'http')
        ip = route['target_ip']
        port = route['target_port']
        target_path = route.get('target_path', '').strip()
        
        # Ensure target_path starts with / if it exists
        if target_path and not target_path.startswith('/'):
            target_path = '/' + target_path
        
        # Ensure sub_path starts with /
        if sub_path and not sub_path.startswith('/'):
            sub_path = '/' + sub_path
        
        # Combine target_path and sub_path
        full_path = target_path + sub_path
        
        return f"{protocol}://{ip}:{port}{full_path}"
    
    def _prepare_headers(self, route: dict) -> dict:
        """
        Prepare headers for the proxied request.
        Strips hop-by-hop headers and Connection-named tokens.
        """
        headers = {}
        
        # Compute dynamic hop-by-hop tokens from incoming Connection header
        dynamic_hbh = _connection_tokens(request.headers)
        
        # Copy headers from original request, excluding hop-by-hop and host
        for header, value in request.headers.items():
            h = header.lower()
            # Also drop Expect: 100-continue to avoid stalls in proxy chains
            if h in HOP_BY_HOP_HEADERS or h in dynamic_hbh or h == 'host' or h == 'expect':
                continue
            headers[header] = value
        
        # Chain X-Forwarded-For properly (append to existing if present)
        xff = request.headers.get('X-Forwarded-For')
        client_ip = request.remote_addr or ''
        headers['X-Forwarded-For'] = f"{xff}, {client_ip}" if xff else client_ip
        
        # Preserve or set other forwarding headers
        headers['X-Forwarded-Proto'] = request.headers.get('X-Forwarded-Proto', request.scheme)
        headers['X-Forwarded-Host'] = request.headers.get('X-Forwarded-Host', request.host)
        headers['X-Forwarded-Port'] = request.environ.get('SERVER_PORT', '')
        
        # Help backends that honor a path base/prefix (useful for Jellyfin/.NET)
        # Use the route path as the prefix (e.g., /jellyfin)
        route_path = route.get('path', '').rstrip('/')
        if route_path:
            headers.setdefault('X-Forwarded-Prefix', route_path)
            headers.setdefault('X-Forwarded-PathBase', route_path)
        
        # RFC 7239 Forwarded header for observability at the backend
        # for=<client>;proto=<scheme>;host="<host>"
        client_ip = request.remote_addr or 'unknown'
        forwarded = f'for="{client_ip}";proto={request.scheme};host="{request.host}"'
        existing_forwarded = headers.get('Forwarded')
        if existing_forwarded:
            headers['Forwarded'] = existing_forwarded + ', ' + forwarded
        else:
            headers['Forwarded'] = forwarded
        
        # Set Host header if preserve_host is enabled (for host-based routing)
        if route.get('preserve_host', False):
            headers['Host'] = request.host
        # else: requests will set Host from target URL
        
        return headers
    
    def _rewrite_location(self, original_location: str, route: dict, route_path: str):
        """
        Safely rewrite redirect Location header using urllib.parse.
        Only rewrites URLs pointing to the backend; leaves cross-origin URLs alone.
        Handles IPv6, default ports, protocol-relative URLs, etc.
        
        Returns:
            Rewritten location string, or None if no rewrite needed/possible
        """
        try:
            # Build backend base components
            protocol = route.get('protocol', 'http')
            ip = route['target_ip']
            port = route['target_port']
            target_path = (route.get('target_path') or '').strip()
            if target_path and not target_path.startswith('/'):
                target_path = '/' + target_path
            
            # Build backend netloc with IPv6 bracket handling and default port normalization
            if ':' in ip and not ip.startswith('['):
                backend_netloc = f"[{ip}]"
            else:
                backend_netloc = ip
            
            # Handle default ports (http:80, https:443) for comparison
            backend_http_netloc = backend_netloc if port in (80, None) and protocol == 'http' else f"{backend_netloc}:{port}"
            backend_https_netloc = backend_netloc if port in (443, None) and protocol == 'https' else f"{backend_netloc}:{port}"
            
            loc = urlparse(original_location)
            
            # Absolute URL pointing at backend host (with or without default port)
            if loc.scheme and loc.netloc:
                # Only rewrite if same origin as backend (accept default-port elision)
                same_backend = (
                    loc.scheme == protocol and
                    loc.netloc in {backend_http_netloc, backend_https_netloc}
                )
                if same_backend:
                    # Remove target_path prefix if present before mapping to route_path
                    new_path = loc.path
                    if target_path and new_path.startswith(target_path):
                        new_path = new_path[len(target_path):] or '/'
                    
                    result = route_path.rstrip('/') + new_path
                    if loc.query:
                        result += '?' + loc.query
                    if loc.fragment:
                        result += '#' + loc.fragment
                    return result
                else:
                    # Different origin → do not rewrite (cross-origin redirect)
                    return None
            
            # Protocol-relative URLs (//host/path)
            if original_location.startswith('//'):
                if (original_location.startswith('//' + backend_http_netloc) or
                    original_location.startswith('//' + backend_https_netloc)):
                    # Parse with dummy scheme
                    rel = urlparse('http:' + original_location)
                    new_path = rel.path
                    if target_path and new_path.startswith(target_path):
                        new_path = new_path[len(target_path):] or '/'
                    
                    result = route_path.rstrip('/') + new_path
                    if rel.query:
                        result += '?' + rel.query
                    if rel.fragment:
                        result += '#' + rel.fragment
                    return result
                # Different host → do not rewrite
                return None
            
            # Pure relative path - handle various cases:
            
            # If it starts with '/', it's path-absolute
            if original_location.startswith('/'):
                # 1. Already has route_path prefix → return as-is
                if original_location.startswith(route_path):
                    logger.debug(f"Relative redirect already has route_path: {original_location}")
                    return original_location
                
                # 2. Has target_path prefix → strip target_path, add route_path
                if target_path and original_location.startswith(target_path):
                    rel_path = original_location[len(target_path):] or '/'
                    result = route_path.rstrip('/') + rel_path
                    logger.debug(f"Stripped target_path {target_path} from {original_location} → {result}")
                    return result
                
                # 3. Other absolute path → prepend route_path
                result = route_path.rstrip('/') + original_location
                logger.debug(f"Prepended route_path to absolute: {original_location} → {result}")
                return result
            
            # Relative to current location (no leading /)
            # e.g., "jellyfin/web/" means relative to current directory
            # Strip target_path from it if present (without leading /), then add route_path
            if target_path:
                target_path_stripped = target_path.lstrip('/')
                if original_location.startswith(target_path_stripped):
                    # Strip the relative target_path and make it absolute with route_path
                    rel_path = original_location[len(target_path_stripped):] or '/'
                    if not rel_path.startswith('/'):
                        rel_path = '/' + rel_path
                    result = route_path.rstrip('/') + rel_path
                    logger.debug(f"Stripped relative target_path {target_path_stripped} from {original_location} → {result}")
                    return result
            
            # Unknown relative format - prepend route_path with a /
            result = route_path.rstrip('/') + '/' + original_location
            logger.debug(f"Prepended route_path/ to relative: {original_location} → {result}")
            return result
            
        except Exception as e:
            logger.warning(f"Failed to rewrite location: {original_location} - {e}")
            return None
    
    def test_connection(self, route_id: str) -> dict:
        """
        Test connectivity to a route's target service
        
        Returns:
            dict with status and response time
        """
        route = self.route_manager.get_route_by_id(route_id)
        
        if not route:
            return {'success': False, 'error': 'Route not found'}
        
        target_url = self._build_target_url(route, '')
        timeout = route.get('timeout', 30)
        
        try:
            import time
            start = time.time()
            
            resp = requests.get(target_url, timeout=min(timeout, 10), verify=self._verify_ssl)
            
            duration = int((time.time() - start) * 1000)  # ms
            
            # Determine status
            if resp.status_code < 500:
                status = 'online'
                if duration > 2000:
                    status = 'slow'
            else:
                status = 'error'
            
            # Update route status in database
            self.route_manager.update_route_status(route_id, status)
            
            return {
                'success': True,
                'status': status,
                'status_code': resp.status_code,
                'response_time': duration
            }
            
        except requests.exceptions.Timeout:
            self.route_manager.update_route_status(route_id, 'timeout')
            return {'success': False, 'error': 'Connection timeout', 'status': 'timeout'}
        
        except requests.exceptions.ConnectionError:
            self.route_manager.update_route_status(route_id, 'offline')
            return {'success': False, 'error': 'Connection refused', 'status': 'offline'}
        
        except Exception as e:
            self.route_manager.update_route_status(route_id, 'error')
            return {'success': False, 'error': str(e), 'status': 'error'}
