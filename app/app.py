"""
Shark-no-Ninsho-Mon - OAuth2 Authentication Gateway with Reverse Proxy Route Manager
"""
from flask import Flask, render_template, request, jsonify, Response, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_talisman import Talisman
import logging
import fcntl
import contextlib
import uuid
from datetime import datetime
import os
import hashlib
import hmac
import threading
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Dict, Set
import collections
import re

from config import get_settings

# Load environment variables from .env file
load_dotenv()

from routes_db import RouteManager
from caddy_manager import CaddyManager
from constants import Limits, RateLimits
from errors import AppError

# In-memory log storage for the web interface
log_entries = collections.deque(maxlen=Limits.MAX_LOG_ENTRIES)

class MemoryLogHandler(logging.Handler):
    """Custom log handler to store logs in memory for web interface"""
    def emit(self, record):
        try:
            # Only store important log levels to reduce memory usage
            if record.levelno >= logging.INFO:
                # Store minimal data to reduce memory footprint
                log_entries.append({
                    'timestamp': datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
                    'level': record.levelname,
                    'message': record.getMessage()[:Limits.LOG_MESSAGE_MAX_LEN]
                })
        except Exception:
            self.handleError(record)

    # Configure logging
logging.basicConfig(
    level=logging.INFO,  # Back to INFO level, but we'll log IP detection results
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add memory handler to capture logs for web interface
memory_handler = MemoryLogHandler()
memory_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(memory_handler)

# Initialize Flask app
app = Flask(__name__)

settings = get_settings()
app.config['SECRET_KEY'] = settings.secret_key

# Configure Flask session cookies
app.config['SESSION_COOKIE_SECURE'] = settings.session_cookie_secure
app.config['SESSION_COOKIE_HTTPONLY'] = settings.session_cookie_httponly
app.config['SESSION_COOKIE_SAMESITE'] = settings.session_cookie_samesite
app.config['PERMANENT_SESSION_LIFETIME'] = settings.permanent_session_lifetime

# Initialize rate limiter
# No default limits - apply specific limits only to sensitive endpoints
limiter = Limiter(
    app=app,
    key_func=lambda: request.remote_addr,
    default_limits=[],
    storage_uri="memory://"
)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Security headers via Flask-Talisman
# force_https=False because TLS is handled by Caddy/Tailscale at the edge
Talisman(app, content_security_policy=False, force_https=False)


@app.after_request
def inject_csrf(response):
    """Inject CSRF token header for JavaScript clients."""
    response.headers['X-CSRF-Token'] = generate_csrf()
    return response


@app.before_request
def add_request_id():
    """Assign a request ID for log correlation."""
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))


@app.after_request
def return_request_id(response):
    """Return the request ID on every response."""
    response.headers['X-Request-ID'] = g.get('request_id', '')
    return response

# Initialize route manager and Caddy manager
route_manager = RouteManager(settings.routes_db_path)
caddy_mgr = CaddyManager()  # uses http://caddy:2019 and :8080 by default

# Shared secret for OAuth2 proxy header validation (defence-in-depth)
PROXY_SECRET = os.environ.get('OAUTH_PROXY_SHARED_SECRET')


def is_dev_mode() -> bool:
    """Check if application is running in development mode."""
    return os.environ.get('FLASK_ENV') == 'development' or os.environ.get('DEV_MODE', '').lower() == 'true'


def validate_proxy_request() -> bool:
    """Validate that the request came through the OAuth2 proxy using a shared secret."""
    if is_dev_mode():
        return True
    sig = request.headers.get('X-Auth-Request-Signature')
    if not sig or not PROXY_SECRET:
        return False
    expected = hmac.new(PROXY_SECRET.encode(), request.path.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


@contextlib.contextmanager
def locked_file(path, mode='r'):
    """Open a file with an exclusive lock for atomic reads/writes."""
    with open(path, mode, encoding='utf-8') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def is_valid_email(email: str) -> bool:
    """Validate email format with RFC 5321 length checks"""
    if not email or not isinstance(email, str):
        return False
    addr = email.strip()
    # RFC 5321 total length
    if len(addr) > 254:
        return False
    parts = addr.split('@')
    if len(parts) != 2:
        return False
    local, domain = parts
    # Local part max 64 chars
    if len(local) > 64 or not local:
        return False
    # Reject consecutive dots
    if '..' in local or '..' in domain:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, addr) is not None

def _load_authorized_emails(path: str) -> Set[str]:
    emails: Set[str] = set()

    original_path = Path(path)
    path_obj = original_path

    if path_obj.is_dir():
        try:
            next(path_obj.iterdir())
        except StopIteration:
            path_obj.rmdir()
            path_obj = original_path
        else:
            path_obj = path_obj / 'emails.txt'

    path_obj.parent.mkdir(parents=True, exist_ok=True)

    if not path_obj.exists():
        path_obj.touch()
        logger.info(f"Created missing emails file at: {path_obj}")

    try:
        with locked_file(str(path_obj), 'r') as handle:
            for line in handle:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    emails.add(stripped.lower())
    except OSError as exc:
        logger.error(f"Failed to load emails file '{path}': {exc}")

    return emails


def refresh_authorized_emails() -> int:
    """Reload authorized emails from disk."""
    global AUTHORIZED_EMAILS
    AUTHORIZED_EMAILS = _load_authorized_emails(settings.emails_file)
    logger.info(f"Loaded {len(AUTHORIZED_EMAILS)} authorized emails")
    return len(AUTHORIZED_EMAILS)


AUTHORIZED_EMAILS: Set[str] = set()
refresh_authorized_emails()


def parse_bool(value: Any, default: bool = False) -> bool:
    """Best effort boolean parsing for JSON payloads."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {'1', 'true', 't', 'yes', 'on'}


def get_user_email() -> str:
    """Get user email from OAuth2 proxy headers"""
    # In production, validate that the request came through the proxy
    if not is_dev_mode() and PROXY_SECRET and not validate_proxy_request():
        return ''

    # Try multiple header variations that oauth2-proxy might use
    email = (
        request.headers.get('X-Forwarded-Email') or
        request.headers.get('X-Auth-Request-Email') or
        request.headers.get('X-Forwarded-User') or
        ''
    ).lower().strip()
    
    # Development mode fallback
    if not email and is_dev_mode():
        return 'dev@localhost'
    
    return email


def is_authorized() -> bool:
    """Check if user is authorized"""
    # Development mode bypass
    if is_dev_mode():
        return True
    
    email = get_user_email()
    return email in AUTHORIZED_EMAILS


# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard"""
    email = get_user_email()
    
    if not is_authorized():
        logger.warning(f"UNAUTHORIZED ACCESS - Email: {email} | Authorized emails: {len(AUTHORIZED_EMAILS)}")
        return render_template('unauthorized.html', email=email), 403
    
    # Get all routes (both enabled and disabled) to display on dashboard
    routes = route_manager.get_all_routes(enabled_only=False)
    
    logger.info(f"ACCESS - User: {email} | Path: /")
    
    return render_template('index.html', email=email, routes=routes)


@app.route('/admin')
def admin():
    """Route management admin page"""
    email = get_user_email()
    
    if not is_authorized():
        return render_template('unauthorized.html', email=email), 403
    
    logger.info(f"ACCESS - User: {email} | Path: /admin")
    
    return render_template('admin.html', email=email)


@app.route('/health')
@limiter.exempt
@csrf.exempt
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'routes_count': len(route_manager.get_all_routes())
    })

@app.route('/logs')
def logs():
    """Display application logs"""
    email = get_user_email()
    
    if not is_authorized():
        return render_template('unauthorized.html', email=email), 403
    
    logger.info(f"ACCESS - User: {email} | Path: /logs")
    
    return render_template('logs.html', email=email)


@app.route('/emails')
def emails():
    """Email management page"""
    email = get_user_email()
    
    if not is_authorized():
        return render_template('unauthorized.html', email=email), 403
    
    logger.info(f"ACCESS - User: {email} | Path: /emails")
    
    return render_template('emails.html', email=email)


@app.route('/route-disabled')
def route_disabled():
    """Route disabled page"""
    email = get_user_email()
    
    if not is_authorized():
        return render_template('unauthorized.html', email=email), 403
    
    route_path = request.args.get('path', 'Unknown Route')
    route_name = request.args.get('name', '')
    
    logger.info(f"ROUTE_DISABLED - User: {email} | Path: {route_path}")
    
    return render_template('route_disabled.html', 
                         email=email, 
                         route_path=route_path, 
                         route_name=route_name)


@app.route('/api/logs', methods=['GET'])
@limiter.limit("30 per minute")
def api_get_logs():
    """Get recent log entries"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Get recent log entries from memory (already limited to 200 entries)
        recent_entries = list(log_entries)
        
        # Format entries for display - simple and fast
        formatted_logs = []
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        for entry in recent_entries:
            formatted_logs.append(f"[{current_date} {entry['timestamp']}] {entry['level']} - {entry['message']}")
        
        logger.info(f"LOGS_ACCESS - User: {email} | Entries: {len(formatted_logs)}")
        
        return jsonify({
            'logs': formatted_logs,
            'count': len(formatted_logs),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error reading logs: {str(e)}")
        return jsonify({
            'logs': [f"Error reading logs: {str(e)}"],
            'count': 1,
            'timestamp': datetime.now().isoformat()
        })


# ============================================================================
# ROUTE MANAGEMENT API
# ============================================================================

@app.route('/api/routes', methods=['GET'])
@limiter.limit("100 per hour")
def api_get_routes():
    """Get all routes"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    routes = route_manager.get_all_routes()
    return jsonify(routes)


@app.route('/api/routes', methods=['POST'])
@limiter.limit("50 per hour")
def api_create_route():
    """Create a new route"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    
    try:
        route = route_manager.add_route(
            path=data.get('path'),
            name=data.get('name'),
            target_ip=data.get('target_ip'),
            target_port=data.get('target_port'),
            target_path=data.get('target_path', '/'),
            protocol=data.get('protocol', 'http'),
            enabled=parse_bool(data.get('enabled', True), True),
            health_check=parse_bool(data.get('health_check', True), True),
            timeout=data.get('timeout', 30),
            preserve_host=parse_bool(data.get('preserve_host', False)),
            websocket=parse_bool(data.get('websocket', False))
        )
        
        logger.info(f"ROUTE_ADD - User: {email} | Path: {route['path']} | Target: {route['target_ip']}:{route['target_port']}")
        
        # After DB change, resync Caddy
        try:
            routes = route_manager.get_all_routes()
            caddy_mgr.sync(routes)
        except Exception as e:
            logger.exception("CADDY_SYNC after add failed: %s", e)
        
        return jsonify(route), 201
    
    except ValueError as e:
        logger.error(f"ROUTE_ADD_ERROR - User: {email} | Error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    
    except Exception as e:
        logger.error(f"ROUTE_ADD_ERROR - User: {email} | Error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/routes/<route_id>', methods=['GET'])
@limiter.limit("100 per hour")
def api_get_route(route_id):
    """Get a single route"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    route = route_manager.get_route_by_id(route_id)
    
    if not route:
        return jsonify({'error': 'Route not found'}), 404
    
    return jsonify(route)


@app.route('/api/routes/<route_id>', methods=['PUT'])
@limiter.limit("50 per hour")
def api_update_route(route_id):
    """Update a route"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    
    try:
        updates: Dict[str, Any] = {}

        if 'path' in data:
            updates['path'] = route_manager.validate_path(data['path'])

        if 'name' in data:
            updates['name'] = route_manager.validate_name(data['name'])

        if 'target_ip' in data:
            route_manager.validate_ip(data['target_ip'])
            updates['target_ip'] = data['target_ip']

        if 'target_port' in data:
            updates['target_port'] = route_manager.validate_port(data['target_port'])

        if 'target_path' in data:
            updates['target_path'] = data['target_path'] if data['target_path'] else '/'

        if 'protocol' in data:
            updates['protocol'] = route_manager.validate_protocol(data['protocol'])

        if 'timeout' in data:
            updates['timeout'] = route_manager.validate_timeout(data['timeout'])

        if 'preserve_host' in data:
            updates['preserve_host'] = parse_bool(data['preserve_host'])

        if 'websocket' in data:
            updates['websocket'] = parse_bool(data['websocket'])

        if 'enabled' in data:
            updates['enabled'] = parse_bool(data['enabled'])

        if 'health_check' in data:
            updates['health_check'] = parse_bool(data['health_check'])

        if not updates:
            return jsonify({'error': 'No valid fields provided'}), 400

        success = route_manager.update_route(route_id, updates)
        
        if success:
            logger.info(f"ROUTE_UPDATE - User: {email} | Route: {route_id} | Changes: {list(updates.keys())}")
            
            # After DB change, resync Caddy
            try:
                routes = route_manager.get_all_routes()
                caddy_mgr.sync(routes)
            except Exception as e:
                logger.exception("CADDY_SYNC after update failed: %s", e)
            
            return jsonify({'success': True, 'route': route_manager.get_route_by_id(route_id)})
        else:
            return jsonify({'error': 'Route not found'}), 404
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    except Exception as e:
        logger.error(f"ROUTE_UPDATE_ERROR - User: {email} | Route: {route_id} | Error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/routes/<route_id>', methods=['DELETE'])
@limiter.limit("50 per hour")
def api_delete_route(route_id):
    """Delete a route"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    success = route_manager.delete_route(route_id)
    
    if success:
        logger.info(f"ROUTE_DELETE - User: {email} | Route: {route_id}")
        
        # After DB change, resync Caddy
        try:
            routes = route_manager.get_all_routes()
            caddy_mgr.sync(routes)
        except Exception as e:
            logger.exception("CADDY_SYNC after delete failed: %s", e)
        
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Route not found'}), 404


_route_test_cooldowns: Dict[str, datetime] = {}
_ROUTE_TEST_COOLDOWN_SEC = Limits.ROUTE_TEST_COOLDOWN_SEC


@app.route('/api/routes/<route_id>/test', methods=['POST'])
@limiter.limit("10 per hour")
def api_test_route(route_id):
    """Test route connectivity"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Per-route cooldown
    last = _route_test_cooldowns.get(route_id)
    if last:
        elapsed = (datetime.now() - last).total_seconds()
        remaining = _ROUTE_TEST_COOLDOWN_SEC - elapsed
        if remaining > 0:
            return jsonify({
                'error': f'Please wait {int(remaining)}s before testing this route again',
                'retry_after': int(remaining)
            }), 429
    
    route = route_manager.get_route_by_id(route_id)
    if not route:
        return jsonify({'error': 'Route not found'}), 404
    
    _route_test_cooldowns[route_id] = datetime.now()
    result = caddy_mgr.test_connection(route)
    
    # Update route status in database
    if result.get('success'):
        route_manager.update_route_status(route_id, result['status'])
    else:
        route_manager.update_route_status(route_id, result.get('status', 'error'))
    
    logger.info(f"ROUTE_TEST - User: {email} | Route: {route_id} | Result: {result.get('status', 'error')}")
    
    return jsonify(result)


@app.route('/api/routes/<route_id>/toggle', methods=['POST'])
@limiter.limit("50 per hour")
def api_toggle_route(route_id):
    """Toggle route enabled status"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    route = route_manager.get_route_by_id(route_id)
    
    if not route:
        return jsonify({'error': 'Route not found'}), 404
    
    new_enabled = not route.get('enabled', True)
    route_manager.update_route(route_id, {'enabled': new_enabled})
    
    logger.info(f"ROUTE_TOGGLE - User: {email} | Route: {route_id} | Enabled: {new_enabled}")
    
    # After DB change, resync Caddy
    try:
        routes = route_manager.get_all_routes()
        caddy_mgr.sync(routes)
    except Exception as e:
        logger.exception("CADDY_SYNC after toggle failed: %s", e)
    
    return jsonify({'success': True, 'enabled': new_enabled})


# ============================================================================
# EMAIL MANAGEMENT API
# ============================================================================

@app.route('/api/emails', methods=['GET'])
@limiter.limit("100 per hour")
def api_get_emails():
    """Get all authorized emails"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'emails': list(AUTHORIZED_EMAILS),
        'count': len(AUTHORIZED_EMAILS)
    })


@app.route('/api/emails', methods=['POST'])
@limiter.limit("20 per hour")
def api_add_email():
    """Add a new authorized email"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    
    new_email = data.get('email', '').strip().lower()
    
    if not new_email:
        return jsonify({'error': 'Email is required'}), 400
    
    # Basic email validation
    if not is_valid_email(new_email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    if new_email in AUTHORIZED_EMAILS:
        return jsonify({'error': 'Email already exists'}), 400
    
    try:
        # Add to file with locking
        with locked_file(str(Path(settings.emails_file)), 'a') as f:
            f.write(f'{new_email}\n')
        
        # Refresh in-memory list
        refresh_authorized_emails()
        
        logger.info(f"EMAIL_ADD - User: {email} | Added: {new_email}")
        
        return jsonify({
            'success': True,
            'email': new_email,
            'total_emails': len(AUTHORIZED_EMAILS)
        }), 201
    
    except Exception as e:
        logger.error(f"EMAIL_ADD_ERROR - User: {email} | Error: {str(e)}")
        return jsonify({'error': 'Failed to add email'}), 500


@app.route('/api/emails/<email_to_remove>', methods=['DELETE'])
@limiter.limit("20 per hour")
def api_remove_email(email_to_remove):
    """Remove an authorized email"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    email_to_remove = email_to_remove.strip().lower()
    
    if email_to_remove not in AUTHORIZED_EMAILS:
        return jsonify({'error': 'Email not found'}), 404
    
    # Prevent removing own email
    if email_to_remove == email:
        return jsonify({'error': 'Cannot remove your own email'}), 400
    
    try:
        # Read and rewrite with file lock for atomicity
        email_file = str(Path(settings.emails_file))
        with locked_file(email_file, 'r') as f:
            emails = []
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and stripped.lower() != email_to_remove:
                    emails.append(stripped)
        
        # Write back without the removed email
        with locked_file(email_file, 'w') as f:
            for e in emails:
                f.write(f'{e}\n')
        
        # Refresh in-memory list
        refresh_authorized_emails()
        
        logger.info(f"EMAIL_REMOVE - User: {email} | Removed: {email_to_remove}")
        
        return jsonify({
            'success': True,
            'removed_email': email_to_remove,
            'total_emails': len(AUTHORIZED_EMAILS)
        })
    
    except Exception as e:
        logger.error(f"EMAIL_REMOVE_ERROR - User: {email} | Error: {str(e)}")
        return jsonify({'error': 'Failed to remove email'}), 500


@app.route('/api/emails/<email_to_update>', methods=['PUT'])
@limiter.limit("10 per hour")
def api_update_email(email_to_update):
    """Update an authorized email"""
    current_user_email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    new_email = data.get('email', '').strip().lower()
    email_to_update = email_to_update.strip().lower()
    
    if not new_email:
        return jsonify({'error': 'New email is required'}), 400
    
    if not is_valid_email(new_email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    if email_to_update not in AUTHORIZED_EMAILS:
        return jsonify({'error': 'Original email not found'}), 404
    
    if new_email in AUTHORIZED_EMAILS and new_email != email_to_update:
        return jsonify({'error': 'New email already exists'}), 409
    
    # Prevent updating own email to avoid locking out
    if email_to_update == current_user_email:
        return jsonify({'error': 'Cannot update your own email for security reasons'}), 400
    
    try:
        # Read and rewrite with file lock for atomicity
        email_file = str(Path(settings.emails_file))
        emails = []
        updated = False
        
        with locked_file(email_file, 'r') as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    if stripped.lower() == email_to_update:
                        emails.append(new_email)
                        updated = True
                    else:
                        emails.append(stripped)
        
        if not updated:
            return jsonify({'error': 'Email not found in file'}), 404
        
        # Write back with updated email
        with locked_file(email_file, 'w') as f:
            for e in emails:
                f.write(f'{e}\n')
        
        # Refresh in-memory list
        refresh_authorized_emails()
        
        logger.info(f"EMAIL_UPDATE - User: {current_user_email} | Updated: {email_to_update} -> {new_email}")
        
        return jsonify({
            'success': True,
            'old_email': email_to_update,
            'new_email': new_email,
            'total_emails': len(AUTHORIZED_EMAILS)
        })
    
    except Exception as e:
        logger.error(f"EMAIL_UPDATE_ERROR - User: {current_user_email} | Error: {str(e)}")
        return jsonify({'error': 'Failed to update email'}), 500


@app.route('/api/emails/refresh', methods=['POST'])
@limiter.limit("10 per hour")
def api_refresh_emails():
    """Refresh authorized emails from disk"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        count = refresh_authorized_emails()
        logger.info(f"EMAIL_REFRESH - User: {email} | Count: {count}")
        
        return jsonify({
            'success': True,
            'count': count,
            'emails': list(AUTHORIZED_EMAILS)
        })
    
    except Exception as e:
        logger.error(f"EMAIL_REFRESH_ERROR - User: {email} | Error: {str(e)}")
        return jsonify({'error': 'Failed to refresh emails'}), 500


@app.route('/api/route-status/<path:route_path>', methods=['GET'])
@limiter.exempt
def api_check_route_status(route_path):
    """API endpoint to check if a route is enabled (for Caddy to use)"""
    # Add leading slash if not present
    if not route_path.startswith('/'):
        route_path = '/' + route_path
    
    # Check if this route exists and is enabled
    routes = route_manager.get_all_routes()
    matching_route = None
    
    for route in routes:
        if route['path'] == route_path or route['path'].rstrip('/') == route_path.rstrip('/'):
            matching_route = route
            break
    
    if matching_route:
        enabled = matching_route.get('enabled', True)
        return jsonify({
            'path': route_path,
            'enabled': enabled,
            'name': matching_route.get('name', ''),
            'status': matching_route.get('status', 'unknown')
        })
    else:
        return jsonify({
            'path': route_path,
            'enabled': False,
            'error': 'Route not found'
        }), 404


# ============================================================================
# ROUTE INTERCEPTION FOR DISABLED ROUTES
# ============================================================================

@app.route('/<path:route_path>')
def check_route_status(route_path):
    """Check if a route is disabled and redirect accordingly"""
    email = get_user_email()
    
    if not is_authorized():
        return render_template('unauthorized.html', email=email), 403
    
    # Add leading slash if not present
    if not route_path.startswith('/'):
        route_path = '/' + route_path
    
    # Check if this route exists in our database
    routes = route_manager.get_all_routes()
    matching_route = None
    
    for route in routes:
        if route['path'] == route_path or route['path'].rstrip('/') == route_path.rstrip('/'):
            matching_route = route
            break
    
    if matching_route:
        # Check if route is disabled
        if not matching_route.get('enabled', True):
            logger.info(f"ROUTE_DISABLED_ACCESS - User: {email} | Path: {route_path} | Route: {matching_route['name']}")
            return render_template('route_disabled.html', 
                                 email=email, 
                                 route_path=route_path, 
                                 route_name=matching_route.get('name', ''))
        else:
            # Route is enabled, let Caddy handle it (this shouldn't normally be reached in production)
            logger.info(f"ROUTE_ENABLED_ACCESS - User: {email} | Path: {route_path} | Route: {matching_route['name']}")
            # In production, this would be handled by Caddy proxy
            # For development, we can show a message or redirect
            return f"Route {route_path} is enabled and should be handled by the reverse proxy.", 200
    else:
        # Route not found in our system, return 404
        logger.warning(f"ROUTE_NOT_FOUND - User: {email} | Path: {route_path}")
        return render_template('404.html', path=route_path), 404

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(AppError)
def handle_app_error(e):
    """Handle custom application errors with consistent JSON response."""
    return jsonify({'error': e.message}), e.status_code


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return render_template('404.html', path=request.path), 404


@app.errorhandler(403)
def forbidden(e):
    """Handle 403 errors"""
    email = get_user_email()
    return render_template('unauthorized.html', email=email), 403


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error(f"500 ERROR - Path: {request.path} | Error: {str(e)}")
    return "Internal Server Error", 500


# ============================================================================
# BACKGROUND HEALTH CHECK
# ============================================================================

health_check_stop_event = threading.Event()
health_thread_lock = threading.Lock()
health_thread = None

# Track consecutive failures per route for exponential backoff
_health_failures: Dict[str, int] = {}


def _check_single_route(route: Dict) -> None:
    """Check a single route's health and update status."""
    route_id = route['id']
    try:
        result = caddy_mgr.test_connection(route)

        # Update with new enhanced status fields
        route_manager.update_route_status(
            route_id,
            status=result.get('status'),
            state=result.get('state'),
            reason=result.get('reason'),
            http_status=result.get('status_code'),
            duration_ms=result.get('response_time'),
            last_error=result.get('error') or result.get('detail')
        )

        if result.get('success'):
            _health_failures[route_id] = 0
        else:
            _health_failures[route_id] = _health_failures.get(route_id, 0) + 1
    except Exception as exc:
        logger.error(f"HEALTH_CHECK_ROUTE_ERROR - Route {route_id}: {exc}")
        _health_failures[route_id] = _health_failures.get(route_id, 0) + 1


def health_check_worker(stop_event: threading.Event, interval: int):
    """Background worker to check route health with concurrency and backoff"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    logger.info(f"HEALTH_CHECK - Worker started with {interval}s interval")

    while not stop_event.is_set():
        try:
            routes = route_manager.get_all_routes()
            eligible = []
            for route in routes:
                if not (route.get('health_check', False) and route.get('enabled', True)):
                    continue
                route_id = route['id']
                failures = _health_failures.get(route_id, 0)
                if failures > 0:
                    backoff = min(60 * (2 ** failures), 1800)
                    # Skip this cycle if backoff hasn't elapsed
                    if failures > 0 and backoff > interval:
                        continue
                eligible.append(route)

            checked = 0
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = {pool.submit(_check_single_route, r): r for r in eligible}
                for future in as_completed(futures, timeout=10):
                    try:
                        future.result()
                    except Exception as exc:
                        logger.error(f"HEALTH_CHECK_FUTURE_ERROR - {exc}")
                    checked += 1

            logger.info(f"HEALTH_CHECK - Checked {checked}/{len(routes)} routes")

        except Exception as e:
            logger.error(f"HEALTH_CHECK_ERROR - {str(e)}")

        if stop_event.wait(interval):
            break


def start_health_check_worker() -> None:
    """Start the health check worker if enabled."""
    global health_thread

    if not settings.health_check_enabled:
        logger.info("HEALTH_CHECK - Worker disabled by configuration")
        return

    interval = settings.health_check_interval
    if interval <= 0:
        logger.info("HEALTH_CHECK - Worker not started due to non-positive interval")
        return

    with health_thread_lock:
        if health_thread and health_thread.is_alive():
            return

        health_check_stop_event.clear()
        health_thread = threading.Thread(
            target=health_check_worker,
            args=(health_check_stop_event, interval),
            daemon=True
        )
        health_thread.start()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    if not debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_health_check_worker()
        
        # Sync routes to Caddy on startup
        try:
            routes = route_manager.get_all_routes()
            caddy_mgr.sync(routes)
            logger.info("CADDY_SYNC: completed on startup")
        except Exception as e:
            logger.exception("CADDY_SYNC on startup failed: %s", e)

    logger.info(f"Starting Shark-no-Ninsho-Mon on port {port}")
    logger.info(f"Authorized emails: {len(AUTHORIZED_EMAILS)}")
    logger.info(f"Existing routes: {len(route_manager.get_all_routes())}")
    
    # DEV_MODE safety checks
    if is_dev_mode():
        logger.critical("=" * 60)
        logger.critical("DEV_MODE ENABLED — ALL AUTHENTICATION BYPASSED")
        logger.critical("NEVER use in production!")
        logger.critical("=" * 60)
        if os.path.exists('/.dockerenv'):
            logger.error("DEV_MODE is active inside Docker — this is likely a mistake!")
        if os.environ.get('OAUTH2_PROXY_CLIENT_ID'):
            logger.error("DEV_MODE active with OAuth configured — unsafe!")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
