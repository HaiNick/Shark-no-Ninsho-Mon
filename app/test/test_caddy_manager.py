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

    # The portal matches all known Flask paths
    paths = route["match"][0]["path"]
    assert "/" in paths
    assert "/admin" in paths
    assert "/static/*" in paths
    assert "/api/*" in paths
    assert "/health" in paths

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


def test_build_config_includes_enabled_routes(caddy_manager, sample_routes):
    """Test that enabled routes are included in config"""
    config = caddy_manager._build_config(sample_routes)
    routes = config["apps"]["http"]["servers"]["srv0"]["routes"]

    # Should have: 2 enabled backend routes + 1 disabled redirect + 1 flask portal = 4
    assert len(routes) == 4

    # Extract all route paths from match rules
    all_paths = []
    for route in routes:
        if route.get("match") and route["match"][0].get("path"):
            all_paths.extend(route["match"][0]["path"])

    # Enabled routes must be present
    assert "/jellyfin" in all_paths
    assert "/grafana" in all_paths
    # Disabled route gets a redirect handler, so its path is still in match rules
    assert "/disabled" in all_paths


def test_build_config_flask_portal_always_included(caddy_manager):
    """Test that Flask portal route is always included"""
    config = caddy_manager._build_config([])
    routes = config["apps"]["http"]["servers"]["srv0"]["routes"]

    # Should have at least Flask portal
    assert len(routes) >= 1

    # Last route should be the flask portal (catch-all)
    portal = routes[-1]
    assert "/" in portal["match"][0]["path"]
    assert portal["handle"][0]["handler"] == "reverse_proxy"
    assert portal["handle"][0]["upstreams"] == [{"dial": "app:8000"}]


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


@patch('caddy_manager.requests.patch')
def test_sync_success(mock_patch, caddy_manager, sample_routes):
    """Test successful sync to Caddy via PATCH"""
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_patch.return_value = mock_response

    result = caddy_manager.sync(sample_routes)

    assert result == {"ok": True}
    mock_patch.assert_called_once()
    assert "/config/apps/http/servers/srv0/routes" in mock_patch.call_args[0][0]


@patch('caddy_manager.requests.patch')
def test_sync_non_json_response(mock_patch, caddy_manager, sample_routes):
    """Test sync with non-JSON success response"""
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_patch.return_value = mock_response

    result = caddy_manager.sync(sample_routes)

    assert result == {"ok": True}


@patch('caddy_manager.requests.put')
@patch('caddy_manager.requests.delete')
@patch('caddy_manager.requests.patch')
def test_sync_patch_fails_falls_back_to_put(mock_patch, mock_delete, mock_put, caddy_manager, sample_routes):
    """Test that sync falls back to DELETE+PUT when PATCH fails"""
    # PATCH fails
    mock_patch_resp = Mock()
    mock_patch_resp.ok = False
    mock_patch_resp.status_code = 409
    mock_patch_resp.text = "conflict"
    mock_patch.return_value = mock_patch_resp

    # DELETE succeeds
    mock_delete_resp = Mock()
    mock_delete_resp.status_code = 200
    mock_delete.return_value = mock_delete_resp

    # PUT succeeds
    mock_put_resp = Mock()
    mock_put_resp.ok = True
    mock_put_resp.status_code = 200
    mock_put_resp.raise_for_status = Mock()
    mock_put.return_value = mock_put_resp

    result = caddy_manager.sync(sample_routes)

    assert result == {"ok": True}
    mock_patch.assert_called_once()
    mock_delete.assert_called_once()
    mock_put.assert_called_once()


@patch('caddy_manager.requests.put')
@patch('caddy_manager.requests.delete')
@patch('caddy_manager.requests.patch')
def test_sync_http_error(mock_patch, mock_delete, mock_put, caddy_manager, sample_routes):
    """Test sync with HTTP error on all attempts"""
    # PATCH fails
    mock_patch_resp = Mock()
    mock_patch_resp.ok = False
    mock_patch_resp.status_code = 500
    mock_patch_resp.text = "server error"
    mock_patch.return_value = mock_patch_resp

    # DELETE succeeds
    mock_delete.return_value = Mock(status_code=200)

    # PUT also fails
    mock_put_resp = Mock()
    mock_put_resp.ok = False
    mock_put_resp.status_code = 500
    mock_put_resp.text = "server error"
    mock_put_resp.raise_for_status.side_effect = Exception("Server error")
    mock_put.return_value = mock_put_resp

    with pytest.raises(Exception):
        caddy_manager.sync(sample_routes)


@patch('caddy_manager.requests.get')
@patch('socket.create_connection')
@patch('socket.getaddrinfo')
@patch('config.get_settings')
def test_connection_success(mock_get_settings, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
    """Test successful connection test"""
    # Mock settings
    mock_settings = Mock()
    mock_settings.http_timeout_sec = 3
    mock_settings.slow_threshold_ms = 2000
    mock_get_settings.return_value = mock_settings

    # Mock DNS and TCP
    mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.100', 8096))]
    mock_create_connection.return_value.__enter__ = Mock()
    mock_create_connection.return_value.__exit__ = Mock()

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
    assert result["state"] in ["UP", "DEGRADED"]
    assert result["status_code"] == 200
    assert "response_time" in result


@patch('caddy_manager.requests.get')
@patch('socket.create_connection')
@patch('socket.getaddrinfo')
@patch('config.get_settings')
def test_connection_timeout(mock_get_settings, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
    """Test connection timeout"""
    import requests

    # Mock settings
    mock_settings = Mock()
    mock_settings.http_timeout_sec = 3
    mock_settings.slow_threshold_ms = 2000
    mock_get_settings.return_value = mock_settings

    # Mock DNS and TCP
    mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.100', 8096))]
    mock_create_connection.return_value.__enter__ = Mock()
    mock_create_connection.return_value.__exit__ = Mock()

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
    assert result["state"] == "DOWN"
    assert result["reason"] == "timeout"


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
@patch('socket.create_connection')
@patch('socket.getaddrinfo')
@patch('config.get_settings')
def test_connection_server_error(mock_get_settings, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
    """Test connection with server error response"""
    # Mock settings
    mock_settings = Mock()
    mock_settings.http_timeout_sec = 3
    mock_settings.slow_threshold_ms = 2000
    mock_get_settings.return_value = mock_settings

    # Mock DNS and TCP
    mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.100', 8096))]
    mock_create_connection.return_value.__enter__ = Mock()
    mock_create_connection.return_value.__exit__ = Mock()

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

    assert result["success"] is False  # Changed: 5xx errors are now considered DOWN
    assert result["status"] == "error"
    assert result["state"] == "DOWN"
    assert result["reason"] == "error_5xx"
    assert result["status_code"] == 500


@patch('caddy_manager.requests.get')
@patch('socket.create_connection')
@patch('socket.getaddrinfo')
@patch('config.get_settings')
def test_connection_slow_response(mock_get_settings, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
    """Test slow connection detection"""
    import time

    # Mock settings
    mock_settings = Mock()
    mock_settings.http_timeout_sec = 3
    mock_settings.slow_threshold_ms = 2000
    mock_get_settings.return_value = mock_settings

    # Mock DNS and TCP
    mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.100', 8096))]
    mock_create_connection.return_value.__enter__ = Mock()
    mock_create_connection.return_value.__exit__ = Mock()

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
    assert result["state"] == "DEGRADED"
    assert result["reason"] == "slow"
    assert result["response_time"] > 2000


def test_connection_uses_timeout(caddy_manager):
    """Test that connection test respects timeout setting"""
    with patch('config.get_settings') as mock_get_settings:
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            with patch('socket.create_connection') as mock_create_connection:
                with patch('caddy_manager.requests.get') as mock_get:
                    # Mock settings
                    mock_settings = Mock()
                    mock_settings.http_timeout_sec = 3  # Config default is 3s
                    mock_settings.slow_threshold_ms = 2000
                    mock_get_settings.return_value = mock_settings

                    # Mock DNS and TCP
                    mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.100', 8096))]
                    mock_create_connection.return_value.__enter__ = Mock()
                    mock_create_connection.return_value.__exit__ = Mock()

                    route = {
                        "target_ip": "192.168.1.100",
                        "target_port": 8096,
                        "protocol": "http",
                        "timeout": 15
                    }

                    caddy_manager.test_connection(route)

                    # Should use min(route_timeout, config_timeout) = min(15, 3) = 3
                    assert mock_get.call_args[1]["timeout"] == 3


def test_connection_uses_protocol(caddy_manager):
    """Test that connection test uses correct protocol"""
    with patch('config.get_settings') as mock_get_settings:
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            with patch('socket.create_connection') as mock_create_connection:
                with patch('caddy_manager.requests.get') as mock_get:
                    # Mock settings
                    mock_settings = Mock()
                    mock_settings.http_timeout_sec = 3
                    mock_settings.slow_threshold_ms = 2000
                    mock_get_settings.return_value = mock_settings

                    # Mock DNS and TCP
                    mock_getaddrinfo.return_value = [(None, None, None, None, ('192.168.1.100', 8443))]
                    mock_create_connection.return_value.__enter__ = Mock()
                    mock_create_connection.return_value.__exit__ = Mock()

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
