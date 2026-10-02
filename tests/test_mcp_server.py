"""
Tests for the JSON-RPC dispatch layer.

The dispatcher is exercised through a stub registry, so no CheckMK client and
no mock detection is involved. Production code must never behave differently
because it is under test.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import pytest

from config import MCPConfig
from mcp.dispatch import Dispatcher
from mcp.registry import ToolRegistry
from mcp.tools import get_all_tools


class RecordingHandler:
    """A handler that records the call it received."""

    def __init__(self, result: Optional[List[Dict[str, Any]]] = None, raises: Optional[Exception] = None):
        self.result = result if result is not None else [{"type": "text", "text": "ok"}]
        self.raises = raises
        self.calls: List[Any] = []

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.calls.append((tool_name, arguments))
        if self.raises is not None:
            raise self.raises
        return self.result


class StubRegistry(ToolRegistry):
    """A registry built directly from a handler mapping, skipping from_client's
    CheckMK-client wiring. handler_for/tool_names are inherited unchanged."""

    def __init__(self, handlers: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(handlers or {})


def make_dispatcher(handlers=None):
    registry = StubRegistry(handlers)
    return Dispatcher(lambda: registry, MCPConfig())


def request(method, params=None, request_id=1):
    body = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        body["params"] = params
    return body


class TestProtocol:
    @pytest.mark.asyncio
    async def test_tools_list_returns_the_catalogue(self):
        # Compared against the catalogue rather than a pinned count: the point
        # is that the protocol layer hands back everything that is declared,
        # and a hard-coded number turns every catalogue change into a failure
        # that says nothing about the protocol.
        response = await make_dispatcher().handle(request("tools/list"))

        assert len(response["result"]["tools"]) == len(get_all_tools())

    @pytest.mark.asyncio
    async def test_initialize_answers_a_supported_version(self):
        response = await make_dispatcher().handle(request("initialize", {"protocolVersion": "1999-01-01-BOGUS"}))

        assert response["result"]["protocolVersion"] in MCPConfig().supported_protocol_versions

    @pytest.mark.asyncio
    async def test_initialized_notification_produces_no_response(self):
        assert await make_dispatcher().handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None

    @pytest.mark.asyncio
    async def test_unknown_method_is_method_not_found(self):
        response = await make_dispatcher().handle(request("no/such/method"))

        assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_request_without_jsonrpc_field_is_invalid(self):
        response = await make_dispatcher().handle({"id": 1, "method": "tools/list"})

        assert response["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_request_that_is_not_an_object_is_invalid(self):
        response = await make_dispatcher().handle("not a dict")

        assert response["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_request_without_method_field_is_invalid(self):
        """`method = request["method"]` sits right after this guard, outside the
        try/except. Without the guard a missing method raises KeyError, which
        escapes handle() entirely instead of producing a -32600 response."""
        response = await make_dispatcher().handle({"jsonrpc": "2.0", "id": "test-5"})

        assert response["error"]["code"] == -32600


class TestToolCalls:
    @pytest.mark.asyncio
    async def test_a_registered_tool_is_invoked(self):
        handler = RecordingHandler()
        dispatcher = make_dispatcher({"vibemk_demo": handler})

        response = await dispatcher.handle(request("tools/call", {"name": "vibemk_demo", "arguments": {}}))

        assert response["result"]["content"] == [{"type": "text", "text": "ok"}]

    @pytest.mark.asyncio
    async def test_arguments_reach_the_handler(self):
        handler = RecordingHandler()
        dispatcher = make_dispatcher({"vibemk_demo": handler})

        await dispatcher.handle(
            request("tools/call", {"name": "vibemk_demo", "arguments": {"host_name": "example.com"}})
        )

        assert handler.calls == [("vibemk_demo", {"host_name": "example.com"})]

    @pytest.mark.asyncio
    async def test_an_unregistered_tool_is_method_not_found(self):
        response = await make_dispatcher().handle(request("tools/call", {"name": "vibemk_nope", "arguments": {}}))

        assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_a_raising_handler_becomes_an_internal_error(self):
        dispatcher = make_dispatcher({"vibemk_demo": RecordingHandler(raises=RuntimeError("boom"))})

        response = await dispatcher.handle(request("tools/call", {"name": "vibemk_demo", "arguments": {}}))

        assert response["error"]["code"] == -32603

    @pytest.mark.asyncio
    async def test_requests_are_served_concurrently(self):
        dispatcher = make_dispatcher({"vibemk_demo": RecordingHandler()})

        responses = await asyncio.gather(
            *(dispatcher.handle(request("tools/call", {"name": "vibemk_demo", "arguments": {}}, i)) for i in range(5))
        )

        assert [r["id"] for r in responses] == [0, 1, 2, 3, 4]


class TestConfigurationErrors:
    @pytest.mark.asyncio
    async def test_a_failing_registry_becomes_readable_tool_output(self):
        def explode():
            raise ValueError("CHECKMK_SERVER_URL is required")

        dispatcher = Dispatcher(explode, MCPConfig())

        response = await dispatcher.handle(request("tools/call", {"name": "vibemk_demo", "arguments": {}}))

        assert response is not None
        assert "CHECKMK_SERVER_URL is required" in response["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_tools_list_works_without_a_usable_registry(self):
        def explode():
            raise ValueError("CHECKMK_SERVER_URL is required")

        response = await Dispatcher(explode, MCPConfig()).handle(request("tools/list"))

        assert response is not None
        assert len(response["result"]["tools"]) == len(get_all_tools())


class TestToolCallsLeaveATrace:
    """A record of what the model actually did.

    This server creates and deletes hosts, rules, users and downtimes. The
    only account of which of those an LLM invoked is the server's own log,
    and after the dispatcher was split out only *failing* calls were logged —
    a successful deletion left nothing behind at all. The old dispatcher
    logged every request before running it; this restores that.

    Arguments are deliberately not logged: they carry host names, comments
    and, for the password tools, secrets.
    """

    @pytest.mark.asyncio
    async def test_a_successful_call_is_logged_with_its_tool_name(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="mcp.dispatch"):
            await make_dispatcher().handle(
                request("tools/call", {"name": "vibemk_get_checkmk_version", "arguments": {}})
            )

        assert any(
            "vibemk_get_checkmk_version" in record.message and record.levelno == logging.INFO
            for record in caplog.records
        ), f"no INFO record names the tool: {[r.message for r in caplog.records]}"

    @pytest.mark.asyncio
    async def test_the_arguments_are_not_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="mcp.dispatch"):
            await make_dispatcher().handle(
                request(
                    "tools/call",
                    {"name": "vibemk_get_checkmk_version", "arguments": {"password": "hunter2"}},
                )
            )

        assert not any("hunter2" in record.message for record in caplog.records)
