"""
Caddy Manager - Syncs route configuration to Caddy Admin API
"""

import os
import json
import logging
import time
import socket
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import requests

log = logging.getLogger(__name__)


class CaddyManager:
    """
    Pushes a computed Caddy JSON config to the Admin API.
    We build the full desired config from your route DB and update /config/apps/http/servers/srv0/routes.
    """

    def __init__(
        self,
        admin_url: Optional[str] = None,
        listen_port: int = 8080,
        flask_upstream: str = "app:8000",
    ):
        self.admin_url = admin_url or os.getenv("CADDY_ADMIN", "http://caddy:2019")
        self.listen_port = int(os.getenv("EDGE_PORT", listen_port))
        self.flask_upstream = flask_upstream

    def sync(self, routes: List[Dict[str, Any]]) -> dict:
        """
        Build a full config and replace the routes array in Caddy.

        routes: list of dicts like:
          {
            "path": "/jellyfin",
            "target_ip": "192.168.178.168",
            "target_port": 8096,
            "protocol": "http",                  # or "https"
            "preserve_host": false,
            "no_upstream_compression": true,     # default true (adds Accept-Encoding: identity upstream)
            "force_content_encoding": "gzip",    # optional ("gzip" or "br") to fix stripped header cases
            "sni": "backend.example.internal",   # optional, when protocol=https
            "insecure_skip_verify": false,       # optional, when protocol=https
            "enabled": true
          }
        """
        cfg = self._build_config(routes)

        # Extract just the routes array
        routes_array = cfg["apps"]["http"]["servers"]["srv0"]["routes"]
        url = f"{self.admin_url}/config/apps/http/servers/srv0/routes"
        log.info(
            "CADDY_SYNC replacing %d backend routes + 1 flask route",
            max(0, len(routes_array) - 1),
        )
        log.debug("CADDY_SYNC routes JSON:\n%s", json.dumps(routes_array, indent=2))

        headers = {"Content-Type": "application/json"}

        # Strategy:
        # 1) Try PATCH with the full array (works on modern Caddy)
        # 2) If that fails (409/4xx), DELETE the key then PUT to recreate it
        r = requests.patch(url, json=routes_array, headers=headers, timeout=10)
        if not r.ok:
            log.warning(
                "CADDY_SYNC PATCH failed (%s). Falling back to DELETE+PUT. Body: %s",
                r.status_code,
                r.text[:400],
            )
            # Best-effort delete of the existing routes key
            try:
                d = requests.delete(url, timeout=10)
                log.info("CADDY_SYNC DELETE routes -> %s", d.status_code)
            except Exception as e:
                log.warning("CADDY_SYNC DELETE error: %s", e)

            r = requests.put(url, json=routes_array, headers=headers, timeout=10)

        if not r.ok:
            log.error("CADDY_SYNC final attempt failed: %s - %s", r.status_code, r.text)
        r.raise_for_status()
        log.info("CADDY_SYNC completed successfully")
        return {"ok": True}

    def _build_config(self, routes: List[Dict[str, Any]]) -> dict:
        # Base server (root portal -> Flask UI)
        server = {
            "listen": [f":{self.listen_port}"],
            "allow_h2c": True,
            "routes": [],
        }

        # 1) Add backend routes FIRST (longest mount first)
        backend_routes_added = 0
        sorted_routes = sorted(
            routes,
            key=lambda x: len((x.get("path") or x.get("route_path") or "")),
            reverse=True,
        )

        for r in sorted_routes:
            enabled = r.get("enabled", True)
            mount = r.get("path") or r.get("route_path")

            log.info("Processing route: path=%s, enabled=%s", mount, enabled)

            if not mount or not isinstance(mount, str) or not mount.startswith("/"):
                log.warning("Skipping invalid route path: %s", mount)
                continue

            if not enabled:
                # Add a redirect to the route-disabled page for disabled routes
                route_name = r.get("name", "")
                log.info("Adding disabled route redirect: %s -> /route-disabled", mount)
                server["routes"].append(
                    self._disabled_route_redirect(mount, route_name)
                )
                backend_routes_added += 1
                continue

            target_ip = r["target_ip"]
            target_port = r["target_port"]
            protocol = str(r.get("protocol", "http")).lower()
            preserve_host = bool(r.get("preserve_host", False))
            no_upstream_compression = bool(r.get("no_upstream_compression", True))
            sni = r.get("sni")
            insecure_skip_verify = bool(r.get("insecure_skip_verify", False))
            force_content_encoding = r.get("force_content_encoding")  # "gzip" or "br" or None

            log.info(
                "Adding backend route: %s -> %s://%s:%s",
                mount,
                protocol,
                target_ip,
                target_port,
            )

            server["routes"].append(
                self._subdir_reverse_proxy_route(
                    mount=mount,
                    protocol=protocol,
                    hostport=f"{target_ip}:{target_port}",
                    preserve_host=preserve_host,
                    no_upstream_compression=no_upstream_compression,
                    sni=sni,
                    insecure_skip_verify=insecure_skip_verify,
                    force_content_encoding=force_content_encoding,
                )
            )
            backend_routes_added += 1

        log.info("Added %d backend routes to Caddy config", backend_routes_added)

        # 2) Add Flask portal route LAST (catch-all for root and static)
        server["routes"].append(self._flask_portal_route())

        return {
            "admin": {"listen": ":2019"},
            "apps": {"http": {"servers": {"srv0": server}}},
        }

    def _flask_portal_route(self) -> dict:
        """
        Flask portal catches root UI paths and API routes.
        This is added LAST so backend routes are checked first.
        NOTE: terminal=False allows fall-through if no Flask route matches.
        """
        return {
            "match": [
                {
                    "path": [
                        "/",
                        "/admin",
                        "/admin/*",
                        "/api/*",
                        "/static/*",
                        "/health",
                        "/logs",
                        "/route-disabled",
                        "/unauthorized",
                        "/emails",
                        "/favicon.ico",
                    ]
                }
            ],
            "handle": [
                {
                    "handler": "reverse_proxy",
                    "upstreams": [{"dial": self.flask_upstream}],
                    "headers": {
                        "request": {
                            "set": {
                                "X-Forwarded-Prefix": ["/"],
                                "X-Forwarded-PathBase": ["/"],
                            }
                        }
                    },
                }
            ],
            "terminal": False,
        }

    def _disabled_route_redirect(self, mount: str, route_name: str = "") -> dict:
        """
        Create a redirect handler for disabled routes.
        Redirects users to the route-disabled page with path and name parameters.
        """
        from urllib.parse import quote
        
        # URL encode the parameters
        encoded_path = quote(mount, safe='')
        encoded_name = quote(route_name, safe='')
        redirect_url = f"/route-disabled?path={encoded_path}&name={encoded_name}"
        
        return {
            "match": [{"path": [mount, f"{mount}/*"]}],
            "handle": [
                {
                    "handler": "static_response",
                    "status_code": 302,
                    "headers": {
                        "Location": [redirect_url]
                    }
                }
            ],
            "terminal": True,
        }

    def _subdir_reverse_proxy_route(
        self,
        mount: str,
        protocol: str,
        hostport: str,
        preserve_host: bool = False,
        no_upstream_compression: bool = True,
        sni: Optional[str] = None,
        insecure_skip_verify: bool = False,
        force_content_encoding: Optional[str] = None,  # e.g. "gzip" or "br"
    ) -> dict:
        """
        Build a Caddy reverse_proxy route for a subdirectory mount.
        Passes the full path to the backend - apps should be configured with Base URL.
        """

        match = {"path": [mount, f"{mount}/*"]}

        # Request headers to pass prefix info and optionally preserve Host
        set_headers: Dict[str, List[str]] = {
            "X-Forwarded-Prefix": [mount],
            "X-Forwarded-PathBase": [mount],
            "X-Forwarded-Proto": ["{http.request.scheme}"],
            "X-Forwarded-For": ["{http.request.remote.host}"],
        }

        # Avoid upstream compression if requested (prevents gibberish when Content-Encoding is mangled)
        if no_upstream_compression:
            set_headers["Accept-Encoding"] = ["identity"]

        if preserve_host:
            # preserve incoming host for upstream if requested
            set_headers["Host"] = ["{http.request.host}"]

        headers_block: Dict[str, Any] = {"request": {"set": set_headers}}

        # If we know the upstream is sending compressed bytes and some hop strips the header,
        # force the Content-Encoding on the response so clients decode correctly.
        if force_content_encoding:
            headers_block["response"] = {
                "set": {
                    "Content-Encoding": [force_content_encoding],
                    "Vary": ["Accept-Encoding"],
                }
            }

        handler: Dict[str, Any] = {
            "handler": "reverse_proxy",
            "upstreams": [{"dial": hostport}],
            "headers": headers_block,
        }

        # Honor HTTPS upstreams by enabling TLS on the transport
        if protocol == "https":
            tls_cfg: Dict[str, Any] = {}
            if sni:
                tls_cfg["server_name"] = sni
            if insecure_skip_verify:
                tls_cfg["insecure_skip_verify"] = True
            handler["transport"] = {"protocol": "http", "tls": tls_cfg}

        return {"match": [match], "handle": [handler], "terminal": True}

    def classify_service_status(self, url: str, timeout_sec: int = 3, slow_ms: int = 2000) -> Tuple[str, str, Optional[str], Optional[int], Optional[int]]:
        """
        Classify service status using a deterministic decision tree.
        
        Returns: (state, reason, detail_message, http_status, duration_ms)
        
        States: UP, DEGRADED, DOWN, UNKNOWN
        Reasons: online, slow, error_5xx, timeout, offline_conn, offline_dns, misconfig, error_exc, unknown
        """
        # 1) Input sanity
        try:
            u = urlparse(url)
            if not (u.scheme and u.hostname):
                return ("DOWN", "misconfig", "Invalid URL components: missing scheme or hostname", None, None)
            # Port validation - use default ports if not specified
            port = u.port
            if port is None:
                port = 443 if u.scheme == 'https' else 80
        except Exception as e:
            return ("DOWN", "misconfig", f"URL parse error: {e}", None, None)

        # 2) DNS resolve
        try:
            socket.getaddrinfo(u.hostname, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as e:
            return ("DOWN", "offline_dns", f"DNS error: {e}", None, None)

        # 3) TCP connect (fast fail)
        try:
            with socket.create_connection((u.hostname, port), timeout=min(timeout_sec, 10)):
                pass
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            return ("DOWN", "offline_conn", f"TCP connect failed: {e}", None, None)

        # 4) HTTP request
        try:
            start = time.perf_counter()
            resp = requests.get(url, timeout=timeout_sec, allow_redirects=True, verify=False)
            dur_ms = int((time.perf_counter() - start) * 1000)

            if resp.status_code >= 500:
                return ("DOWN", "error_5xx", f"HTTP {resp.status_code} in {dur_ms} ms", resp.status_code, dur_ms)
            if dur_ms > slow_ms:
                return ("DEGRADED", "slow", f"HTTP {resp.status_code} in {dur_ms} ms", resp.status_code, dur_ms)
            return ("UP", "online", f"HTTP {resp.status_code} in {dur_ms} ms", resp.status_code, dur_ms)

        except requests.exceptions.Timeout:
            return ("DOWN", "timeout", f"HTTP timeout after {timeout_sec}s", None, None)
        except Exception as e:
            return ("DOWN", "error_exc", f"Unexpected error: {e}", None, None)

    def test_connection(self, route: Dict[str, Any]) -> dict:
        """
        Test connectivity to a backend service using enhanced classification.

        Args:
            route: Route dict with fields:
                - target_ip (str), target_port (int)
                - protocol (str: http|https)
                - timeout (int, seconds) optional
                - health_path (str) optional, default '/'
                - verify_tls (bool) optional (https only, default True unless insecure_skip_verify)
                - insecure_skip_verify (bool) optional (https only)
                - sni (str) optional, only used to build URL host if provided

        Returns:
            dict with success, status (legacy), state, reason, status_code, response_time, error, and detail
        """
        target_ip = route["target_ip"]
        target_port = route["target_port"]
        protocol = str(route.get("protocol", "http")).lower()
        timeout = int(route.get("timeout", 30))
        health_path = route.get("health_path", "/")
        insecure_skip_verify = bool(route.get("insecure_skip_verify", False))
        sni = route.get("sni")

        # Build URL; for HTTPS we prefer a hostname when available (better for cert/SNI validation)
        host_for_url = sni if (protocol == "https" and sni) else target_ip
        target_url = f"{protocol}://{host_for_url}:{target_port}{health_path}"

        # Get slow threshold from config or use default
        from config import get_settings
        settings = get_settings()
        timeout_sec = min(timeout, settings.http_timeout_sec)
        slow_ms = settings.slow_threshold_ms

        # Use new classification logic
        state, reason, detail, http_status, duration_ms = self.classify_service_status(
            target_url, timeout_sec, slow_ms
        )

        # Map state to legacy status for backward compatibility
        legacy_status_map = {
            "UP": "online",
            "DEGRADED": "slow",
            "DOWN": "offline",
            "UNKNOWN": "unknown"
        }
        
        # For DOWN state, check reason for more specific legacy status
        if state == "DOWN":
            if reason in ["error_5xx", "error_exc"]:
                legacy_status = "error"
            elif reason == "timeout":
                legacy_status = "timeout"
            else:
                legacy_status = "offline"
        else:
            legacy_status = legacy_status_map.get(state, "unknown")

        success = state in ["UP", "DEGRADED"]

        result = {
            "success": success,
            "status": legacy_status,  # Legacy field
            "state": state,           # New field
            "reason": reason,         # New field
            "detail": detail,         # New field
        }

        if http_status is not None:
            result["status_code"] = http_status
        if duration_ms is not None:
            result["response_time"] = duration_ms
        if not success and detail:
            result["error"] = detail

        return result
