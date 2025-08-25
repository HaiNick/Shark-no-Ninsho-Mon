# file: app/app.py
from flask import Flask, request, jsonify
import logging
import datetime
import os

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('/app/access.log')  # File output
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
    <title>Shark Authentication Test</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }}
        
        .header p {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .info-card {{
            background: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }}
        
        .info-card h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        
        .info-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .info-item:last-child {{
            border-bottom: none;
        }}
        
        .info-label {{
            font-weight: 600;
            color: #495057;
        }}
        
        .info-value {{
            color: #007bff;
            font-family: 'Courier New', monospace;
        }}
        
        .nav-section {{
            margin: 30px 0;
        }}
        
        .nav-section h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        
        .nav-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        
        .nav-item {{
            display: block;
            padding: 15px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
            text-align: center;
        }}
        
        .nav-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        
        .nav-item .icon {{
            font-family: monospace;
            font-size: 1.2em;
            margin-right: 8px;
        }}
        
        .security-note {{
            background: #e8f4fd;
            border: 1px solid #bee5eb;
            border-radius: 8px;
            padding: 20px;
            margin: 30px 0;
        }}
        
        .security-note h4 {{
            color: #0c5460;
            margin-bottom: 10px;
        }}
        
        .security-note p {{
            color: #0c5460;
            margin: 0;
        }}
        
        @media (max-width: 768px) {{
            .info-item {{
                flex-direction: column;
            }}
            
            .nav-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SHARK AUTHENTICATION TEST</h1>
            <p>Secure Access via Tailscale Funnel + OAuth2-Proxy</p>
        </div>
        
        <div class="content">
            <div class="info-card">
                <h3>Authentication Information</h3>
                <div class="info-item">
                    <span class="info-label">Authenticated as:</span>
                    <span class="info-value">{email}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Your IP Address:</span>
                    <span class="info-value">{real_ip}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Access Time:</span>
                    <span class="info-value">{timestamp}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Host:</span>
                    <span class="info-value">{request.headers.get('X-Forwarded-Host', 'localhost')}</span>
                </div>
            </div>
            
            <div class="nav-section">
                <h3>Available Endpoints</h3>
                <div class="nav-grid">
                    <a href="/api/whoami" class="nav-item">
                        <span class="icon">[?]</span>
                        <span>/api/whoami - JSON user info</span>
                    </a>
                    <a href="/headers" class="nav-item">
                        <span class="icon">[#]</span>
                        <span>/headers - Authentication headers</span>
                    </a>
                    <a href="/logs" class="nav-item">
                        <span class="icon">[*]</span>
                        <span>/logs - Recent access logs</span>
                    </a>
                    <a href="/health" class="nav-item">
                        <span class="icon">[+]</span>
                        <span>/health - Health check</span>
                    </a>
                </div>
            </div>
            
            <div class="security-note">
                <h4>Security Notice</h4>
                <p>This page is protected by oauth2-proxy with Google authentication. Only users listed in emails.txt can access this application. All requests are logged for security monitoring.</p>
            </div>
        </div>
    </div>
</body>
</html>"""

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
    auth_headers = [
        "X-Forwarded-Email", "X-Forwarded-User", "X-Auth-Request-Email",
        "X-Forwarded-Proto", "X-Forwarded-Host", "X-Forwarded-Uri", 
        "X-Real-IP", "X-Forwarded-For", "CF-Connecting-IP",
        "X-Client-IP", "User-Agent", "Host"
    ]
    
    email = get_email()
    real_ip = get_real_ip()
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authentication Headers - Shark Test</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            margin: 0;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .info-summary {{
            background: #e8f4fd;
            border-left: 4px solid #007bff;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 8px;
        }}
        
        .code-section {{
            margin: 20px 0;
        }}
        
        .code-section h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        
        .code-block {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            font-family: 'Courier New', Monaco, monospace;
            font-size: 14px;
            line-height: 1.4;
            overflow-x: auto;
            white-space: pre-wrap;
        }}
        
        .back-link {{
            display: inline-block;
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-top: 20px;
            transition: transform 0.2s;
        }}
        
        .back-link:hover {{
            transform: translateY(-2px);
        }}
        
        .highlight {{
            color: #007bff;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AUTHENTICATION HEADERS DEBUG</h1>
            <p>Header Analysis and Debugging Information</p>
        </div>
        
        <div class="content">
            <div class="info-summary">
                <h3>Parsed Information Summary</h3>
                <p><strong>Detected Email:</strong> <span class="highlight">{email}</span></p>
                <p><strong>Detected IP:</strong> <span class="highlight">{real_ip}</span></p>
            </div>
            
            <div class="code-section">
                <h3>Authentication Headers</h3>
                <div class="code-block">""" + "\n".join(f"{header}: {request.headers.get(header, 'None')}" for header in auth_headers) + f"""</div>
            </div>
            
            <div class="code-section">
                <h3>All Request Headers</h3>
                <div class="code-block">""" + "\n".join(f"{header}: {value}" for header, value in request.headers) + f"""</div>
            </div>
            
            <a href="/" class="back-link">&larr; Back to Home</a>
        </div>
    </div>
</body>
</html>"""

@app.route("/logs")
def show_logs():
    """Show recent access logs"""
    try:
        with open('/app/access.log', 'r') as f:
            logs = f.readlines()
            # Show last 50 lines
            recent_logs = logs[-50:] if len(logs) > 50 else logs
            
        log_content = ''.join(recent_logs)
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Logs - Shark Test</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            margin: 0;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .log-info {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 8px;
        }}
        
        .log-container {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            height: 500px;
            overflow-y: auto;
            font-family: 'Courier New', Monaco, monospace;
            font-size: 13px;
            line-height: 1.4;
            white-space: pre-wrap;
        }}
        
        .back-link {{
            display: inline-block;
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-top: 20px;
            transition: transform 0.2s;
        }}
        
        .back-link:hover {{
            transform: translateY(-2px);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>RECENT ACCESS LOGS</h1>
            <p>Real-time Activity Monitoring</p>
        </div>
        
        <div class="content">
            <div class="log-info">
                <p><strong>Log Entries:</strong> Showing last {len(recent_logs)} entries</p>
                <p><strong>Auto-refresh:</strong> Reload page to see latest activity</p>
            </div>
            
            <div class="log-container">{log_content}</div>
            
            <a href="/" class="back-link">&larr; Back to Home</a>
        </div>
    </div>
</body>
</html>"""
    except FileNotFoundError:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Logs - Shark Test</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            margin: 0;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .content {{
            padding: 30px;
            text-align: center;
        }}
        
        .no-logs {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }}
        
        .back-link {{
            display: inline-block;
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-top: 20px;
            transition: transform 0.2s;
        }}
        
        .back-link:hover {{
            transform: translateY(-2px);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ACCESS LOGS</h1>
            <p>Activity Monitoring</p>
        </div>
        
        <div class="content">
            <div class="no-logs">
                <h3>No Log File Found</h3>
                <p>Logs will appear here after some requests are made to the application.</p>
            </div>
            
            <a href="/" class="back-link">&larr; Back to Home</a>
        </div>
    </div>
</body>
</html>"""

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

@app.errorhandler(404)
def not_found(error):
    email = get_email()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Page Not Found</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .container {{
            max-width: 500px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            padding: 40px;
            text-align: center;
        }}
        
        .error-code {{
            font-size: 4em;
            font-weight: bold;
            color: #dc3545;
            margin-bottom: 20px;
        }}
        
        .error-message {{
            font-size: 1.2em;
            margin-bottom: 20px;
            color: #6c757d;
        }}
        
        .user-info {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        
        .back-link {{
            display: inline-block;
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-top: 20px;
            transition: transform 0.2s;
        }}
        
        .back-link:hover {{
            transform: translateY(-2px);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="error-code">404</div>
        <div class="error-message">Page Not Found</div>
        <p>The requested page could not be found on this server.</p>
        
        <div class="user-info">
            <strong>Authenticated as:</strong> {email}
        </div>
        
        <a href="/" class="back-link">&larr; Back to Home</a>
    </div>
</body>
</html>""", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
