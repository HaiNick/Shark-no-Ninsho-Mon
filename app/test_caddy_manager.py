"""
Unit tests for CaddyManager
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from caddy_manager import CaddyManager


@pytest.fixture
def caddy_manager():
    """Create a CaddyManager instance"""
    return CaddyManager(admin_url="http://localhost:2019", listen_port=8080, flask_upstream="app:8000")


@pytest.fixture
def sample_routes():
    """Sample routes for testing"""
    return [
        {
            "id": "1",
            "path": "/jellyfin",
            "name": "Jellyfin",
            "target_ip": "192.168.1.100",
            "target_port": 8096,
            "protocol": "http",
            "enabled": True,
            "preserve_host": False
        },
        {
            "id": "2",
            "path": "/grafana",
            "name": "Grafana",
            "target_ip": "192.168.1.101",
            "target_port": 3000,
            "protocol": "http",
            "enabled": True,
            "preserve_host": True
        },
        {
            "id": "3",
            "path": "/disabled",
            "name": "Disabled Service",
            "target_ip": "192.168.1.102",
            "target_port": 8080,
            "protocol": "http",
            "enabled": False,
            "preserve_host": False
        }
    ]


def test_caddy_manager_init():
    """Test CaddyManager initialization"""
    mgr = CaddyManager()
    assert mgr.admin_url == "http://caddy:2019"
    assert mgr.listen_port == 8080
    assert mgr.flask_upstream == "app:8000"


def test_caddy_manager_custom_init():
    """Test CaddyManager with custom parameters"""
    mgr = CaddyManager(admin_url="http://custom:3000", listen_port=9090, flask_upstream="flask:5000")
    assert mgr.admin_url == "http://custom:3000"
    assert mgr.listen_port == 9090
    assert mgr.flask_upstream == "flask:5000"


def test_flask_portal_route(caddy_manager):
    """Test Flask portal route generation"""
    route = caddy_manager._flask_portal_route()
    
    assert route["match"] == [{"path": ["/", "/static/*"]}]
    assert route["handle"][0]["handler"] == "reverse_proxy"
    assert route["handle"][0]["upstreams"] == [{"dial": "app:8000"}]
    assert route["handle"][0]["headers"]["request"]["set"]["X-Forwarded-Prefix"] == ["/"]
    assert route["terminal"] is False


def test_subdir_reverse_proxy_route(caddy_manager):
    """Test subdir reverse proxy route generation"""
    route = caddy_manager._subdir_reverse_proxy_route("/jellyfin", "http", "192.168.1.100:8096", preserve_host=False)
    
    assert route["match"] == [{"path": ["/jellyfin", "/jellyfin/*"]}]
    assert route["handle"][0]["handler"] == "reverse_proxy"
    assert route["handle"][0]["upstreams"] == [{"dial": "192.168.1.100:8096"}]
    assert route["handle"][0]["headers"]["request"]["set"]["X-Forwarded-Prefix"] == ["/jellyfin"]
    assert route["terminal"] is True


def test_subdir_reverse_proxy_route_with_preserve_host(caddy_manager):
    """Test subdir route with host preservation"""
    route = caddy_manager._subdir_reverse_proxy_route("/grafana", "http", "192.168.1.101:3000", preserve_host=True)
    
    assert route["handle"][0]["headers"]["request"]["set"]["Host"] == ["{http.request.host}"]


def test_build_config_structure(caddy_manager, sample_routes):
    """Test full config structure"""
    config = caddy_manager._build_config(sample_routes)
    
    # Check admin config
    assert config["admin"]["listen"] == ":2019"
    
    # Check HTTP app
    assert "http" in config["apps"]
    assert "srv0" in config["apps"]["http"]["servers"]
    
    # Check server config
    server = config["apps"]["http"]["servers"]["srv0"]
    assert server["listen"] == [":8080"]
    assert server["allow_h2c"] is True
    assert "routes" in server


def test_build_config_enabled_routes_only(caddy_manager, sample_routes):
    """Test that disabled routes are excluded"""
    config = caddy_manager._build_config(sample_routes)
    routes = config["apps"]["http"]["servers"]["srv0"]["routes"]
    
    # Should have Flask portal + 2 enabled routes (not the disabled one)
    assert len(routes) == 3
    
    # Extract route paths
    paths = []
    for route in routes:
        if route.get("match") and route["match"][0].get("path"):
            paths.extend(route["match"][0]["path"])
    
    assert "/jellyfin" in paths
    assert "/grafana" in paths
    assert "/disabled" not in paths


def test_build_config_flask_portal_always_included(caddy_manager):
    """Test that Flask portal route is always included"""
    config = caddy_manager._build_config([])
    routes = config["apps"]["http"]["servers"]["srv0"]["routes"]
    
    # Should have at least Flask portal
    assert len(routes) >= 1
    assert routes[0]["match"] == [{"path": ["/", "/static/*"]}]


def test_build_config_invalid_routes_skipped(caddy_manager):
    """Test that invalid routes are skipped"""
    invalid_routes = [
        {"path": "", "target_ip": "192.168.1.100", "target_port": 8080, "enabled": True},  # Empty path
        {"target_ip": "192.168.1.101", "target_port": 8080, "enabled": True},  # No path
        {"path": "no-slash", "target_ip": "192.168.1.102", "target_port": 8080, "enabled": True},  # No leading slash
    ]
    
    config = caddy_manager._build_config(invalid_routes)
    routes = config["apps"]["http"]["servers"]["srv0"]["routes"]
    
    # Should only have Flask portal
    assert len(routes) == 1


@patch('caddy_manager.requests.put')
def test_sync_success(mock_put, caddy_manager, sample_routes):
    """Test successful sync to Caddy"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"status": "ok"}
    mock_put.return_value = mock_response
    
    result = caddy_manager.sync(sample_routes)
    
    assert result == {"status": "ok"}
    mock_put.assert_called_once()
    assert mock_put.call_args[0][0] == "http://localhost:2019/config"


@patch('caddy_manager.requests.put')
def test_sync_non_json_response(mock_put, caddy_manager, sample_routes):
    """Test sync with non-JSON response"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain"}
    mock_put.return_value = mock_response
    
    result = caddy_manager.sync(sample_routes)
    
    assert result == {"ok": True}


@patch('caddy_manager.requests.put')
def test_sync_http_error(mock_put, caddy_manager, sample_routes):
    """Test sync with HTTP error"""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("Server error")
    mock_put.return_value = mock_response
    
    with pytest.raises(Exception):
        caddy_manager.sync(sample_routes)


@patch('caddy_manager.requests.get')
def test_connection_success(mock_get, caddy_manager):
    """Test successful connection test"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    route = {
        "target_ip": "192.168.1.100",
        "target_port": 8096,
        "protocol": "http",
        "timeout": 30
    }
    
    result = caddy_manager.test_connection(route)
    
    assert result["success"] is True
    assert result["status"] in ["online", "slow"]
    assert result["status_code"] == 200
    assert "response_time" in result


@patch('caddy_manager.requests.get')
def test_connection_timeout(mock_get, caddy_manager):
    """Test connection timeout"""
    import requests
    mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
    
    route = {
        "target_ip": "192.168.1.100",
        "target_port": 8096,
        "protocol": "http",
        "timeout": 5
    }
    
    result = caddy_manager.test_connection(route)
    
    assert result["success"] is False
    assert result["status"] == "timeout"


@patch('caddy_manager.requests.get')
def test_connection_refused(mock_get, caddy_manager):
    """Test connection refused"""
    import requests
    mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
    
    route = {
        "target_ip": "192.168.1.100",
        "target_port": 8096,
        "protocol": "http",
        "timeout": 5
    }
    
    result = caddy_manager.test_connection(route)
    
    assert result["success"] is False
    assert result["status"] == "offline"


@patch('caddy_manager.requests.get')
def test_connection_server_error(mock_get, caddy_manager):
    """Test connection with server error response"""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response
    
    route = {
        "target_ip": "192.168.1.100",
        "target_port": 8096,
        "protocol": "http",
        "timeout": 30
    }
    
    result = caddy_manager.test_connection(route)
    
    assert result["success"] is True
    assert result["status"] == "error"
    assert result["status_code"] == 500


@patch('caddy_manager.requests.get')
def test_connection_slow_response(mock_get, caddy_manager):
    """Test slow connection detection"""
    import time
    
    def slow_request(*args, **kwargs):
        time.sleep(2.5)  # Simulate slow response
        mock_response = Mock()
        mock_response.status_code = 200
        return mock_response
    
    mock_get.side_effect = slow_request
    
    route = {
        "target_ip": "192.168.1.100",
        "target_port": 8096,
        "protocol": "http",
        "timeout": 30
    }
    
    result = caddy_manager.test_connection(route)
    
    assert result["success"] is True
    assert result["status"] == "slow"
    assert result["response_time"] > 2000


def test_connection_uses_timeout(caddy_manager):
    """Test that connection test respects timeout setting"""
    with patch('caddy_manager.requests.get') as mock_get:
        route = {
            "target_ip": "192.168.1.100",
            "target_port": 8096,
            "protocol": "http",
            "timeout": 15
        }
        
        caddy_manager.test_connection(route)
        
        # Should use min(timeout, 10) = 10
        assert mock_get.call_args[1]["timeout"] == 10


def test_connection_uses_protocol(caddy_manager):
    """Test that connection test uses correct protocol"""
    with patch('caddy_manager.requests.get') as mock_get:
        route = {
            "target_ip": "192.168.1.100",
            "target_port": 8443,
            "protocol": "https",
            "timeout": 30
        }
        
        caddy_manager.test_connection(route)
        
        assert mock_get.call_args[0][0] == "https://192.168.1.100:8443/"


def test_sync_builds_valid_json(caddy_manager, sample_routes):
    """Test that sync produces valid JSON"""
    config = caddy_manager._build_config(sample_routes)
    
    # Should be JSON serializable
    json_str = json.dumps(config)
    assert json_str is not None
    
    # Should be parseable
    parsed = json.loads(json_str)
    assert parsed == config
