"""
Tool-call semantics for vibeMK

Turns a tool name and its arguments into an MCP `CallToolResult`. Knows
nothing about JSON-RPC or about transport -- the SDK owns both.
"""

import asyncio
from typing import AbstractSet, Any, Callable, Dict, List, Mapping, Optional, Sequence

import mcp.types as types
from jsonschema import Draft202012Validator

from vibemk.server.registry import ToolRegistry
from vibemk.utils import get_logger

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
        self,
        registry_provider: Callable[[], ToolRegistry],
        allowed_tools: Optional[AbstractSet[str]] = None,
        input_schemas: Optional[Mapping[str, Mapping[str, Any]]] = None,
    ) -> None:
        self._registry_provider = registry_provider
        # None allows every tool. Read-only mode passes the read tools only.
        self._allowed_tools = allowed_tools
        # The SDK's low-level server leaves argument validation to us. Built
        # once: compiling a validator per call would cost more than the check.
        self._validators = {name: Draft202012Validator(schema) for name, schema in (input_schemas or {}).items()}
        # The tools whose schema offers activate_changes. Deciding here, from
        # the schema, keeps what is offered and what is done in one place:
        # when four handlers each carried their own copy, the other 34 tools
        # advertised the flag and ignored it.
        self._activating = frozenset(
            name for name, schema in (input_schemas or {}).items() if "activate_changes" in schema.get("properties", {})
        )

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

        problems = self._argument_problems(name, arguments or {})
        if problems:
            # A result, not a protocol error: the model can correct the
            # arguments and call again, and every problem is listed so it
            # can do so in one go.
            return self._failure(f"❌ **Invalid arguments for {name}**\n\n" + "\n".join(f"- {p}" for p in problems))

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

        failed = is_error(content)
        if not failed and name in self._activating and (arguments or {}).get("activate_changes") is True:
            content = self._with_activation(handler, content)

        structured = structured_of(content)
        result = types.CallToolResult(content=to_content_blocks(content), is_error=failed)
        if structured is not None:
            result.structured_content = structured
        return result

    @staticmethod
    def _with_activation(handler: Any, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Activate the pending changes and append the one-line outcome to the report.

        _run_activation honours NEVER_ACTIVATE_CHANGES and never raises, so a
        failed activation cannot hide the write that did succeed.
        """
        line = handler._run_activation()
        texts = [i for i, block in enumerate(content) if block.get("type") == "text"]
        if not texts:
            return [*content, {"type": "text", "text": line}]
        last = texts[-1]
        updated = dict(content[last], text=f"{content[last].get('text', '')}\n{line}")
        return [*content[:last], updated, *content[last + 1 :]]

    def _argument_problems(self, name: str, arguments: Dict[str, Any]) -> List[str]:
        """What is wrong with the arguments, one line per problem; empty if nothing is."""
        validator = self._validators.get(name)
        if validator is None:
            return []
        problems = []
        for error in sorted(validator.iter_errors(arguments), key=lambda e: list(map(str, e.absolute_path))):
            location = ".".join(str(part) for part in error.absolute_path)
            problems.append(f"{location}: {error.message}" if location else error.message)
        return problems

    @staticmethod
    def _failure(text: str) -> types.CallToolResult:
        return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=True)
