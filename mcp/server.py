"""
vibeMK MCP Server implementation

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

import asyncio
import json
import sys
from typing import Any, Dict, Optional

from api import CheckMKClient
from config import CheckMKConfig, MCPConfig
from handlers.configuration import ConfigurationHandler
from handlers.connection import ConnectionHandler
from handlers.debug import DebugHandler
from handlers.downtimes import DowntimeHandler
from handlers.folders import FolderHandler
from handlers.groups import GroupsHandler
from handlers.host_group_rules import HostGroupRulesHandler
from handlers.hosts import HostHandler
from handlers.metrics import MetricsHandler
from handlers.monitoring import MonitoringHandler
from handlers.passwords import PasswordsHandler
from handlers.rules import RulesHandler
from handlers.services import ServiceHandler
from handlers.tags import TagsHandler
from handlers.timeperiods import TimePeriodsHandler
from handlers.users import UserHandler
from mcp.tools import get_all_tools
from utils import get_logger

logger = get_logger(__name__)


class CheckMKMCPServer:
    """vibeMK MCP Server for CheckMK integration"""

    def __init__(self):
        self.config = CheckMKConfig.from_env()
        self.mcp_config = MCPConfig()

        # Validate configuration
        self.config.validate()

        # Setup client and handlers
        self.client = CheckMKClient(self.config)
        self._setup_handlers()

    def _setup_handlers(self):
        """Initialize all handlers"""
        # Create handler instances
        connection_handler = ConnectionHandler(self.client)
        host_handler = HostHandler(self.client)
        service_handler = ServiceHandler(self.client)
        monitoring_handler = MonitoringHandler(self.client)
        configuration_handler = ConfigurationHandler(self.client)
        folder_handler = FolderHandler(self.client)
        metrics_handler = MetricsHandler(self.client)
        user_handler = UserHandler(self.client)
        groups_handler = GroupsHandler(self.client)
        rules_handler = RulesHandler(self.client)
        tags_handler = TagsHandler(self.client)
        timeperiods_handler = TimePeriodsHandler(self.client)
        passwords_handler = PasswordsHandler(self.client)
        debug_handler = DebugHandler(self.client)
        host_group_rules_handler = HostGroupRulesHandler(self.client)
        downtime_handler = DowntimeHandler(self.client)

        # Define tool-to-handler mapping with vibemk_ prefix
        self.handlers = {
            # Connection tools
            "vibemk_debug_checkmk_connection": connection_handler,
            "vibemk_debug_url_detection": connection_handler,
            "vibemk_test_direct_url": connection_handler,
            "vibemk_test_all_endpoints": connection_handler,
            "vibemk_get_checkmk_version": connection_handler,
            # Host management tools
            "vibemk_get_checkmk_hosts": host_handler,
            "vibemk_get_host_status": host_handler,
            "vibemk_get_host_details": host_handler,
            "vibemk_get_host_config": host_handler,
            "vibemk_create_host": host_handler,
            "vibemk_update_host": host_handler,
            "vibemk_delete_host": host_handler,
            "vibemk_move_host": host_handler,
            "vibemk_bulk_update_hosts": host_handler,
            # Service management tools
            "vibemk_get_checkmk_services": service_handler,
            "vibemk_get_service_status": service_handler,
            "vibemk_discover_services": service_handler,
            # Monitoring and problems
            "vibemk_get_current_problems": monitoring_handler,
            "vibemk_acknowledge_problem": monitoring_handler,
            "vibemk_schedule_downtime": monitoring_handler,
            "vibemk_get_downtimes": monitoring_handler,
            "vibemk_delete_downtime": monitoring_handler,
            "vibemk_reschedule_check": monitoring_handler,
            "vibemk_get_comments": monitoring_handler,
            "vibemk_add_comment": monitoring_handler,
            # Configuration management
            "vibemk_activate_changes": configuration_handler,
            "vibemk_get_pending_changes": configuration_handler,
            # Folder management
            "vibemk_get_folders": folder_handler,
            "vibemk_create_folder": folder_handler,
            "vibemk_delete_folder": folder_handler,
            "vibemk_update_folder": folder_handler,
            "vibemk_move_folder": folder_handler,
            "vibemk_get_folder_hosts": folder_handler,
            # Metrics and performance data (RRD access)
            "vibemk_get_host_metrics": metrics_handler,
            "vibemk_get_service_metrics": metrics_handler,
            "vibemk_get_custom_graph": metrics_handler,
            "vibemk_search_metrics": metrics_handler,
            "vibemk_list_available_metrics": metrics_handler,
            # User management
            "vibemk_get_users": user_handler,
            "vibemk_create_user": user_handler,
            "vibemk_update_user": user_handler,
            "vibemk_delete_user": user_handler,
            "vibemk_get_contact_groups": user_handler,
            "vibemk_create_contact_group": user_handler,
            "vibemk_update_contact_group": user_handler,
            "vibemk_delete_contact_group": user_handler,
            "vibemk_add_user_to_group": user_handler,
            "vibemk_remove_user_from_group": user_handler,
            # Group management (host and service groups)
            "vibemk_get_host_groups": groups_handler,
            "vibemk_create_host_group": groups_handler,
            "vibemk_update_host_group": groups_handler,
            "vibemk_delete_host_group": groups_handler,
            "vibemk_get_service_groups": groups_handler,
            "vibemk_create_service_group": groups_handler,
            "vibemk_update_service_group": groups_handler,
            "vibemk_delete_service_group": groups_handler,
            # Rule management
            "vibemk_get_rulesets": rules_handler,
            "vibemk_get_ruleset": rules_handler,
            "vibemk_create_rule": rules_handler,
            "vibemk_update_rule": rules_handler,
            "vibemk_delete_rule": rules_handler,
            "vibemk_move_rule": rules_handler,
            # Tag management (host tags)
            "vibemk_get_host_tags": tags_handler,
            "vibemk_create_host_tag": tags_handler,
            "vibemk_update_host_tag": tags_handler,
            "vibemk_delete_host_tag": tags_handler,
            # Time period management
            "vibemk_get_timeperiods": timeperiods_handler,
            "vibemk_create_timeperiod": timeperiods_handler,
            "vibemk_update_timeperiod": timeperiods_handler,
            "vibemk_delete_timeperiod": timeperiods_handler,
            # Password management
            "vibemk_get_passwords": passwords_handler,
            "vibemk_create_password": passwords_handler,
            "vibemk_update_password": passwords_handler,
            "vibemk_delete_password": passwords_handler,
            # Debug tools
            "vibemk_debug_api_endpoints": debug_handler,
            "vibemk_debug_permissions": debug_handler,
            # Host group rules
            "vibemk_find_host_grouping_rulesets": host_group_rules_handler,
            "vibemk_create_host_contactgroup_rule": host_group_rules_handler,
            "vibemk_create_host_hostgroup_rule": host_group_rules_handler,
            "vibemk_get_example_rule_structures": host_group_rules_handler,
            # Downtime management
            "vibemk_schedule_host_downtime": downtime_handler,
            "vibemk_schedule_service_downtime": downtime_handler,
            "vibemk_list_downtimes": downtime_handler,
            "vibemk_get_active_downtimes": downtime_handler,
            "vibemk_delete_downtime": downtime_handler,
        }

        # Add placeholder handlers for remaining unimplemented tools
        remaining_tools = [
            # Notifications (still to be implemented)
            "vibemk_get_notification_rules",
            "vibemk_test_notification",
        ]

        # Add placeholders for not-yet-implemented tools
        for tool_name in remaining_tools:
            if tool_name not in self.handlers:
                self.handlers[tool_name] = None  # Will trigger "not yet implemented" message

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming MCP requests"""
        method = request.get("method")
        request_id = request.get("id")

        logger.debug(f"Handling request: {method}")

        try:
            if method == "initialize":
                return await self._handle_initialize(request_id)
            elif method == "notifications/initialized":
                return None
            elif method == "tools/list":
                return await self._handle_tools_list(request_id)
            elif method == "tools/call":
                return await self._handle_tools_call(request)
            else:
                return self._error_response(request_id, -32601, f"Method not found: {method}")

        except Exception as e:
            logger.exception(f"Error handling request {method}")
            return self._error_response(request_id, -32603, f"Internal error: {str(e)}")

    async def _handle_initialize(self, request_id: str) -> Dict[str, Any]:
        """Handle initialization request"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": self.mcp_config.protocol_version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": self.mcp_config.server_name, "version": self.mcp_config.server_version},
            },
        }

    async def _handle_tools_list(self, request_id: str) -> Dict[str, Any]:
        """Handle tools list request"""
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": get_all_tools()}}

    async def _handle_tools_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call request"""
        request_id = request.get("id")
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.debug(f"Tool call: {tool_name} with args: {arguments}")

        # Find appropriate handler
        handler = self.handlers.get(tool_name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"🔧 **Tool Available**: '{tool_name}'\n\nThis tool is part of vibeMK but not yet implemented.",
                        }
                    ]
                },
            }

        try:
            content = await handler.handle(tool_name, arguments)
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": content}}
        except Exception as e:
            logger.exception(f"Error in tool call {tool_name}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": f"❌ Error: {str(e)}"}]},
            }

    def _error_response(self, request_id: str, code: int, message: str) -> Dict[str, Any]:
        """Create error response"""
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    async def run(self):
        """Main server loop"""
        logger.info(f"Starting vibeMK Server {self.mcp_config.server_version}")
        logger.info(f"CheckMK Server: {self.config.server_url}")
        logger.info(f"API Base URL: {self.client.api_base_url}")

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {line}")
                    continue

                response = await self.handle_request(request)

                if response is not None:
                    print(json.dumps(response, ensure_ascii=False), flush=True)

            except KeyboardInterrupt:
                logger.info("Server stopped by user")
                break
            except Exception as e:
                logger.exception("Error in main loop")
                break
