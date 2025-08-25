# test_local.py - Local development server with simulated oauth2-proxy headers
import os
import sys
from flask import Flask, request
from app import app

# Override the before_request function to inject test headers
original_before_request = None

def simulate_oauth_headers():
    """Simulate oauth2-proxy headers for local testing"""
    # Store original request environ
    if not hasattr(request, '_test_headers_injected'):
        # Inject test headers into the request
        test_headers = {
            'X-Forwarded-User': '01nicklas07@gmail.com',
            'X-Forwarded-Email': 'test@example.com',  # Can be None
            'X-Auth-Request-Email': None,
            'X-Forwarded-Proto': 'http',
            'X-Forwarded-Host': 'localhost:5000',
            'X-Forwarded-Uri': request.path,
            'X-Real-IP': '127.0.0.1',
            'X-Forwarded-For': '192.168.1.100, 127.0.0.1',
            'User-Agent': 'Test-Browser/1.0'
        }
        
        # Inject headers into request.environ (Flask's header storage)
        for header, value in test_headers.items():
            if value is not None:
                # Convert header name to environ format
                environ_key = f'HTTP_{header.upper().replace("-", "_")}'
                request.environ[environ_key] = value
        
        # Mark as injected to avoid double injection
        request._test_headers_injected = True

# Monkey patch the app to inject headers before each request
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 SHARK LOCAL DEVELOPMENT SERVER")
    print("=" * 60)
    print("📍 URL: http://localhost:5000")
    print("🔐 Simulated User: 01nicklas07@gmail.com")
    print("🌐 Simulated IP: 192.168.1.100")
    print("📝 Log File: ./access.log (local directory)")
    print("=" * 60)
    print()
    
    # Override log file location for local testing
    import logging
    
    # Remove existing file handler and add local one
    for handler in app.logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            app.logger.removeHandler(handler)
    
    # Add local file handler
    local_file_handler = logging.FileHandler('access.log')
    local_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    app.logger.addHandler(local_file_handler)
    
    # Add the header simulation to before_request
    @app.before_request
    def before_request_with_simulation():
        simulate_oauth_headers()
        # Call original logging function from app.py
        from app import log_access
        log_access()
    
    # Run the development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )
