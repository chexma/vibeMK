"""
vibeMK MCP Server

Wires the tool catalogue and the dispatcher onto the official MCP SDK. The SDK
owns the protocol: version negotiation, JSON-RPC framing, the stdio and
Streamable HTTP transports, and the distinction between a protocol error and a
tool execution error.

The CheckMK connection is established on the first tool call, not at startup,
so a misconfigured server still answers initialize and tools/list.

Copyright (C) 2024 Andre <andre@example.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from typing import Any, Optional

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from api import CheckMKClient
from config import CheckMKConfig, MCPConfig
from utils import get_logger
from vibemk_mcp.dispatch import Dispatcher
from vibemk_mcp.registry import ToolRegistry
from vibemk_mcp.tools import get_all_tools

logger = get_logger(__name__)


class CheckMKMCPServer:
    """vibeMK MCP server for CheckMK integration."""

    def __init__(self) -> None:
        self.mcp_config = MCPConfig()
        self._registry: Optional[ToolRegistry] = None
        self._dispatcher = Dispatcher(self._registry_provider)
        self._server = Server(self.mcp_config.server_name)
        self._register_handlers()

    def _registry_provider(self) -> ToolRegistry:
        """Build the registry on first use; raises when configuration is unusable."""
        if self._registry is None:
            logger.info("Initializing CheckMK connection for the first tool call")
            config = CheckMKConfig.from_env()
            logger.info("CheckMK config loaded: %s site=%s user=%s", config.server_url, config.site, config.username)
            self._registry = ToolRegistry.from_client(CheckMKClient(config))
            logger.info("Registry initialized: %d tools", len(self._registry.tool_names()))
        return self._registry

    def _register_handlers(self) -> None:
        async def list_tools(_ctx: Any, _params: Any) -> types.ListToolsResult:
            # The catalogue is declared as plain dictionaries in camelCase,
            # which is the shape the Tool model validates from directly.
            return types.ListToolsResult(tools=[types.Tool.model_validate(tool) for tool in get_all_tools()])

        async def call_tool(_ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
            return await self._dispatcher.call_tool(params.name, params.arguments)

        self._server.add_request_handler("tools/list", types.PaginatedRequestParams, list_tools)
        self._server.add_request_handler("tools/call", types.CallToolRequestParams, call_tool)

    async def run(self) -> None:
        """Serve MCP requests on stdio until the input ends."""
        logger.info("Starting vibeMK %s", self.mcp_config.server_version)
        async with stdio_server() as (read_stream, write_stream):
            await self._server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=self.mcp_config.server_name,
                    server_version=self.mcp_config.server_version,
                    capabilities=self._server.get_capabilities(notification_options=None),
                ),
            )
