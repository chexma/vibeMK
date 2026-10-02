"""
Read-only mode

An operator who wants a model to look but not touch starts the server with
--read-only or VIBEMK_READ_ONLY=1. The write tools then are not offered, and
a call that names one anyway -- from a client holding an older tool list --
is refused before it reaches CheckMK.
"""

from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from mcp import Client

from vibemk.server.annotations import DESTRUCTIVE, READ_ONLY, SAFE_WRITES
from vibemk.server.cli import parse_arguments
from vibemk.server.dispatch import Dispatcher
from vibemk.server.registry import ToolRegistry
from vibemk.server.server import CheckMKMCPServer
from vibemk.server.tools import get_all_tools


class RecordingHandler:
    def __init__(self) -> None:
        self.calls: List[str] = []

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.calls.append(tool_name)
        return [{"type": "text", "text": "✅ **Done**"}]


class TestTheSwitch:
    def test_off_by_default(self, monkeypatch):
        monkeypatch.delenv("VIBEMK_READ_ONLY", raising=False)
        assert parse_arguments([]).read_only is False

    def test_command_line_flag(self, monkeypatch):
        monkeypatch.delenv("VIBEMK_READ_ONLY", raising=False)
        assert parse_arguments(["--read-only"]).read_only is True

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
    def test_environment_variable_turns_it_on(self, monkeypatch, value):
        monkeypatch.setenv("VIBEMK_READ_ONLY", value)
        assert parse_arguments([]).read_only is True

    @pytest.mark.parametrize("value", ["", "0", "false", "no", "off"])
    def test_environment_variable_can_say_no(self, monkeypatch, value):
        monkeypatch.setenv("VIBEMK_READ_ONLY", value)
        assert parse_arguments([]).read_only is False


class TestTheDispatcherRefusesWrites:
    @pytest.mark.asyncio
    async def test_a_write_tool_is_refused_without_running(self):
        handler = RecordingHandler()
        registry = ToolRegistry({"vibemk_delete_host": handler})

        result = await Dispatcher(lambda: registry, allowed_tools=READ_ONLY).call_tool("vibemk_delete_host", {})

        assert result.is_error is True
        assert "read-only" in result.content[0].text
        assert handler.calls == []

    @pytest.mark.asyncio
    async def test_a_read_tool_still_runs(self):
        handler = RecordingHandler()
        registry = ToolRegistry({"vibemk_get_checkmk_hosts": handler})

        result = await Dispatcher(lambda: registry, allowed_tools=READ_ONLY).call_tool("vibemk_get_checkmk_hosts", {})

        assert result.is_error is False
        assert handler.calls == ["vibemk_get_checkmk_hosts"]


class TestOverTheProtocol:
    @pytest.mark.asyncio
    async def test_only_read_tools_are_listed(self):
        server = CheckMKMCPServer(read_only=True)

        async with Client(server._server, mode="legacy") as client:
            listed = {tool.name for tool in (await client.list_tools()).tools}

        assert listed
        assert listed <= READ_ONLY
        assert listed == {tool["name"] for tool in get_all_tools()} & READ_ONLY

    @pytest.mark.asyncio
    async def test_every_tool_is_listed_without_the_switch(self):
        server = CheckMKMCPServer()

        async with Client(server._server, mode="legacy") as client:
            listed = {tool.name for tool in (await client.list_tools()).tools}

        assert listed & (DESTRUCTIVE | SAFE_WRITES)

    @pytest.mark.asyncio
    async def test_a_hidden_tool_is_refused_before_connecting_to_checkmk(self):
        server = CheckMKMCPServer(read_only=True)

        with patch.object(server, "_registry_provider", side_effect=AssertionError("must not connect")):
            async with Client(server._server, mode="legacy") as client:
                result = await client.call_tool("vibemk_delete_host", {"host_name": "web01"})

        assert result.is_error is True
        assert "read-only" in result.content[0].text
