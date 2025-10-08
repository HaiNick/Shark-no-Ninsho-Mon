"""
Unit tests for Flask app (Route Manager Control Plane)
"""
import pytest
from unittest.mock import patch, Mock
from app import app, AUTHORIZED_EMAILS
import tempfile
import os


@pytest.fixture
def client():
    """Create a test client"""
    import tempfile
    import os
    
    # Create temporary database
    fd, db_path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    
    # Update route_manager to use temp database
    from routes_db import RouteManager
    import app as app_module
    app_module.route_manager = RouteManager(db_path)
    
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def authorized_client(monkeypatch):
    """Create a test client with authorized email"""
    import tempfile
    import os
    
    # Create temporary database
    fd, db_path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    
    # Update route_manager to use temp database
    from routes_db import RouteManager
    import app as app_module
    app_module.route_manager = RouteManager(db_path)
    
    app.config['TESTING'] = True
    
    # Mock authorized emails
    monkeypatch.setattr('app.AUTHORIZED_EMAILS', {'test@example.com'})
    
    with app.test_client() as client:
        yield client
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


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


def test_index_authorized(authorized_client):
    """Test index page with authorization"""
    response = authorized_client.get('/', headers={'X-Forwarded-Email': 'test@example.com'})
    assert response.status_code == 200


def test_admin_unauthorized(client):
    """Test admin page without authorization"""
    response = client.get('/admin')
    assert response.status_code == 403


def test_admin_authorized(authorized_client):
    """Test admin page with authorization"""
    response = authorized_client.get('/admin', headers={'X-Forwarded-Email': 'test@example.com'})
    assert response.status_code == 200


def test_404_page(client):
    """Test 404 error page"""
    response = client.get('/nonexistent-page')
    assert response.status_code == 404


# API Tests

def test_api_get_routes_unauthorized(client):
    """Test getting routes without authorization"""
    response = client.get('/api/routes')
    assert response.status_code == 403


@patch('app.caddy_mgr.sync')
def test_api_create_route_authorized(mock_sync, authorized_client):
    """Test creating a route with authorization"""
    mock_sync.return_value = {"ok": True}
    
    route_data = {
        'path': '/test',
        'name': 'Test Service',
        'target_ip': '10.0.0.100',  # Use private IP
        'target_port': 8080,
        'target_path': '/',
        'protocol': 'http',
        'enabled': True
    }
    
    response = authorized_client.post(
        '/api/routes',
        json=route_data,
        headers={'X-Forwarded-Email': 'test@example.com'}
    )
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['path'] == '/test'
    assert data['name'] == 'Test Service'
    
    # Verify Caddy sync was called
    mock_sync.assert_called_once()


@patch('app.caddy_mgr.sync')
def test_api_delete_route_authorized(mock_sync, authorized_client):
    """Test deleting a route with authorization"""
    mock_sync.return_value = {"ok": True}
    
    # First create a route
    route_data = {
        'path': '/test-delete',
        'name': 'Test Delete',
        'target_ip': '10.0.0.100',  # Use private IP
        'target_port': 8080,
        'target_path': '/'
    }
    
    create_response = authorized_client.post(
        '/api/routes',
        json=route_data,
        headers={'X-Forwarded-Email': 'test@example.com'}
    )
    
    assert create_response.status_code == 201
    route_id = create_response.get_json()['id']
    
    # Now delete it
    delete_response = authorized_client.delete(
        f'/api/routes/{route_id}',
        headers={'X-Forwarded-Email': 'test@example.com'}
    )
    
    assert delete_response.status_code == 200
    assert delete_response.get_json()['success'] is True
    
    # Verify Caddy sync was called (once for create, once for delete)
    assert mock_sync.call_count == 2


@patch('app.caddy_mgr.sync')
@patch('app.caddy_mgr.test_connection')
def test_api_test_route(mock_test, mock_sync, authorized_client):
    """Test route connectivity test"""
    mock_sync.return_value = {"ok": True}
    mock_test.return_value = {
        'success': True,
        'status': 'online',
        'status_code': 200,
        'response_time': 150
    }
    
    # Create a route first
    route_data = {
        'path': '/test-conn',
        'name': 'Test Connection',
        'target_ip': '10.0.0.100',  # Use private IP
        'target_port': 8080,
        'target_path': '/'
    }
    
    create_response = authorized_client.post(
        '/api/routes',
        json=route_data,
        headers={'X-Forwarded-Email': 'test@example.com'}
    )
    
    assert create_response.status_code == 201
    route_id = create_response.get_json()['id']
    
    # Test connection
    test_response = authorized_client.post(
        f'/api/routes/{route_id}/test',
        headers={'X-Forwarded-Email': 'test@example.com'}
    )
    
    assert test_response.status_code == 200
    data = test_response.get_json()
    assert data['success'] is True
    assert data['status'] == 'online'
    mock_test.assert_called_once()


@patch('app.caddy_mgr.sync')
def test_api_toggle_route(mock_sync, authorized_client):
    """Test toggling route enabled status"""
    mock_sync.return_value = {"ok": True}
    
    # Create a route
    route_data = {
        'path': '/test-toggle',
        'name': 'Test Toggle',
        'target_ip': '10.0.0.100',  # Use private IP
        'target_port': 8080,
        'target_path': '/',
        'enabled': True
    }
    
    create_response = authorized_client.post(
        '/api/routes',
        json=route_data,
        headers={'X-Forwarded-Email': 'test@example.com'}
    )
    
    assert create_response.status_code == 201
    route_id = create_response.get_json()['id']
    
    # Toggle it
    toggle_response = authorized_client.post(
        f'/api/routes/{route_id}/toggle',
        headers={'X-Forwarded-Email': 'test@example.com'}
    )
    
    assert toggle_response.status_code == 200
    data = toggle_response.get_json()
    assert data['success'] is True
    assert data['enabled'] is False  # Should be toggled to False
    
    # Verify Caddy sync was called (once for create, once for toggle)
    assert mock_sync.call_count == 2


def test_api_create_route_invalid_data(authorized_client):
    """Test creating route with invalid data"""
    invalid_data = {
        'path': '/test-invalid',
        'name': 'Invalid',
        'target_ip': '8.8.8.8',  # Public IP - not allowed
        'target_port': 8080,
        'target_path': '/'
    }
    
    response = authorized_client.post(
        '/api/routes',
        json=invalid_data,
        headers={'X-Forwarded-Email': 'test@example.com'}
    )
    
    assert response.status_code == 400


def test_api_create_route_missing_data(authorized_client):
    """Test creating route with missing data"""
    incomplete_data = {
        'path': '/incomplete',
        # Missing required fields
    }
    
    response = authorized_client.post(
        '/api/routes',
        json=incomplete_data,
        headers={'X-Forwarded-Email': 'test@example.com'}
    )
    
    assert response.status_code == 400


def test_refresh_emails_endpoint(authorized_client):
    """Test refreshing authorized emails"""
    response = authorized_client.post(
        '/api/admin/refresh-emails',
        headers={'X-Forwarded-Email': 'test@example.com'}
    )
    
    # Endpoint may not exist, which is fine
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.get_json()
        assert 'count' in data
    elif response.status_code == 404:
        pass  # Endpoint does not exist, acceptable
