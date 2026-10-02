"""
Tool-to-handler registry for vibeMK

Owns the mapping from an MCP tool name to the handler that serves it. Knows
nothing about the JSON-RPC protocol or about transport.
"""

from typing import Dict, FrozenSet, Optional

from api import CheckMKClient
from handlers.acknowledgements import AcknowledgementHandler
from handlers.active_checks import ActiveChecksHandler
from handlers.agents import AgentHandler
from handlers.audit_log import AuditLogHandler
from handlers.aux_tags import AuxTagsHandler
from handlers.base import BaseHandler
from handlers.configuration import ConfigurationHandler
from handlers.connection import ConnectionHandler
from handlers.debug import DebugHandler
from handlers.discovery import DiscoveryHandler
from handlers.downtimes import DowntimeHandler
from handlers.event_console import EventConsoleHandler
from handlers.folders import FolderHandler
from handlers.groups import GroupsHandler
from handlers.host_group_rules import HostGroupRulesHandler
from handlers.hosts import HostHandler
from handlers.metrics import MetricsHandler
from handlers.monitoring import MonitoringHandler
from handlers.notifications import NotificationHandler
from handlers.passwords import PasswordsHandler
from handlers.rules import RulesHandler
from handlers.rulesets import RulesetsHandler
from handlers.service_groups import ServiceGroupHandler
from handlers.service_params import ServiceParamsHandler
from handlers.services import ServiceHandler
from handlers.sites import SitesHandler
from handlers.tags import TagsHandler
from handlers.timeperiods import TimePeriodsHandler
from handlers.user_roles import UserRolesHandler
from handlers.users import UserHandler


class ToolRegistry:
    """Maps MCP tool names to the handler instances that serve them."""

    def __init__(self, handlers: Dict[str, BaseHandler]) -> None:
        self._handlers = handlers

    @classmethod
    def from_client(cls, client: CheckMKClient) -> "ToolRegistry":
        """Build every handler against one CheckMK client."""
        connection_handler = ConnectionHandler(client)
        host_handler = HostHandler(client)
        service_handler = ServiceHandler(client)
        monitoring_handler = MonitoringHandler(client)
        notification_handler = NotificationHandler(client)
        configuration_handler = ConfigurationHandler(client)
        folder_handler = FolderHandler(client)
        metrics_handler = MetricsHandler(client)
        user_handler = UserHandler(client)
        user_roles_handler = UserRolesHandler(client)
        groups_handler = GroupsHandler(client)
        rules_handler = RulesHandler(client)
        rulesets_handler = RulesetsHandler(client)
        tags_handler = TagsHandler(client)
        timeperiods_handler = TimePeriodsHandler(client)
        passwords_handler = PasswordsHandler(client)
        debug_handler = DebugHandler(client)
        host_group_rules_handler = HostGroupRulesHandler(client)
        downtime_handler = DowntimeHandler(client)
        acknowledgement_handler = AcknowledgementHandler(client)
        discovery_handler = DiscoveryHandler(client)
        service_group_handler = ServiceGroupHandler(client)
        active_checks_handler = ActiveChecksHandler(client)
        agent_handler = AgentHandler(client)
        audit_log_handler = AuditLogHandler(client)
        aux_tags_handler = AuxTagsHandler(client)
        event_console_handler = EventConsoleHandler(client)
        service_params_handler = ServiceParamsHandler(client)
        sites_handler = SitesHandler(client)

        return cls(
            {
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
                "vibemk_bulk_create_hosts": host_handler,
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
                # Monitoring and problems
                "vibemk_get_current_problems": monitoring_handler,
                "vibemk_acknowledge_problem": monitoring_handler,
                "vibemk_schedule_downtime": downtime_handler,
                "vibemk_get_downtimes": monitoring_handler,
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
                # Notification rules
                "vibemk_get_notification_rules": notification_handler,
                "vibemk_get_notification_rule": notification_handler,
                "vibemk_create_notification_rule": notification_handler,
                "vibemk_update_notification_rule": notification_handler,
                "vibemk_delete_notification_rule": notification_handler,
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
                # Active checks (PR #3)
                "vibemk_create_custom_check": active_checks_handler,
                "vibemk_create_dns_check": active_checks_handler,
                "vibemk_create_ftp_check": active_checks_handler,
                "vibemk_create_http_check": active_checks_handler,
                "vibemk_create_icmp_check": active_checks_handler,
                "vibemk_create_inventory_check": active_checks_handler,
                "vibemk_create_ldap_check": active_checks_handler,
                "vibemk_create_mkevents_check": active_checks_handler,
                "vibemk_create_smb_check": active_checks_handler,
                "vibemk_create_smtp_check": active_checks_handler,
                "vibemk_create_tcp_check": active_checks_handler,
                "vibemk_delete_active_check": active_checks_handler,
                "vibemk_list_active_checks": active_checks_handler,
                # Agent bakery (CEE/Cloud)
                "vibemk_bake_agents": agent_handler,
                "vibemk_baking_status": agent_handler,
                "vibemk_download_agent_by_host": agent_handler,
                # Audit log
                "vibemk_get_audit_log": audit_log_handler,
                # Auxiliary tags
                "vibemk_create_aux_tag": aux_tags_handler,
                "vibemk_delete_aux_tag": aux_tags_handler,
                "vibemk_get_aux_tags": aux_tags_handler,
                "vibemk_update_aux_tag": aux_tags_handler,
                # Event console
                "vibemk_acknowledge_event": event_console_handler,
                "vibemk_change_event_state": event_console_handler,
                "vibemk_delete_events": event_console_handler,
                "vibemk_get_events": event_console_handler,
                # Service parameters
                "vibemk_delete_service_param_rule": service_params_handler,
                "vibemk_list_process_rules": service_params_handler,
                "vibemk_set_interface_params": service_params_handler,
                "vibemk_set_memory_thresholds": service_params_handler,
                "vibemk_set_process_thresholds": service_params_handler,
                # Sites
                "vibemk_get_sites": sites_handler,
                "vibemk_login_site": sites_handler,
                "vibemk_logout_site": sites_handler,
                # Further tools added alongside the handlers above
                "vibemk_checkmk_rules_guide": configuration_handler,
                "vibemk_modify_downtime": downtime_handler,
                "vibemk_clone_host": host_handler,
                "vibemk_rename_host": host_handler,
                "vibemk_get_custom_graph": metrics_handler,
                "vibemk_search_metrics": metrics_handler,
                "vibemk_delete_comment": monitoring_handler,
            }
        )

    def handler_for(self, tool_name: str) -> Optional[BaseHandler]:
        """Return the handler for a tool, or None when it is not registered."""
        return self._handlers.get(tool_name)

    def tool_names(self) -> FrozenSet[str]:
        """Every tool name this registry can route."""
        return frozenset(self._handlers)
