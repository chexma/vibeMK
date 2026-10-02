"""
Retry safety for the CheckMK API client.

A 5xx retry is free on a method HTTP calls idempotent. On a POST it is not:
re-issuing POST .../downtime/actions/delete/invoke after a gateway timeout can
delete a second time, and the first attempt may well have succeeded before the
proxy gave up.
"""

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from api.client import CheckMKClient
from api.exceptions import CheckMKAPIError


def _ok() -> MagicMock:
    response = MagicMock()
    response.status = 200
    response.read.return_value = b"{}"
    response.headers = {}
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def _http_error(code: int, headers: dict | None = None) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("test", code, "Error", headers or {}, None)


@pytest.fixture
def client(mock_config):
    mock_config.max_retries = 2
    return CheckMKClient(mock_config, skip_url_detection=True)


class TestRetrySafety:
    """Only methods HTTP calls idempotent may be repeated."""

    def test_get_is_retried_on_server_error(self, client):
        with patch("urllib.request.urlopen") as urlopen, patch("time.sleep"):
            urlopen.side_effect = [_http_error(500), _http_error(500), _ok()]

            client.get("version")

            assert urlopen.call_count == 3  # original + 2 retries

    def test_delete_is_retried_on_server_error(self, client):
        """DELETE is idempotent: deleting twice leaves the same state."""
        with patch("urllib.request.urlopen") as urlopen, patch("time.sleep"):
            urlopen.side_effect = [_http_error(500), _ok()]

            client.delete("objects/host_config/gone")

            assert urlopen.call_count == 2

    def test_post_is_not_retried_on_server_error(self, client):
        with patch("urllib.request.urlopen") as urlopen, patch("time.sleep"):
            urlopen.side_effect = [_http_error(500), _ok(), _ok()]

            with pytest.raises(CheckMKAPIError):
                client.post("domain-types/downtime/actions/delete/invoke", data={"delete_type": "by_id"})

            assert urlopen.call_count == 1, "a POST must not be repeated after a 5xx"

    def test_patch_is_not_retried_on_server_error(self, client):
        with patch("urllib.request.urlopen") as urlopen, patch("time.sleep"):
            urlopen.side_effect = [_http_error(500), _ok(), _ok()]

            with pytest.raises(CheckMKAPIError):
                client.patch("objects/host_config/web01", data={"attributes": {}})

            assert urlopen.call_count == 1


class TestRateLimiting:
    """429 says 'wait', and usually says how long."""

    def test_rate_limited_request_is_retried(self, client):
        with patch("urllib.request.urlopen") as urlopen, patch("time.sleep"):
            urlopen.side_effect = [_http_error(429), _ok()]

            client.get("version")

            assert urlopen.call_count == 2

    def test_retry_after_sets_the_delay(self, client):
        with patch("urllib.request.urlopen") as urlopen, patch("time.sleep") as sleep:
            urlopen.side_effect = [_http_error(429, {"Retry-After": "7"}), _ok()]

            client.get("version")

            assert sleep.call_args[0][0] == 7.0

    def test_unparseable_retry_after_falls_back_to_backoff(self, client):
        with patch("urllib.request.urlopen") as urlopen, patch("time.sleep") as sleep:
            urlopen.side_effect = [_http_error(429, {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}), _ok()]

            client.get("version")

            assert sleep.call_args[0][0] == 1.0  # 2**0


class TestEmptyBody:
    """An empty JSON object is a body; absent data is not."""

    def test_empty_dict_is_sent_as_an_empty_object(self, client):
        with patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value = _ok()

            client.post("domain-types/folder_config/actions/bulk-update/invoke", data={})

            assert urlopen.call_args[0][0].data == json.dumps({}).encode()

    def test_no_data_sends_no_body(self, client):
        with patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value = _ok()

            client.post("domain-types/activation_run/actions/activate-changes/invoke")

            assert urlopen.call_args[0][0].data is None
