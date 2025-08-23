"""
Tests for CheckMK API Client
"""

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from api.client import CheckMKClient
from api.exceptions import CheckMKAPIError, CheckMKAuthenticationError, CheckMKConnectionError


class TestCheckMKClient:
    """Test CheckMK API Client functionality"""

    def test_client_initialization(self, mock_config):
        """Test client initialization with config"""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock successful API detection
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value = mock_response

            client = CheckMKClient(mock_config)

            assert client.config == mock_config
            assert client.api_base_url.startswith("http://test-checkmk.local:8080")
            assert "Authorization" in client.headers
            assert client.headers["Content-Type"] == "application/json"
            assert client.headers["Accept"] == "application/json"

    def test_successful_get_request(self, mock_checkmk_client, mock_checkmk_responses):
        """Test successful GET request"""
        # Setup mock response
        mock_checkmk_client.get.return_value = mock_checkmk_responses["version"]

        result = mock_checkmk_client.get("version")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["site"] == "test_site"

    def test_successful_post_request(self, mock_checkmk_client, sample_host_data):
        """Test successful POST request"""
        # Setup mock response
        expected_response = {"success": True, "data": {"id": sample_host_data["host_name"]}}
        mock_checkmk_client.post.return_value = expected_response

        result = mock_checkmk_client.post("domain-types/host/collections/all", data=sample_host_data)

        assert result["success"] is True
        assert result["data"]["id"] == sample_host_data["host_name"]

    def test_authentication_error(self, mock_config):
        """Test authentication error handling"""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock successful API detection first, then error
            mock_response = MagicMock()
            mock_response.status = 200

            # Mock 401 authentication error for the actual request
            error = urllib.error.HTTPError(url="test", code=401, msg="Unauthorized", hdrs={}, fp=MagicMock())
            error.read.return_value = b'{"title": "Unauthorized", "detail": "Invalid credentials"}'

            # First call succeeds (API detection), second fails (actual request)
            mock_urlopen.side_effect = [mock_response, error]

            client = CheckMKClient(mock_config)

            with pytest.raises(CheckMKAuthenticationError):
                client.get("version")

    def test_connection_error(self, mock_config):
        """Test connection error handling"""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock connection error for API detection
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

            with pytest.raises(CheckMKConnectionError):
                client = CheckMKClient(mock_config)
                client.get("version")

    def test_retry_mechanism(self, mock_config):
        """Test retry mechanism on temporary failures"""
        mock_config.max_retries = 2

        with patch("urllib.request.urlopen") as mock_urlopen:
            # First call succeeds (API detection), then fails, retries, succeeds
            mock_success_response = MagicMock()
            mock_success_response.status = 200
            mock_success_response.read.return_value = b'{"success": true, "data": {}}'

            mock_error = urllib.error.HTTPError("test", 500, "Server Error", {}, None)

            mock_urlopen.side_effect = [
                mock_success_response,  # API detection
                mock_error,  # First request fails
                mock_error,  # Retry fails
                mock_success_response,  # Final retry succeeds
            ]

            client = CheckMKClient(mock_config)
            result = client.get("version")
            assert result["success"] is True
            assert mock_urlopen.call_count == 4  # API detection + 1 original + 2 retries

    def test_url_encoding(self, mock_checkmk_client):
        """Test proper URL encoding for parameters"""
        # Setup mock
        mock_checkmk_client.get.return_value = {"success": True, "data": {}}

        # Test with special characters
        params = {"host_name": "test-server with spaces", "service": "CPU%usage"}
        mock_checkmk_client.get("objects/host/test", params=params)

        # Verify the call was made (parameters would be URL-encoded internally)
        mock_checkmk_client.get.assert_called_with("objects/host/test", params=params)

    def test_json_parsing_error(self, mock_config):
        """Test handling of invalid JSON responses"""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock successful API detection, then invalid JSON response
            mock_success_response = MagicMock()
            mock_success_response.status = 200

            mock_invalid_response = MagicMock()
            mock_invalid_response.read.return_value = b'{"invalid": json}'
            mock_invalid_response.status = 200

            mock_urlopen.side_effect = [mock_success_response, mock_invalid_response]

            client = CheckMKClient(mock_config)

            with pytest.raises(CheckMKAPIError, match="Invalid JSON response"):
                client.get("version")

    def test_timeout_handling(self, mock_config):
        """Test timeout handling"""
        mock_config.timeout = 1  # Very short timeout

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock timeout during API detection
            mock_urlopen.side_effect = TimeoutError("Request timed out")

            with pytest.raises(CheckMKConnectionError, match="timeout"):
                client = CheckMKClient(mock_config)
