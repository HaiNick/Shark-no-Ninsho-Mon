"""
SQLite Route Manager - Database wrapper for managing reverse proxy routes
"""
import sqlite3
import json
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import ipaddress
import re
from pathlib import Path

# Columns stored as booleans (INTEGER 0/1 in SQLite)
_BOOL_COLUMNS = {'enabled', 'health_check', 'preserve_host', 'websocket'}

# All columns in insertion order (matches CREATE TABLE)
_COLUMNS = [
    'id', 'path', 'name', 'target_ip', 'target_port', 'target_path',
    'protocol', 'enabled', 'health_check', 'timeout', 'preserve_host',
    'websocket', 'status', 'state', 'reason', 'http_status', 'duration_ms',
    'last_error', 'last_check', 'retries_used', 'created_at', 'updated_at',
]


def _row_to_dict(row: sqlite3.Row) -> Dict:
    """Convert a sqlite3.Row to a plain dict with proper bool coercion."""
    d = dict(row)
    for col in _BOOL_COLUMNS:
        if col in d:
            d[col] = bool(d[col]) if d[col] is not None else False
    return d


class RouteManager:
    """Manage reverse proxy routes using SQLite"""

    def __init__(self, db_path='routes.json'):
        path = Path(db_path)

        # If the path ends in .json, swap extension to .db
        if path.suffix == '.json':
            path = path.with_suffix('.db')
        elif path.suffix != '.db':
            path = Path(str(path) + '.db')

        if path.is_dir():
            try:
                next(path.iterdir())
            except StopIteration:
                # Empty directory -> replace with file
                path.rmdir()
            else:
                # Directory already in use -> store inside it
                path = path / 'routes.db'

        path.parent.mkdir(parents=True, exist_ok=True)

        self._db_path = str(path)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute('PRAGMA journal_mode=WAL')
        self._create_table()

    def _create_table(self):
        self._conn.execute('''
            CREATE TABLE IF NOT EXISTS routes (
                id            TEXT PRIMARY KEY,
                path          TEXT NOT NULL UNIQUE,
                name          TEXT NOT NULL,
                target_ip     TEXT NOT NULL,
                target_port   INTEGER NOT NULL,
                target_path   TEXT NOT NULL DEFAULT '',
                protocol      TEXT NOT NULL DEFAULT 'http',
                enabled       INTEGER NOT NULL DEFAULT 1,
                health_check  INTEGER NOT NULL DEFAULT 1,
                timeout       INTEGER NOT NULL DEFAULT 30,
                preserve_host INTEGER NOT NULL DEFAULT 0,
                websocket     INTEGER NOT NULL DEFAULT 0,
                status        TEXT DEFAULT 'unknown',
                state         TEXT DEFAULT 'UNKNOWN',
                reason        TEXT DEFAULT 'unknown',
                http_status   INTEGER,
                duration_ms   INTEGER,
                last_error    TEXT,
                last_check    TEXT,
                retries_used  INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL
            )
        ''')
        self._conn.execute('CREATE INDEX IF NOT EXISTS idx_routes_path ON routes (path)')
        self._conn.execute('CREATE INDEX IF NOT EXISTS idx_routes_enabled ON routes (enabled)')
        self._conn.commit()

    def add_route(self, path: str, name: str, target_ip: str,
                  target_port: int, protocol: str = 'http',
                  enabled: bool = True, health_check: bool = True,
                  timeout: int = 30, preserve_host: bool = False,
                  websocket: bool = False, target_path: str = '') -> Dict:
        """Add a new route"""
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
        target_path = self.validate_target_path(target_path)

        # Check for duplicate path
        if self.get_route_by_path(path):
            raise ValueError(f"Route with path '{path}' already exists")

        now = datetime.now().isoformat()
        route = {
            'id': str(uuid.uuid4()),
            'path': path,
            'name': name,
            'target_ip': target_ip,
            'target_port': target_port,
            'target_path': target_path,
            'protocol': protocol,
            'enabled': enabled,
            'health_check': health_check,
            'timeout': timeout,
            'preserve_host': preserve_host,
            'websocket': websocket,
            'status': 'unknown',
            'state': 'UNKNOWN',
            'reason': 'unknown',
            'http_status': None,
            'duration_ms': None,
            'last_error': None,
            'last_check': None,
            'retries_used': 0,
            'created_at': now,
            'updated_at': now,
        }

        placeholders = ', '.join('?' for _ in _COLUMNS)
        col_names = ', '.join(_COLUMNS)
        values = [int(route[c]) if c in _BOOL_COLUMNS else route[c] for c in _COLUMNS]

        with self._conn:
            self._conn.execute('BEGIN IMMEDIATE')
            self._conn.execute(
                f'INSERT INTO routes ({col_names}) VALUES ({placeholders})', values
            )

        return route

    def get_all_routes(self, enabled_only: bool = False) -> List[Dict]:
        """Get all routes"""
        if enabled_only:
            rows = self._conn.execute('SELECT * FROM routes WHERE enabled = 1').fetchall()
        else:
            rows = self._conn.execute('SELECT * FROM routes').fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_route_by_path(self, path: str) -> Optional[Dict]:
        """Get route by path"""
        row = self._conn.execute('SELECT * FROM routes WHERE path = ?', (path,)).fetchone()
        return _row_to_dict(row) if row else None

    def get_route_by_id(self, route_id: str) -> Optional[Dict]:
        """Get route by ID"""
        row = self._conn.execute('SELECT * FROM routes WHERE id = ?', (route_id,)).fetchone()
        return _row_to_dict(row) if row else None

    def update_route(self, route_id: str, updates: Dict) -> bool:
        """Update a route"""
        if not updates:
            return False

        sanitized = self._sanitize_updates(updates)
        if not sanitized:
            return False

        sanitized['updated_at'] = datetime.now().isoformat()

        set_clauses = []
        values = []
        for key, val in sanitized.items():
            set_clauses.append(f'{key} = ?')
            values.append(int(val) if key in _BOOL_COLUMNS else val)
        values.append(route_id)

        with self._conn:
            self._conn.execute('BEGIN IMMEDIATE')
            cur = self._conn.execute(
                f'UPDATE routes SET {", ".join(set_clauses)} WHERE id = ?', values
            )
            return cur.rowcount > 0

    def delete_route(self, route_id: str) -> bool:
        """Delete a route"""
        with self._conn:
            self._conn.execute('BEGIN IMMEDIATE')
            cur = self._conn.execute('DELETE FROM routes WHERE id = ?', (route_id,))
            return cur.rowcount > 0

    def update_route_status(self, route_id: str, status: str = None, last_check: str = None,
                            state: str = None, reason: str = None, http_status: int = None,
                            duration_ms: int = None, last_error: str = None, retries_used: int = None):
        """Update route health status with enhanced fields"""
        updates = {
            'last_check': last_check or datetime.now().isoformat()
        }

        # Support legacy status field for backward compatibility
        if status is not None:
            updates['status'] = status

        # New enhanced status fields
        if state is not None:
            updates['state'] = state
        if reason is not None:
            updates['reason'] = reason
        if http_status is not None:
            updates['http_status'] = http_status
        if duration_ms is not None:
            updates['duration_ms'] = duration_ms
        if last_error is not None:
            updates['last_error'] = last_error
        if retries_used is not None:
            updates['retries_used'] = retries_used

        return self.update_route(route_id, updates)

    def search_routes(self, query: str) -> List[Dict]:
        """Search routes by name or path (case-insensitive)"""
        pattern = f'%{query}%'
        rows = self._conn.execute(
            'SELECT * FROM routes WHERE name LIKE ? OR path LIKE ?',
            (pattern, pattern)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    
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
    
    BLOCKED_IPS = {
        '169.254.169.254',  # AWS/GCP/Azure (IPv4)
        'fd00:ec2::254',    # AWS (IPv6)
        '100.100.100.200',  # Alibaba Cloud
        '169.254.0.23',     # OpenStack
    }

    @staticmethod
    def validate_ip(ip: str):
        """Validate IP address - only allow private IPs"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Block localhost
            if ip_obj.is_loopback:
                raise ValueError("Localhost IPs are not allowed")
            
            # Block link-local addresses
            if ip_obj.is_link_local:
                raise ValueError("Link-local IPs are not allowed")
            
            # Block cloud metadata endpoints
            if str(ip_obj) in RouteManager.BLOCKED_IPS:
                raise ValueError("Cloud metadata IPs are not allowed")
            
            # Block reserved addresses
            if ip_obj.is_reserved:
                raise ValueError("Reserved IPs are not allowed")
            
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

    @staticmethod
    def validate_target_path(target_path: str) -> str:
        """Validate and sanitize target path."""
        if not target_path or not str(target_path).strip():
            return '/'
        path = str(target_path).strip()
        if not path.startswith('/'):
            path = '/' + path
        if '..' in path:
            raise ValueError("Invalid target path: '..' is not allowed")
        if '//' in path:
            raise ValueError("Invalid target path: '//' is not allowed")
        if not re.match(r'^/[a-zA-Z0-9/_.\-]*$', path):
            raise ValueError("Target path contains invalid characters")
        return path

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

        if 'target_path' in updates:
            sanitized['target_path'] = self.validate_target_path(updates['target_path'])

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

        if 'state' in updates:
            sanitized['state'] = str(updates['state'])

        if 'reason' in updates:
            sanitized['reason'] = str(updates['reason'])

        if 'http_status' in updates:
            sanitized['http_status'] = updates['http_status']

        if 'duration_ms' in updates:
            sanitized['duration_ms'] = updates['duration_ms']

        if 'last_error' in updates:
            sanitized['last_error'] = updates['last_error']

        if 'retries_used' in updates:
            sanitized['retries_used'] = updates['retries_used']

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
