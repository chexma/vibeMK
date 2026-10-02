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

from vibemk.server.dispatch import Dispatcher
from vibemk.server.registry import ToolRegistry
from vibemk.server.server import CheckMKMCPServer
from vibemk.server.tools import get_all_tools

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


class TestUnknownArgumentsAreRefused:
    """additionalProperties: false on every tool, so a misspelt argument is an
    error instead of being dropped without a word."""

    def test_every_tool_closes_its_top_level_arguments(self):
        open_schemas = [
            tool["name"] for tool in get_all_tools() if tool["inputSchema"].get("additionalProperties") is not False
        ]
        assert open_schemas == []

    @pytest.mark.asyncio
    async def test_a_misspelt_argument_is_named(self):
        server = CheckMKMCPServer()

        async with Client(server._server, mode="legacy") as client:
            result = await client.call_tool("vibemk_get_host_status", {"host_name": "web01", "hostname": "web01"})

        assert result.is_error is True
        assert "'hostname' was unexpected" in result.content[0].text


class _RecordingArguments(dict):
    """An argument dict that remembers every key a handler asked for."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.read: set = set()

    def __getitem__(self, key: Any) -> Any:
        self.read.add(key)
        return super().__getitem__(key)

    def get(self, key: Any, default: Any = None) -> Any:
        self.read.add(key)
        return super().get(key, default)

    def __contains__(self, key: Any) -> bool:
        self.read.add(key)
        return super().__contains__(key)


def _sample(prop: Dict[str, Any]) -> Any:
    if "enum" in prop:
        return prop["enum"][0]
    kind = prop.get("type")
    if kind == "string":
        return "web01"
    if kind in ("integer", "number"):
        return max(1, prop.get("minimum", 1))
    if kind == "boolean":
        return False
    if kind == "array":
        return [_sample(prop["items"])] if prop.get("items") else ["web01"]
    if kind == "object":
        return {}
    return "web01"


class TestHandlersOnlyReadDeclaredArguments:
    """With additionalProperties false, an argument a handler reads but the
    schema does not declare can never arrive: the feature behind it is dead.
    That was the case for force and author on the downtime tools and port on
    the SMTP check."""

    @pytest.mark.asyncio
    async def test_no_handler_reads_an_undeclared_argument(self, mock_config):
        from unittest.mock import AsyncMock, MagicMock, patch

        from vibemk.api.client import CheckMKClient

        response = {"success": True, "status": 200, "data": {"value": [], "extensions": {}}, "headers": {}}
        client = CheckMKClient(mock_config, skip_url_detection=True)
        for method in ("get", "post", "put", "delete", "patch", "request"):
            setattr(client, method, MagicMock(return_value=response))
        registry = ToolRegistry.from_client(client)

        undeclared = {}
        with patch("time.sleep"), patch("asyncio.sleep", new=AsyncMock()):
            for tool in get_all_tools():
                declared = tool["inputSchema"].get("properties", {})
                arguments = _RecordingArguments({key: _sample(prop) for key, prop in declared.items()})
                handler = registry.handler_for(tool["name"])
                try:
                    await handler.handle(tool["name"], arguments)
                except Exception:  # the question is what was read, not whether the mock satisfied it
                    pass
                extra = sorted(arguments.read - set(declared))
                if extra:
                    undeclared[tool["name"]] = extra

        assert undeclared == {}
