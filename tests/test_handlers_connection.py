"""
Tests for handlers/connection.py

Covers the same over-narrowed except defect as api/client.py: HTTPError.read()
is a live socket read of the error body, not a parse of already-buffered data,
so a transport failure while reading it must not escape as a raw OSError.
"""

import urllib.error
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
        with patch("urllib.request.urlopen") as mock_urlopen:
            error = urllib.error.HTTPError(url="test", code=500, msg="Server Error", hdrs=Message(), fp=None)
            # Replacing .read() is the point of the test double; strict mode's
            # objection to overwriting a method is intentional here.
            error.read = MagicMock(side_effect=ConnectionResetError("Connection reset by peer"))  # type: ignore[method-assign]
            mock_urlopen.side_effect = error

            # A raw OSError escaping here would propagate out of _test_direct_url
            # uncaught by its own except clauses (it's raised from inside the
            # `except urllib.error.HTTPError` handler, so its siblings don't
            # apply); it should instead fall through to the generic error_data
            # fallback and produce a normal error response.
            result = await handler._test_direct_url("http://example.invalid/version")

        assert isinstance(result, list)
        assert "HTTP Error 500" in result[0]["text"]
