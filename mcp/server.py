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
from handlers.acknowledgements import AcknowledgementHandler
from handlers.configuration import ConfigurationHandler
from handlers.connection import ConnectionHandler
from handlers.debug import DebugHandler
from handlers.discovery import DiscoveryHandler
from handlers.downtimes import DowntimeHandler
from handlers.folders import FolderHandler
from handlers.groups import GroupsHandler
from handlers.host_group_rules import HostGroupRulesHandler
from handlers.hosts import HostHandler
from handlers.metrics import MetricsHandler
from handlers.monitoring import MonitoringHandler
from handlers.passwords import PasswordsHandler
from handlers.rules import RulesHandler
from handlers.rulesets import RulesetsHandler
from handlers.service_groups import ServiceGroupHandler
from handlers.services import ServiceHandler
from handlers.tags import TagsHandler
from handlers.timeperiods import TimePeriodsHandler
from handlers.user_roles import UserRolesHandler
from handlers.users import UserHandler
from mcp.tools import get_all_tools
from utils import get_logger

logger = get_logger(__name__)


class CheckMKMCPServer:
    """vibeMK MCP Server for CheckMK integration"""

    def __init__(self):
        self.mcp_config = MCPConfig()

        # Defer CheckMK configuration validation until first API call
        self.config = None
        self.client = None
        self.handlers = None
        self._initialized = False

    def _ensure_initialized(self):
        """Initialize CheckMK connection and handlers on first use"""
        if self._initialized:
            logger.debug("CheckMK connection already initialized")
            return

        logger.info("Initializing CheckMK connection for first tool call...")

        try:
            # Load and validate CheckMK configuration
            logger.debug("Loading CheckMK configuration from environment...")
            self.config = CheckMKConfig.from_env()
            logger.info(
                f"CheckMK config loaded: {self.config.server_url} site={self.config.site} user={self.config.username}"
            )

            logger.debug("Validating CheckMK configuration...")
            self.config.validate()
            logger.info("CheckMK configuration validated successfully")

            # Setup client and handlers
            logger.debug("Creating CheckMK API client...")
            self.client = CheckMKClient(self.config)
            logger.info("CheckMK API client created")

            logger.debug("Setting up tool handlers...")
            self._setup_handlers()
            logger.info(f"All handlers initialized: {len(self.handlers)} tools available")

            self._initialized = True
            logger.info("CheckMK connection initialization complete")

        except Exception as e:
            # Log error with full traceback but don't crash the server
            logger.exception(f"Failed to initialize CheckMK connection: {e}")
            logger.error("This is usually due to missing environment variables or unreachable CheckMK server")
            # Raise the error so it can be handled in the tool call
            raise

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
        user_roles_handler = UserRolesHandler(self.client)
        groups_handler = GroupsHandler(self.client)
        rules_handler = RulesHandler(self.client)
        rulesets_handler = RulesetsHandler(self.client)
        tags_handler = TagsHandler(self.client)
        timeperiods_handler = TimePeriodsHandler(self.client)
        passwords_handler = PasswordsHandler(self.client)
        debug_handler = DebugHandler(self.client)
        host_group_rules_handler = HostGroupRulesHandler(self.client)
        downtime_handler = DowntimeHandler(self.client)
        acknowledgement_handler = AcknowledgementHandler(self.client)
        discovery_handler = DiscoveryHandler(self.client)
        service_group_handler = ServiceGroupHandler(self.client)

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
            "vibemk_create_cluster_host": host_handler,
            "vibemk_validate_host_config": host_handler,
            "vibemk_compare_host_states": host_handler,
            "vibemk_get_host_effective_attributes": host_handler,
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
            # User roles management
            "vibemk_list_user_roles": user_roles_handler,
            "vibemk_show_user_role": user_roles_handler,
            "vibemk_create_user_role": user_roles_handler,
            "vibemk_update_user_role": user_roles_handler,
            "vibemk_delete_user_role": user_roles_handler,
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
            # Ruleset discovery and search
            "vibemk_search_rulesets": rulesets_handler,
            "vibemk_show_ruleset": rulesets_handler,
            "vibemk_list_rulesets": rulesets_handler,
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
            "vibemk_check_host_downtime_status": downtime_handler,
            # Acknowledgement management
            "vibemk_acknowledge_host_problem": acknowledgement_handler,
            "vibemk_acknowledge_service_problem": acknowledgement_handler,
            "vibemk_list_acknowledgements": acknowledgement_handler,
            "vibemk_remove_acknowledgement": acknowledgement_handler,
            # Discovery management
            "vibemk_start_service_discovery": discovery_handler,
            "vibemk_start_bulk_discovery": discovery_handler,
            "vibemk_get_discovery_status": discovery_handler,
            "vibemk_get_bulk_discovery_status": discovery_handler,
            "vibemk_get_discovery_result": discovery_handler,
            "vibemk_wait_for_discovery": discovery_handler,
            "vibemk_get_discovery_background_job": discovery_handler,
            # Service group management
            "vibemk_create_service_group": service_group_handler,
            "vibemk_list_service_groups": service_group_handler,
            "vibemk_get_service_group": service_group_handler,
            "vibemk_update_service_group": service_group_handler,
            "vibemk_delete_service_group": service_group_handler,
            "vibemk_bulk_create_service_groups": service_group_handler,
            "vibemk_bulk_update_service_groups": service_group_handler,
            "vibemk_bulk_delete_service_groups": service_group_handler,
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
                return await self._handle_initialize(request)
            elif method == "notifications/initialized":
                return None  # No response needed for notifications
            elif method == "tools/list":
                return await self._handle_tools_list(request_id)
            elif method == "tools/call":
                return await self._handle_tools_call(request)
            else:
                return self._error_response(request_id, -32601, f"Method not found: {method}")

        except Exception as e:
            logger.exception(f"Error handling request {method}")
            return self._error_response(request_id, -32603, f"Internal error: {str(e)}")

    async def _handle_initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request"""
        request_id = request.get("id")
        params = request.get("params", {})

        logger.info(f"Initialize request received from client, ID: {request_id}")
        logger.debug(f"Initialize params: {params}")

        # Use client's protocol version if provided, otherwise use our default
        client_protocol_version = params.get("protocolVersion", self.mcp_config.protocol_version)
        logger.info(
            f"Protocol version negotiation: client={client_protocol_version}, server={self.mcp_config.protocol_version}"
        )

        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": client_protocol_version,  # Echo client's version for compatibility
                "capabilities": {"tools": {}},
                "serverInfo": {"name": self.mcp_config.server_name, "version": self.mcp_config.server_version},
            },
        }
        logger.info(f"Initialize response prepared: {response}")
        return response

    async def _handle_tools_list(self, request_id: str) -> Dict[str, Any]:
        """Handle tools list request"""
        logger.info(f"Tools list request received, ID: {request_id}")
        tools = get_all_tools()
        logger.info(f"Returning {len(tools)} tools in response")
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}

    async def _handle_tools_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call request"""
        request_id = request.get("id")
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info(f"Tool call request: {tool_name} with {len(arguments)} arguments")
        logger.debug(f"Tool call request ID: {request_id}, args: {arguments}")

        try:
            # Initialize CheckMK connection on first tool call
            self._ensure_initialized()
        except Exception as e:
            # Return configuration error to user
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"❌ **CheckMK Configuration Error**\n\n{str(e)}\n\nPlease set the required environment variables:\n- CHECKMK_SERVER_URL\n- CHECKMK_SITE\n- CHECKMK_USERNAME\n- CHECKMK_PASSWORD",
                        }
                    ]
                },
            }

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
        logger.info("CheckMK connection will be initialized on first tool call")
        logger.info("Server ready to accept MCP requests on stdin")

        while True:
            try:
                # Log that we're waiting for input
                logger.debug("Waiting for input on stdin...")
                line = sys.stdin.readline()

                if not line:
                    logger.info("No input received, stdin closed - shutting down")
                    break

                line = line.strip()
                if not line:
                    logger.debug("Empty line received, continuing")
                    continue

                logger.debug(f"Received request: {line[:100]}...")

                try:
                    request = json.loads(line)
                    logger.debug(f"Parsed JSON request, method: {request.get('method')}")
                except json.JSONDecodeError as json_err:
                    logger.error(f"Invalid JSON received: {line[:200]}... - Error: {json_err}")
                    continue

                response = await self.handle_request(request)

                if response is not None:
                    response_str = json.dumps(response, ensure_ascii=False)
                    logger.debug(f"Sending response: {response_str[:100]}...")
                    print(response_str, flush=True)
                else:
                    logger.debug("No response to send")

            except KeyboardInterrupt:
                logger.info("Server stopped by user (KeyboardInterrupt)")
                break
            except EOFError:
                logger.info("EOF reached, exiting gracefully")
                break
            except Exception as e:
                # Log the error with full traceback for debugging
                logger.exception(f"Unexpected error in main loop (continuing): {e}")
                continue

        logger.info("vibeMK Server shutdown complete")
