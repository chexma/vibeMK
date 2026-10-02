"""
Tool-call semantics.

The SDK owns the protocol -- framing, version negotiation, and the difference
between a JSON-RPC error and a result. What stays ours is what a tool call
means: which handler runs, whether a failure is reported as a result the model
can act on, and what reaches the log.
"""

import asyncio
import logging
from typing import Any, Dict, List

import pytest

from vibemk_mcp.dispatch import Dispatcher, is_error
from vibemk_mcp.registry import ToolRegistry
from vibemk_mcp.server import CheckMKMCPServer
from vibemk_mcp.tools import get_all_tools

TOOL = "vibemk_get_checkmk_version"


class RecordingHandler:
    """A handler that records what it was asked and answers predictably."""

    def __init__(self, text: str = "✅ **Done**", raises: BaseException | None = None) -> None:
        self.text = text
        self.raises = raises
        self.calls: List[Dict[str, Any]] = []

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.calls.append({"tool": tool_name, "arguments": arguments})
        if self.raises is not None:
            raise self.raises
        return [{"type": "text", "text": self.text}]


def make_dispatcher(handlers: Dict[str, Any] | None = None) -> Dispatcher:
    registry = ToolRegistry(handlers if handlers is not None else {TOOL: RecordingHandler()})
    return Dispatcher(lambda: registry)


class TestErrorsAreReportedAsResults:
    """A tool that ran and failed is actionable; a missing tool is not."""

    @pytest.mark.asyncio
    async def test_a_successful_call_is_not_an_error(self):
        result = await make_dispatcher().call_tool(TOOL, {})

        assert result.is_error is False
        assert result.content[0].text == "✅ **Done**"

    @pytest.mark.asyncio
    async def test_a_handler_reporting_failure_sets_is_error(self):
        handlers = {TOOL: RecordingHandler(text="❌ **Host not found**")}

        result = await make_dispatcher(handlers).call_tool(TOOL, {})

        assert result.is_error is True

    @pytest.mark.asyncio
    async def test_a_raising_handler_becomes_a_result_not_an_exception(self):
        """The model can fix an argument and retry; a -32603 gives it nothing."""
        handlers = {TOOL: RecordingHandler(raises=RuntimeError("boom"))}

        result = await make_dispatcher(handlers).call_tool(TOOL, {})

        assert result.is_error is True
        assert "boom" in result.content[0].text

    @pytest.mark.asyncio
    async def test_an_unknown_tool_raises_so_the_sdk_reports_a_protocol_error(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            await make_dispatcher().call_tool("vibemk_not_a_tool", {})


class TestTheHandlerIsReached:
    @pytest.mark.asyncio
    async def test_the_registered_handler_runs(self):
        handler = RecordingHandler()

        await make_dispatcher({TOOL: handler}).call_tool(TOOL, {})

        assert handler.calls[0]["tool"] == TOOL

    @pytest.mark.asyncio
    async def test_arguments_reach_the_handler(self):
        handler = RecordingHandler()

        await make_dispatcher({TOOL: handler}).call_tool(TOOL, {"host_name": "web01"})

        assert handler.calls[0]["arguments"] == {"host_name": "web01"}

    @pytest.mark.asyncio
    async def test_absent_arguments_arrive_as_an_empty_mapping(self):
        handler = RecordingHandler()

        await make_dispatcher({TOOL: handler}).call_tool(TOOL, None)

        assert handler.calls[0]["arguments"] == {}

    @pytest.mark.asyncio
    async def test_calls_are_served_concurrently(self):
        handler = RecordingHandler()
        dispatcher = make_dispatcher({TOOL: handler})

        await asyncio.gather(*(dispatcher.call_tool(TOOL, {"n": n}) for n in range(5)))

        assert len(handler.calls) == 5


class TestConfigurationErrors:
    @pytest.mark.asyncio
    async def test_an_unusable_configuration_becomes_readable_tool_output(self):
        def explode() -> ToolRegistry:
            raise ValueError("CHECKMK_SERVER_URL is required")

        result = await Dispatcher(explode).call_tool(TOOL, {})

        assert result.is_error is True
        assert "CHECKMK_SERVER_URL" in result.content[0].text

    def test_the_catalogue_is_available_without_a_usable_registry(self):
        """tools/list must answer before CheckMK is ever contacted."""
        assert len(get_all_tools()) > 0


class TestToolCallsLeaveATrace:
    """The server's log is the only record of what a model actually did."""

    @pytest.mark.asyncio
    async def test_a_successful_call_is_logged_with_its_tool_name(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="vibemk_mcp.dispatch"):
            await make_dispatcher().call_tool(TOOL, {})

        assert any(
            TOOL in record.message and record.levelno == logging.INFO for record in caplog.records
        ), f"no INFO record names the tool: {[r.message for r in caplog.records]}"

    @pytest.mark.asyncio
    async def test_the_arguments_are_not_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """They carry host names, comment text and, for the password tools, secrets."""
        with caplog.at_level(logging.DEBUG, logger="vibemk_mcp.dispatch"):
            await make_dispatcher().call_tool(TOOL, {"password": "hunter2"})

        assert not any("hunter2" in record.getMessage() for record in caplog.records)


class TestIsErrorDetection:
    def test_a_cross_marks_a_failure(self):
        assert is_error([{"type": "text", "text": "❌ **Failed**"}]) is True

    def test_leading_whitespace_does_not_hide_the_marker(self):
        assert is_error([{"type": "text", "text": "  ❌ **Failed**"}]) is True

    def test_a_tick_is_a_success(self):
        assert is_error([{"type": "text", "text": "✅ **Done**"}]) is False

    def test_empty_content_is_a_success(self):
        assert is_error([]) is False


class TestServerWiring:
    def test_the_server_registers_the_tool_methods(self):
        server = CheckMKMCPServer()

        assert server._server.get_request_handler("tools/list") is not None
        assert server._server.get_request_handler("tools/call") is not None

    def test_every_declared_tool_validates_against_the_sdk_model(self):
        """tools/list builds these on every call; a malformed one breaks it."""
        import mcp.types as types

        for tool in get_all_tools():
            types.Tool.model_validate(tool)


class TestBothTransportsAgree:
    """The HTTP transport reads serverInfo from the Server, stdio from its options."""

    def test_the_server_carries_its_version(self):
        from config import MCPConfig

        server = CheckMKMCPServer()

        assert server._server.server_info.version == MCPConfig().server_version

    def test_the_server_carries_its_name(self):
        from config import MCPConfig

        server = CheckMKMCPServer()

        assert server._server.server_info.name == MCPConfig().server_name
