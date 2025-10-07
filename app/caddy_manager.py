"""
Caddy Manager - Syncs route configuration to Caddy Admin API
"""
import os
import json
import logging
from typing import List, Dict, Any
import requests

log = logging.getLogger(__name__)


class CaddyManager:
    """
    Pushes a computed Caddy JSON config to the Admin API.
    We build the full desired config from your route DB and PUT it to /config.
    """
    def __init__(self,
                 admin_url: str | None = None,
                 listen_port: int = 8080,
                 flask_upstream: str = "app:8000"):
        self.admin_url = admin_url or os.getenv("CADDY_ADMIN", "http://caddy:2019")
        self.listen_port = int(os.getenv("EDGE_PORT", listen_port))
        self.flask_upstream = flask_upstream

    def sync(self, routes: List[Dict[str, Any]]) -> dict:
        """
        Build a full config and PUT it to Caddy /config.
        routes: list of dicts like:
          {
            "path": "/jellyfin",
            "target_ip": "192.168.178.168",
            "target_port": 8096,
            "protocol": "http",
            "preserve_host": false,
            "enabled": true
          }
        """
        cfg = self._build_config(routes)
        url = f"{self.admin_url}/config"
        log.info("CADDY_SYNC PUT %s", url)
        r = requests.put(url, json=cfg, timeout=10)
        r.raise_for_status()
        return r.json() if r.headers.get("content-type","").startswith("application/json") else {"ok": True}

    def _build_config(self, routes: List[Dict[str, Any]]) -> dict:
        # Base server (root portal -> Flask UI)
        server = {
            "listen": [f":{self.listen_port}"],
            "allow_h2c": True,
            "routes": []
        }
        # 1) Keep root and static served by Flask UI
        server["routes"].append(self._flask_portal_route())

        # 2) Add one route per configured backend (mounted under subdir)
        for r in routes:
            if not r.get("enabled", True):
                continue
            mount = r.get("path") or r.get("route_path")
            if not mount or not mount.startswith("/"):
                # ignore invalid
                continue
            target_ip = r["target_ip"]
            target_port = r["target_port"]
            proto = r.get("protocol","http")
            preserve_host = bool(r.get("preserve_host", False))
            server["routes"].append(
                self._subdir_reverse_proxy_route(
                    mount, proto, f"{target_ip}:{target_port}", preserve_host=preserve_host
                )
            )

        return {
            "admin": { "listen": ":2019" },
            "apps": {
                "http": {
                    "servers": {
                        "srv0": server
                    }
                }
            }
        }

    def _flask_portal_route(self) -> dict:
        return {
            "match": [ { "path": ["/", "/static/*"] } ],
            "handle": [
                {
                    "handler": "reverse_proxy",
                    "upstreams": [ { "dial": self.flask_upstream } ],
                    "headers": {
                        "request": {
                            "set": {
                                "X-Forwarded-Prefix": ["/"],
                                "X-Forwarded-PathBase": ["/"]
                            }
                        }
                    }
                }
            ],
            "terminal": False
        }

    def _subdir_reverse_proxy_route(self, mount: str, proto: str, hostport: str, preserve_host: bool = False) -> dict:
        """
        Build a Caddy reverse_proxy route for a subdirectory mount.
        Do NOT strip the mount prefix; apps are made prefix-aware (Base URL),
        so they expect to see /mount/... at the backend.
        """
        match = { "path": [mount, f"{mount}/*"] }

        # Request headers to pass prefix info and optionally preserve Host
        set_headers = {
            "X-Forwarded-Prefix": [mount],
            "X-Forwarded-PathBase": [mount]
        }
        if preserve_host:
            # preserve incoming host for upstream if requested
            set_headers["Host"] = ["{http.request.host}"]

        handler = {
            "handler": "reverse_proxy",
            "upstreams": [ { "dial": f"{hostport}" } ],
            "headers": { "request": { "set": set_headers } },
            # Caddy handles WebSockets, HTTP/2, compression, buffering automatically
        }

        return {
            "match": [ match ],
            "handle": [ handler ],
            "terminal": True
        }
