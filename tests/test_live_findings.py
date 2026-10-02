"""
Defects found by driving the tools against a live CheckMK 2.5

Each test uses the response shape CheckMK actually returned, captured from the
local Raw instance, rather than the shape the handler expected.
"""

import time
import urllib.error
from email.message import Message
from unittest.mock import MagicMock, patch

import pytest

from api.exceptions import CheckMKAPIError
from handlers.configuration import ConfigurationHandler
from handlers.discovery import DiscoveryHandler
from handlers.hosts import HostHandler
from vibemk_mcp.dispatch import is_error, structured_of


def _redirect(code: int) -> urllib.error.HTTPError:
    headers = Message()
    headers["Location"] = "/cmk/check_mk/api/1.0/objects/service_discovery_run/web01/actions/wait-for-completion/invoke"
    return urllib.error.HTTPError(url="test", code=code, msg="redirect", hdrs=headers, fp=None)


class TestClientCanHandBackARedirect:
    """CheckMK reports discovery progress through redirects, not through a body."""

    def test_redirect_is_returned_instead_of_followed(self, mock_config):
        from api.client import CheckMKClient

        client = CheckMKClient(mock_config, skip_url_detection=True)
        with patch("urllib.request.build_opener") as build_opener:
            build_opener.return_value.open.side_effect = _redirect(302)
            result = client.request("objects/service_discovery_run/web01", follow_redirects=False)

        assert result["status"] == 302
        assert result["success"] is True
        assert result["location"].endswith("/wait-for-completion/invoke")


class TestWaitForDiscovery:
    @pytest.fixture
    def handler(self, mock_checkmk_client):
        return DiscoveryHandler(mock_checkmk_client)

    @pytest.mark.asyncio
    async def test_polls_while_the_job_runs_and_reports_completion(self, handler):
        # 302 to itself while running, 204 once finished -- as CheckMK 2.5 answers
        handler.client.request = MagicMock(
            side_effect=[
                {"success": True, "status": 302, "data": {}},
                {"success": True, "status": 302, "data": {}},
                {"success": True, "status": 204, "data": {}},
            ]
        )
        with patch("handlers.discovery.asyncio.sleep") as sleep:
            sleep.return_value = None
            result = await handler.handle("vibemk_wait_for_discovery", {"host_name": "web01"})

        assert not is_error(result)
        assert "Discovery Completed" in result[0]["text"]
        assert handler.client.request.call_count == 3
        assert all(call.kwargs["follow_redirects"] is False for call in handler.client.request.call_args_list)

    @pytest.mark.asyncio
    async def test_gives_up_after_the_timeout_without_failing(self, handler):
        handler.client.request = MagicMock(return_value={"success": True, "status": 302, "data": {}})
        clock = iter(range(0, 10_000, 30))
        with (
            patch("handlers.discovery.asyncio.sleep") as sleep,
            patch("handlers.discovery.time.monotonic", side_effect=lambda: next(clock)),
        ):
            sleep.return_value = None
            result = await handler.handle("vibemk_wait_for_discovery", {"host_name": "web01", "timeout": 60})

        assert "still running" in result[0]["text"]


class TestStartServiceDiscovery:
    @pytest.fixture
    def handler(self, mock_checkmk_client):
        return DiscoveryHandler(mock_checkmk_client)

    @pytest.mark.asyncio
    async def test_303_means_started_and_needs_no_bulk_fallback(self, handler):
        handler.client.request = MagicMock(return_value={"success": True, "status": 303, "data": {}})

        result = await handler.handle("vibemk_start_service_discovery", {"host_name": "web01"})

        assert "Service Discovery Started" in result[0]["text"]
        assert "bulk" not in result[0]["text"].lower()
        handler.client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_409_reports_the_running_job_instead_of_starting_a_bulk_one(self, handler):
        handler.client.request = MagicMock(
            side_effect=CheckMKAPIError(
                "HTTP 409: CONFLICT", 409, {"detail": "A service discovery background job is currently running"}
            )
        )

        result = await handler.handle("vibemk_start_service_discovery", {"host_name": "web01"})

        assert "already running" in result[0]["text"]
        handler.client.post.assert_not_called()


class TestPendingChanges:
    @pytest.mark.asyncio
    async def test_reads_the_fields_checkmk_sends(self, mock_checkmk_client):
        mock_checkmk_client.get.return_value = {
            "success": True,
            "data": {
                "value": [
                    {
                        "id": "6ab960ba-7623-49b8-92dd-eed832acbe84",
                        "user_id": "cmkadmin",
                        "action_name": "edit-host",
                        "text": "Modified host vibemk-test.",
                        "time": "2026-10-02T19:36:10.993928+00:00",
                    }
                ]
            },
        }

        content = await ConfigurationHandler(mock_checkmk_client).handle("vibemk_get_pending_changes", {})

        text = content[0]["text"]
        assert "unknown" not in text.lower()
        assert "Modified host vibemk-test." in text
        assert "cmkadmin" in text
        assert "edit: 1" in text
        assert structured_of(content)["changes"][0]["text"] == "Modified host vibemk-test."


class TestHostTimestampZero:
    """CheckMK sends 0 for a timestamp that has not happened yet."""

    @pytest.mark.asyncio
    async def test_state_change_of_zero_is_not_shown_as_1970(self, mock_checkmk_client):
        mock_checkmk_client.get.return_value = {
            "success": True,
            "data": {
                "extensions": {
                    "name": "vibemk-test",
                    "state": 0,
                    "hard_state": 0,
                    "state_type": 1,
                    "has_been_checked": 1,
                    "plugin_output": "OK",
                    "last_check": int(time.time()) - 3,
                    "last_state_change": 0,
                }
            },
        }

        content = await HostHandler(mock_checkmk_client).handle("vibemk_get_host_status", {"host_name": "vibemk-test"})

        text = content[0]["text"]
        assert "**Last State Change:** Never" in text
        assert structured_of(content)["last_state_change"] is None


class TestEveryAdvertisedDiscoveryModeWorks:
    """The schema offered tabula_rasa and only_service_labels; the handler refused both."""

    @pytest.fixture
    def handler(self, mock_checkmk_client):
        return DiscoveryHandler(mock_checkmk_client)

    @staticmethod
    def _advertised_modes():
        from vibemk_mcp.tools import get_all_tools

        tool = next(t for t in get_all_tools() if t["name"] == "vibemk_start_service_discovery")
        return tool["inputSchema"]["properties"]["mode"]["enum"]

    @pytest.mark.asyncio
    async def test_handler_accepts_every_advertised_mode(self, handler):
        handler.client.request = MagicMock(return_value={"success": True, "status": 303, "data": {}})

        for mode in self._advertised_modes():
            result = await handler.handle("vibemk_start_service_discovery", {"host_name": "web01", "mode": mode})
            assert not is_error(result), f"{mode}: {result[0]['text']}"
            assert handler.client.request.call_args.kwargs["data"]["mode"] == mode

    @pytest.mark.asyncio
    async def test_immediate_modes_report_a_result_not_a_background_job(self, handler):
        # Only refresh and tabula_rasa run as a job; the others answer at once.
        handler.client.request = MagicMock(return_value={"success": True, "status": 200, "data": {}})

        result = await handler.handle("vibemk_start_service_discovery", {"host_name": "web01", "mode": "fix_all"})

        assert "Service Discovery Completed" in result[0]["text"]
        assert "background" not in result[0]["text"]

    def test_a_tool_that_can_remove_every_service_is_annotated_destructive(self):
        from vibemk_mcp.annotations import DESTRUCTIVE

        assert "tabula_rasa" in self._advertised_modes()
        assert "vibemk_start_service_discovery" in DESTRUCTIVE
