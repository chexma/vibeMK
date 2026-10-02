"""
Tests for handlers/connection.py

Covers the same over-narrowed except defect as api/client.py: HTTPError.read()
is a live socket read of the error body, not a parse of already-buffered data,
so a transport failure while reading it must not escape as a raw OSError.
"""

import urllib.error
import urllib.request
from email.message import Message
from unittest.mock import MagicMock, patch

import pytest

from handlers.connection import ConnectionHandler


@pytest.fixture
def handler(mock_checkmk_client):
    return ConnectionHandler(mock_checkmk_client)


class TestDirectUrlTestSurvivesErrorBodySocketFailure:
    @pytest.mark.asyncio
    async def test_connection_reset_reading_error_body_does_not_raise(self, handler):
        with patch("urllib.request.build_opener") as mock_build_opener:
            error = urllib.error.HTTPError(url="test", code=500, msg="Server Error", hdrs=Message(), fp=None)
            # Replacing .read() is the point of the test double; strict mode's
            # objection to overwriting a method is intentional here.
            error.read = MagicMock(side_effect=ConnectionResetError("Connection reset by peer"))  # type: ignore[method-assign]
            mock_build_opener.return_value.open.side_effect = error

            # A raw OSError escaping here would propagate out of _test_direct_url
            # uncaught by its own except clauses (it's raised from inside the
            # `except urllib.error.HTTPError` handler, so its siblings don't
            # apply); it should instead fall through to the generic error_data
            # fallback and produce a normal error response.
            result = await handler._test_direct_url(f"{handler.client.api_base_url}/version")

        assert isinstance(result, list)
        assert "HTTP Error 500" in result[0]["text"]


class TestDirectUrlStaysOnTheCheckmkApi:
    """The request carries the CheckMK credentials; it must not go anywhere else."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url",
        [
            "http://attacker.example/steal",
            "https://test-checkmk.local:8080/cmk/check_mk/api/1.0/version",
            "http://test-checkmk.local:9999/cmk/check_mk/api/1.0/version",
            "http://test-checkmk.local:8080.attacker.example/cmk/check_mk/api/1.0/version",
            "http://user:pw@test-checkmk.local:8080/cmk/check_mk/api/1.0/version",
            "http://test-checkmk.local:8080/cmk/check_mk/login.py",
            "http://test-checkmk.local:8080/cmk/check_mk/api/1.0/../../wato.py",
            "http://test-checkmk.local:8080/cmk/check_mk/api/1.0/%2e%2e/%2e%2e/wato.py",
            "http://test-checkmk.local:8080/cmk/check_mk/api/1.0x/version",
            "file:///etc/passwd",
        ],
    )
    async def test_foreign_url_is_refused_without_a_request(self, handler, url):
        with patch("urllib.request.build_opener") as mock_build_opener:
            result = await handler._test_direct_url(url)

        mock_build_opener.assert_not_called()
        assert "URL not allowed" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_url_under_the_api_is_sent_without_following_redirects(self, handler):
        response = MagicMock(status=200)
        response.read.return_value = b'{"versions": {}}'
        response.__enter__.return_value = response

        with patch("urllib.request.build_opener") as mock_build_opener:
            mock_build_opener.return_value.open.return_value = response
            result = await handler._test_direct_url(f"{handler.client.api_base_url}/version")

        handler_types = mock_build_opener.call_args.args
        assert any(isinstance(h, type) and issubclass(h, urllib.request.HTTPRedirectHandler) for h in handler_types)
        assert "Direct URL Test Successful" in result[0]["text"]
