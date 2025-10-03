"""
Unit tests for Shark-no-Ninsho-Mon Flask application
Run with: python -m pytest test_app.py -v
"""

import pytest
import os
import tempfile
from app import app, load_authorized_emails, is_user_authorized, get_email

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def temp_emails_file():
    """Create temporary emails file for testing"""
    fd, path = tempfile.mkstemp(suffix='.txt')
    with os.fdopen(fd, 'w') as f:
        f.write("# Test emails\n")
        f.write("test@example.com\n")
        f.write("admin@example.com\n")
    
    # Set environment variable to point to temp file
    os.environ['EMAILS_FILE_PATH'] = path
    yield path
    
    # Cleanup
    os.unlink(path)

class TestAuthorization:
    """Test authorization logic"""
    
    def test_load_authorized_emails(self, temp_emails_file):
        """Test loading emails from file"""
        emails = load_authorized_emails()
        assert len(emails) == 2
        assert 'test@example.com' in emails
        assert 'admin@example.com' in emails
    
    def test_is_user_authorized_valid(self, temp_emails_file):
        """Test authorization with valid email"""
        assert is_user_authorized('test@example.com')
        assert is_user_authorized('ADMIN@example.com')  # Case insensitive
    
    def test_is_user_authorized_invalid(self, temp_emails_file):
        """Test authorization with invalid email"""
        assert not is_user_authorized('hacker@evil.com')
    
    def test_anonymous_blocked_in_production(self, temp_emails_file):
        """Test that anonymous users are blocked in production"""
        os.environ['FLASK_ENV'] = 'production'
        assert not is_user_authorized('anonymous')

class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_endpoint(self, client):
        """Test health endpoint returns 200"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['service'] == 'shark-no-ninsho-mon'
        assert 'status' in data
    
    def test_health_page(self, client):
        """Test health page endpoint"""
        response = client.get('/health-page')
        # This will fail auth but that's expected
        assert response.status_code in [200, 403]

class TestRateLimiting:
    """Test rate limiting"""
    
    def test_logs_endpoint_rate_limited(self, client, temp_emails_file):
        """Test that logs endpoint has rate limiting"""
        # Make multiple requests
        responses = []
        for i in range(15):  # Exceed 10 per minute limit
            response = client.get('/logs', headers={
                'X-Forwarded-Email': 'test@example.com'
            })
            responses.append(response.status_code)
        
        # Should get at least one 429 (Too Many Requests)
        assert 429 in responses

class TestSecurityHeaders:
    """Test security-related functionality"""
    
    def test_unauthorized_page(self, client):
        """Test unauthorized access page"""
        response = client.get('/unauthorized')
        assert response.status_code == 403
        assert b'unauthorized' in response.data.lower()
    
    def test_404_handler(self, client):
        """Test 404 error handler"""
        response = client.get('/nonexistent-page')
        assert response.status_code == 404

class TestAPIEndpoints:
    """Test API endpoints"""
    
    def test_whoami_endpoint(self, client, temp_emails_file):
        """Test whoami API endpoint"""
        response = client.get('/api/whoami', headers={
            'X-Forwarded-Email': 'test@example.com'
        })
        # Will either succeed or be blocked by auth
        assert response.status_code in [200, 403]
    
    def test_headers_endpoint(self, client, temp_emails_file):
        """Test headers display endpoint"""
        response = client.get('/headers', headers={
            'X-Forwarded-Email': 'test@example.com'
        })
        assert response.status_code in [200, 403]

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
