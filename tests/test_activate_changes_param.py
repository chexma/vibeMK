"""
activate_changes on the write tools

tools.py offers an activate_changes argument on every write tool, but only
four of the fourteen handlers behind them read it -- each with its own copy of
the same block. On the other 34 tools (rules, folders, groups, passwords, time
periods, tags, roles...) a model that asked for activation got a success
report and changes that stayed pending.

The dispatcher now honours it for every tool whose schema offers it, so what
is advertised and what is done come from the same place.
"""

import pathlib
from typing import Any, Dict, List

import pytest

from vibemk_mcp.dispatch import Dispatcher
from vibemk_mcp.registry import ToolRegistry
from vibemk_mcp.tools import get_all_tools

WRITE_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "activate_changes": {"type": "boolean"}},
    "additionalProperties": False,
}
READ_SCHEMA = {"type": "object", "properties": {"name": {"type": "string"}}, "additionalProperties": False}


class ActivatingHandler:
    def __init__(self, text: str = "✅ **Rule created**") -> None:
        self.text = text
        self.activations = 0

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"type": "text", "text": self.text}]

    def _run_activation(self) -> str:
        self.activations += 1
        return "🔄 Changes activated"


def _dispatcher(handler: ActivatingHandler) -> Dispatcher:
    registry = ToolRegistry({"write": handler, "read": handler})
    return Dispatcher(lambda: registry, input_schemas={"write": WRITE_SCHEMA, "read": READ_SCHEMA})


class TestTheDispatcherActivates:
    @pytest.mark.asyncio
    async def test_a_successful_write_with_the_flag_is_activated(self):
        handler = ActivatingHandler()

        result = await _dispatcher(handler).call_tool("write", {"name": "x", "activate_changes": True})

        assert handler.activations == 1
        assert result.content[-1].text.endswith("🔄 Changes activated")
        assert result.is_error is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("arguments", [{"name": "x"}, {"name": "x", "activate_changes": False}])
    async def test_without_the_flag_nothing_is_activated(self, arguments):
        handler = ActivatingHandler()

        await _dispatcher(handler).call_tool("write", arguments)

        assert handler.activations == 0

    @pytest.mark.asyncio
    async def test_a_failed_write_is_not_activated(self):
        handler = ActivatingHandler(text="❌ **Creating the rule failed**")

        result = await _dispatcher(handler).call_tool("write", {"name": "x", "activate_changes": True})

        assert handler.activations == 0
        assert result.is_error is True


class TestEveryOfferIsHonoured:
    def test_the_handlers_leave_activation_to_the_dispatcher(self):
        """One place decides. A handler with its own copy would activate twice."""
        handlers = pathlib.Path(__file__).resolve().parent.parent / "handlers"
        copies = [path.name for path in sorted(handlers.glob("*.py")) if '.get("activate_changes")' in path.read_text()]
        assert copies == []

    def test_every_tool_offering_it_reaches_a_handler_that_can_activate(self):
        from unittest.mock import MagicMock

        registry = ToolRegistry.from_client(MagicMock())
        offering = [t["name"] for t in get_all_tools() if "activate_changes" in t["inputSchema"].get("properties", {})]

        assert len(offering) > 30
        assert [n for n in offering if not hasattr(registry.handler_for(n), "_run_activation")] == []
