"""
Tool-call semantics for vibeMK

Turns a tool name and its arguments into an MCP `CallToolResult`. Knows
nothing about JSON-RPC or about transport -- the SDK owns both.
"""

from typing import Any, Callable, Dict, List, Optional, Sequence

import mcp.types as types

from utils import get_logger
from vibemk_mcp.registry import ToolRegistry

logger = get_logger(__name__)

CONFIGURATION_HELP = (
    "Please set the required environment variables:\n"
    "- CHECKMK_SERVER_URL\n- CHECKMK_SITE\n- CHECKMK_USERNAME\n- CHECKMK_PASSWORD"
)

# Handlers mark a failure by opening the first text block with this. It is the
# convention BaseHandler.error_response established and every handler follows,
# including the ones that build their content inline.
ERROR_MARKER = "❌"


def is_error(content: Sequence[Dict[str, Any]]) -> bool:
    """Whether a handler's content reports a failure.

    MCP distinguishes a protocol error (the request was malformed, or the tool
    does not exist) from a tool execution error (the tool ran and failed). The
    second belongs in the result with `isError: true`, because that is what a
    model can act on. Handlers signal it in prose, so it is read back here.
    """
    for block in content:
        if block.get("type") == "text":
            return str(block.get("text", "")).lstrip().startswith(ERROR_MARKER)
    return False


def to_content_blocks(content: Sequence[Dict[str, Any]]) -> List[types.ContentBlock]:
    """Validate a handler's raw dictionaries into typed content blocks."""
    return [types.TextContent(type="text", text=str(block.get("text", ""))) for block in content]


class Dispatcher:
    """Runs one tool call and shapes its result."""

    def __init__(self, registry_provider: Callable[[], ToolRegistry]) -> None:
        self._registry_provider = registry_provider

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]]) -> types.CallToolResult:
        """Run a tool and return its result, failures included.

        Raises only when the tool does not exist: an unknown name is a
        protocol error, and the SDK renders it as one.
        """
        # The only record of what the model did. This server creates and
        # deletes hosts, rules, users and downtimes; without this line a
        # successful deletion leaves no trace anywhere. Arguments are left out
        # on purpose -- they carry host names, comment text and, for the
        # password tools, secrets.
        logger.info("Tool call: %s", name)

        try:
            registry = self._registry_provider()
        except Exception as error:  # a misconfigured server still answers
            logger.exception("CheckMK configuration is unusable")
            return self._failure(f"❌ **CheckMK Configuration Error**\n\n{error}\n\n{CONFIGURATION_HELP}")

        handler = registry.handler_for(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")

        try:
            content = await handler.handle(name, arguments or {})
        except Exception as error:
            # The tool ran and failed. That is actionable -- the model can fix
            # an argument and retry -- so it is a result, not a -32603.
            logger.exception("Error in tool call %s", name)
            return self._failure(f"❌ **{name} failed**\n\n{error}")

        return types.CallToolResult(content=to_content_blocks(content), is_error=is_error(content))

    @staticmethod
    def _failure(text: str) -> types.CallToolResult:
        return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=True)
