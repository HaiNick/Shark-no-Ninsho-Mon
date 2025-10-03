"""
Proxy Handler - Forward requests to internal services
"""
import requests
from flask import Response, request, stream_with_context
import logging

logger = logging.getLogger(__name__)


class ProxyHandler:
    """Handle proxying requests to backend services"""
    
    def __init__(self, route_manager, verify_ssl: bool = False):
        self.route_manager = route_manager
        self._verify_ssl = verify_ssl

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
        
        # Get request data
        method = request.method
        data = request.get_data()
        params = request.args
        timeout = route.get('timeout', 30)
        
        try:
            logger.info(f"PROXY_REQUEST - Path: {route_path}{sub_path} | Target: {target_url} | Method: {method}")
            
            # Make the proxied request
            resp = requests.request(
                method=method,
                url=target_url,
                headers=headers,
                data=data,
                params=params,
                cookies=request.cookies,
                timeout=timeout,
                stream=True,  # Stream response for large files
                allow_redirects=False,  # Handle redirects ourselves
                verify=self._verify_ssl
            )
            
            # Build response
            response = Response(
                stream_with_context(resp.iter_content(chunk_size=8192)),
                status=resp.status_code
            )
            
            # Copy relevant headers from upstream response
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            for header, value in resp.headers.items():
                if header.lower() not in excluded_headers:
                    response.headers[header] = value
            
            logger.info(f"PROXY_SUCCESS - Path: {route_path}{sub_path} | Status: {resp.status_code}")
            return response
            
        except requests.exceptions.Timeout:
            logger.error(f"PROXY_TIMEOUT - Path: {route_path}{sub_path} | Target: {target_url}")
            return Response("Service timeout", status=504)
        
        except requests.exceptions.ConnectionError:
            logger.error(f"PROXY_CONNECTION_ERROR - Path: {route_path}{sub_path} | Target: {target_url}")
            return Response("Service unavailable", status=503)
        
        except Exception as e:
            logger.error(f"PROXY_ERROR - Path: {route_path}{sub_path} | Error: {str(e)}")
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
        """Prepare headers for the proxied request"""
        headers = {}
        
        # Copy most headers from original request
        excluded = ['host', 'connection', 'content-length']
        for header, value in request.headers:
            if header.lower() not in excluded:
                headers[header] = value
        
        # Add X-Forwarded headers
        headers['X-Forwarded-For'] = request.remote_addr
        headers['X-Forwarded-Proto'] = request.scheme
        headers['X-Forwarded-Host'] = request.host
        
        # Preserve host header if requested
        if route.get('preserve_host', False):
            headers['Host'] = request.host
        
        return headers
    
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
