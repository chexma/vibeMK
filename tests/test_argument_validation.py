"""
Tool arguments are checked against the tool's inputSchema

The server registers its tools/call handler on the SDK's low-level server,
which does not validate arguments. Without this check a missing or mistyped
argument reached the handler, which either answered with its own message or
sent CheckMK something it would refuse.
"""

from typing import Any, Dict, List

import pytest
from mcp import Client

from vibemk_mcp.dispatch import Dispatcher
from vibemk_mcp.registry import ToolRegistry
from vibemk_mcp.server import CheckMKMCPServer
from vibemk_mcp.tools import get_all_tools

SCHEMA = {
    "type": "object",
    "properties": {
        "host_name": {"type": "string"},
        "mode": {"type": "string", "enum": ["new", "refresh"]},
        "timeout": {"type": "number", "minimum": 1},
    },
    "required": ["host_name"],
}


class RecordingHandler:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.calls.append(arguments)
        return [{"type": "text", "text": "✅ **Done**"}]


@pytest.fixture
def handler():
    return RecordingHandler()


@pytest.fixture
def dispatcher(handler):
    registry = ToolRegistry({"tool": handler})
    return Dispatcher(lambda: registry, input_schemas={"tool": SCHEMA})


class TestArgumentsAreValidated:
    @pytest.mark.asyncio
    async def test_valid_arguments_reach_the_handler(self, dispatcher, handler):
        result = await dispatcher.call_tool("tool", {"host_name": "web01", "mode": "new", "timeout": 30})

        assert result.is_error is False
        assert handler.calls == [{"host_name": "web01", "mode": "new", "timeout": 30}]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("arguments", "expected"),
        [
            ({}, "'host_name' is a required property"),
            ({"host_name": 42}, "host_name: 42 is not of type 'string'"),
            ({"host_name": "web01", "mode": "tabula"}, "mode: 'tabula' is not one of"),
            ({"host_name": "web01", "timeout": "30"}, "timeout: '30' is not of type 'number'"),
            ({"host_name": "web01", "timeout": 0}, "timeout: 0 is less than the minimum of 1"),
        ],
    )
    async def test_invalid_arguments_are_refused_before_the_handler(self, dispatcher, handler, arguments, expected):
        result = await dispatcher.call_tool("tool", arguments)

        assert result.is_error is True
        assert "Invalid arguments" in result.content[0].text
        assert expected in result.content[0].text
        assert handler.calls == []

    @pytest.mark.asyncio
    async def test_every_problem_is_reported_at_once(self, dispatcher):
        result = await dispatcher.call_tool("tool", {"mode": "tabula", "timeout": "30"})

        text = result.content[0].text
        assert "'host_name' is a required property" in text
        assert "mode:" in text
        assert "timeout:" in text

    @pytest.mark.asyncio
    async def test_missing_arguments_count_as_an_empty_object(self, dispatcher):
        result = await dispatcher.call_tool("tool", None)

        assert result.is_error is True
        assert "'host_name' is a required property" in result.content[0].text


class TestOverTheProtocol:
    @pytest.mark.asyncio
    async def test_the_server_validates_against_the_catalogue(self):
        server = CheckMKMCPServer()

        async with Client(server._server, mode="legacy") as client:
            result = await client.call_tool("vibemk_get_host_status", {})

        assert result.is_error is True
        assert "'host_name' is a required property" in result.content[0].text

    def test_every_tool_has_a_schema_to_validate_against(self):
        from jsonschema import Draft202012Validator

        for tool in get_all_tools():
            Draft202012Validator.check_schema(tool["inputSchema"])
