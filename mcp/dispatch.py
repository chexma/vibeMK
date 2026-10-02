"""
JSON-RPC dispatch for vibeMK

Implements the MCP methods over plain dictionaries. Performs no I/O and knows
nothing about how a request arrived.
"""

from typing import Any, Callable, Dict, Optional

from config import MCPConfig
from mcp.registry import ToolRegistry
from mcp.tools import get_all_tools
from utils import get_logger

logger = get_logger(__name__)

CONFIGURATION_HELP = (
    "Please set the required environment variables:\n"
    "- CHECKMK_SERVER_URL\n- CHECKMK_SITE\n- CHECKMK_USERNAME\n- CHECKMK_PASSWORD"
)


class Dispatcher:
    """Routes MCP requests to handlers and shapes JSON-RPC responses."""

    def __init__(self, registry_provider: Callable[[], ToolRegistry], config: MCPConfig) -> None:
        self._registry_provider = registry_provider
        self._config = config

    async def handle(self, request: Any) -> Optional[Dict[str, Any]]:
        """Handle one MCP request; returns None for notifications."""
        if not isinstance(request, dict):
            return self._error(None, -32600, "Invalid Request: must be an object")

        request_id = request.get("id")
        if "method" not in request:
            return self._error(request_id, -32600, "Invalid Request: missing required field 'method'")
        if request.get("jsonrpc") != "2.0":
            return self._error(request_id, -32600, "Invalid Request: missing or invalid 'jsonrpc' field")

        method = request["method"]
        try:
            return await self._route(method, request)
        except Exception as error:  # the loop must survive any handler
            logger.exception("Error handling request %s", method)
            return self._error(request_id, -32603, f"Internal error: {error}")

    async def _route(self, method: str, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        request_id = request.get("id")
        if method == "initialize":
            return self._initialize(request)
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": get_all_tools()}}
        if method == "tools/call":
            return await self._call_tool(request)
        return self._error(request_id, -32601, f"Method not found: {method}")

    def _initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        params = request.get("params", {})
        negotiated = self._config.negotiate_protocol_version(params.get("protocolVersion"))
        logger.info("Protocol negotiation: client=%s, answered=%s", params.get("protocolVersion"), negotiated)
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": negotiated,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": self._config.server_name, "version": self._config.server_version},
            },
        }

    async def _call_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        request_id = request.get("id")
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        # The only record of what the model did. This server creates and
        # deletes hosts, rules, users and downtimes; without this line a
        # successful deletion leaves no trace anywhere. Arguments are left out
        # on purpose — they carry host names, comment text and, for the
        # password tools, secrets.
        logger.info("Tool call: %s", tool_name)

        try:
            registry = self._registry_provider()
        except Exception as error:  # reported as tool content, not a crash
            logger.exception("CheckMK configuration is unusable")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"❌ **CheckMK Configuration Error**\n\n{error}\n\n{CONFIGURATION_HELP}",
                        }
                    ]
                },
            }

        handler = registry.handler_for(tool_name)
        if handler is None:
            return self._error(request_id, -32601, f"Unknown tool: {tool_name}")

        try:
            content = await handler.handle(tool_name, arguments)
        except Exception as error:  # one bad tool must not end the session
            logger.exception("Error in tool call %s", tool_name)
            return self._error(request_id, -32603, f"Internal error in {tool_name}: {error}")
        return {"jsonrpc": "2.0", "id": request_id, "result": {"content": content}}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
