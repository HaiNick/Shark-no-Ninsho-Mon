"""
Shark-no-Ninsho-Mon - OAuth2 Authentication Gateway with Reverse Proxy Route Manager
"""
from flask import Flask, render_template, request, jsonify, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from datetime import datetime
import os
import threading
import time

from routes_db import RouteManager
from proxy_handler import ProxyHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Initialize route manager and proxy handler
route_manager = RouteManager('/app/routes.json')
proxy_handler = ProxyHandler(route_manager)

# Load authorized emails
AUTHORIZED_EMAILS = set()
emails_file = os.environ.get('EMAILS_FILE', '/app/emails.txt')
if os.path.exists(emails_file):
    with open(emails_file, 'r') as f:
        AUTHORIZED_EMAILS = {line.strip().lower() for line in f if line.strip() and not line.startswith('#')}
    logger.info(f"Loaded {len(AUTHORIZED_EMAILS)} authorized emails")
else:
    logger.warning(f"Emails file not found: {emails_file}")


def get_user_email():
    """Get user email from OAuth2 proxy headers"""
    return request.headers.get('X-Forwarded-Email', '').lower()


def is_authorized():
    """Check if user is authorized"""
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
        return render_template('unauthorized.html', email=email), 403
    
    # Get enabled routes to display on dashboard
    routes = route_manager.get_all_routes(enabled_only=True)
    
    logger.info(f"ACCESS - User: {email} | Path: / | IP: {request.remote_addr}")
    
    return render_template('index.html', email=email, routes=routes)


@app.route('/admin')
def admin():
    """Route management admin page"""
    email = get_user_email()
    
    if not is_authorized():
        return render_template('unauthorized.html', email=email), 403
    
    logger.info(f"ACCESS - User: {email} | Path: /admin | IP: {request.remote_addr}")
    
    return render_template('admin.html', email=email)


@app.route('/health')
@limiter.exempt
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'routes_count': len(route_manager.get_all_routes())
    })


@app.route('/whoami')
def whoami():
    """Return user information"""
    email = get_user_email()
    
    return jsonify({
        'email': email,
        'authorized': is_authorized(),
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', '')
    })


@app.route('/headers')
def headers():
    """Display all request headers"""
    email = get_user_email()
    
    if not is_authorized():
        return render_template('unauthorized.html', email=email), 403
    
    headers_dict = dict(request.headers)
    
    logger.info(f"ACCESS - User: {email} | Path: /headers | IP: {request.remote_addr}")
    
    return render_template('headers.html', email=email, headers=headers_dict)


@app.route('/logs')
def logs():
    """Display application logs"""
    email = get_user_email()
    
    if not is_authorized():
        return render_template('unauthorized.html', email=email), 403
    
    logger.info(f"ACCESS - User: {email} | Path: /logs | IP: {request.remote_addr}")
    
    return render_template('logs.html', email=email)


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
    
    data = request.json
    
    try:
        route = route_manager.add_route(
            path=data.get('path'),
            name=data.get('name'),
            target_ip=data.get('target_ip'),
            target_port=int(data.get('target_port')),
            protocol=data.get('protocol', 'http'),
            enabled=data.get('enabled', True),
            health_check=data.get('health_check', True),
            timeout=int(data.get('timeout', 30)),
            preserve_host=data.get('preserve_host', False),
            websocket=data.get('websocket', False)
        )
        
        logger.info(f"ROUTE_ADD - User: {email} | Path: {route['path']} | Target: {route['target_ip']}:{route['target_port']}")
        
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
    
    data = request.json
    
    try:
        # Validate data if provided
        if 'target_ip' in data:
            route_manager.validate_ip(data['target_ip'])
        
        if 'target_port' in data:
            route_manager.validate_port(int(data['target_port']))
        
        if 'path' in data:
            data['path'] = route_manager.validate_path(data['path'])
        
        success = route_manager.update_route(route_id, data)
        
        if success:
            logger.info(f"ROUTE_UPDATE - User: {email} | Route: {route_id} | Changes: {list(data.keys())}")
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
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Route not found'}), 404


@app.route('/api/routes/<route_id>/test', methods=['POST'])
@limiter.limit("30 per hour")
def api_test_route(route_id):
    """Test route connectivity"""
    email = get_user_email()
    
    if not is_authorized():
        return jsonify({'error': 'Unauthorized'}), 403
    
    result = proxy_handler.test_connection(route_id)
    
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
    
    return jsonify({'success': True, 'enabled': new_enabled})


# ============================================================================
# DYNAMIC PROXY HANDLER (Catch-all)
# ============================================================================

@app.route('/<path:full_path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def dynamic_proxy(full_path):
    """
    Dynamic proxy handler - catches all unmatched routes
    This should be the last route defined
    """
    email = get_user_email()
    
    if not is_authorized():
        return render_template('unauthorized.html', email=email), 403
    
    # Extract route path (first segment)
    path_parts = full_path.split('/', 1)
    route_path = '/' + path_parts[0]
    sub_path = '/' + path_parts[1] if len(path_parts) > 1 else ''
    
    # Check if route exists
    route = route_manager.get_route_by_path(route_path)
    
    if not route:
        logger.warning(f"404 - User: {email} | Path: /{full_path} | IP: {request.remote_addr}")
        return render_template('404.html', path=f'/{full_path}'), 404
    
    # Proxy the request
    return proxy_handler.proxy_request(route_path, sub_path)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

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

def health_check_worker():
    """Background worker to check route health"""
    while True:
        try:
            time.sleep(300)  # Check every 5 minutes
            
            routes = route_manager.get_all_routes()
            for route in routes:
                if route.get('health_check', False) and route.get('enabled', True):
                    proxy_handler.test_connection(route['id'])
            
            logger.info(f"HEALTH_CHECK - Checked {len(routes)} routes")
        
        except Exception as e:
            logger.error(f"HEALTH_CHECK_ERROR - {str(e)}")


# Start health check worker
health_thread = threading.Thread(target=health_check_worker, daemon=True)
health_thread.start()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Shark-no-Ninsho-Mon on port {port}")
    logger.info(f"Authorized emails: {len(AUTHORIZED_EMAILS)}")
    logger.info(f"Existing routes: {len(route_manager.get_all_routes())}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
