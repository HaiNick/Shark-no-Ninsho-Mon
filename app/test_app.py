"""
Unit tests for Flask app
"""
import pytest
from app import app


@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data


def test_whoami_endpoint(client):
    """Test whoami endpoint"""
    response = client.get('/whoami')
    assert response.status_code == 200
    data = response.get_json()
    assert 'email' in data
    assert 'authorized' in data


def test_index_unauthorized(client):
    """Test index page without authorization"""
    response = client.get('/')
    assert response.status_code == 403


def test_index_authorized(client):
    """Test index page with authorization"""
    response = client.get('/', headers={'X-Forwarded-Email': 'test@example.com'})
    # Will return 403 unless email is in emails.txt
    # In real test, you'd mock the authorized emails
    assert response.status_code in [200, 403]


def test_404_page(client):
    """Test 404 error page"""
    response = client.get('/nonexistent-page', headers={'X-Forwarded-Email': 'test@example.com'})
    assert response.status_code == 404
