"""
Unit tests for service status classification logic
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import socket
import requests
from caddy_manager import CaddyManager


@pytest.fixture
def caddy_manager():
    """Create a CaddyManager instance"""
    return CaddyManager(admin_url="http://localhost:2019", listen_port=8080, flask_upstream="app:8000")


class TestClassifyServiceStatus:
    """Test the new classify_service_status method"""

    def test_misconfig_invalid_url(self, caddy_manager):
        """Test misconfig state for invalid URL"""
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "not-a-valid-url", 3, 2000
        )
        assert state == "DOWN"
        assert reason == "misconfig"
        assert "Invalid URL" in detail or "parse error" in detail.lower()
        assert http_status is None
        assert duration_ms is None

    def test_misconfig_missing_scheme(self, caddy_manager):
        """Test misconfig state for URL without scheme"""
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "example.com:8080", 3, 2000
        )
        assert state == "DOWN"
        assert reason == "misconfig"
        assert http_status is None

    @patch('socket.getaddrinfo')
    def test_offline_dns_error(self, mock_getaddrinfo, caddy_manager):
        """Test offline_dns state for DNS resolution failure"""
        mock_getaddrinfo.side_effect = socket.gaierror("Name or service not known")
        
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "http://nonexistent.example.com:8080/", 3, 2000
        )
        assert state == "DOWN"
        assert reason == "offline_dns"
        assert "DNS error" in detail
        assert http_status is None

    @patch('socket.create_connection')
    @patch('socket.getaddrinfo')
    def test_offline_conn_refused(self, mock_getaddrinfo, mock_create_connection, caddy_manager):
        """Test offline_conn state for connection refused"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 8080))]
        mock_create_connection.side_effect = ConnectionRefusedError("Connection refused")
        
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "http://192.168.1.100:8080/", 3, 2000
        )
        assert state == "DOWN"
        assert reason == "offline_conn"
        assert "TCP connect failed" in detail
        assert http_status is None

    @patch('socket.create_connection')
    @patch('socket.getaddrinfo')
    def test_offline_conn_timeout(self, mock_getaddrinfo, mock_create_connection, caddy_manager):
        """Test offline_conn state for connection timeout"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 8080))]
        mock_create_connection.side_effect = TimeoutError("Connection timed out")
        
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "http://192.168.1.100:8080/", 3, 2000
        )
        assert state == "DOWN"
        assert reason == "offline_conn"
        assert http_status is None

    @patch('requests.get')
    @patch('socket.create_connection')
    @patch('socket.getaddrinfo')
    def test_timeout_http_request(self, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
        """Test timeout state for HTTP request timeout"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 8080))]
        mock_create_connection.return_value.__enter__ = Mock()
        mock_create_connection.return_value.__exit__ = Mock()
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
        
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "http://192.168.1.100:8080/", 3, 2000
        )
        assert state == "DOWN"
        assert reason == "timeout"
        assert "timeout after 3s" in detail
        assert http_status is None

    @patch('requests.get')
    @patch('socket.create_connection')
    @patch('socket.getaddrinfo')
    def test_error_5xx_response(self, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
        """Test error_5xx state for 5xx HTTP responses"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 8080))]
        mock_create_connection.return_value.__enter__ = Mock()
        mock_create_connection.return_value.__exit__ = Mock()
        
        mock_response = Mock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response
        
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "http://192.168.1.100:8080/", 3, 2000
        )
        assert state == "DOWN"
        assert reason == "error_5xx"
        assert "503" in detail
        assert http_status == 503
        assert duration_ms is not None

    @patch('requests.get')
    @patch('socket.create_connection')
    @patch('socket.getaddrinfo')
    def test_slow_response(self, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
        """Test slow state for responses exceeding threshold"""
        import time
        
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 8080))]
        mock_create_connection.return_value.__enter__ = Mock()
        mock_create_connection.return_value.__exit__ = Mock()
        
        def slow_request(*args, **kwargs):
            time.sleep(2.5)
            mock_response = Mock()
            mock_response.status_code = 200
            return mock_response
        
        mock_get.side_effect = slow_request
        
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "http://192.168.1.100:8080/", 3, 2000
        )
        assert state == "DEGRADED"
        assert reason == "slow"
        assert "200" in detail
        assert http_status == 200
        assert duration_ms > 2000

    @patch('requests.get')
    @patch('socket.create_connection')
    @patch('socket.getaddrinfo')
    def test_online_fast_response(self, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
        """Test online state for fast successful responses"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 8080))]
        mock_create_connection.return_value.__enter__ = Mock()
        mock_create_connection.return_value.__exit__ = Mock()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "http://192.168.1.100:8080/", 3, 2000
        )
        assert state == "UP"
        assert reason == "online"
        assert "200" in detail
        assert http_status == 200
        assert duration_ms is not None
        assert duration_ms < 2000

    @patch('requests.get')
    @patch('socket.create_connection')
    @patch('socket.getaddrinfo')
    def test_online_redirect_response(self, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
        """Test online state for 3xx redirect responses"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 8080))]
        mock_create_connection.return_value.__enter__ = Mock()
        mock_create_connection.return_value.__exit__ = Mock()
        
        mock_response = Mock()
        mock_response.status_code = 302
        mock_get.return_value = mock_response
        
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "http://192.168.1.100:8080/", 3, 2000
        )
        assert state == "UP"
        assert reason == "online"
        assert http_status == 302

    @patch('requests.get')
    @patch('socket.create_connection')
    @patch('socket.getaddrinfo')
    def test_online_auth_required(self, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
        """Test online state for 401 auth required (service is up, just protected)"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 8080))]
        mock_create_connection.return_value.__enter__ = Mock()
        mock_create_connection.return_value.__exit__ = Mock()
        
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "http://192.168.1.100:8080/", 3, 2000
        )
        assert state == "UP"
        assert reason == "online"
        assert http_status == 401

    @patch('requests.get')
    @patch('socket.create_connection')
    @patch('socket.getaddrinfo')
    def test_online_not_found(self, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
        """Test online state for 404 not found (service is up, wrong path)"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 8080))]
        mock_create_connection.return_value.__enter__ = Mock()
        mock_create_connection.return_value.__exit__ = Mock()
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "http://192.168.1.100:8080/", 3, 2000
        )
        assert state == "UP"
        assert reason == "online"
        assert http_status == 404

    @patch('requests.get')
    @patch('socket.create_connection')
    @patch('socket.getaddrinfo')
    def test_error_exc_unexpected_exception(self, mock_getaddrinfo, mock_create_connection, mock_get, caddy_manager):
        """Test error_exc state for unexpected exceptions"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 8080))]
        mock_create_connection.return_value.__enter__ = Mock()
        mock_create_connection.return_value.__exit__ = Mock()
        mock_get.side_effect = Exception("Unexpected error")
        
        state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
            "http://192.168.1.100:8080/", 3, 2000
        )
        assert state == "DOWN"
        assert reason == "error_exc"
        assert "Unexpected error" in detail
        assert http_status is None

    def test_default_port_http(self, caddy_manager):
        """Test that default port 80 is used for HTTP URLs without explicit port"""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 80))]
            with patch('socket.create_connection') as mock_create_connection:
                mock_create_connection.side_effect = ConnectionRefusedError()
                
                state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
                    "http://192.168.1.100/", 3, 2000
                )
                # Verify that port 80 was used
                mock_getaddrinfo.assert_called_once()
                assert mock_getaddrinfo.call_args[0][1] == 80

    def test_default_port_https(self, caddy_manager):
        """Test that default port 443 is used for HTTPS URLs without explicit port"""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.100', 443))]
            with patch('socket.create_connection') as mock_create_connection:
                mock_create_connection.side_effect = ConnectionRefusedError()
                
                state, reason, detail, http_status, duration_ms = caddy_manager.classify_service_status(
                    "https://192.168.1.100/", 3, 2000
                )
                # Verify that port 443 was used
                mock_getaddrinfo.assert_called_once()
                assert mock_getaddrinfo.call_args[0][1] == 443


class TestEnhancedTestConnection:
    """Test the enhanced test_connection method"""

    @patch('caddy_manager.CaddyManager.classify_service_status')
    @patch('config.get_settings')
    def test_test_connection_uses_classification(self, mock_get_settings, mock_classify, caddy_manager):
        """Test that test_connection uses the new classification logic"""
        # Mock settings
        mock_settings = Mock()
        mock_settings.http_timeout_sec = 3
        mock_settings.slow_threshold_ms = 2000
        mock_get_settings.return_value = mock_settings
        
        # Mock classification result
        mock_classify.return_value = ("UP", "online", "HTTP 200 in 120 ms", 200, 120)
        
        route = {
            "target_ip": "192.168.1.100",
            "target_port": 8080,
            "protocol": "http",
            "timeout": 30
        }
        
        result = caddy_manager.test_connection(route)
        
        assert result["success"] is True
        assert result["status"] == "online"
        assert result["state"] == "UP"
        assert result["reason"] == "online"
        assert result["status_code"] == 200
        assert result["response_time"] == 120

    @patch('caddy_manager.CaddyManager.classify_service_status')
    @patch('config.get_settings')
    def test_test_connection_degraded_maps_to_slow(self, mock_get_settings, mock_classify, caddy_manager):
        """Test that DEGRADED state maps to 'slow' legacy status"""
        mock_settings = Mock()
        mock_settings.http_timeout_sec = 3
        mock_settings.slow_threshold_ms = 2000
        mock_get_settings.return_value = mock_settings
        
        mock_classify.return_value = ("DEGRADED", "slow", "HTTP 200 in 2500 ms", 200, 2500)
        
        route = {
            "target_ip": "192.168.1.100",
            "target_port": 8080,
            "protocol": "http",
            "timeout": 30
        }
        
        result = caddy_manager.test_connection(route)
        
        assert result["success"] is True  # DEGRADED is still considered success
        assert result["status"] == "slow"
        assert result["state"] == "DEGRADED"
        assert result["reason"] == "slow"

    @patch('caddy_manager.CaddyManager.classify_service_status')
    @patch('config.get_settings')
    def test_test_connection_down_5xx_maps_to_error(self, mock_get_settings, mock_classify, caddy_manager):
        """Test that DOWN/error_5xx maps to 'error' legacy status"""
        mock_settings = Mock()
        mock_settings.http_timeout_sec = 3
        mock_settings.slow_threshold_ms = 2000
        mock_get_settings.return_value = mock_settings
        
        mock_classify.return_value = ("DOWN", "error_5xx", "HTTP 503 in 50 ms", 503, 50)
        
        route = {
            "target_ip": "192.168.1.100",
            "target_port": 8080,
            "protocol": "http",
            "timeout": 30
        }
        
        result = caddy_manager.test_connection(route)
        
        assert result["success"] is False
        assert result["status"] == "error"
        assert result["state"] == "DOWN"
        assert result["reason"] == "error_5xx"
        assert result["error"] is not None

    @patch('caddy_manager.CaddyManager.classify_service_status')
    @patch('config.get_settings')
    def test_test_connection_down_timeout_maps_to_timeout(self, mock_get_settings, mock_classify, caddy_manager):
        """Test that DOWN/timeout maps to 'timeout' legacy status"""
        mock_settings = Mock()
        mock_settings.http_timeout_sec = 3
        mock_settings.slow_threshold_ms = 2000
        mock_get_settings.return_value = mock_settings
        
        mock_classify.return_value = ("DOWN", "timeout", "HTTP timeout after 3s", None, None)
        
        route = {
            "target_ip": "192.168.1.100",
            "target_port": 8080,
            "protocol": "http",
            "timeout": 30
        }
        
        result = caddy_manager.test_connection(route)
        
        assert result["success"] is False
        assert result["status"] == "timeout"
        assert result["state"] == "DOWN"
        assert result["reason"] == "timeout"

    @patch('caddy_manager.CaddyManager.classify_service_status')
    @patch('config.get_settings')
    def test_test_connection_down_offline_maps_to_offline(self, mock_get_settings, mock_classify, caddy_manager):
        """Test that DOWN/offline_* maps to 'offline' legacy status"""
        mock_settings = Mock()
        mock_settings.http_timeout_sec = 3
        mock_settings.slow_threshold_ms = 2000
        mock_get_settings.return_value = mock_settings
        
        mock_classify.return_value = ("DOWN", "offline_conn", "TCP connect failed", None, None)
        
        route = {
            "target_ip": "192.168.1.100",
            "target_port": 8080,
            "protocol": "http",
            "timeout": 30
        }
        
        result = caddy_manager.test_connection(route)
        
        assert result["success"] is False
        assert result["status"] == "offline"
        assert result["state"] == "DOWN"
        assert result["reason"] == "offline_conn"
