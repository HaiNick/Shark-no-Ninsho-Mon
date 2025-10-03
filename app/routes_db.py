"""
TinyDB Route Manager - Database wrapper for managing reverse proxy routes
"""
from tinydb import TinyDB, Query
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import ipaddress
import re
import threading
from pathlib import Path


class RouteManager:
    """Manage reverse proxy routes using TinyDB"""
    
    def __init__(self, db_path='routes.json'):
        original_path = Path(db_path)
        path = original_path

        if path.is_dir():
            try:
                next(path.iterdir())
            except StopIteration:
                # Empty directory -> replace with file
                path.rmdir()
            else:
                # Directory already in use -> store inside it
                path = path / 'routes.json'

        path.parent.mkdir(parents=True, exist_ok=True)

        if not path.exists():
            path.write_text('{"_default": {}}', encoding='utf-8')

        self._lock = threading.RLock()
        self.db = TinyDB(str(path))
        self.routes = self.db.table('routes')
        self.Route = Query()
    
    def add_route(self, path: str, name: str, target_ip: str,
                  target_port: int, protocol: str = 'http',
                  enabled: bool = True, health_check: bool = True,
                  timeout: int = 30, preserve_host: bool = False,
                  websocket: bool = False) -> Dict:
        """Add a new route"""
        # Validate inputs
        path = self.validate_path(path)
        name = self.validate_name(name)
        self.validate_ip(target_ip)
        target_port = self.validate_port(target_port)
        protocol = self.validate_protocol(protocol)
        timeout = self.validate_timeout(timeout)
        preserve_host = self._coerce_bool(preserve_host)
        websocket = self._coerce_bool(websocket)
        enabled = self._coerce_bool(enabled)
        health_check = self._coerce_bool(health_check)
        
        # Check for duplicate path
        if self.get_route_by_path(path):
            raise ValueError(f"Route with path '{path}' already exists")
        
        route = {
            'id': str(uuid.uuid4()),
            'path': path,
            'name': name,
            'target_ip': target_ip,
            'target_port': target_port,
            'protocol': protocol,
            'enabled': enabled,
            'health_check': health_check,
            'timeout': timeout,
            'preserve_host': preserve_host,
            'websocket': websocket,
            'status': 'unknown',
            'last_check': None,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        with self._lock:
            self.routes.insert(route)
            return route
    
    def get_all_routes(self, enabled_only: bool = False) -> List[Dict]:
        """Get all routes"""
        with self._lock:
            if enabled_only:
                return self.routes.search(self.Route.enabled == True)
            return self.routes.all()
    
    def get_route_by_path(self, path: str) -> Optional[Dict]:
        """Get route by path"""
        with self._lock:
            result = self.routes.search(self.Route.path == path)
            return result[0] if result else None
    
    def get_route_by_id(self, route_id: str) -> Optional[Dict]:
        """Get route by ID"""
        with self._lock:
            result = self.routes.search(self.Route.id == route_id)
            return result[0] if result else None
    
    def update_route(self, route_id: str, updates: Dict) -> bool:
        """Update a route"""
        if not updates:
            return False

        sanitized = self._sanitize_updates(updates)
        if not sanitized:
            return False

        sanitized['updated_at'] = datetime.now().isoformat()

        with self._lock:
            result = self.routes.update(sanitized, self.Route.id == route_id)
            return len(result) > 0
    
    def delete_route(self, route_id: str) -> bool:
        """Delete a route"""
        with self._lock:
            result = self.routes.remove(self.Route.id == route_id)
            return len(result) > 0
    
    def update_route_status(self, route_id: str, status: str, last_check: str = None):
        """Update route health status"""
        updates = {
            'status': status,
            'last_check': last_check or datetime.now().isoformat()
        }
        return self.update_route(route_id, updates)
    
    def search_routes(self, query: str) -> List[Dict]:
        """Search routes by name or path"""
        query = query.lower()
        with self._lock:
            return self.routes.search(
                (self.Route.name.search(query, flags=re.IGNORECASE)) |
                (self.Route.path.search(query, flags=re.IGNORECASE))
            )
    
    @staticmethod
    def validate_path(path: str) -> str:
        """Validate and sanitize route path"""
        if not path:
            raise ValueError("Path cannot be empty")
        
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
        
        # Remove trailing slash
        if len(path) > 1 and path.endswith('/'):
            path = path[:-1]
        
        # Only allow alphanumeric, dash, underscore, and forward slash
        if not re.match(r'^/[a-zA-Z0-9/_-]+$', path):
            raise ValueError("Path must contain only alphanumeric characters, dash, underscore, and forward slash")
        
        return path

    @staticmethod
    def validate_name(name: str) -> str:
        """Ensure the route name is a non-empty string."""
        if not isinstance(name, str):
            raise ValueError("Name must be a string")
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty")
        return cleaned
    
    @staticmethod
    def validate_ip(ip: str):
        """Validate IP address - only allow private IPs"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Block localhost
            if ip_obj.is_loopback:
                raise ValueError("Localhost IPs are not allowed")
            
            # Block cloud metadata endpoints
            if str(ip) == '169.254.169.254':
                raise ValueError("Cloud metadata IP is not allowed")
            
            # Only allow private IPs
            if not ip_obj.is_private:
                raise ValueError("Only private IP addresses are allowed (10.x.x.x, 192.168.x.x, 172.16-31.x.x)")
            
        except ValueError as e:
            raise ValueError(f"Invalid IP address: {e}")
    
    @staticmethod
    def validate_port(port: int) -> int:
        """Validate port number and return the coerced int."""
        try:
            coerced = int(port)
        except (TypeError, ValueError):
            raise ValueError("Port must be between 1 and 65535") from None

        if coerced < 1 or coerced > 65535:
            raise ValueError("Port must be between 1 and 65535")
        return coerced

    @staticmethod
    def validate_timeout(timeout: int) -> int:
        """Validate timeout seconds and return coerced int."""
        try:
            coerced = int(timeout)
        except (TypeError, ValueError):
            raise ValueError("Timeout must be a positive integer") from None

        if coerced < 1:
            raise ValueError("Timeout must be a positive integer")
        return coerced

    @staticmethod
    def validate_protocol(protocol: str) -> str:
        """Ensure protocol is supported."""
        if not isinstance(protocol, str):
            raise ValueError("Protocol must be a string")
        value = protocol.strip().lower()
        if value not in {"http", "https"}:
            raise ValueError("Protocol must be either 'http' or 'https'")
        return value

    def _sanitize_updates(self, updates: Dict) -> Dict:
        """Whitelist and validate update fields."""
        sanitized: Dict = {}

        if 'path' in updates:
            sanitized['path'] = self.validate_path(updates['path'])

        if 'name' in updates:
            sanitized['name'] = self.validate_name(updates['name'])

        if 'target_ip' in updates:
            self.validate_ip(updates['target_ip'])
            sanitized['target_ip'] = updates['target_ip']

        if 'target_port' in updates:
            sanitized['target_port'] = self.validate_port(updates['target_port'])

        if 'protocol' in updates:
            sanitized['protocol'] = self.validate_protocol(updates['protocol'])

        if 'timeout' in updates:
            sanitized['timeout'] = self.validate_timeout(updates['timeout'])

        if 'preserve_host' in updates:
            sanitized['preserve_host'] = self._coerce_bool(updates['preserve_host'])

        if 'websocket' in updates:
            sanitized['websocket'] = self._coerce_bool(updates['websocket'])

        if 'enabled' in updates:
            sanitized['enabled'] = self._coerce_bool(updates['enabled'])

        if 'health_check' in updates:
            sanitized['health_check'] = self._coerce_bool(updates['health_check'])

        if 'status' in updates:
            sanitized['status'] = str(updates['status'])

        if 'last_check' in updates:
            sanitized['last_check'] = updates['last_check']

        return sanitized

    @staticmethod
    def _coerce_bool(value) -> bool:
        """Coerce typical truthy/falsey JSON values into booleans."""
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).strip().lower() in {'1', 'true', 't', 'yes', 'on'}
