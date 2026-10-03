"""
Tool-call semantics.

The SDK owns the protocol -- framing, version negotiation, and the difference
between a JSON-RPC error and a result. What stays ours is what a tool call
means: which handler runs, whether a failure is reported as a result the model
can act on, and what reaches the log.
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from vibemk.server.dispatch import Dispatcher, is_error
from vibemk.server.registry import ToolRegistry
from vibemk.server.server import CheckMKMCPServer
from vibemk.server.tools import get_all_tools

TOOL = "vibemk_get_checkmk_version"
OTHER_TOOL = "vibemk_get_host_status"


class RecordingHandler:
    """A handler that records what it was asked and answers predictably."""

    def __init__(self, text: str = "✅ **Done**", raises: BaseException | None = None, failed: bool = False) -> None:
        self.text = text
        self.raises = raises
        self.failed = failed
        self.calls: List[Dict[str, Any]] = []

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.calls.append({"tool": tool_name, "arguments": arguments})
        if self.raises is not None:
            raise self.raises
        return [{"type": "text", "text": self.text}, *([{"type": "_error"}] if self.failed else [])]


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
        handlers = {TOOL: RecordingHandler(text="❌ **Host not found**", failed=True)}

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


class BlockingHandler:
    """Waits the way the CheckMK client does: synchronously, without an await."""

    def __init__(self, release: threading.Event) -> None:
        self.release = release
        self.released = False

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.released = self.release.wait(timeout=2)
        return [{"type": "text", "text": "✅ **Done**"}]


class ReleasingHandler:
    def __init__(self, release: threading.Event) -> None:
        self.release = release

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.release.set()
        return [{"type": "text", "text": "✅ **Done**"}]


class TestABlockingCallDoesNotStallTheServer:
    """The client blocks in urllib. Over Streamable HTTP several sessions share
    one event loop, so a call waiting on CheckMK must not hold up the others."""

    @pytest.mark.asyncio
    async def test_a_second_call_runs_while_the_first_one_blocks(self):
        release = threading.Event()
        slow = BlockingHandler(release)
        dispatcher = make_dispatcher({TOOL: slow, OTHER_TOOL: ReleasingHandler(release)})

        # On a shared loop the slow call holds it until its wait times out,
        # and the call that would release it only runs afterwards.
        await asyncio.gather(dispatcher.call_tool(TOOL, {}), dispatcher.call_tool(OTHER_TOOL, {}))

        assert slow.released is True

    @pytest.mark.asyncio
    async def test_a_handler_failure_still_comes_back_as_a_result(self):
        handlers = {TOOL: RecordingHandler(raises=RuntimeError("boom"))}

        result = await make_dispatcher(handlers).call_tool(TOOL, {})

        assert result.is_error is True
        assert "boom" in result.content[0].text


class TestTheConnectionIsBuiltOnce:
    def test_concurrent_first_calls_share_one_registry(self):
        """Calls now arrive on worker threads; the first ones must not each
        run URL detection and build a registry of their own."""
        server = CheckMKMCPServer()
        built: List[object] = []

        def slow_registry(_client: object) -> ToolRegistry:
            time.sleep(0.05)
            registry = ToolRegistry({})
            built.append(registry)
            return registry

        with (
            patch("vibemk.server.server.CheckMKConfig.from_env"),
            patch("vibemk.server.server.CheckMKClient"),
            patch("vibemk.server.server.ToolRegistry.from_client", side_effect=slow_registry),
            ThreadPoolExecutor(max_workers=4) as pool,
        ):
            registries = list(pool.map(lambda _: server._registry_provider(), range(4)))

        assert len(built) == 1
        assert all(registry is built[0] for registry in registries)


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
        with caplog.at_level(logging.INFO, logger="vibemk.server.dispatch"):
            await make_dispatcher().call_tool(TOOL, {})

        assert any(
            TOOL in record.message and record.levelno == logging.INFO for record in caplog.records
        ), f"no INFO record names the tool: {[r.message for r in caplog.records]}"

    @pytest.mark.asyncio
    async def test_the_arguments_are_not_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """They carry host names, comment text and, for the password tools, secrets."""
        with caplog.at_level(logging.DEBUG, logger="vibemk.server.dispatch"):
            await make_dispatcher().call_tool(TOOL, {"password": "hunter2"})

        assert not any("hunter2" in record.getMessage() for record in caplog.records)


class TestIsErrorDetection:
    """A failure is what the handler declares, not what its prose looks like."""

    def test_the_error_block_marks_a_failure(self):
        assert is_error([{"type": "text", "text": "❌ **Failed**"}, {"type": "_error"}]) is True

    def test_a_cross_in_the_text_alone_is_not_a_failure(self):
        """A CRITICAL service or a failed job may well be shown with ❌ -- the call itself succeeded."""
        assert is_error([{"type": "text", "text": "❌ **Check_MK** is CRITICAL"}]) is False

    def test_a_tick_is_a_success(self):
        assert is_error([{"type": "text", "text": "✅ **Done**"}]) is False

    def test_empty_content_is_a_success(self):
        assert is_error([]) is False

    def test_the_error_block_never_reaches_the_client(self):
        from vibemk.server.dispatch import to_content_blocks

        blocks = to_content_blocks([{"type": "text", "text": "❌ **Failed**"}, {"type": "_error"}])

        assert [block.text for block in blocks] == ["❌ **Failed**"]


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
        from vibemk.config import MCPConfig

        server = CheckMKMCPServer()

        assert server._server.server_info.version == MCPConfig().server_version

    def test_the_server_carries_its_name(self):
        from vibemk.config import MCPConfig

        server = CheckMKMCPServer()

        assert server._server.server_info.name == MCPConfig().server_name
