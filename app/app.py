# file: app/app.py
from flask import Flask, request, jsonify, render_template, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import datetime
import os
import functools
import time

app = Flask(__name__)

# Environment configuration
FLASK_ENV = os.getenv('FLASK_ENV', 'production')
EMAILS_FILE_PATH = os.getenv('EMAILS_FILE_PATH', '/app/emails.txt')
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', '/app/access.log')

# Configure logging with error handling
try:
    # Ensure log directory exists
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler(LOG_FILE_PATH)  # File output
        ]
    )
except (PermissionError, OSError) as e:
    # Fallback to console-only logging if file logging fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    print(f"WARNING: Could not create log file at {LOG_FILE_PATH}: {e}")

logger = logging.getLogger(__name__)

# Rate limiting configuration
def get_real_ip_for_limiter():
    """Get real IP for rate limiter"""
    return get_real_ip()

limiter = Limiter(
    app=app,
    key_func=get_real_ip_for_limiter,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Cache for authorized emails with file modification time tracking
_email_cache = {'emails': set(), 'mtime': 0}

def load_authorized_emails():
    """Load authorized emails from emails.txt file with caching"""
    global _email_cache
    
    # Check multiple possible paths for emails file
    possible_paths = [
        EMAILS_FILE_PATH,
        '/app/emails.txt',
        '../emails.txt',
        './emails.txt'
    ]
    
    emails_file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            emails_file_path = path
            break
    
    if not emails_file_path:
        logger.error(f"Emails file not found in any of these locations: {possible_paths}")
        return set()
    
    try:
        # Check file modification time for cache invalidation
        current_mtime = os.path.getmtime(emails_file_path)
        
        # Return cached emails if file hasn't changed
        if _email_cache['mtime'] == current_mtime and _email_cache['emails']:
            return _email_cache['emails']
        
        # Load emails from file
        authorized_emails = set()
        with open(emails_file_path, 'r') as f:
            for line in f:
                email = line.strip()
                if email and not email.startswith('#'):  # Skip empty lines and comments
                    authorized_emails.add(email.lower())  # Store in lowercase for case-insensitive comparison
        
        # Update cache
        _email_cache['emails'] = authorized_emails
        _email_cache['mtime'] = current_mtime
        
        logger.info(f"Loaded {len(authorized_emails)} authorized emails from {emails_file_path}")
        return authorized_emails
        
    except FileNotFoundError:
        logger.error(f"Emails file not found at {emails_file_path}. All users will be blocked.")
        return set()
    except PermissionError:
        logger.error(f"Permission denied reading {emails_file_path}. All users will be blocked.")
        return set()
    except Exception as e:
        logger.error(f"Error loading emails file: {e}")
        return set()

def is_user_authorized(email):
    """Check if user email is in the authorized list"""
    # SECURITY: Block anonymous users in production
    if email == "anonymous":
        if FLASK_ENV == 'production':
            logger.warning("SECURITY BLOCK - Anonymous user blocked in production mode")
            return False
        else:
            logger.warning("DEV MODE - Anonymous user allowed (NOT FOR PRODUCTION)")
            # In development, still check the email list
    
    authorized_emails = load_authorized_emails()
    
    # If no emails are configured, block everyone for security
    if not authorized_emails:
        logger.critical("SECURITY ALERT - No authorized emails configured! Blocking all access.")
        return False
    
    is_authorized = email.lower() in authorized_emails
    
    if is_authorized:
        logger.info(f"AUTHORIZATION SUCCESS - User '{email}' is authorized to access the application")
    else:
        logger.warning(f"AUTHORIZATION FAILED - User '{email}' is not in authorized list")
    
    return is_authorized

def check_authorization():
    """Check if current user is authorized to access the application"""
    email = get_email()
    
    if not is_user_authorized(email):
        logger.warning(f"SECURITY BLOCK - Unauthorized access attempt by: {email} | IP: {get_real_ip()} | Path: {request.path}")
        return False
    
    return True

def get_email():
    """Get user email from various possible headers"""
    return (request.headers.get("X-Forwarded-Email")
            or request.headers.get("X-Auth-Request-Email")
            or request.headers.get("X-Forwarded-User")
            or "anonymous")

def get_real_ip():
    """Get the real IP address of the user from various possible headers"""
    # Try multiple headers that might contain the real IP
    possible_ip_headers = [
        'X-Real-IP',
        'X-Forwarded-For',
        'CF-Connecting-IP',  # Cloudflare
        'X-Client-IP',
        'X-Cluster-Client-IP',
        'Forwarded'
    ]
    
    for header in possible_ip_headers:
        ip = request.headers.get(header)
        if ip:
            # X-Forwarded-For can be a comma-separated list, take the first one
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            # Only log in debug mode to reduce log noise
            if FLASK_ENV == 'development':
                logger.debug(f"Found IP in header {header}: {ip}")
            return ip
    
    # Fallback to Flask's remote_addr
    fallback_ip = request.remote_addr or '127.0.0.1'
    if FLASK_ENV == 'development':
        logger.debug(f"Using fallback IP from request.remote_addr: {fallback_ip}")
    return fallback_ip

def log_access():
    """Log access details for monitoring and debugging"""
    email = get_email()
    real_ip = get_real_ip()
    timestamp = datetime.datetime.now().isoformat()
    
    # Get all relevant headers
    auth_headers = {
        'X-Forwarded-Email': request.headers.get('X-Forwarded-Email'),
        'X-Forwarded-User': request.headers.get('X-Forwarded-User'),
        'X-Auth-Request-Email': request.headers.get('X-Auth-Request-Email'),
        'X-Forwarded-Proto': request.headers.get('X-Forwarded-Proto'),
        'X-Forwarded-Host': request.headers.get('X-Forwarded-Host'),
        'X-Forwarded-Uri': request.headers.get('X-Forwarded-Uri'),
        'X-Real-IP': request.headers.get('X-Real-IP'),
        'X-Forwarded-For': request.headers.get('X-Forwarded-For'),
        'User-Agent': request.headers.get('User-Agent'),
    }
    
    # Log the access
    logger.info(f"ACCESS - Email: {email} | IP: {real_ip} | Path: {request.path} | Method: {request.method} | Host: {request.headers.get('X-Forwarded-Host', 'unknown')}")
    
    # Log detailed headers for debugging (only in debug mode)
    if app.debug or os.getenv('FLASK_ENV') == 'development':
        logger.debug(f"All auth headers: {auth_headers}")

@app.before_request
def before_request():
    """Check authorization and log every request"""
    # Skip authorization check for certain endpoints
    skip_auth_paths = ['/favicon.ico', '/static/', '/unauthorized']
    
    if not any(request.path.startswith(path) for path in skip_auth_paths):
        if not check_authorization():
            # Log the unauthorized attempt
            log_access()
            # Generate incident ID for tracking
            import uuid
            incident_id = str(uuid.uuid4())[:8]
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Redirect to unauthorized page
            return render_template('unauthorized.html', 
                                 email=get_email(), 
                                 real_ip=get_real_ip(),
                                 timestamp=timestamp,
                                 incident_id=incident_id), 403
    
    # Log the request
    log_access()

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/api/whoami")
def whoami():
    email = get_email()
    real_ip = get_real_ip()
    
    user_info = {
        "email": email,
        "ip_address": real_ip,
        "timestamp": datetime.datetime.now().isoformat(),
        "authenticated": email != "anonymous",
        "host": request.headers.get('X-Forwarded-Host'),
        "protocol": request.headers.get('X-Forwarded-Proto'),
        "user_agent": request.headers.get('User-Agent'),
        "request_path": request.path,
        "method": request.method
    }
    
    return jsonify(user_info)

@app.route("/headers")
def headers():
    """Show all authentication and forwarding headers"""
    auth_headers_list = [
        "X-Forwarded-Email", "X-Forwarded-User", "X-Auth-Request-Email",
        "X-Forwarded-Proto", "X-Forwarded-Host", "X-Forwarded-Uri", 
        "X-Real-IP", "X-Forwarded-For", "CF-Connecting-IP",
        "X-Client-IP", "User-Agent", "Host"
    ]
    
    email = get_email()
    real_ip = get_real_ip()
    
    auth_headers = [(header, request.headers.get(header)) for header in auth_headers_list]
    all_headers = [(header, value) for header, value in request.headers]
    
    return render_template('headers.html', 
                         email=email, 
                         real_ip=real_ip,
                         auth_headers=auth_headers,
                         all_headers=all_headers)

@app.route("/api/headers")
def api_headers():
    """API endpoint for headers information"""
    auth_headers_list = [
        "X-Forwarded-Email", "X-Forwarded-User", "X-Auth-Request-Email",
        "X-Forwarded-Proto", "X-Forwarded-Host", "X-Forwarded-Uri", 
        "X-Real-IP", "X-Forwarded-For", "CF-Connecting-IP",
        "X-Client-IP", "User-Agent", "Host"
    ]
    
    email = get_email()
    real_ip = get_real_ip()
    
    headers_data = {
        "detected_email": email,
        "detected_ip": real_ip,
        "auth_headers": {header: request.headers.get(header) for header in auth_headers_list},
        "all_headers": dict(request.headers),
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    return jsonify(headers_data)

@app.route("/logs")
@limiter.limit("10 per minute")
def show_logs():
    """Show recent access logs"""
    try:
        with open(LOG_FILE_PATH, 'r') as f:
            logs = f.readlines()
            # Show last 50 lines
            recent_logs = logs[-50:] if len(logs) > 50 else logs
            
        log_content = ''.join(recent_logs)
        log_count = len(recent_logs)
        
        return render_template('logs.html', logs=log_content, log_count=log_count)
        
    except FileNotFoundError:
        return render_template('logs.html', 
                             logs='No log file found. Logs will appear here after some requests are made to the application.',
                             log_count=0)
    except PermissionError:
        return render_template('logs.html', 
                             logs='Permission denied reading log file.',
                             log_count=0)

@app.route("/api/logs")
@limiter.limit("10 per minute")
def api_logs():
    """API endpoint for logs"""
    try:
        with open(LOG_FILE_PATH, 'r') as f:
            logs = f.readlines()
            # Show last 50 lines
            recent_logs = logs[-50:] if len(logs) > 50 else logs
            
        log_content = ''.join(recent_logs)
        
        return jsonify({
            "logs": log_content,
            "log_count": len(recent_logs),
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except FileNotFoundError:
        return jsonify({
            "logs": "No log file found",
            "log_count": 0,
            "timestamp": datetime.datetime.now().isoformat(),
            "error": "Log file not found"
        }), 404
    except PermissionError:
        return jsonify({
            "logs": "Permission denied",
            "log_count": 0,
            "timestamp": datetime.datetime.now().isoformat(),
            "error": "Permission denied reading log file"
        }), 403

@app.route("/health")
@limiter.exempt
def health():
    """Health check endpoint for Docker and monitoring systems"""
    # Basic health check - doesn't require authentication
    health_info = {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "service": "shark-no-ninsho-mon",
        "version": "2.0.0",
        "environment": FLASK_ENV
    }
    
    # Check if emails file is accessible
    try:
        authorized_emails = load_authorized_emails()
        health_info["authorized_emails_count"] = len(authorized_emails)
        health_info["emails_file_status"] = "ok"
    except Exception as e:
        health_info["emails_file_status"] = f"error: {str(e)}"
        health_info["status"] = "degraded"
    
    # Check if log file is writable
    try:
        with open(LOG_FILE_PATH, 'a') as f:
            pass
        health_info["log_file_status"] = "ok"
    except Exception as e:
        health_info["log_file_status"] = f"error: {str(e)}"
        health_info["status"] = "degraded"
    
    status_code = 200 if health_info["status"] == "healthy" else 503
    return jsonify(health_info), status_code

@app.route("/health-page")
def health_page():
    """Health check page"""
    return render_template('health_page.html')

@app.route("/unauthorized")
def unauthorized_page():
    """Display unauthorized access page"""
    import uuid
    incident_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    return render_template('unauthorized.html', 
                         email=get_email(), 
                         real_ip=get_real_ip(),
                         timestamp=timestamp,
                         incident_id=incident_id), 403

@app.route("/favicon.ico")
def favicon():
    """Simple favicon endpoint to prevent 404s"""
    return "", 204

@app.errorhandler(404)
def not_found(error):
    email = get_email()
    return render_template('404.html', email=email), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
