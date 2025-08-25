# app_dev.py - Development version with local paths
from flask import Flask, request, jsonify
import logging
import datetime
import os

app = Flask(__name__)

# Configure logging for local development
log_file = os.path.join(os.getcwd(), 'access.log')  # Local directory
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler(log_file)  # Local file output
    ]
)
logger = logging.getLogger(__name__)

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
    
    # Log the access
    logger.info(f"ACCESS - Email: {email} | IP: {real_ip} | Path: {request.path} | Method: {request.method} | Host: {request.headers.get('X-Forwarded-Host', 'localhost')}")

@app.before_request
def before_request():
    """Log every request"""
    log_access()

@app.route("/")
def index():
    email = get_email()
    real_ip = get_real_ip()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shark Authentication Test - DEV MODE</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        .dev-banner {{ background: #ff6b6b; color: white; padding: 10px; text-align: center; border-radius: 4px; margin-bottom: 20px; }}
        .info {{ background: #e8f4fd; padding: 15px; border-radius: 4px; margin: 10px 0; }}
        .nav {{ margin: 20px 0; }}
        .nav a {{ display: inline-block; margin: 5px; padding: 10px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="dev-banner">
            <strong>DEVELOPMENT MODE</strong> - Local Testing Environment
        </div>
        
        <h1>SHARK AUTHENTICATION TEST</h1>
        
        <div class="info">
            <h3>Authentication Information</h3>
            <p><strong>Authenticated as:</strong> {email}</p>
            <p><strong>Your IP Address:</strong> {real_ip}</p>
            <p><strong>Access Time:</strong> {timestamp}</p>
            <p><strong>Host:</strong> {request.headers.get('X-Forwarded-Host', 'localhost:5000')}</p>
        </div>
        
        <div class="nav">
            <a href="/api/whoami">/api/whoami</a>
            <a href="/headers">/headers</a>
            <a href="/logs">/logs</a>
            <a href="/health">/health</a>
        </div>
        
        <div class="info">
            <h4>Development Notes</h4>
            <p>• Headers are simulated for local testing</p>
            <p>• Log file: {log_file}</p>
            <p>• This simulates the oauth2-proxy environment</p>
        </div>
    </div>
</body>
</html>"""

@app.route("/api/whoami")
def whoami():
    email = get_email()
    real_ip = get_real_ip()
    
    return jsonify({
        "email": email,
        "ip_address": real_ip,
        "timestamp": datetime.datetime.now().isoformat(),
        "authenticated": email != "anonymous",
        "host": request.headers.get('X-Forwarded-Host', 'localhost'),
        "dev_mode": True,
        "log_file": log_file
    })

@app.route("/headers")
def headers():
    return f"""<h2>Headers Debug</h2>
    <h3>All Headers:</h3>
    <pre>{"<br>".join(f"{k}: {v}" for k, v in request.headers)}</pre>
    <p><a href="/">Back</a></p>"""

@app.route("/logs")
def show_logs():
    try:
        with open(log_file, 'r') as f:
            content = f.read()
        return f"""<h2>Access Logs</h2>
        <pre style="background: #f8f8f8; padding: 15px; max-height: 400px; overflow-y: auto;">{content}</pre>
        <p><a href="/">Back</a></p>"""
    except FileNotFoundError:
        return f"""<h2>No logs yet</h2>
        <p>Log file will be created at: {log_file}</p>
        <p><a href="/">Back</a></p>"""

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "mode": "development",
        "timestamp": datetime.datetime.now().isoformat(),
        "log_file": log_file
    })

if __name__ == "__main__":
    print("🧪 Starting Shark Development Server")
    print(f"📍 URL: http://localhost:5000")
    print(f"📝 Logs: {log_file}")
    print("🔄 Auto-reload enabled")
    app.run(host='0.0.0.0', port=5000, debug=True)
