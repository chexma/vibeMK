"""
Behavioural annotations for the tool catalogue.

MCP lets a server tell the client what a tool does before it runs: whether it
only reads, whether it can destroy something, whether calling it twice is the
same as calling it once. A host uses that to decide what needs a confirmation
prompt, and a model uses it to decide what is safe to try.

The classification is explicit rather than derived from the tool name. A wrong
`readOnlyHint` on a tool that deletes hosts is worse than no hint at all, so
a tool that is in none of these sets is treated as a write that may be
destructive -- the cautious reading -- and `test_tool_registry` fails until it
is classified here.

Note on the metric tools: they reach CheckMK over POST, because its metric API
is queried that way. The verb is not the question; `readOnlyHint` asks whether
the tool changes anything, and they do not.
"""

from typing import Any, Dict

# Tools that only read. Every entry here was checked against its handler.
READ_ONLY = frozenset(
    {
        "vibemk_baking_status",
        "vibemk_check_host_downtime_status",
        "vibemk_checkmk_rules_guide",
        "vibemk_compare_host_states",
        "vibemk_debug_api_endpoints",
        "vibemk_debug_checkmk_connection",
        "vibemk_debug_permissions",
        "vibemk_debug_url_detection",
        "vibemk_download_agent_by_host",
        "vibemk_find_host_grouping_rulesets",
        "vibemk_get_active_downtimes",
        "vibemk_get_audit_log",
        "vibemk_get_aux_tags",
        "vibemk_get_bulk_discovery_status",
        "vibemk_get_checkmk_hosts",
        "vibemk_get_checkmk_services",
        "vibemk_get_checkmk_version",
        "vibemk_get_comments",
        "vibemk_get_contact_groups",
        "vibemk_get_current_problems",
        "vibemk_get_custom_graph",
        "vibemk_get_discovery_background_job",
        "vibemk_get_discovery_status",
        "vibemk_get_downtimes",
        "vibemk_get_events",
        "vibemk_get_example_rule_structures",
        "vibemk_get_folder_hosts",
        "vibemk_get_folders",
        "vibemk_get_host_config",
        "vibemk_get_host_details",
        "vibemk_get_host_effective_attributes",
        "vibemk_get_host_groups",
        "vibemk_get_host_metrics",
        "vibemk_get_host_status",
        "vibemk_get_host_tags",
        "vibemk_get_notification_rule",
        "vibemk_get_notification_rules",
        "vibemk_get_passwords",
        "vibemk_get_pending_changes",
        "vibemk_get_ruleset",
        "vibemk_get_rulesets",
        "vibemk_get_service_group",
        "vibemk_get_service_groups",
        "vibemk_get_service_metrics",
        "vibemk_get_service_status",
        "vibemk_get_sites",
        "vibemk_get_timeperiods",
        "vibemk_get_users",
        "vibemk_list_acknowledgements",
        "vibemk_list_active_checks",
        "vibemk_list_available_metrics",
        "vibemk_list_downtimes",
        "vibemk_list_process_rules",
        "vibemk_list_rulesets",
        "vibemk_list_service_groups",
        "vibemk_list_user_roles",
        "vibemk_search_metrics",
        "vibemk_search_rulesets",
        "vibemk_show_ruleset",
        "vibemk_show_user_role",
        "vibemk_test_all_endpoints",
        "vibemk_test_direct_url",
        "vibemk_validate_host_config",
        "vibemk_wait_for_discovery",
    }
)

# Tools that remove something. Repeating one leaves the same state, so they
# are idempotent as well as destructive.
DESTRUCTIVE = frozenset(
    {
        "vibemk_bulk_delete_service_groups",
        "vibemk_delete_active_check",
        "vibemk_delete_aux_tag",
        "vibemk_delete_comment",
        "vibemk_delete_contact_group",
        "vibemk_delete_downtime",
        "vibemk_delete_events",
        "vibemk_delete_folder",
        "vibemk_delete_host",
        "vibemk_delete_host_group",
        "vibemk_delete_host_tag",
        "vibemk_delete_notification_rule",
        "vibemk_delete_password",
        "vibemk_delete_rule",
        "vibemk_delete_service_group",
        "vibemk_delete_service_param_rule",
        "vibemk_delete_timeperiod",
        "vibemk_delete_user",
        "vibemk_delete_user_role",
        "vibemk_remove_acknowledgement",
        "vibemk_remove_user_from_group",
    }
)

# Writes that change something without removing it.
SAFE_WRITES = frozenset(
    {
        "vibemk_acknowledge_event",
        "vibemk_acknowledge_host_problem",
        "vibemk_acknowledge_problem",
        "vibemk_acknowledge_service_problem",
        "vibemk_activate_changes",
        "vibemk_add_comment",
        "vibemk_add_user_to_group",
        "vibemk_bake_agents",
        "vibemk_bulk_create_hosts",
        "vibemk_bulk_create_service_groups",
        "vibemk_bulk_update_hosts",
        "vibemk_bulk_update_service_groups",
        "vibemk_change_event_state",
        "vibemk_clone_host",
        "vibemk_create_aux_tag",
        "vibemk_create_cluster_host",
        "vibemk_create_contact_group",
        "vibemk_create_custom_check",
        "vibemk_create_dns_check",
        "vibemk_create_folder",
        "vibemk_create_ftp_check",
        "vibemk_create_host",
        "vibemk_create_host_contactgroup_rule",
        "vibemk_create_host_group",
        "vibemk_create_host_hostgroup_rule",
        "vibemk_create_host_tag",
        "vibemk_create_http_check",
        "vibemk_create_icmp_check",
        "vibemk_create_inventory_check",
        "vibemk_create_ldap_check",
        "vibemk_create_mkevents_check",
        "vibemk_create_notification_rule",
        "vibemk_create_password",
        "vibemk_create_rule",
        "vibemk_create_service_group",
        "vibemk_create_smb_check",
        "vibemk_create_smtp_check",
        "vibemk_create_tcp_check",
        "vibemk_create_timeperiod",
        "vibemk_create_user",
        "vibemk_create_user_role",
        "vibemk_login_site",
        "vibemk_logout_site",
        "vibemk_modify_downtime",
        "vibemk_move_folder",
        "vibemk_move_host",
        "vibemk_move_rule",
        "vibemk_rename_host",
        "vibemk_schedule_downtime",
        "vibemk_schedule_host_downtime",
        "vibemk_schedule_service_downtime",
        "vibemk_set_interface_params",
        "vibemk_set_memory_thresholds",
        "vibemk_set_process_thresholds",
        "vibemk_start_bulk_discovery",
        "vibemk_start_service_discovery",
        "vibemk_update_aux_tag",
        "vibemk_update_contact_group",
        "vibemk_update_folder",
        "vibemk_update_host",
        "vibemk_update_host_group",
        "vibemk_update_host_tag",
        "vibemk_update_notification_rule",
        "vibemk_update_password",
        "vibemk_update_rule",
        "vibemk_update_service_group",
        "vibemk_update_timeperiod",
        "vibemk_update_user",
        "vibemk_update_user_role",
    }
)

# Writes where repeating the call leads to the same state.
IDEMPOTENT_WRITES = frozenset(
    {
        "vibemk_bulk_update_hosts",
        "vibemk_bulk_update_service_groups",
        "vibemk_change_event_state",
        "vibemk_login_site",
        "vibemk_logout_site",
        "vibemk_modify_downtime",
        "vibemk_move_folder",
        "vibemk_move_host",
        "vibemk_move_rule",
        "vibemk_rename_host",
        "vibemk_set_interface_params",
        "vibemk_set_memory_thresholds",
        "vibemk_set_process_thresholds",
        "vibemk_update_aux_tag",
        "vibemk_update_contact_group",
        "vibemk_update_folder",
        "vibemk_update_host",
        "vibemk_update_host_group",
        "vibemk_update_host_tag",
        "vibemk_update_notification_rule",
        "vibemk_update_password",
        "vibemk_update_rule",
        "vibemk_update_service_group",
        "vibemk_update_timeperiod",
        "vibemk_update_user",
        "vibemk_update_user_role",
    }
)


def annotations_for(name: str) -> Dict[str, Any]:
    """The behavioural hints for one tool.

    `openWorldHint` is true throughout: every tool talks to a CheckMK site,
    which is an external system whose state this server does not own.
    """
    if name in READ_ONLY:
        return {"readOnlyHint": True, "openWorldHint": True}

    if name in DESTRUCTIVE:
        # Removing the same thing twice leaves the same state.
        return {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        }

    if name in SAFE_WRITES:
        return {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": name in IDEMPOTENT_WRITES,
            "openWorldHint": True,
        }

    # Unclassified: assume the worst, so a tool added without a decision here
    # is announced as destructive rather than as safe.
    return {
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    }


def title_for(description: str) -> str:
    """The human-readable name a client shows, taken from the description.

    Descriptions read "<emoji> Name - explanation", so the part before the
    dash is the name. Falls back to the whole description when it does not.
    """
    head = description.split(" - ", 1)[0]
    # Drop a leading emoji and any space after it.
    return head.lstrip("".join(c for c in head if not c.isalnum() and c not in "()_/")).strip() or description
