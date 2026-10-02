"""
Tool-call semantics for vibeMK

Turns a tool name and its arguments into an MCP `CallToolResult`. Knows
nothing about JSON-RPC or about transport -- the SDK owns both.
"""

import asyncio
from typing import AbstractSet, Any, Callable, Dict, List, Optional, Sequence

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

# Handlers attach machine-readable data in a block of this type. It is lifted
# out here into the result's structuredContent and never sent as content.
STRUCTURED_BLOCK = "_structured"


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
    return [
        types.TextContent(type="text", text=str(block.get("text", "")))
        for block in content
        if block.get("type") != STRUCTURED_BLOCK
    ]


def structured_of(content: Sequence[Dict[str, Any]]) -> Any:
    """The machine-readable payload a handler attached, if any."""
    for block in content:
        if block.get("type") == STRUCTURED_BLOCK:
            return block.get("data")
    return None


class Dispatcher:
    """Runs one tool call and shapes its result."""

    def __init__(
        self, registry_provider: Callable[[], ToolRegistry], allowed_tools: Optional[AbstractSet[str]] = None
    ) -> None:
        self._registry_provider = registry_provider
        # None allows every tool. Read-only mode passes the read tools only.
        self._allowed_tools = allowed_tools

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

        # The handlers are coroutines, but the CheckMK client underneath them
        # blocks in urllib and never yields. Run on this loop, one call waiting
        # on a slow CheckMK -- a timeout plus retries -- would stall every other
        # session sharing the Streamable HTTP server. A worker thread with a
        # loop of its own keeps this one free.
        return await asyncio.to_thread(asyncio.run, self._call(name, arguments))

    async def _call(self, name: str, arguments: Optional[Dict[str, Any]]) -> types.CallToolResult:
        # Before the registry: a refused write must not even open the
        # CheckMK connection. A client holding a tool list from before the
        # server was restarted read-only can still name a write tool.
        if self._allowed_tools is not None and name not in self._allowed_tools:
            logger.warning("Refused %s: the server runs read-only", name)
            return self._failure(
                f"❌ **{name} is not available**\n\n"
                "This vibeMK server runs read-only: it only offers tools that read from CheckMK. "
                "Ask the operator to restart it without --read-only (VIBEMK_READ_ONLY) to make changes."
            )

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

        structured = structured_of(content)
        result = types.CallToolResult(content=to_content_blocks(content), is_error=is_error(content))
        if structured is not None:
            result.structured_content = structured
        return result

    @staticmethod
    def _failure(text: str) -> types.CallToolResult:
        return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=True)
