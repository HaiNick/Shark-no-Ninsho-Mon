"""
Unit tests for RouteManager (TinyDB wrapper)
"""
import pytest
import os
import tempfile
from routes_db import RouteManager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    
    manager = RouteManager(path)
    yield manager
    
    # Cleanup
    os.unlink(path)


def test_add_route(temp_db):
    """Test adding a new route"""
    route = temp_db.add_route(
        path='/test',
        name='Test Service',
        target_ip='192.168.1.100',
        target_port=8080
    )
    
    assert route['path'] == '/test'
    assert route['name'] == 'Test Service'
    assert route['target_ip'] == '192.168.1.100'
    assert route['target_port'] == 8080
    assert 'id' in route


def test_add_duplicate_route_fails(temp_db):
    """Test that adding duplicate path fails"""
    temp_db.add_route(
        path='/test',
        name='Test Service',
        target_ip='192.168.1.100',
        target_port=8080
    )
    
    with pytest.raises(ValueError, match="already exists"):
        temp_db.add_route(
            path='/test',
            name='Another Service',
            target_ip='192.168.1.101',
            target_port=8081
        )


def test_get_all_routes(temp_db):
    """Test getting all routes"""
    temp_db.add_route('/test1', 'Test 1', '192.168.1.100', 8080)
    temp_db.add_route('/test2', 'Test 2', '192.168.1.101', 8081)
    
    routes = temp_db.get_all_routes()
    assert len(routes) == 2


def test_get_route_by_path(temp_db):
    """Test getting route by path"""
    temp_db.add_route('/test', 'Test Service', '192.168.1.100', 8080)
    
    route = temp_db.get_route_by_path('/test')
    assert route is not None
    assert route['name'] == 'Test Service'


def test_get_route_by_id(temp_db):
    """Test getting route by ID"""
    added = temp_db.add_route('/test', 'Test Service', '192.168.1.100', 8080)
    
    route = temp_db.get_route_by_id(added['id'])
    assert route is not None
    assert route['path'] == '/test'


def test_update_route(temp_db):
    """Test updating a route"""
    added = temp_db.add_route('/test', 'Test Service', '192.168.1.100', 8080)
    
    success = temp_db.update_route(added['id'], {'name': 'Updated Service'})
    assert success
    
    route = temp_db.get_route_by_id(added['id'])
    assert route['name'] == 'Updated Service'


def test_delete_route(temp_db):
    """Test deleting a route"""
    added = temp_db.add_route('/test', 'Test Service', '192.168.1.100', 8080)
    
    success = temp_db.delete_route(added['id'])
    assert success
    
    route = temp_db.get_route_by_id(added['id'])
    assert route is None


def test_validate_path(temp_db):
    """Test path validation"""
    # Valid paths
    assert temp_db.validate_path('/test') == '/test'
    assert temp_db.validate_path('test') == '/test'  # Adds leading slash
    assert temp_db.validate_path('/test-service') == '/test-service'
    assert temp_db.validate_path('/test_service') == '/test_service'
    
    # Invalid paths
    with pytest.raises(ValueError):
        temp_db.validate_path('')
    
    with pytest.raises(ValueError):
        temp_db.validate_path('/test service')  # Space not allowed


def test_validate_ip_private_only(temp_db):
    """Test IP validation - only private IPs allowed"""
    # Valid private IPs
    temp_db.validate_ip('192.168.1.100')
    temp_db.validate_ip('10.0.0.1')
    temp_db.validate_ip('172.16.0.1')
    
    # Invalid IPs
    with pytest.raises(ValueError, match="Only private IP"):
        temp_db.validate_ip('8.8.8.8')  # Public IP
    
    with pytest.raises(ValueError, match="Localhost"):
        temp_db.validate_ip('127.0.0.1')  # Localhost
    
    with pytest.raises(ValueError, match="metadata"):
        temp_db.validate_ip('169.254.169.254')  # Cloud metadata


def test_validate_port(temp_db):
    """Test port validation"""
    # Valid ports
    temp_db.validate_port(80)
    temp_db.validate_port(8080)
    temp_db.validate_port(65535)
    
    # Invalid ports
    with pytest.raises(ValueError):
        temp_db.validate_port(0)
    
    with pytest.raises(ValueError):
        temp_db.validate_port(65536)
    
    with pytest.raises(ValueError):
        temp_db.validate_port(-1)


def test_enabled_only_filter(temp_db):
    """Test filtering for enabled routes only"""
    temp_db.add_route('/test1', 'Test 1', '192.168.1.100', 8080, enabled=True)
    temp_db.add_route('/test2', 'Test 2', '192.168.1.101', 8081, enabled=False)
    
    all_routes = temp_db.get_all_routes()
    enabled_routes = temp_db.get_all_routes(enabled_only=True)
    
    assert len(all_routes) == 2
    assert len(enabled_routes) == 1
    assert enabled_routes[0]['path'] == '/test1'
