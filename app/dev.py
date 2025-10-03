"""
Development entry point - Runs Flask app without OAuth2 requirements
"""
import os
os.environ['FLASK_ENV'] = 'development'
os.environ['DEBUG'] = 'True'

# Mock the emails file if it doesn't exist
if not os.path.exists('emails.txt'):
    with open('emails.txt', 'w') as f:
        f.write('dev@localhost\n')

from app import app, get_user_email
from flask import request

# Override get_user_email for development
original_get_user_email = get_user_email

def dev_get_user_email():
    """Return a dev email for testing"""
    # Check if header exists (for testing with headers)
    email = request.headers.get('X-Forwarded-Email', '').lower()
    if email:
        return email
    # Default to dev email
    return 'dev@localhost'

# Monkey patch for development
app.before_request_funcs.setdefault(None, []).insert(0, lambda: None)

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 DEVELOPMENT MODE - Authentication Bypassed")
    print("=" * 60)
    print(f"📍 URL: http://localhost:8000")
    print(f"👤 Logged in as: dev@localhost")
    print(f"🔓 All routes accessible without OAuth2")
    print("=" * 60)
    print()
    
    # Replace the get_user_email function
    import app as app_module
    app_module.get_user_email = dev_get_user_email
    
    # Add dev email to authorized list
    from app import AUTHORIZED_EMAILS
    AUTHORIZED_EMAILS.add('dev@localhost')
    
    app.run(host='0.0.0.0', port=8000, debug=True)
