"""
vibeMK Tool definitions for CheckMK operations
"""

from typing import Any, Dict, List


def get_connection_tools() -> List[Dict[str, Any]]:
    """Connection and diagnostic tools"""
    return [
        {
            "name": "vibemk_debug_checkmk_connection",
            "description": "🔍 CheckMK connection diagnostics - Test server connectivity and API access",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_debug_url_detection",
            "description": "🔍 Debug URL detection - Show all tested URL patterns and results",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_test_direct_url",
            "description": "🧪 Test direct URL - Test a specific API URL manually",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "test_url": {
                        "type": "string",
                        "description": "Full URL to test (e.g., http://localhost:8080/cmk/check_mk/api/1.0/version)",
                    }
                },
                "required": ["test_url"],
            },
        },
        {
            "name": "vibemk_test_all_endpoints",
            "description": "🧪 Test all API endpoints - Comprehensive endpoint availability check",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_get_checkmk_version",
            "description": "📋 Get CheckMK version - Show version information and system details",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def get_host_tools() -> List[Dict[str, Any]]:
    """Host management tools"""
    return [
        {
            "name": "vibemk_get_checkmk_hosts",
            "description": "🖥️ List hosts - Show all monitored hosts with optional folder filtering",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Folder path to filter hosts"},
                    "effective_attributes": {"type": "boolean", "description": "Include effective attributes"},
                },
            },
        },
        {
            "name": "vibemk_get_host_status",
            "description": "📊 Get host status - Show current monitoring status of a specific host",
            "inputSchema": {
                "type": "object",
                "properties": {"host_name": {"type": "string", "description": "Name of the host"}},
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_get_host_details",
            "description": "🔍 Host details - Get comprehensive host information",
            "inputSchema": {
                "type": "object",
                "properties": {"host_name": {"type": "string", "description": "Name of the host"}},
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_get_host_config",
            "description": "⚙️ Get host configuration - Show host configuration with attributes",
            "inputSchema": {
                "type": "object",
                "properties": {"host_name": {"type": "string", "description": "Name of the host"}},
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_create_host",
            "description": "➕ Create host - Add a new host to monitoring",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Name of the new host"},
                    "folder": {"type": "string", "description": "Folder path"},
                    "attributes": {"type": "object", "description": "Host attributes (ipaddress, etc.)"},
                },
                "required": ["host_name", "folder", "attributes"],
            },
        },
        {
            "name": "vibemk_update_host",
            "description": "📝 Update host - Modify host configuration with flexible attribute management",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Name of the host"},
                    "attributes": {"type": "object", "description": "Updated attributes"},
                    "update_mode": {
                        "type": "string",
                        "description": "Update mode: 'update' (merge), 'overwrite' (replace), 'remove' (delete attributes)",
                        "enum": ["update", "overwrite", "remove"],
                        "default": "update",
                    },
                    "remove_attributes": {
                        "type": "array",
                        "description": "List of attribute names to remove (used with remove mode)",
                        "items": {"type": "string"},
                    },
                },
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_delete_host",
            "description": "🗑️ Delete host - Remove host from monitoring",
            "inputSchema": {
                "type": "object",
                "properties": {"host_name": {"type": "string", "description": "Name of the host"}},
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_move_host",
            "description": "📁 Move host - Move host to different folder",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Name of the host"},
                    "target_folder": {"type": "string", "description": "Target folder path"},
                },
                "required": ["host_name", "target_folder"],
            },
        },
        {
            "name": "vibemk_bulk_update_hosts",
            "description": "🔄 Bulk update hosts - Update multiple hosts at once",
            "inputSchema": {
                "type": "object",
                "properties": {"entries": {"type": "array", "description": "List of host update entries"}},
                "required": ["entries"],
            },
        },
        {
            "name": "vibemk_create_cluster_host",
            "description": "🏢 Create cluster host - Create a cluster host with multiple nodes",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Name of the cluster host"},
                    "folder": {"type": "string", "description": "Folder path"},
                    "nodes": {"type": "array", "description": "List of node hostnames for the cluster"},
                    "attributes": {"type": "object", "description": "Additional host attributes"},
                },
                "required": ["host_name", "nodes"],
            },
        },
        {
            "name": "vibemk_validate_host_config",
            "description": "✅ Validate host config - Validate host configuration before applying changes",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Name of the host to validate"},
                    "attributes": {"type": "object", "description": "Host attributes to validate"},
                    "operation": {"type": "string", "description": "Operation type (create, update)"},
                    "folder": {"type": "string", "description": "Folder path"},
                },
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_compare_host_states",
            "description": "🔄 Compare host states - Compare current vs desired host configuration",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Name of the host"},
                    "desired_attributes": {"type": "object", "description": "Desired host attributes"},
                },
                "required": ["host_name", "desired_attributes"],
            },
        },
        {
            "name": "vibemk_get_host_effective_attributes",
            "description": "📋 Get effective host attributes - Show host attributes including inherited values",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Name of the host"},
                },
                "required": ["host_name"],
            },
        },
    ]


def get_service_tools() -> List[Dict[str, Any]]:
    """Service management tools"""
    return [
        {
            "name": "vibemk_get_checkmk_services",
            "description": "🔧 List services - Show services with optional host filtering",
            "inputSchema": {
                "type": "object",
                "properties": {"host_name": {"type": "string", "description": "Filter by host name"}},
            },
        },
        {
            "name": "vibemk_get_service_status",
            "description": "📊 Get service status - Show current status of a service",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Name of the host"},
                    "service_description": {"type": "string", "description": "Service description"},
                },
                "required": ["host_name", "service_description"],
            },
        },
        {
            "name": "vibemk_discover_services",
            "description": "🔍 Discover services - Start enhanced service discovery for hosts",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Name of the host"},
                    "hosts": {"type": "array", "description": "List of host names for bulk discovery"},
                    "mode": {
                        "type": "string",
                        "description": "Discovery mode: new, remove, fix_all, only_host_labels, only_service_labels",
                        "default": "new",
                    },
                    "do_full_scan": {"type": "boolean", "description": "Perform full service scan", "default": False},
                    "bulk_size": {"type": "number", "description": "Bulk processing size", "default": 10},
                    "wait_for_completion": {
                        "type": "boolean",
                        "description": "Wait for discovery completion",
                        "default": False,
                    },
                },
            },
        },
    ]


def get_monitoring_tools() -> List[Dict[str, Any]]:
    """Monitoring and problem management tools"""
    return [
        {
            "name": "vibemk_get_current_problems",
            "description": "🚨 Get current problems - Show all hosts and services with problems",
            "inputSchema": {
                "type": "object",
                "properties": {"host_name": {"type": "string", "description": "Filter by host name"}},
            },
        },
        {
            "name": "vibemk_acknowledge_problem",
            "description": "✅ Acknowledge problem - Acknowledge host or service problem",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "acknowledge_type": {"type": "string", "description": "Type: host or service"},
                    "host_name": {"type": "string", "description": "Name of the host"},
                    "service_description": {"type": "string", "description": "Service description (for service ack)"},
                    "comment": {"type": "string", "description": "Acknowledgment comment"},
                },
                "required": ["acknowledge_type", "host_name", "comment"],
            },
        },
        {
            "name": "vibemk_schedule_downtime",
            "description": "⏰ Schedule downtime - Schedule maintenance downtime",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "downtime_type": {"type": "string", "description": "Type: host, service, or hostgroup"},
                    "host_name": {"type": "string", "description": "Name of the host"},
                    "service_description": {
                        "type": "string",
                        "description": "Service description (for service downtime)",
                    },
                    "start_time": {"type": "string", "description": "Start time (ISO format)"},
                    "end_time": {"type": "string", "description": "End time (ISO format)"},
                    "comment": {"type": "string", "description": "Downtime comment"},
                },
                "required": ["downtime_type", "start_time", "end_time", "comment"],
            },
        },
    ]


def get_configuration_tools() -> List[Dict[str, Any]]:
    """Configuration management tools"""
    return [
        {
            "name": "vibemk_activate_changes",
            "description": "🔄 Activate changes - Deploy pending configuration changes",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sites": {"type": "array", "description": "List of site names"},
                    "force_foreign_changes": {"type": "boolean", "description": "Force activation"},
                },
            },
        },
        {
            "name": "vibemk_get_pending_changes",
            "description": "📋 Get pending changes - Show uncommitted configuration changes",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def get_folder_tools() -> List[Dict[str, Any]]:
    """Folder management tools"""
    return [
        {
            "name": "vibemk_get_folders",
            "description": "📁 List folders - Show folder structure with optional parent filtering",
            "inputSchema": {
                "type": "object",
                "properties": {"parent": {"type": "string", "description": "Parent folder path to filter"}},
            },
        },
        {
            "name": "vibemk_create_folder",
            "description": "➕ Create folder - Add new folder to the structure",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Folder path"},
                    "title": {"type": "string", "description": "Display title"},
                    "parent": {"type": "string", "description": "Parent folder path"},
                },
                "required": ["folder", "title"],
            },
        },
        {
            "name": "vibemk_delete_folder",
            "description": "🗑️ Delete folder - Remove folder (with options for recursive deletion)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Folder path to delete"},
                    "delete_mode": {
                        "type": "string",
                        "description": "Delete mode: 'abort_on_nonempty' or 'recursive'",
                        "default": "abort_on_nonempty",
                    },
                },
                "required": ["folder"],
            },
        },
        {
            "name": "vibemk_update_folder",
            "description": "📝 Update folder - Modify folder properties",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Folder path"},
                    "title": {"type": "string", "description": "New display title"},
                    "attributes": {"type": "object", "description": "Folder attributes"},
                },
                "required": ["folder"],
            },
        },
        {
            "name": "vibemk_move_folder",
            "description": "📁 Move folder - Move folder to different parent",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Folder path to move"},
                    "destination": {"type": "string", "description": "New parent folder path"},
                },
                "required": ["folder", "destination"],
            },
        },
        {
            "name": "vibemk_get_folder_hosts",
            "description": "🖥️ Get folder hosts - List all hosts in a specific folder",
            "inputSchema": {
                "type": "object",
                "properties": {"folder": {"type": "string", "description": "Folder path"}},
                "required": ["folder"],
            },
        },
    ]


def get_user_management_tools() -> List[Dict[str, Any]]:
    """User and contact management tools"""
    return [
        {
            "name": "vibemk_get_users",
            "description": "👥 List users - Show all CheckMK users",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_create_user",
            "description": "👤 Create user - Add new CheckMK user",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Username"},
                    "fullname": {"type": "string", "description": "Full name"},
                    "email": {"type": "string", "description": "Email address"},
                    "password": {"type": "string", "description": "Password"},
                    "roles": {"type": "array", "description": "User roles"},
                    "contactgroups": {"type": "array", "description": "Contact groups to assign user to"},
                },
                "required": ["username", "fullname"],
            },
        },
        {
            "name": "vibemk_update_user",
            "description": "📝 Update user - Modify user properties",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Username"},
                    "fullname": {"type": "string", "description": "Full name"},
                    "email": {"type": "string", "description": "Email address"},
                    "roles": {"type": "array", "description": "User roles"},
                    "contactgroups": {"type": "array", "description": "Contact groups to assign user to"},
                },
                "required": ["username"],
            },
        },
        {
            "name": "vibemk_delete_user",
            "description": "🗑️ Delete user - Remove CheckMK user",
            "inputSchema": {
                "type": "object",
                "properties": {"username": {"type": "string", "description": "Username to delete"}},
                "required": ["username"],
            },
        },
        {
            "name": "vibemk_get_contact_groups",
            "description": "👥 List contact groups - Show contact groups",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_create_contact_group",
            "description": "➕ Create contact group - Add new contact group",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Group name"},
                    "alias": {"type": "string", "description": "Display alias"},
                    "members": {"type": "array", "description": "Group members"},
                },
                "required": ["name", "alias"],
            },
        },
        {
            "name": "vibemk_add_user_to_group",
            "description": "👥 Add user to contact group - Assign user to contact group",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Username"},
                    "group_name": {"type": "string", "description": "Contact group name"},
                },
                "required": ["username", "group_name"],
            },
        },
        {
            "name": "vibemk_remove_user_from_group",
            "description": "👥 Remove user from contact group - Remove user from contact group",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Username"},
                    "group_name": {"type": "string", "description": "Contact group name"},
                },
                "required": ["username", "group_name"],
            },
        },
        {
            "name": "vibemk_update_contact_group",
            "description": "📝 Update contact group - Modify contact group properties",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Group name"},
                    "alias": {"type": "string", "description": "Display alias"},
                    "members": {"type": "array", "description": "Group members"},
                },
                "required": ["name"],
            },
        },
        {
            "name": "vibemk_delete_contact_group",
            "description": "🗑️ Delete contact group - Remove contact group",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Group name to delete"}},
                "required": ["name"],
            },
        },
    ]


def get_user_roles_tools() -> List[Dict[str, Any]]:
    """User roles management tools"""
    return [
        {
            "name": "vibemk_list_user_roles",
            "description": "👥 List user roles - Show all available user roles (built-in and custom)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "show_builtin": {
                        "type": "boolean",
                        "description": "Include built-in roles (admin, user, guest) in the list",
                        "default": True,
                    }
                },
            },
        },
        {
            "name": "vibemk_show_user_role",
            "description": "🔍 Show user role details - Display detailed information about a specific user role",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "role_id": {
                        "type": "string",
                        "description": "ID of the role to show details for",
                    }
                },
                "required": ["role_id"],
            },
        },
        {
            "name": "vibemk_create_user_role",
            "description": "➕ Create user role - Clone an existing role to create a new custom role",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "base_role_id": {
                        "type": "string",
                        "description": "Existing role ID to clone from (e.g., 'admin', 'user', 'guest')",
                    },
                    "new_role_id": {
                        "type": "string",
                        "description": "ID for the new role",
                    },
                    "new_alias": {
                        "type": "string",
                        "description": "Display name/alias for the new role",
                    },
                },
                "required": ["base_role_id", "new_role_id"],
            },
        },
        {
            "name": "vibemk_update_user_role",
            "description": "✏️ Update user role - Modify an existing user role's alias or permissions",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "role_id": {
                        "type": "string",
                        "description": "ID of the role to update",
                    },
                    "alias": {
                        "type": "string",
                        "description": "New display name/alias for the role",
                    },
                    "permissions": {
                        "type": "object",
                        "description": "Permission dictionary (permission_id: boolean)",
                    },
                },
                "required": ["role_id"],
            },
        },
        {
            "name": "vibemk_delete_user_role",
            "description": "🗑️ Delete user role - Remove a custom user role (built-in roles cannot be deleted)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "role_id": {
                        "type": "string",
                        "description": "ID of the custom role to delete",
                    }
                },
                "required": ["role_id"],
            },
        },
    ]


def get_group_management_tools() -> List[Dict[str, Any]]:
    """Host and service group management tools"""
    return [
        {
            "name": "vibemk_get_host_groups",
            "description": "🏠 List host groups - Show all host groups",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_create_host_group",
            "description": "➕ Create host group - Add new host group",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Group name"},
                    "alias": {"type": "string", "description": "Display alias"},
                },
                "required": ["name", "alias"],
            },
        },
        {
            "name": "vibemk_update_host_group",
            "description": "📝 Update host group - Modify host group properties",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Group name"},
                    "alias": {"type": "string", "description": "Display alias"},
                },
                "required": ["name"],
            },
        },
        {
            "name": "vibemk_delete_host_group",
            "description": "🗑️ Delete host group - Remove host group",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Group name to delete"}},
                "required": ["name"],
            },
        },
        {
            "name": "vibemk_get_service_groups",
            "description": "🔧 List service groups - Show all service groups",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_create_service_group",
            "description": "➕ Create service group - Add new service group",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Group name"},
                    "alias": {"type": "string", "description": "Display alias"},
                },
                "required": ["name", "alias"],
            },
        },
        {
            "name": "vibemk_update_service_group",
            "description": "📝 Update service group - Modify service group properties",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Group name"},
                    "alias": {"type": "string", "description": "Display alias"},
                },
                "required": ["name"],
            },
        },
        {
            "name": "vibemk_delete_service_group",
            "description": "🗑️ Delete service group - Remove service group",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Group name to delete"}},
                "required": ["name"],
            },
        },
    ]


def get_advanced_monitoring_tools() -> List[Dict[str, Any]]:
    """Advanced monitoring and alerting tools"""
    return [
        {
            "name": "vibemk_get_comments",
            "description": "💬 List comments - Show host/service comments",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Filter by host name"},
                    "service_description": {"type": "string", "description": "Filter by service"},
                },
            },
        },
        {
            "name": "vibemk_add_comment",
            "description": "💬 Add comment - Add comment to host or service",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "comment_type": {"type": "string", "description": "Type: host or service"},
                    "host_name": {"type": "string", "description": "Host name"},
                    "service_description": {"type": "string", "description": "Service (for service comments)"},
                    "comment": {"type": "string", "description": "Comment text"},
                    "persistent": {"type": "boolean", "description": "Persistent comment"},
                },
                "required": ["comment_type", "host_name", "comment"],
            },
        },
        {
            "name": "vibemk_get_downtimes",
            "description": "⏰ List downtimes - Show scheduled downtimes",
            "inputSchema": {
                "type": "object",
                "properties": {"host_name": {"type": "string", "description": "Filter by host name"}},
            },
        },
        {
            "name": "vibemk_delete_downtime",
            "description": "🗑️ Delete downtime - Remove scheduled downtime",
            "inputSchema": {
                "type": "object",
                "properties": {"downtime_id": {"type": "string", "description": "Downtime ID"}},
                "required": ["downtime_id"],
            },
        },
        {
            "name": "vibemk_reschedule_check",
            "description": "🔄 Reschedule check - Force immediate check execution",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "check_type": {"type": "string", "description": "Type: host or service"},
                    "host_name": {"type": "string", "description": "Host name"},
                    "service_description": {"type": "string", "description": "Service (for service checks)"},
                },
                "required": ["check_type", "host_name"],
            },
        },
    ]


def get_rule_management_tools() -> List[Dict[str, Any]]:
    """Rule and configuration management tools"""
    return [
        {
            "name": "vibemk_get_rulesets",
            "description": "📋 List rulesets - Show available rulesets",
            "inputSchema": {
                "type": "object",
                "properties": {"search": {"type": "string", "description": "Search term to filter rulesets"}},
            },
        },
        {
            "name": "vibemk_get_ruleset",
            "description": "📋 Get ruleset - Show specific ruleset configuration",
            "inputSchema": {
                "type": "object",
                "properties": {"ruleset_name": {"type": "string", "description": "Ruleset name"}},
                "required": ["ruleset_name"],
            },
        },
        {
            "name": "vibemk_create_rule",
            "description": "➕ Create rule - Add new monitoring rule",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ruleset_name": {"type": "string", "description": "Ruleset name"},
                    "rule_config": {"type": "object", "description": "Rule configuration"},
                    "conditions": {"type": "object", "description": "Rule conditions"},
                    "comment": {"type": "string", "description": "Rule comment"},
                    "folder": {"type": "string", "description": "Target folder", "default": "/"},
                    "position": {
                        "type": "string",
                        "description": "Rule position: top, bottom, before, after",
                        "default": "top",
                    },
                },
                "required": ["ruleset_name", "rule_config"],
            },
        },
        {
            "name": "vibemk_update_rule",
            "description": "📝 Update rule - Modify existing monitoring rule",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID"},
                    "rule_config": {"type": "object", "description": "Rule configuration"},
                    "conditions": {"type": "object", "description": "Rule conditions"},
                    "comment": {"type": "string", "description": "Rule comment"},
                    "disabled": {"type": "boolean", "description": "Disable rule"},
                },
                "required": ["rule_id"],
            },
        },
        {
            "name": "vibemk_delete_rule",
            "description": "🗑️ Delete rule - Remove monitoring rule",
            "inputSchema": {
                "type": "object",
                "properties": {"rule_id": {"type": "string", "description": "Rule ID to delete"}},
                "required": ["rule_id"],
            },
        },
        {
            "name": "vibemk_move_rule",
            "description": "🔄 Move rule - Change rule position in ruleset",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID"},
                    "position": {
                        "type": "string",
                        "description": "Position: top, bottom, before, after",
                        "default": "top",
                    },
                    "target_rule_id": {"type": "string", "description": "Target rule ID for before/after positioning"},
                },
                "required": ["rule_id"],
            },
        },
    ]


def get_ruleset_discovery_tools() -> List[Dict[str, Any]]:
    """Ruleset search and discovery tools"""
    return [
        {
            "name": "vibemk_search_rulesets",
            "description": "🔍 Search rulesets - Find rulesets with filters (text, folder, name)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "fulltext": {
                        "type": "string",
                        "description": "Search all keys (name, title, help) for this text. Regex allowed.",
                    },
                    "folder": {
                        "type": "string",
                        "description": "The folder in which to search for rules. Path delimiters can be ~, /, or \\",
                    },
                    "deprecated": {
                        "type": "boolean",
                        "description": "Only show deprecated rulesets",
                        "default": False,
                    },
                    "used": {
                        "type": "boolean",
                        "description": "Only show used rulesets",
                        "default": True,
                    },
                    "name": {
                        "type": "string",
                        "description": "A regex of the ruleset name",
                    },
                },
            },
        },
        {
            "name": "vibemk_show_ruleset",
            "description": "📋 Show ruleset details - Display detailed information about a specific ruleset",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ruleset_name": {
                        "type": "string",
                        "description": "The name of the ruleset (e.g., host_groups, host_contactgroups)",
                    }
                },
                "required": ["ruleset_name"],
            },
        },
        {
            "name": "vibemk_list_rulesets",
            "description": "📋 List all rulesets - Show all available rulesets with basic information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of rulesets to return",
                        "default": 50,
                    },
                    "show_deprecated": {
                        "type": "boolean",
                        "description": "Include deprecated rulesets in the list",
                        "default": False,
                    },
                },
            },
        },
    ]


def get_tag_management_tools() -> List[Dict[str, Any]]:
    """Host tag management tools"""
    return [
        {
            "name": "vibemk_get_host_tags",
            "description": "🏷️ List host tags - Show available host tag groups",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_create_host_tag",
            "description": "🏷️ Create host tag - Add new host tag group",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tag_id": {"type": "string", "description": "Tag group ID"},
                    "title": {"type": "string", "description": "Tag group title"},
                    "topic": {"type": "string", "description": "Tag topic/category"},
                    "tags": {"type": "array", "description": "List of tags with id and title"},
                    "help": {"type": "string", "description": "Help text"},
                },
                "required": ["tag_id", "title", "tags"],
            },
        },
        {
            "name": "vibemk_update_host_tag",
            "description": "📝 Update host tag - Modify host tag group",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tag_id": {"type": "string", "description": "Tag group ID"},
                    "title": {"type": "string", "description": "Tag group title"},
                    "topic": {"type": "string", "description": "Tag topic/category"},
                    "tags": {"type": "array", "description": "List of tags with id and title"},
                    "help": {"type": "string", "description": "Help text"},
                    "repair": {"type": "boolean", "description": "Repair host assignments", "default": False},
                },
                "required": ["tag_id"],
            },
        },
        {
            "name": "vibemk_delete_host_tag",
            "description": "🗑️ Delete host tag - Remove host tag group",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tag_id": {"type": "string", "description": "Tag group ID to delete"},
                    "repair": {"type": "boolean", "description": "Repair host assignments", "default": False},
                },
                "required": ["tag_id"],
            },
        },
    ]


def get_timeperiod_tools() -> List[Dict[str, Any]]:
    """Time period management tools"""
    return [
        {
            "name": "vibemk_get_timeperiods",
            "description": "⏰ List time periods - Show all configured time periods",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_create_timeperiod",
            "description": "⏰ Create time period - Add new time period",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Time period name"},
                    "alias": {"type": "string", "description": "Time period alias"},
                    "active_time_ranges": {"type": "array", "description": "Active time ranges"},
                    "exceptions": {"type": "array", "description": "Exception time ranges"},
                    "exclude": {"type": "array", "description": "Excluded time periods"},
                },
                "required": ["name", "active_time_ranges"],
            },
        },
        {
            "name": "vibemk_update_timeperiod",
            "description": "📝 Update time period - Modify time period configuration",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Time period name"},
                    "alias": {"type": "string", "description": "Time period alias"},
                    "active_time_ranges": {"type": "array", "description": "Active time ranges"},
                    "exceptions": {"type": "array", "description": "Exception time ranges"},
                    "exclude": {"type": "array", "description": "Excluded time periods"},
                },
                "required": ["name"],
            },
        },
        {
            "name": "vibemk_delete_timeperiod",
            "description": "🗑️ Delete time period - Remove time period",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Time period name to delete"}},
                "required": ["name"],
            },
        },
    ]


def get_password_tools() -> List[Dict[str, Any]]:
    """Password management tools"""
    return [
        {
            "name": "vibemk_get_passwords",
            "description": "🔐 List passwords - Show stored passwords",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_create_password",
            "description": "🔐 Create password - Store new password securely",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ident": {"type": "string", "description": "Password identifier"},
                    "title": {"type": "string", "description": "Password title"},
                    "password": {"type": "string", "description": "Password value"},
                    "comment": {"type": "string", "description": "Password description"},
                    "documentation_url": {"type": "string", "description": "Documentation URL"},
                    "owner": {"type": "string", "description": "Owner user/group", "default": "admin"},
                    "shared": {"type": "array", "description": "Shared with users/groups"},
                },
                "required": ["ident", "password"],
            },
        },
        {
            "name": "vibemk_update_password",
            "description": "📝 Update password - Modify stored password",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ident": {"type": "string", "description": "Password identifier"},
                    "title": {"type": "string", "description": "Password title"},
                    "password": {"type": "string", "description": "Password value"},
                    "comment": {"type": "string", "description": "Password description"},
                    "documentation_url": {"type": "string", "description": "Documentation URL"},
                    "owner": {"type": "string", "description": "Owner user/group"},
                    "shared": {"type": "array", "description": "Shared with users/groups"},
                },
                "required": ["ident"],
            },
        },
        {
            "name": "vibemk_delete_password",
            "description": "🗑️ Delete password - Remove stored password",
            "inputSchema": {
                "type": "object",
                "properties": {"ident": {"type": "string", "description": "Password identifier to delete"}},
                "required": ["ident"],
            },
        },
    ]


def get_notification_tools() -> List[Dict[str, Any]]:
    """Notification and alerting tools"""
    return [
        {
            "name": "vibemk_get_notification_rules",
            "description": "📢 List notification rules - Show notification configuration",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_test_notification",
            "description": "🧪 Test notification - Send test notification",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "contact": {"type": "string", "description": "Contact to notify"},
                    "message": {"type": "string", "description": "Test message"},
                },
                "required": ["contact"],
            },
        },
    ]


def get_metrics_tools() -> List[Dict[str, Any]]:
    """Metrics and performance tools for RRD data access"""
    return [
        {
            "name": "vibemk_get_host_metrics",
            "description": "📊 Get host metrics - Extract performance data from CheckMK RRD databases",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name"},
                    "metric_name": {"type": "string", "description": "Specific metric name (optional)"},
                    "time_range": {
                        "type": "string",
                        "description": "Time range: '1h', '4h', '24h', '7d', '30d'",
                        "default": "1h",
                    },
                    "reduce": {
                        "type": "string",
                        "description": "Aggregation function: 'max', 'min', 'average'",
                        "default": "max",
                    },
                },
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_get_service_metrics",
            "description": "📊 Get service metrics - Extract service performance data from CheckMK metrics API",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name"},
                    "service_description": {"type": "string", "description": "Service description"},
                    "metric_name": {
                        "type": "string",
                        "description": "Specific metric ID (e.g., 'if_in_bps', 'cpu_util')",
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range: '1h', '4h', '24h', '7d', '30d'",
                        "default": "1h",
                    },
                    "reduce": {
                        "type": "string",
                        "description": "Aggregation function: 'max', 'min', 'average'",
                        "default": "max",
                    },
                    "site": {"type": "string", "description": "CheckMK site name", "default": "cmk"},
                },
                "required": ["host_name", "service_description"],
            },
        },
        {
            "name": "vibemk_get_custom_graph",
            "description": "📊 Get custom graph - Retrieve predefined custom graph data",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "custom_graph_id": {"type": "string", "description": "Custom graph ID"},
                    "time_range": {
                        "type": "string",
                        "description": "Time range: '1h', '4h', '24h', '7d', '30d'",
                        "default": "1h",
                    },
                    "reduce": {"type": "string", "description": "Aggregation function", "default": "max"},
                },
                "required": ["custom_graph_id"],
            },
        },
        {
            "name": "vibemk_search_metrics",
            "description": "🔍 Search metrics - Filter and search performance data across hosts/services",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_filter": {"type": "string", "description": "Host filter pattern"},
                    "service_filter": {"type": "string", "description": "Service filter pattern (optional)"},
                    "site_filter": {"type": "string", "description": "Site filter (optional)"},
                    "time_range": {"type": "string", "description": "Time range", "default": "1h"},
                    "reduce": {"type": "string", "description": "Aggregation function", "default": "max"},
                },
                "required": ["host_filter"],
            },
        },
        {
            "name": "vibemk_list_available_metrics",
            "description": "📋 List available metrics - Show all available metrics for host or service",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name"},
                    "service_description": {
                        "type": "string",
                        "description": "Service description (optional for service metrics)",
                    },
                },
                "required": ["host_name"],
            },
        },
    ]


def get_debug_tools() -> List[Dict[str, Any]]:
    """Basic debug tools for API troubleshooting"""
    return [
        {
            "name": "vibemk_debug_api_endpoints",
            "description": "🔍 Debug API endpoints - Analyze available CheckMK API endpoints and their structure",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_debug_permissions",
            "description": "🔐 Debug permissions - Check automation user permissions for API access",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def get_host_group_rules_tools() -> List[Dict[str, Any]]:
    """Host grouping and contact assignment rule tools"""
    return [
        {
            "name": "vibemk_find_host_grouping_rulesets",
            "description": "🔍 Find host grouping rulesets - Discover available rulesets for host group and contact group assignment",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_create_host_contactgroup_rule",
            "description": "📞 Create host contact group rule - Assign contact groups to hosts based on conditions",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "contact_groups": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of contact group names to assign",
                    },
                    "host_conditions": {
                        "type": "object",
                        "description": "Conditions to match hosts (optional, empty = all hosts)",
                        "properties": {
                            "host_name": {"type": "object", "description": "Host name matching conditions"},
                            "host_tags": {"type": "object", "description": "Host tag conditions"},
                            "host_labels": {"type": "object", "description": "Host label conditions"},
                        },
                    },
                    "comment": {"type": "string", "description": "Rule comment"},
                    "folder": {"type": "string", "description": "Folder path", "default": "/"},
                },
                "required": ["contact_groups"],
            },
        },
        {
            "name": "vibemk_create_host_hostgroup_rule",
            "description": "🏠 Create host group rule - Assign hosts to host groups based on conditions",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_groups": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of host group names to assign",
                    },
                    "host_conditions": {
                        "type": "object",
                        "description": "Conditions to match hosts (optional, empty = all hosts)",
                        "properties": {
                            "host_name": {"type": "object", "description": "Host name matching conditions"},
                            "host_tags": {"type": "object", "description": "Host tag conditions"},
                            "host_labels": {"type": "object", "description": "Host label conditions"},
                        },
                    },
                    "comment": {"type": "string", "description": "Rule comment"},
                    "folder": {"type": "string", "description": "Folder path", "default": "/"},
                },
                "required": ["host_groups"],
            },
        },
        {
            "name": "vibemk_get_example_rule_structures",
            "description": "📚 Get example rule structures - Show example JSON structures for host grouping rules",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def get_downtime_tools() -> List[Dict[str, Any]]:
    """Downtime management tools"""
    return [
        {
            "name": "vibemk_schedule_host_downtime",
            "description": "🔧 Schedule host downtime - Schedule maintenance downtime for a host to suppress alerts",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name to schedule downtime for"},
                    "start_time": {
                        "type": "string",
                        "description": "Start time (ISO format, 'now', or relative like '+1h'). Default: now",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time (ISO format or relative like '+2h'). Optional if duration specified",
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Downtime duration in minutes. Default: 60",
                        "minimum": 1,
                    },
                    "comment": {
                        "type": "string",
                        "description": "Comment describing the reason for downtime. Default: 'Scheduled maintenance'",
                    },
                    "recur": {
                        "type": "string",
                        "description": "Optional recurring pattern: 'hour', 'day', 'week', 'month'",
                        "enum": ["hour", "day", "week", "month"],
                    },
                },
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_schedule_service_downtime",
            "description": "🔧 Schedule service downtime - Schedule maintenance downtime for specific services",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name where services are located"},
                    "service_descriptions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of service descriptions to schedule downtime for",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time (ISO format, 'now', or relative like '+1h'). Default: now",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time (ISO format or relative like '+2h'). Optional if duration specified",
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Downtime duration in minutes. Default: 60",
                        "minimum": 1,
                    },
                    "comment": {
                        "type": "string",
                        "description": "Comment describing the reason for downtime. Default: 'Scheduled service maintenance'",
                    },
                    "recur": {
                        "type": "string",
                        "description": "Optional recurring pattern: 'hour', 'day', 'week', 'month'",
                        "enum": ["hour", "day", "week", "month"],
                    },
                },
                "required": ["host_name", "service_descriptions"],
            },
        },
        {
            "name": "vibemk_list_downtimes",
            "description": "📋 List downtimes - Show all scheduled downtimes with filtering options",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {
                        "type": "string",
                        "description": "Optional: Filter downtimes for specific host",
                    },
                    "service_description": {
                        "type": "string",
                        "description": "Optional: Filter downtimes for specific service",
                    },
                    "active_only": {
                        "type": "boolean",
                        "description": "Show only active downtimes (default: true)",
                    },
                },
            },
        },
        {
            "name": "vibemk_get_active_downtimes",
            "description": "🔴 Get active downtimes - Show only currently active downtimes that are suppressing alerts",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {
                        "type": "string",
                        "description": "Optional: Filter active downtimes for specific host",
                    }
                },
            },
        },
        {
            "name": "vibemk_delete_downtime",
            "description": "🗑️ Delete downtime - Cancel a scheduled or active downtime by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "downtime_id": {
                        "type": "integer",
                        "description": "Downtime ID to delete (get from list_downtimes)",
                    }
                },
                "required": ["downtime_id"],
            },
        },
    ]


def get_discovery_tools() -> List[Dict[str, Any]]:
    """Host discovery and service detection tools"""
    return [
        {
            "name": "vibemk_start_service_discovery",
            "description": "🔍 Start service discovery - Automatically detect services on a host",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name to discover services on"},
                    "mode": {
                        "type": "string",
                        "description": "Discovery mode: 'new', 'remove', 'fix_all', 'refresh', 'only_host_labels'",
                        "default": "refresh",
                        "enum": ["new", "remove", "fix_all", "refresh", "only_host_labels"],
                    },
                },
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_start_bulk_discovery",
            "description": "🔍 Start bulk discovery - Discover services on multiple hosts simultaneously",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostnames": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of host names to discover services on",
                    },
                    "options": {
                        "type": "object",
                        "description": "Discovery options",
                        "properties": {
                            "monitor_undecided_services": {"type": "boolean", "default": True},
                            "remove_vanished_services": {"type": "boolean", "default": True},
                            "update_service_labels": {"type": "boolean", "default": True},
                            "update_host_labels": {"type": "boolean", "default": True},
                        },
                    },
                    "do_full_scan": {"type": "boolean", "description": "Perform full service scan", "default": True},
                    "bulk_size": {
                        "type": "integer",
                        "description": "Number of hosts to process simultaneously",
                        "default": 10,
                    },
                    "ignore_errors": {"type": "boolean", "description": "Continue on errors", "default": True},
                },
                "required": ["hostnames"],
            },
        },
        {
            "name": "vibemk_get_discovery_status",
            "description": "📊 Get discovery status - Show current service discovery results for a host",
            "inputSchema": {
                "type": "object",
                "properties": {"host_name": {"type": "string", "description": "Host name to check discovery status"}},
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_get_bulk_discovery_status",
            "description": "📊 Get bulk discovery status - Show progress of a bulk discovery job",
            "inputSchema": {
                "type": "object",
                "properties": {"job_id": {"type": "string", "description": "Bulk discovery job ID"}},
                "required": ["job_id"],
            },
        },
        {
            "name": "vibemk_wait_for_discovery",
            "description": "⏳ Wait for discovery completion - Wait until service discovery finishes on a host",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name to wait for discovery completion"}
                },
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_get_discovery_background_job",
            "description": "📋 Get discovery background job - Show last discovery job status on a host",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name to check background job status"}
                },
                "required": ["host_name"],
            },
        },
    ]


def get_service_group_tools() -> List[Dict[str, Any]]:
    """Service group management tools"""
    return [
        {
            "name": "vibemk_create_service_group",
            "description": "🔧 Create service group - Create a new service group for organizing services",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Service group name (letters, numbers, hyphens, underscores only)",
                    },
                    "alias": {
                        "type": "string",
                        "description": "Human-readable description/alias for the service group",
                    },
                },
                "required": ["name", "alias"],
            },
        },
        {
            "name": "vibemk_list_service_groups",
            "description": "📋 List service groups - Show all configured service groups",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_get_service_group",
            "description": "🔍 Get service group details - Show detailed information about a specific service group",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Service group name to retrieve",
                    }
                },
                "required": ["name"],
            },
        },
        {
            "name": "vibemk_update_service_group",
            "description": "📝 Update service group - Modify an existing service group's alias",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Service group name to update",
                    },
                    "alias": {
                        "type": "string",
                        "description": "New alias/description for the service group",
                    },
                },
                "required": ["name", "alias"],
            },
        },
        {
            "name": "vibemk_delete_service_group",
            "description": "🗑️ Delete service group - Remove a service group from CheckMK",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Service group name to delete",
                    }
                },
                "required": ["name"],
            },
        },
        {
            "name": "vibemk_bulk_create_service_groups",
            "description": "🔧 Bulk create service groups - Create multiple service groups at once",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entries": {
                        "type": "array",
                        "description": "List of service groups to create",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Service group name"},
                                "alias": {"type": "string", "description": "Service group alias"},
                            },
                            "required": ["name", "alias"],
                        },
                    }
                },
                "required": ["entries"],
            },
        },
        {
            "name": "vibemk_bulk_update_service_groups",
            "description": "📝 Bulk update service groups - Update multiple service groups at once",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entries": {
                        "type": "array",
                        "description": "List of service groups to update",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Service group name"},
                                "attributes": {
                                    "type": "object",
                                    "properties": {
                                        "alias": {"type": "string", "description": "New alias for the service group"}
                                    },
                                    "required": ["alias"],
                                },
                            },
                            "required": ["name", "attributes"],
                        },
                    }
                },
                "required": ["entries"],
            },
        },
        {
            "name": "vibemk_bulk_delete_service_groups",
            "description": "🗑️ Bulk delete service groups - Delete multiple service groups at once",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entries": {
                        "type": "array",
                        "description": "List of service group names to delete",
                        "items": {"type": "string"},
                    }
                },
                "required": ["entries"],
            },
        },
    ]


def get_all_tools() -> List[Dict[str, Any]]:
    """Get all available tools"""
    tools = []
    tools.extend(get_connection_tools())
    tools.extend(get_host_tools())
    tools.extend(get_service_tools())
    tools.extend(get_monitoring_tools())
    tools.extend(get_configuration_tools())
    tools.extend(get_folder_tools())
    tools.extend(get_user_management_tools())
    tools.extend(get_user_roles_tools())
    tools.extend(get_group_management_tools())
    tools.extend(get_advanced_monitoring_tools())
    tools.extend(get_rule_management_tools())
    tools.extend(get_tag_management_tools())
    tools.extend(get_timeperiod_tools())
    tools.extend(get_password_tools())
    tools.extend(get_notification_tools())
    tools.extend(get_metrics_tools())
    tools.extend(get_debug_tools())
    tools.extend(get_host_group_rules_tools())
    tools.extend(get_downtime_tools())
    tools.extend(get_discovery_tools())
    tools.extend(get_service_group_tools())
    tools.extend(get_ruleset_discovery_tools())
    return tools
