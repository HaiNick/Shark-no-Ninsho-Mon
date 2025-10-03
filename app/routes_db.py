"""
TinyDB Route Manager - Database wrapper for managing reverse proxy routes
"""
from tinydb import TinyDB, Query
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import validators
import ipaddress
import re


class RouteManager:
    """Manage reverse proxy routes using TinyDB"""
    
    def __init__(self, db_path='routes.json'):
        self.db = TinyDB(db_path)
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
        self.validate_ip(target_ip)
        self.validate_port(target_port)
        
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
        
        self.routes.insert(route)
        return route
    
    def get_all_routes(self, enabled_only: bool = False) -> List[Dict]:
        """Get all routes"""
        if enabled_only:
            return self.routes.search(self.Route.enabled == True)
        return self.routes.all()
    
    def get_route_by_path(self, path: str) -> Optional[Dict]:
        """Get route by path"""
        result = self.routes.search(self.Route.path == path)
        return result[0] if result else None
    
    def get_route_by_id(self, route_id: str) -> Optional[Dict]:
        """Get route by ID"""
        result = self.routes.search(self.Route.id == route_id)
        return result[0] if result else None
    
    def update_route(self, route_id: str, updates: Dict) -> bool:
        """Update a route"""
        updates['updated_at'] = datetime.now().isoformat()
        result = self.routes.update(updates, self.Route.id == route_id)
        return len(result) > 0
    
    def delete_route(self, route_id: str) -> bool:
        """Delete a route"""
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
    def validate_port(port: int):
        """Validate port number"""
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError("Port must be between 1 and 65535")
