"""
vibeMK Tool definitions for CheckMK operations
"""

from typing import Any, Dict, List

from vibemk_mcp.annotations import annotations_for, title_for
from vibemk_mcp.schemas import output_schema_for


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
            "description": (
                "🧪 Test direct URL - Send a GET to a URL under the configured CheckMK API and show the raw "
                "response. URLs on other hosts or outside the API path are refused."
            ),
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
            "description": "➕ Create host(s) - Add one or multiple hosts to monitoring (automatically uses bulk API for multiple hosts)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Name of the new host (single host mode)"},
                    "folder": {"type": "string", "description": "Folder path (single host mode)"},
                    "attributes": {
                        "type": "object",
                        "description": "Host attributes - ipaddress, etc. (single host mode)",
                    },
                    "hosts": {
                        "type": "array",
                        "description": "List of hosts to create (multiple hosts mode - automatically uses bulk API)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "host_name": {"type": "string", "description": "Name of the new host"},
                                "folder": {"type": "string", "description": "Folder path"},
                                "attributes": {
                                    "type": "object",
                                    "description": "Host attributes (ipaddress, alias, etc.)",
                                },
                            },
                            "required": ["host_name", "folder", "attributes"],
                        },
                        "minItems": 1,
                    },
                    "bake_agent": {
                        "type": "boolean",
                        "description": "Whether to bake agents after creation (bulk mode only)",
                        "default": False,
                    },
                },
                "oneOf": [
                    {
                        "description": "Single host mode",
                        "required": ["host_name", "folder", "attributes"],
                        "not": {"required": ["hosts"]},
                    },
                    {
                        "description": "Multiple hosts mode (uses bulk API automatically)",
                        "required": ["hosts"],
                        "not": {
                            "anyOf": [
                                {"required": ["host_name"]},
                                {"required": ["folder"]},
                                {"required": ["attributes"]},
                            ]
                        },
                    },
                ],
            },
        },
        {
            "name": "vibemk_bulk_create_hosts",
            "description": "➕ Bulk create hosts - Create multiple hosts in a single operation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entries": {
                        "type": "array",
                        "description": "List of hosts to create",
                        "items": {
                            "type": "object",
                            "properties": {
                                "host_name": {"type": "string", "description": "Name of the new host"},
                                "folder": {"type": "string", "description": "Folder path where host will be created"},
                                "attributes": {
                                    "type": "object",
                                    "description": "Host attributes (ipaddress, alias, site, tags, etc.)",
                                },
                            },
                            "required": ["host_name", "folder", "attributes"],
                        },
                        "minItems": 1,
                    },
                    "bake_agent": {
                        "type": "boolean",
                        "description": "Whether to bake agents after creation (CheckMK Enterprise Edition only)",
                        "default": False,
                    },
                },
                "required": ["entries"],
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
            "name": "vibemk_rename_host",
            "description": "✏️ Rename host - Rename a host in CheckMK (starts a background job)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Current host name"},
                    "new_name": {"type": "string", "description": "New host name (FQDN)"},
                },
                "required": ["host_name", "new_name"],
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
                    "sticky": {
                        "type": "boolean",
                        "default": True,
                        "description": "Hold the acknowledgement until the object returns to UP/OK",
                    },
                    "notify": {
                        "type": "boolean",
                        "default": True,
                        "description": "Send notifications to the configured contacts",
                    },
                    "persistent": {
                        "type": "boolean",
                        "default": False,
                        "description": "Keep the comment after the acknowledgement is removed",
                    },
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
            "description": (
                "🔄 Activate changes - Deploy pending configuration changes. INTERNAL: vibeMK reads the ETag from pending_changes itself, so there is no manual ETag handling to do. After activating, wait for the next check cycle before results become visible."
            ),
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
            "name": "vibemk_delete_comment",
            "description": "🗑️ Delete comment - Remove a host or service comment by ID or query",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "delete_type": {
                        "type": "string",
                        "description": "Deletion mode: 'by_id' (requires comment_id) or 'by_query' (requires host_name)",
                        "default": "by_id",
                    },
                    "comment_id": {"type": "integer", "description": "Comment ID (for delete_type=by_id)"},
                    "host_name": {"type": "string", "description": "Host name (for delete_type=by_query)"},
                    "service_description": {
                        "type": "string",
                        "description": "Service description (optional, for delete_type=by_query)",
                    },
                    "site_id": {"type": "string", "description": "Site ID (defaults to configured site)"},
                },
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
            "description": (
                "📋 List the rules of a ruleset, optionally filtered by host name. Shows the rule IDs vibemk_delete_rule needs."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ruleset_name": {
                        "type": "string",
                        "description": "Ruleset name, e.g. 'active_checks:http' or 'host_label_rules'",
                    },
                    "hostname": {
                        "type": "string",
                        "description": "Show only rules for this host (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of rules to return (default: 50)",
                    },
                },
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
                        "enum": ["top_of_folder", "bottom_of_folder", "before_specific_rule", "after_specific_rule"],
                        "description": (
                            "Where to place the new rule. Omit to leave placement to CheckMK. "
                            "The two *_specific_rule values need target_rule_id."
                        ),
                    },
                    "target_rule_id": {
                        "type": "string",
                        "description": "Rule to position relative to, for before_specific_rule/after_specific_rule",
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
                        "enum": ["top_of_folder", "bottom_of_folder", "before_specific_rule", "after_specific_rule"],
                        "description": "Where to move the rule. The two *_specific_rule values need target_rule_id.",
                        "default": "top_of_folder",
                    },
                    "target_rule_id": {
                        "type": "string",
                        "description": "Rule to position relative to, for before_specific_rule/after_specific_rule",
                    },
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
    """Notification rule tools

    rule_config mirrors CheckMK's NotificationRuleRequest, which is deeply
    nested and marks nearly every field required. Fetching an existing rule
    and adapting it is far more reliable than composing one from scratch.
    """
    return [
        {
            "name": "vibemk_get_notification_rules",
            "description": "📢 List notification rules - Show all configured notification rules with their IDs",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_get_notification_rule",
            "description": (
                "🔍 Show notification rule - Return one rule including its full rule_config. "
                "Use this first to obtain a template before creating or updating a rule."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID from get_notification_rules"},
                },
                "required": ["rule_id"],
            },
        },
        {
            "name": "vibemk_create_notification_rule",
            "description": (
                "➕ Create notification rule - CheckMK requires the complete rule_config structure "
                "(properties, contact selection, conditions and notification_method), and nearly every "
                "field is mandatory. Read an existing rule with vibemk_get_notification_rule and adapt "
                "its rule_config rather than composing one from scratch. Activate changes afterwards."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_config": {
                        "type": "object",
                        "description": "Complete rule configuration as returned by vibemk_get_notification_rule",
                    },
                },
                "required": ["rule_config"],
            },
        },
        {
            "name": "vibemk_update_notification_rule",
            "description": (
                "✏️ Update notification rule - Replaces the rule's configuration. Send the complete "
                "rule_config, not just the fields you want changed; read the current one first. "
                "Activate changes afterwards."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID from get_notification_rules"},
                    "rule_config": {
                        "type": "object",
                        "description": "Complete replacement configuration",
                    },
                },
                "required": ["rule_id", "rule_config"],
            },
        },
        {
            "name": "vibemk_delete_notification_rule",
            "description": "🗑️ Delete notification rule - Remove a notification rule by ID. Activate changes afterwards.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID from get_notification_rules"},
                },
                "required": ["rule_id"],
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
            "description": "📊 Get custom graph - Retrieve predefined custom graph data Enterprise/Cloud only: a Raw site does not serve this endpoint and answers 404.",
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
            "description": (
                "🔍 Search metrics - Read one predefined graph (graph_id) or one metric (metric_id) "
                "across the hosts and services a filter matches. Exactly one of the two IDs is "
                "required; both are shown in the service view once 'Show internal IDs' is enabled "
                "in its display options. Enterprise/Cloud only: a Raw site does not serve this "
                "endpoint and answers 404."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_filter": {"type": "string", "description": "Host filter pattern"},
                    "service_filter": {"type": "string", "description": "Service filter pattern (optional)"},
                    "site_filter": {"type": "string", "description": "Site filter (optional)"},
                    "graph_id": {
                        "type": "string",
                        "description": "ID of a predefined graph, e.g. cmk_cpu_time_by_phase. Exclusive with metric_id",
                    },
                    "metric_id": {
                        "type": "string",
                        "description": "ID of a single metric, e.g. cmk_time_agent. Exclusive with graph_id",
                    },
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
                        "description": "Start time - supports natural language: '22:00 today', 'tomorrow at 14:00', 'monday at 09:00', '2024-08-23 at 22:00', 'in 2 hours', 'now', or ISO format. Default: now",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time - supports natural language: '23:30 today', 'tomorrow at 16:00', 'monday at 17:00', or relative like '+2h'. Optional if duration specified",
                    },
                    "duration": {
                        "type": ["integer", "string"],
                        "description": "Downtime duration - supports natural language: '2h', '1h30m', '90m' or minutes as integer. Default: 60",
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
                        "description": "Start time - supports natural language: '22:00 today', 'tomorrow at 14:00', 'monday at 09:00', '2024-08-23 at 22:00', 'in 2 hours', 'now', or ISO format. Default: now",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time - supports natural language: '23:30 today', 'tomorrow at 16:00', 'monday at 17:00', or relative like '+2h'. Optional if duration specified",
                    },
                    "duration": {
                        "type": ["integer", "string"],
                        "description": "Downtime duration - supports natural language: '2h', '1h30m', '90m' or minutes as integer. Default: 60",
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
        {
            "name": "vibemk_check_host_downtime_status",
            "description": "🔍 Check host downtime status - Distinguish between host-level and service-level downtimes",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {
                        "type": "string",
                        "description": "Host name to check downtime status for",
                    }
                },
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_modify_downtime",
            "description": "✏️ Modify downtime - Extend or shorten an active downtime's end time",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "downtime_id": {
                        "type": "integer",
                        "description": "Downtime ID to modify (use vibemk_list_downtimes to find it)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "New end time in ISO 8601 format, e.g. '2026-06-09T18:00:00Z'",
                    },
                    "comment": {"type": "string", "description": "New comment (optional)"},
                    "host_name": {
                        "type": "string",
                        "description": "Host name for query-based modification (alternative to downtime_id)",
                    },
                    "service_description": {
                        "type": "string",
                        "description": "Service description (optional, narrows query-based modification)",
                    },
                },
                "required": ["end_time"],
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
                        "description": (
                            "Discovery mode. 'tabula_rasa' removes every service and rediscovers, "
                            "so it is the destructive one."
                        ),
                        "default": "refresh",
                        "enum": [
                            "new",
                            "remove",
                            "fix_all",
                            "refresh",
                            "tabula_rasa",
                            "only_host_labels",
                            "only_service_labels",
                        ],
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


def get_active_check_tools() -> List[Dict[str, Any]]:
    """Active check creation tools (HTTP, TCP, ICMP, custom)"""
    return [
        {
            "name": "vibemk_create_http_check",
            "description": (
                "🌐 Create an HTTP/HTTPS check for a host (active_checks:http). Supports URL mode (content check, auth, timing) and certificate mode."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Host the rule applies to (Checkmk host name)",
                    },
                    "name": {
                        "type": "string",
                        "description": "Service name in the monitoring, e.g. 'HTTP Main' or 'API Health'",
                    },
                    "uri": {
                        "type": "string",
                        "description": "URL path, or a full URL (default: '/')",
                    },
                    "port": {"type": "integer", "description": "HTTP port (default: 80, or 443 with SSL)"},
                    "ssl": {"type": "boolean", "description": "Use HTTPS/SSL (default: false)"},
                    "virt_host": {
                        "type": "string",
                        "description": "Virtual host header, when it differs from the host name",
                    },
                    "direct_address": {
                        "type": "string",
                        "description": "Address to contact instead of the host name (optional)",
                    },
                    "proxy_address": {
                        "type": "string",
                        "description": "HTTP proxy address (optional, e.g. 'proxy.internal')",
                    },
                    "proxy_port": {
                        "type": "integer",
                        "description": "HTTP proxy port (default: 80)",
                    },
                    "address_family": {
                        "type": "string",
                        "description": "IP version: 'ipv4' or 'ipv6' (optional)",
                    },
                    "expect_string": {
                        "type": "string",
                        "description": "Literal string the response body must contain, e.g. 'ok' or 'healthy'",
                    },
                    "expect_regex": {
                        "type": "string",
                        "description": 'Regular expression the response body must match, e.g. \'"status":\\s*"ok"\'',
                    },
                    "expect_response": {
                        "type": "string",
                        "description": "Expected HTTP status line, e.g. 'HTTP/1.1 200' or 'HTTP/1.1 404'",
                    },
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET, POST, HEAD, PUT, DELETE, OPTIONS, CONNECT (default: GET)",
                    },
                    "no_body": {
                        "type": "boolean",
                        "description": "Fetch headers only, not the body (default: false)",
                    },
                    "onredirect": {
                        "type": "string",
                        "description": "Redirect handling: 'ok', 'warning', 'critical', 'follow', 'sticky', 'stickyport'",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (optional)",
                    },
                    "response_time_warn": {
                        "type": "number",
                        "description": "Response time WARN threshold in seconds, e.g. 2.0",
                    },
                    "response_time_crit": {
                        "type": "number",
                        "description": "Response time CRIT threshold in seconds, e.g. 5.0",
                    },
                    "extended_perfdata": {
                        "type": "boolean",
                        "description": "Collect extended performance data such as body and header size (default: false)",
                    },
                    "auth_user": {
                        "type": "string",
                        "description": "HTTP basic auth user name (optional)",
                    },
                    "auth_password": {
                        "type": "string",
                        "description": "HTTP basic auth password (optional)",
                    },
                    "cert_mode": {
                        "type": "boolean",
                        "description": "Check certificate expiry instead of the URL (default: false)",
                    },
                    "cert_days_warn": {
                        "type": "integer",
                        "description": "WARN this many days before the certificate expires (default: 14, cert_mode only)",
                    },
                    "cert_days_crit": {
                        "type": "integer",
                        "description": "CRIT this many days before the certificate expires (default: 7, cert_mode only)",
                    },
                    "folder": {
                        "type": "string",
                        "description": "Checkmk folder (optional, defaults to the host's own folder)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname"],
            },
        },
        {
            "name": "vibemk_create_tcp_check",
            "description": (
                "🔌 Create a TCP port check for a host. Tests reachability, optionally the response content, and the SSL certificate."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Hostname"},
                    "port": {"type": "integer", "description": "TCP port, e.g. 8080"},
                    "name": {"type": "string", "description": "Optional service name"},
                    "ssl": {
                        "type": "boolean",
                        "description": "Use SSL/TLS (default: false)",
                    },
                    "cert_days_warn": {
                        "type": "integer",
                        "description": "WARN this many days before the certificate expires (ssl=true only)",
                    },
                    "cert_days_crit": {
                        "type": "integer",
                        "description": "CRIT this many days before the certificate expires (ssl=true only)",
                    },
                    "expect": {
                        "type": "string",
                        "description": "String expected in the TCP response, e.g. 'SSH-2.0' or 'Connection refused'",
                    },
                    "refuse_state": {
                        "type": "string",
                        "description": "State when the port refuses the connection: 'ok', 'warn', 'crit' (default: 'crit')",
                    },
                    "mismatch_state": {
                        "type": "string",
                        "description": "State when the expected string does not match: 'ok', 'warn', 'crit'",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (optional)",
                    },
                    "response_time_warn": {
                        "type": "number",
                        "description": "Response time WARN threshold in seconds",
                    },
                    "response_time_crit": {
                        "type": "number",
                        "description": "Response time CRIT threshold in seconds",
                    },
                    "folder": {"type": "string", "description": "Checkmk folder (optional)"},
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname", "port"],
            },
        },
        {
            "name": "vibemk_create_icmp_check",
            "description": (
                "🏓 Create an ICMP/PING check for a host. Measures reachability, packet loss and round-trip time."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Hostname"},
                    "name": {"type": "string", "description": "Service name (default: 'PING')"},
                    "packets": {"type": "integer", "description": "Number of packets (default: 5)"},
                    "timeout": {"type": "number", "description": "Timeout in seconds (default: 20)"},
                    "explicit_address": {
                        "type": "string",
                        "description": "Ping this address instead of the host name (optional)",
                    },
                    "rta_warn_ms": {
                        "type": "number",
                        "description": "Round-trip time WARN threshold in milliseconds, e.g. 200",
                    },
                    "rta_crit_ms": {
                        "type": "number",
                        "description": "Round-trip time CRIT threshold in milliseconds, e.g. 500",
                    },
                    "loss_warn_percent": {
                        "type": "number",
                        "description": "Packet loss WARN threshold in percent, e.g. 20",
                    },
                    "loss_crit_percent": {
                        "type": "number",
                        "description": "Packet loss CRIT threshold in percent, e.g. 100",
                    },
                    "min_pings": {
                        "type": "integer",
                        "description": "Minimum number of replies for the result to count (optional)",
                    },
                    "folder": {"type": "string", "description": "Checkmk folder (optional)"},
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname"],
            },
        },
        {
            "name": "vibemk_create_custom_check",
            "description": ("🔧 Create a custom Nagios plugin check for a host. Runs any Nagios-compatible plugin."),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Hostname"},
                    "service_description": {"type": "string", "description": "Service name in the monitoring"},
                    "command_line": {
                        "type": "string",
                        "description": "Plugin command line, e.g. '$USER1$/check_smtp -H $HOSTNAME$ -t 5'",
                    },
                    "command_name": {
                        "type": "string",
                        "description": "Optional internal name for the command",
                    },
                    "folder": {"type": "string", "description": "Checkmk folder (default: '~')"},
                    "description": {
                        "type": "string",
                        "description": "Rule description, shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname", "service_description", "command_line"],
            },
        },
        {
            "name": "vibemk_create_dns_check",
            "description": (
                "🔎 Create a DNS check for a host. Tests whether a name resolves and whether the answer arrives in time."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Host the rule applies to"},
                    "lookup_hostname": {
                        "type": "string",
                        "description": "Name to resolve (defaults to hostname)",
                    },
                    "dns_server": {
                        "type": "string",
                        "description": "DNS server IP (optional, defaults to the system resolver)",
                    },
                    "expected_addresses": {
                        "type": "string",
                        "description": "Expected IP address or addresses, one or a comma-separated list (optional)",
                    },
                    "expect_all_addresses": {
                        "type": "boolean",
                        "description": "Require every expected_addresses entry to be returned (default: false)",
                    },
                    "response_time_warn": {
                        "type": "number",
                        "description": "WARN threshold in seconds (default: 0.2)",
                    },
                    "response_time_crit": {
                        "type": "number",
                        "description": "CRIT threshold in seconds (default: 0.3)",
                    },
                    "folder": {"type": "string", "description": "Checkmk folder (optional)"},
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname"],
            },
        },
        {
            "name": "vibemk_create_smtp_check",
            "description": (
                "📧 Create an SMTP check for a host. Tests the SMTP service, optionally STARTTLS and certificate expiry."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Hostname"},
                    "name": {"type": "string", "description": "Service name (default: 'SMTP')"},
                    "starttls": {
                        "type": "boolean",
                        "description": "Use STARTTLS and check the certificate (default: false)",
                    },
                    "check_cert": {
                        "type": "boolean",
                        "description": "Check the certificate only, without STARTTLS (default: false)",
                    },
                    "cert_days_warn": {
                        "type": "integer",
                        "description": "WARN this many days before the certificate expires (default: 14, with starttls or check_cert)",
                    },
                    "cert_days_crit": {
                        "type": "integer",
                        "description": "CRIT this many days before the certificate expires (default: 7, with starttls or check_cert)",
                    },
                    "folder": {"type": "string", "description": "Checkmk folder (optional)"},
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname"],
            },
        },
        {
            "name": "vibemk_create_ftp_check",
            "description": "📁 Create an FTP check for a host. Tests whether an FTP port is reachable.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Hostname"},
                    "port": {"type": "integer", "description": "FTP port (default: 21)"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (optional)"},
                    "passive": {
                        "type": "boolean",
                        "description": "Passive FTP mode (optional)",
                    },
                    "refuse_state": {
                        "type": "string",
                        "description": "State when the connection is refused: 'crit', 'warn', 'ok' (default: 'crit')",
                    },
                    "folder": {"type": "string", "description": "Checkmk folder (optional)"},
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname"],
            },
        },
        {
            "name": "vibemk_create_ldap_check",
            "description": ("🗂️ Create an LDAP check for a host. Tests the LDAP service and its response time."),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Hostname"},
                    "name": {"type": "string", "description": "Service name (default: 'LDAP')"},
                    "base_dn": {
                        "type": "string",
                        "description": "LDAP base DN, e.g. 'DC=example,DC=com'",
                    },
                    "bind_dn": {
                        "type": "string",
                        "description": "Bind DN for authentication (optional)",
                    },
                    "password": {"type": "string", "description": "LDAP password (optional)"},
                    "port": {"type": "integer", "description": "LDAP port (optional, default: 389)"},
                    "attribute": {
                        "type": "string",
                        "description": "LDAP attribute or filter string (optional, e.g. '(objectclass=*)')",
                    },
                    "response_time_warn_ms": {
                        "type": "number",
                        "description": "Response time WARN threshold in milliseconds (default: 500)",
                    },
                    "response_time_crit_ms": {
                        "type": "number",
                        "description": "Response time CRIT threshold in milliseconds (default: 800)",
                    },
                    "folder": {"type": "string", "description": "Checkmk folder (optional)"},
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname", "base_dn"],
            },
        },
        {
            "name": "vibemk_create_smb_check",
            "description": (
                "🖥️ Create an SMB/CIFS share check for a host. Tests availability and used space of a Windows network share."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Hostname"},
                    "share": {
                        "type": "string",
                        "description": "Share name without backslashes, e.g. 'public'",
                    },
                    "smb_host": {
                        "type": "string",
                        "description": "SMB host IP or name (default: 'use_parent_host')",
                    },
                    "warn_percent": {
                        "type": "number",
                        "description": "Used space WARN threshold in percent (default: 85)",
                    },
                    "crit_percent": {
                        "type": "number",
                        "description": "Used space CRIT threshold in percent (default: 95)",
                    },
                    "username": {"type": "string", "description": "SMB user name (optional)"},
                    "password": {"type": "string", "description": "SMB password (optional)"},
                    "workgroup": {"type": "string", "description": "Workgroup or domain (optional)"},
                    "folder": {"type": "string", "description": "Checkmk folder (optional)"},
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname", "share"],
            },
        },
        {
            "name": "vibemk_create_mkevents_check",
            "description": (
                "📋 Create an Event Console check for a host. Reports whether the Checkmk Event Console holds open events for it."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Hostname"},
                    "ignore_acknowledged": {
                        "type": "boolean",
                        "description": "Ignore acknowledged events (default: true)",
                    },
                    "show_last_log": {
                        "type": "string",
                        "description": "'none', 'summary' or 'long' (default: 'summary')",
                    },
                    "remote_ec_host": {
                        "type": "string",
                        "description": "IP or host of an external Event Console (optional)",
                    },
                    "folder": {"type": "string", "description": "Checkmk folder (optional)"},
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname"],
            },
        },
        {
            "name": "vibemk_create_inventory_check",
            "description": (
                "🔬 Create a HW/SW inventory check for a host. Triggers hardware and software inventory and reports changes since the last scan."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Hostname"},
                    "sw_changes_state": {
                        "type": "integer",
                        "description": "State on software changes: 0=OK, 1=WARN, 2=CRIT (default: 0)",
                    },
                    "sw_missing_state": {
                        "type": "integer",
                        "description": "State when software data is missing: 0=OK, 1=WARN, 2=CRIT (default: 0)",
                    },
                    "hw_changes_state": {
                        "type": "integer",
                        "description": "State on hardware changes: 0=OK, 1=WARN, 2=CRIT (default: 0)",
                    },
                    "fail_status": {
                        "type": "integer",
                        "description": "State when the inventory fails: 0=OK, 1=WARN, 2=CRIT (default: 0)",
                    },
                    "status_data_inventory": {
                        "type": "boolean",
                        "description": "Enable status data inventory (default: true)",
                    },
                    "folder": {"type": "string", "description": "Checkmk folder (optional)"},
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname"],
            },
        },
        {
            "name": "vibemk_list_active_checks",
            "description": ("🔍 List active check rules, optionally filtered by host or check type."),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Show only rules for this host name (optional)",
                    },
                    "check_type": {
                        "type": "string",
                        "description": "Type: 'http', 'tcp', 'icmp', 'dns', 'smtp', 'custom' (optional, all types when empty)",
                    },
                },
            },
        },
        {
            "name": "vibemk_delete_active_check",
            "description": (
                "🗑️ Delete an active check rule, either by rule_id (UUID) or by hostname plus an optional service_name, which finds and deletes the matching rules."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_id": {
                        "type": "string",
                        "description": "Rule ID (UUID) — deletes that rule directly",
                    },
                    "hostname": {
                        "type": "string",
                        "description": "Host name; finds every active check rule for this host",
                    },
                    "service_name": {
                        "type": "string",
                        "description": "Optional service name filter, e.g. 'HTTP' or 'HTTPS'",
                    },
                    "check_type": {
                        "type": "string",
                        "description": "Check type filter: 'http', 'tcp', 'icmp', 'custom' (optional)",
                    },
                },
            },
        },
    ]


def get_event_console_tools() -> List[Dict[str, Any]]:
    """Event Console tools"""
    return [
        {
            "name": "vibemk_get_events",
            "description": (
                "🗃️ Retrieve Event Console events. Shows open and acknowledged events, optionally filtered by host, state and phase."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "phase": {
                        "type": "string",
                        "description": "Phase: 'open' (default) or 'ack' (acknowledged)",
                    },
                    "state": {
                        "type": "string",
                        "description": "State filter: 'ok', 'warning', 'critical', 'unknown'",
                    },
                    "host": {"type": "string", "description": "Host name filter"},
                    "application": {"type": "string", "description": "Application filter"},
                    "site_id": {"type": "string", "description": "Site ID, e.g. 'im' or 'uel'"},
                },
            },
        },
        {
            "name": "vibemk_acknowledge_event",
            "description": "✅ Acknowledge an Event Console event.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID"},
                    "comment": {"type": "string", "description": "Comment recorded with the acknowledgement"},
                },
                "required": ["event_id"],
            },
        },
        {
            "name": "vibemk_change_event_state",
            "description": "🔄 Change the state of an Event Console event.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID"},
                    "new_state": {
                        "type": "string",
                        "description": "New state: 'ok', 'warning', 'critical', 'unknown'",
                    },
                },
                "required": ["event_id", "new_state"],
            },
        },
        {
            "name": "vibemk_delete_events",
            "description": (
                "🗑️ Delete Event Console events, either by a list of IDs or every event of one phase or host."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "event_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of event IDs; when empty, phase and host are used as the filter",
                    },
                    "phase": {"type": "string", "description": "Phase filter: 'open', 'ack' (default: 'open')"},
                    "host": {"type": "string", "description": "Delete only the events of this host"},
                },
            },
        },
    ]


def get_aux_tag_tools() -> List[Dict[str, Any]]:
    """Auxiliary tag CRUD tools"""
    return [
        {
            "name": "vibemk_get_aux_tags",
            "description": "🏷️ List every configured auxiliary tag.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_create_aux_tag",
            "description": "🏷️ Create a new auxiliary tag.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tag_id": {"type": "string", "description": "Unique tag ID, e.g. 'sys-linux'"},
                    "title": {"type": "string", "description": "Display name, e.g. 'Linux System'"},
                    "topic": {
                        "type": "string",
                        "description": "Topic the tag is grouped under, e.g. 'Operating System'",
                    },
                    "help": {"type": "string", "description": "Help text"},
                },
                "required": ["tag_id", "title"],
            },
        },
        {
            "name": "vibemk_update_aux_tag",
            "description": "🏷️ Update an auxiliary tag.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tag_id": {"type": "string", "description": "Tag ID"},
                    "title": {"type": "string", "description": "New display name"},
                    "topic": {"type": "string", "description": "New topic"},
                    "help": {"type": "string", "description": "New help text"},
                },
                "required": ["tag_id"],
            },
        },
        {
            "name": "vibemk_delete_aux_tag",
            "description": "🗑️ Delete an auxiliary tag.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tag_id": {"type": "string", "description": "Tag ID"},
                },
                "required": ["tag_id"],
            },
        },
    ]


def get_audit_log_tools() -> List[Dict[str, Any]]:
    """Audit log tools"""
    return [
        {
            "name": "vibemk_get_audit_log",
            "description": (
                "📋 Retrieve the audit log: Checkmk configuration changes such as hosts created or deleted, rules changed, and activations."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD, default: today)",
                    },
                    "object_type": {
                        "type": "string",
                        "description": "Object type filter: 'All', 'Folder', 'Host', 'User', 'Rule', 'Ruleset'",
                    },
                    "object_id": {
                        "type": "string",
                        "description": "Object name filter, e.g. a host name",
                    },
                    "user_id": {"type": "string", "description": "User filter"},
                    "regexp": {
                        "type": "string",
                        "description": "Regular expression filtered against user_id, action and summary",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of entries (default: 50)",
                    },
                },
            },
        },
    ]


def get_site_tools() -> List[Dict[str, Any]]:
    """Site management tools"""
    return [
        {
            "name": "vibemk_get_sites",
            "description": ("🌐 List monitoring sites: every configured Checkmk instance in a distributed setup."),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_login_site",
            "description": "🔑 Log in to a remote site (distributed monitoring).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "site_id": {"type": "string", "description": "Site ID, e.g. 'uel' or 'ham'"},
                    "username": {"type": "string", "description": "User name"},
                    "password": {"type": "string", "description": "Password"},
                },
                "required": ["site_id", "username", "password"],
            },
        },
        {
            "name": "vibemk_logout_site",
            "description": "🚪 Log out of a remote site.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "site_id": {"type": "string", "description": "Site ID"},
                },
                "required": ["site_id"],
            },
        },
    ]


def get_clone_tools() -> List[Dict[str, Any]]:
    """Clone host tool"""
    return [
        {
            "name": "vibemk_clone_host",
            "description": (
                "🔁 Clone a host - copies the folder, tags and labels of a source host onto a new target host. A different IP address can optionally be given."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_hostname": {
                        "type": "string",
                        "description": "Source host name, e.g. 'web01.example.com'",
                    },
                    "target_hostname": {
                        "type": "string",
                        "description": "New host name, e.g. 'web02.example.com'",
                    },
                    "ip_address": {
                        "type": "string",
                        "description": (
                            "Optional IP address for the new host. Without it, the source host's IP is copied."
                        ),
                    },
                },
                "required": ["source_hostname", "target_hostname"],
            },
        }
    ]


_WRITE_TOOLS = frozenset(
    {
        # Hosts
        "vibemk_create_host",
        "vibemk_bulk_create_hosts",
        "vibemk_update_host",
        "vibemk_delete_host",
        "vibemk_move_host",
        "vibemk_bulk_update_hosts",
        "vibemk_create_cluster_host",
        "vibemk_clone_host",
        # Folders
        "vibemk_create_folder",
        "vibemk_delete_folder",
        "vibemk_update_folder",
        "vibemk_move_folder",
        # Rules
        "vibemk_create_rule",
        "vibemk_update_rule",
        "vibemk_delete_rule",
        "vibemk_move_rule",
        "vibemk_create_host_contactgroup_rule",
        "vibemk_create_host_hostgroup_rule",
        # Groups
        "vibemk_create_host_group",
        "vibemk_update_host_group",
        "vibemk_delete_host_group",
        "vibemk_create_service_group",
        "vibemk_update_service_group",
        "vibemk_delete_service_group",
        "vibemk_bulk_create_service_groups",
        "vibemk_bulk_update_service_groups",
        "vibemk_bulk_delete_service_groups",
        "vibemk_create_contact_group",
        "vibemk_update_contact_group",
        "vibemk_delete_contact_group",
        # Tags
        "vibemk_create_host_tag",
        "vibemk_update_host_tag",
        "vibemk_delete_host_tag",
        # Timeperiods
        "vibemk_create_timeperiod",
        "vibemk_update_timeperiod",
        "vibemk_delete_timeperiod",
        # Passwords
        "vibemk_create_password",
        "vibemk_update_password",
        "vibemk_delete_password",
        # User roles
        "vibemk_create_user_role",
        "vibemk_update_user_role",
        "vibemk_delete_user_role",
        # Active checks (as rules — need activation)
        "vibemk_create_http_check",
        "vibemk_create_tcp_check",
        "vibemk_create_icmp_check",
        "vibemk_create_custom_check",
        "vibemk_create_dns_check",
        "vibemk_create_smtp_check",
        "vibemk_create_ftp_check",
        "vibemk_create_ldap_check",
        "vibemk_create_smb_check",
        "vibemk_create_mkevents_check",
        "vibemk_create_inventory_check",
        "vibemk_delete_active_check",
        # Aux tags
        "vibemk_create_aux_tag",
        "vibemk_update_aux_tag",
        "vibemk_delete_aux_tag",
        # Service params
        "vibemk_set_process_thresholds",
        "vibemk_set_interface_params",
        "vibemk_set_memory_thresholds",
        "vibemk_delete_service_param_rule",
    }
)

_ACTIVATE_PROP: Dict[str, Any] = {
    "type": "boolean",
    "description": (
        "Activate the changes immediately after the operation (default: false). Ask the user first whether they want that."
    ),
}


def get_service_param_tools() -> List[Dict[str, Any]]:
    """Service parameter / threshold rules"""
    return [
        {
            "name": "vibemk_set_process_thresholds",
            "description": (
                "⚙️ Create process monitoring with thresholds for a host (inventory_processes_rules). The rule defines which processes are watched and how many instances trigger WARN and CRIT. A service discovery runs afterwards so the thresholds take effect immediately. Example: 'Process wnscli.exe' on host X should warn at >=10 instances and go critical at >=12."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Checkmk host name the rule applies to",
                    },
                    "process_name": {
                        "type": "string",
                        "description": (
                            "Process name, e.g. 'wnscli.exe', 'nginx' or 'java'. Used both as the process match and as the service name. A leading 'Process ' is stripped if present."
                        ),
                    },
                    "warn_max": {
                        "type": "integer",
                        "description": "WARNING when more than this many processes run (e.g. 10)",
                    },
                    "crit_max": {
                        "type": "integer",
                        "description": "CRITICAL when more than this many processes run (e.g. 12)",
                    },
                    "warn_min": {
                        "type": "integer",
                        "description": "WARNING when fewer than this many processes run (default: 1)",
                    },
                    "crit_min": {
                        "type": "integer",
                        "description": "CRITICAL when fewer than this many processes run (default: 1)",
                    },
                    "cpu_warn_percent": {
                        "type": "number",
                        "description": "Total CPU usage WARN threshold in percent (optional, e.g. 80)",
                    },
                    "cpu_crit_percent": {
                        "type": "number",
                        "description": "Total CPU usage CRIT threshold in percent (optional, e.g. 95)",
                    },
                    "single_cpu_warn_percent": {
                        "type": "number",
                        "description": "Per-process CPU usage WARN threshold in percent (optional)",
                    },
                    "single_cpu_crit_percent": {
                        "type": "number",
                        "description": "Per-process CPU usage CRIT threshold in percent (optional)",
                    },
                    "cpu_average_min": {
                        "type": "integer",
                        "description": "Average CPU over N minutes instead of using the instantaneous value (optional, e.g. 15)",
                    },
                    "mem_warn_mb": {
                        "type": "integer",
                        "description": "Virtual memory WARN threshold in MB (optional)",
                    },
                    "mem_crit_mb": {
                        "type": "integer",
                        "description": "Virtual memory CRIT threshold in MB (optional)",
                    },
                    "resident_warn_mb": {
                        "type": "integer",
                        "description": "Resident memory (RSS) WARN threshold in MB (optional)",
                    },
                    "resident_crit_mb": {
                        "type": "integer",
                        "description": "Resident memory (RSS) CRIT threshold in MB (optional)",
                    },
                    "run_discovery": {
                        "type": "boolean",
                        "description": (
                            "Run a service discovery after creating the rule (default: true). Set it to false only when creating several rules at once."
                        ),
                    },
                    "folder": {
                        "type": "string",
                        "description": "Checkmk folder (optional, defaults to the host's own folder)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO. Pick one that says what the rule is for.",
                    },
                },
                "required": ["hostname", "process_name", "warn_max", "crit_max"],
            },
        },
        {
            "name": "vibemk_set_interface_params",
            "description": (
                "🌐 Override interface parameters for a Checkmk host (checkgroup_parameters:interfaces). Typically used to set the expected speed and clear an 'expected speed' WARN. Example: interface vmbr1 warns because 10 Gbit/s is expected and 1 Gbit/s is real; expected_speed_mbit=1000 sets the expectation to 1 Gbit/s. RULE ORDER: the new rule is created in the host's own folder, not in root, so that subfolder precedence applies. Only activate_changes is needed, no service discovery."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Checkmk host name, e.g. 'web01.example.com'",
                    },
                    "interface_name": {
                        "type": "string",
                        "description": (
                            "Interface name, e.g. 'vmbr1', 'eth0' or 'bond0'. A leading 'Interface ' is stripped if present."
                        ),
                    },
                    "expected_speed_mbit": {
                        "type": "integer",
                        "description": (
                            "Expected interface speed in Mbit/s. "
                            "Typical values: 10, 100, 1000 (1 Gbit/s), 10000 (10 Gbit/s)."
                        ),
                    },
                    "folder": {
                        "type": "string",
                        "description": "Checkmk folder (optional, defaults to the host's own folder)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO (optional)",
                    },
                },
                "required": ["hostname", "interface_name", "expected_speed_mbit"],
            },
        },
        {
            "name": "vibemk_set_memory_thresholds",
            "description": (
                "💾 Set memory thresholds for a host (checkgroup_parameters:memory_linux), creating a rule for RAM and/or swap usage. IMPORTANT, the memory keys are: RAM = levels_virtual (not 'levels'), swap = levels_swap, physical RAM = levels_ram, committed = levels_committed. RULE ORDER: the new rule is created in the host's own folder, not in root. Check with vibemk_get_ruleset whether a rule for this host already exists and update it with vibemk_update_rule rather than adding a second one. Only activate_changes is needed."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Checkmk host name, e.g. 'web01.example.com'",
                    },
                    "ram_warn_percent": {
                        "type": "number",
                        "description": "Total virtual memory WARN in percent (levels_virtual, e.g. 90). Optional.",
                    },
                    "ram_crit_percent": {
                        "type": "number",
                        "description": "Total virtual memory CRIT in percent (levels_virtual, e.g. 95). Required when ram_warn is set.",
                    },
                    "swap_warn_percent": {
                        "type": "number",
                        "description": "Swap usage WARN threshold in percent (e.g. 30). Optional.",
                    },
                    "swap_crit_percent": {
                        "type": "number",
                        "description": "Swap usage CRIT threshold in percent (e.g. 50). Required when swap_warn is set.",
                    },
                    "folder": {
                        "type": "string",
                        "description": "Checkmk folder (optional, defaults to the host's own folder)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Rule description shown in WATO (optional)",
                    },
                },
                "required": ["hostname"],
            },
        },
        {
            "name": "vibemk_list_process_rules",
            "description": (
                "🔍 List process monitoring rules (inventory_processes_rules): which processes are monitored on which hosts, and at what thresholds."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Show only rules for this host (optional)",
                    },
                    "process_name": {
                        "type": "string",
                        "description": "Show only rules for this process (optional)",
                    },
                },
            },
        },
        {
            "name": "vibemk_delete_service_param_rule",
            "description": (
                "🗑️ Delete a service parameter rule, such as a process threshold rule. Needs the rule ID from vibemk_list_process_rules."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_id": {
                        "type": "string",
                        "description": "Rule ID, from vibemk_list_process_rules",
                    },
                },
                "required": ["rule_id"],
            },
        },
    ]


def get_checkmk_guide_tools() -> List[Dict[str, Any]]:
    """CheckMK rule management guide and tips"""
    return [
        {
            "name": "vibemk_checkmk_rules_guide",
            "description": (
                "📖 CheckMK Rules Guide - Returns the complete guide for rule management, "
                "ordering pitfalls, and API tricks. Call this BEFORE creating/modifying rules "
                "when unsure about the correct approach."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def get_agent_tools() -> List[Dict[str, Any]]:
    """Agent bakery tools (CheckMK CEE/Cloud only)"""
    return [
        {
            "name": "vibemk_bake_agents",
            "description": "🍞 Bake agents - Trigger agent package baking for all hosts (CEE/Cloud only)",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_baking_status",
            "description": "🍞 Baking status - Get current agent baking status Enterprise/Cloud only: a Raw site does not serve this endpoint and answers 404.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_download_agent_by_host",
            "description": "📦 Download agent - Get download URL for the agent package of a specific host Enterprise/Cloud only: a Raw site does not serve this endpoint and answers 404.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name to get agent for"},
                    "os_type": {
                        "type": "string",
                        "description": "OS type, e.g. linux_deb, linux_rpm, windows_msi",
                        "default": "linux_deb",
                    },
                },
                "required": ["host_name"],
            },
        },
    ]


def get_acknowledgement_tools() -> List[Dict[str, Any]]:
    """Problem acknowledgement tools"""
    return [
        {
            "name": "vibemk_acknowledge_host_problem",
            "description": "✅ Acknowledge host problem - Suppress notifications for a DOWN/UNREACHABLE host",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name"},
                    "comment": {"type": "string", "description": "Why the problem is being acknowledged"},
                    "sticky": {
                        "type": "boolean",
                        "default": True,
                        "description": "Hold the acknowledgement until the host returns to UP",
                    },
                    "persistent": {
                        "type": "boolean",
                        "default": False,
                        "description": "Keep the comment after the acknowledgement is removed",
                    },
                    "notify": {
                        "type": "boolean",
                        "default": True,
                        "description": "Send notifications to the configured contacts",
                    },
                    "expire_on": {
                        "type": "string",
                        "description": "Optional expiry as ISO-8601, e.g. 2026-12-24T22:00:00Z",
                    },
                },
                "required": ["host_name"],
            },
        },
        {
            "name": "vibemk_acknowledge_service_problem",
            "description": "✅ Acknowledge service problem - Suppress notifications for a WARN/CRIT/UNKNOWN service",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name"},
                    "service_description": {
                        "type": "string",
                        "description": "Service name exactly as CheckMK shows it, e.g. 'CPU utilization'",
                    },
                    "comment": {"type": "string", "description": "Why the problem is being acknowledged"},
                    "sticky": {
                        "type": "boolean",
                        "default": True,
                        "description": "Hold the acknowledgement until the service returns to OK",
                    },
                    "persistent": {
                        "type": "boolean",
                        "default": False,
                        "description": "Keep the comment after the acknowledgement is removed",
                    },
                    "notify": {
                        "type": "boolean",
                        "default": True,
                        "description": "Send notifications to the configured contacts",
                    },
                    "expire_on": {
                        "type": "string",
                        "description": "Optional expiry as ISO-8601, e.g. 2026-12-24T22:00:00Z",
                    },
                },
                "required": ["host_name", "service_description"],
            },
        },
        {
            "name": "vibemk_list_acknowledgements",
            "description": "📋 List acknowledgements - Show all currently acknowledged host and service problems",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "vibemk_remove_acknowledgement",
            "description": "🗑️ Remove acknowledgement - Delete by ID, by host/service, or by comment pattern",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "acknowledgement_id": {
                        "type": "string",
                        "description": "Acknowledgement ID from list_acknowledgements",
                    },
                    "host_name": {"type": "string", "description": "Remove the acknowledgement on this host"},
                    "service_description": {
                        "type": "string",
                        "description": "Restrict removal to this service on the host",
                    },
                    "comment_pattern": {
                        "type": "string",
                        "description": "Remove acknowledgements whose comment contains this text",
                    },
                    "delete_all_matching": {
                        "type": "boolean",
                        "description": "Remove every match instead of only the first (default: false)",
                    },
                },
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
    tools.extend(get_acknowledgement_tools())
    tools.extend(get_clone_tools())
    tools.extend(get_active_check_tools())
    tools.extend(get_event_console_tools())
    tools.extend(get_aux_tag_tools())
    tools.extend(get_audit_log_tools())
    tools.extend(get_site_tools())
    tools.extend(get_service_param_tools())
    tools.extend(get_agent_tools())
    tools.extend(get_checkmk_guide_tools())
    # Inject activate_changes into all write tools. Must run before the
    # de-duplication below, so the surviving definition carries the property.
    for tool in tools:
        if tool["name"] in _WRITE_TOOLS:
            tool["inputSchema"]["properties"]["activate_changes"] = _ACTIVATE_PROP

    # De-duplicate by tool name (a few tools were declared in two groups, e.g.
    # the service-group and delete_downtime tools). Keep the LAST definition so
    # the advertised schema matches the handler that wins routing in server.py.
    deduped = {}
    for tool in tools:
        deduped[tool["name"]] = tool

    return [_enriched(tool) for tool in deduped.values()]


def _enriched(tool: Dict[str, Any]) -> Dict[str, Any]:
    """Add the metadata MCP clients use to present and judge a tool.

    `title` is what a client shows instead of the wire name, and `annotations`
    tell a host whether a call needs a confirmation prompt. Both are derived
    here rather than repeated in 154 literals, so a new tool gets them by
    being declared.
    """
    tool.setdefault("title", title_for(tool["description"]))
    tool.setdefault("annotations", annotations_for(tool["name"]))

    schema = output_schema_for(tool["name"])
    if schema is not None:
        tool.setdefault("outputSchema", schema)

    # A tool with no parameters: the specification recommends saying so
    # explicitly rather than accepting any object.
    schema = tool.get("inputSchema")
    if schema and schema.get("type") == "object" and not schema.get("properties"):
        schema.pop("properties", None)
        schema.setdefault("additionalProperties", False)

    return tool
