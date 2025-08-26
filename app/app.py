# file: app/app.py
from flask import Flask, request, jsonify, render_template, abort
import logging
import datetime
import os

app = Flask(__name__)

# Configure logging
log_file_path = '/app/access.log' if os.path.exists('/app') else './access.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler(log_file_path)  # File output
    ]
)
logger = logging.getLogger(__name__)

def load_authorized_emails():
    """Load authorized emails from emails.txt file"""
    emails_file_path = '../emails.txt' if os.path.exists('../emails.txt') else './emails.txt'
    authorized_emails = set()
    
    try:
        with open(emails_file_path, 'r') as f:
            for line in f:
                email = line.strip()
                if email and not email.startswith('#'):  # Skip empty lines and comments
                    authorized_emails.add(email.lower())  # Store in lowercase for case-insensitive comparison
        logger.info(f"Loaded {len(authorized_emails)} authorized emails from {emails_file_path}")
    except FileNotFoundError:
        logger.warning(f"Emails file not found at {emails_file_path}. All users will be blocked.")
    except Exception as e:
        logger.error(f"Error loading emails file: {e}")
    
    return authorized_emails

def is_user_authorized(email):
    """Check if user email is in the authorized list"""
    if email == "anonymous":
        # For development purposes, we'll temporarily allow anonymous but check the email list anyway
        # In production, you'd remove this or change it to return False
        pass
    
    authorized_emails = load_authorized_emails()
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
            logger.info(f"Found IP in header {header}: {ip}")
            return ip
    
    # Fallback to Flask's remote_addr
    fallback_ip = request.remote_addr
    logger.info(f"Using fallback IP from request.remote_addr: {fallback_ip}")
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
def show_logs():
    """Show recent access logs"""
    log_file_path = '/app/access.log' if os.path.exists('/app') else './access.log'
    try:
        with open(log_file_path, 'r') as f:
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

@app.route("/api/logs")
def api_logs():
    """API endpoint for logs"""
    log_file_path = '/app/access.log' if os.path.exists('/app') else './access.log'
    try:
        with open(log_file_path, 'r') as f:
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
        })

@app.route("/health")
def health():
    """Health check endpoint"""
    health_info = {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "service": "shark-no-ninsho-mon",
        "version": "1.0.0",
        "authenticated_user": get_email(),
        "client_ip": get_real_ip()
    }
    
    return jsonify(health_info)

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
