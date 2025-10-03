"""
Unit tests for ProxyHandler
"""
import pytest
from unittest.mock import Mock, patch
import tempfile
import os
from routes_db import RouteManager
from proxy_handler import ProxyHandler


@pytest.fixture
def temp_manager():
    """Create a temporary route manager"""
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    
    manager = RouteManager(path)
    yield manager
    
    os.unlink(path)


@pytest.fixture
def proxy_handler(temp_manager):
    """Create a proxy handler with temp manager"""
    return ProxyHandler(temp_manager)


def test_build_target_url(proxy_handler, temp_manager):
    """Test URL building"""
    route = temp_manager.add_route(
        '/test',
        'Test Service',
        '192.168.1.100',
        8080,
        protocol='http'
    )
    
    url = proxy_handler._build_target_url(route, '/dashboard')
    assert url == 'http://192.168.1.100:8080/dashboard'


def test_build_target_url_https(proxy_handler, temp_manager):
    """Test HTTPS URL building"""
    route = temp_manager.add_route(
        '/test',
        'Test Service',
        '192.168.1.100',
        8443,
        protocol='https'
    )
    
    url = proxy_handler._build_target_url(route, '/api')
    assert url == 'https://192.168.1.100:8443/api'


def test_prepare_headers(proxy_handler, temp_manager):
    """Test header preparation"""
    route = temp_manager.add_route(
        '/test',
        'Test Service',
        '192.168.1.100',
        8080
    )
    
    # Mock Flask request
    with patch('proxy_handler.request') as mock_request:
        mock_request.headers = [
            ('User-Agent', 'TestAgent'),
            ('Accept', 'application/json'),
            ('Host', 'original-host.com')
        ]
        mock_request.remote_addr = '10.0.0.1'
        mock_request.scheme = 'https'
        mock_request.host = 'proxy-host.com'
        
        headers = proxy_handler._prepare_headers(route)
        
        assert 'X-Forwarded-For' in headers
        assert headers['X-Forwarded-For'] == '10.0.0.1'
        assert 'X-Forwarded-Proto' in headers
        assert 'X-Forwarded-Host' in headers


def test_test_connection_success(proxy_handler, temp_manager):
    """Test connection testing - success"""
    route = temp_manager.add_route(
        '/test',
        'Test Service',
        '192.168.1.100',
        8080
    )
    
    with patch('proxy_handler.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = proxy_handler.test_connection(route['id'])
        
        assert result['success'] is True
        assert result['status'] == 'online'


def test_test_connection_timeout(proxy_handler, temp_manager):
    """Test connection testing - timeout"""
    route = temp_manager.add_route(
        '/test',
        'Test Service',
        '192.168.1.100',
        8080
    )
    
    with patch('proxy_handler.requests.get') as mock_get:
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        result = proxy_handler.test_connection(route['id'])
        
        assert result['success'] is False
        assert result['status'] == 'timeout'


def test_test_connection_offline(proxy_handler, temp_manager):
    """Test connection testing - offline"""
    route = temp_manager.add_route(
        '/test',
        'Test Service',
        '192.168.1.100',
        8080
    )
    
    with patch('proxy_handler.requests.get') as mock_get:
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        result = proxy_handler.test_connection(route['id'])
        
        assert result['success'] is False
        assert result['status'] == 'offline'
