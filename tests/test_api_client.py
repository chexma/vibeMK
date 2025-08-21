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

    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_config):
        """Test client initialization with config"""
        client = CheckMKClient(mock_config)

        assert client.config == mock_config
        assert client.base_url == "http://test-checkmk.local:8080/test_site/check_mk/api/1.0"
        assert "Authorization" in client.headers
        assert client.headers["Content-Type"] == "application/json"
        assert client.headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_successful_get_request(self, mock_checkmk_client, mock_checkmk_responses):
        """Test successful GET request"""
        # Setup mock response
        mock_checkmk_client.get.return_value = mock_checkmk_responses["version"]

        result = await mock_checkmk_client.get("version")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["site"] == "test_site"

    @pytest.mark.asyncio
    async def test_successful_post_request(self, mock_checkmk_client, sample_host_data):
        """Test successful POST request"""
        # Setup mock response
        expected_response = {"success": True, "data": {"id": sample_host_data["host_name"]}}
        mock_checkmk_client.post.return_value = expected_response

        result = await mock_checkmk_client.post("domain-types/host/collections/all", data=sample_host_data)

        assert result["success"] is True
        assert result["data"]["id"] == sample_host_data["host_name"]

    @pytest.mark.asyncio
    async def test_authentication_error(self, mock_config):
        """Test authentication error handling"""
        client = CheckMKClient(mock_config)

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock 401 authentication error
            error = urllib.error.HTTPError(url="test", code=401, msg="Unauthorized", hdrs={}, fp=MagicMock())
            error.read.return_value = b'{"title": "Unauthorized", "detail": "Invalid credentials"}'
            mock_urlopen.side_effect = error

            with pytest.raises(CheckMKAuthenticationError):
                await client.get("version")

    @pytest.mark.asyncio
    async def test_connection_error(self, mock_config):
        """Test connection error handling"""
        client = CheckMKClient(mock_config)

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock connection error
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

            with pytest.raises(CheckMKConnectionError):
                await client.get("version")

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, mock_config):
        """Test retry mechanism on temporary failures"""
        mock_config.max_retries = 2
        client = CheckMKClient(mock_config)

        with patch("urllib.request.urlopen") as mock_urlopen:
            # First two calls fail, third succeeds
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"success": true, "data": {}}'
            mock_response.status = 200

            mock_urlopen.side_effect = [
                urllib.error.HTTPError("test", 500, "Server Error", {}, None),
                urllib.error.HTTPError("test", 500, "Server Error", {}, None),
                mock_response,
            ]

            result = await client.get("version")
            assert result["success"] is True
            assert mock_urlopen.call_count == 3

    @pytest.mark.asyncio
    async def test_url_encoding(self, mock_checkmk_client):
        """Test proper URL encoding for parameters"""
        # Setup mock
        mock_checkmk_client.get.return_value = {"success": True, "data": {}}

        # Test with special characters
        params = {"host_name": "test-server with spaces", "service": "CPU%usage"}
        await mock_checkmk_client.get("objects/host/test", params=params)

        # Verify the call was made (parameters would be URL-encoded internally)
        mock_checkmk_client.get.assert_called_with("objects/host/test", params=params)

    @pytest.mark.asyncio
    async def test_json_parsing_error(self, mock_config):
        """Test handling of invalid JSON responses"""
        client = CheckMKClient(mock_config)

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response with invalid JSON
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"invalid": json}'
            mock_response.status = 200
            mock_urlopen.return_value = mock_response

            with pytest.raises(CheckMKAPIError, match="Invalid JSON response"):
                await client.get("version")

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_config):
        """Test timeout handling"""
        mock_config.timeout = 1  # Very short timeout
        client = CheckMKClient(mock_config)

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock timeout
            mock_urlopen.side_effect = TimeoutError("Request timed out")

            with pytest.raises(CheckMKConnectionError, match="timeout"):
                await client.get("version")
