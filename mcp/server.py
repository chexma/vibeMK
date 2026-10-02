"""
vibeMK MCP Server

Wires the transport, the dispatcher and the tool registry together. The
CheckMK connection is established on the first tool call, not at startup, so a
misconfigured server still answers initialize and tools/list.

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

from typing import Any, Dict, Optional

from api import CheckMKClient
from config import CheckMKConfig, MCPConfig
from mcp.dispatch import Dispatcher
from mcp.registry import ToolRegistry
from mcp.transport import StdioTransport
from utils import get_logger

logger = get_logger(__name__)


class CheckMKMCPServer:
    """vibeMK MCP server for CheckMK integration."""

    def __init__(self) -> None:
        self.mcp_config = MCPConfig()
        self._registry: Optional[ToolRegistry] = None
        self._dispatcher = Dispatcher(self._registry_provider, self.mcp_config)
        self._transport = StdioTransport(self._dispatcher.handle)

    def _registry_provider(self) -> ToolRegistry:
        """Build the registry on first use; raises when configuration is unusable."""
        if self._registry is None:
            logger.info("Initializing CheckMK connection for the first tool call")
            config = CheckMKConfig.from_env()
            logger.info("CheckMK config loaded: %s site=%s user=%s", config.server_url, config.site, config.username)
            self._registry = ToolRegistry.from_client(CheckMKClient(config))
            logger.info("Registry initialized: %d tools", len(self._registry.tool_names()))
        return self._registry

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle one MCP request directly, without going through the transport."""
        return await self._dispatcher.handle(request)

    async def run(self) -> None:
        """Serve MCP requests on stdio until the input ends."""
        logger.info("Starting vibeMK %s", self.mcp_config.server_version)
        await self._transport.run()
