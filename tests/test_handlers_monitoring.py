"""
Tests for the problem overview.

An LLM asking "what's wrong in monitoring right now?" needs to know *why* each
service is failing, not only that it is. When the answer carries no check
output, the model's only way forward is to go looking elsewhere — which is
exactly what happened when this server was driven by a real agent: it read the
handler source and started calling the CheckMK API directly, because
`get_current_problems` threw away the plugin_output it had already fetched.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

from handlers.monitoring import MonitoringHandler
from vibemk_mcp.tools import get_all_tools

HOST_COLUMNS = ["name", "state"]

# The instant the fixture's failing service last changed state.
BROKE_AT = 1757000000


def service(host: str, description: str, state: int, output: str = "", changed: int = 0) -> Dict[str, Any]:
    return {
        "extensions": {
            "host_name": host,
            "description": description,
            "state": state,
            "plugin_output": output,
            "last_state_change": changed,
        }
    }


def collection(values: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"success": True, "status": 200, "headers": {}, "data": {"value": values}}


@pytest.fixture
def handler(mock_checkmk_client):
    return MonitoringHandler(mock_checkmk_client)


@pytest.fixture
def one_critical_service(mock_checkmk_client):
    """A site with every host up and a single failing service."""
    hosts = collection([{"extensions": {"name": "web01", "state": 0}}])
    services = collection(
        [
            service("web01", "CPU utilization", 0, "OK - 12% used"),
            service(
                "web01",
                "Filesystem /var",
                2,
                "CRIT - 94.1% used (89.2 of 94.8 GiB), trend: +1.2 GiB / 24 hours",
                BROKE_AT,
            ),
        ]
    )

    def answer(endpoint: str, params: Any = None, **_: Any) -> Dict[str, Any]:
        return hosts if "host/collections" in endpoint else services

    mock_checkmk_client.get.side_effect = answer
    return mock_checkmk_client


class TestProblemsCarryTheirCause:
    @pytest.mark.asyncio
    async def test_the_check_output_is_shown(self, handler, one_critical_service):
        result = await handler.handle("vibemk_get_current_problems", {})

        assert "94.1% used" in result[0]["text"], "the output that explains the problem is missing"

    @pytest.mark.asyncio
    async def test_the_service_is_still_named(self, handler, one_critical_service):
        result = await handler.handle("vibemk_get_current_problems", {})

        text = result[0]["text"]
        assert "web01" in text
        assert "Filesystem /var" in text
        assert "CRITICAL" in text

    @pytest.mark.asyncio
    async def test_healthy_services_are_not_listed(self, handler, one_critical_service):
        result = await handler.handle("vibemk_get_current_problems", {})

        assert "CPU utilization" not in result[0]["text"]

    @pytest.mark.asyncio
    async def test_since_when_is_answerable(self, handler, one_critical_service):
        # "What broke while I was away" cannot be answered without this.
        expected = datetime.fromtimestamp(BROKE_AT, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

        result = await handler.handle("vibemk_get_current_problems", {})

        assert expected in result[0]["text"], "last_state_change is not surfaced"

    @pytest.mark.asyncio
    async def test_last_state_change_is_requested_from_checkmk(self, handler, one_critical_service):
        await handler.handle("vibemk_get_current_problems", {})

        service_call = [c for c in handler.client.get.call_args_list if "service/collections" in c.args[0]][0]
        assert "last_state_change" in service_call.kwargs["params"]["columns"]


class TestNoProblems:
    @pytest.mark.asyncio
    async def test_an_all_clear_is_reported(self, handler, mock_checkmk_client):
        mock_checkmk_client.get.return_value = collection([])

        result = await handler.handle("vibemk_get_current_problems", {})

        assert "No current problems" in result[0]["text"]


class TestTheGenericAcknowledgeToolIsSteerable:
    """vibemk_acknowledge_problem hard-wired sticky and notify to True. The
    values match CheckMK's defaults, so the acknowledgements were right — but
    a caller could not ask for anything else, and the tool schema did not
    mention either flag, so a model had no way to know they existed."""

    @pytest.mark.asyncio
    async def test_the_defaults_are_checkmks(self, handler, mock_checkmk_client):
        mock_checkmk_client.post.return_value = collection([])

        await handler.handle(
            "vibemk_acknowledge_problem",
            {"acknowledge_type": "host", "host_name": "web01", "comment": "on it"},
        )

        body = mock_checkmk_client.post.call_args.kwargs["data"]
        assert body["sticky"] is True
        assert body["notify"] is True

    @pytest.mark.asyncio
    async def test_the_caller_can_override_them(self, handler, mock_checkmk_client):
        mock_checkmk_client.post.return_value = collection([])

        await handler.handle(
            "vibemk_acknowledge_problem",
            {
                "acknowledge_type": "host",
                "host_name": "web01",
                "comment": "quietly",
                "sticky": False,
                "notify": False,
            },
        )

        body = mock_checkmk_client.post.call_args.kwargs["data"]
        assert body["sticky"] is False
        assert body["notify"] is False

    def test_the_flags_are_declared(self):
        tool = next(t for t in get_all_tools() if t["name"] == "vibemk_acknowledge_problem")

        for flag in ("sticky", "notify"):
            assert flag in tool["inputSchema"]["properties"], f"{flag} is sent but never advertised"
