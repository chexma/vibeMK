"""
User roles management handlers for CheckMK user role operations
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class UserRolesHandler(BaseHandler):
    """Handle user role management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle user role-related tool calls"""

        try:
            if tool_name == "vibemk_list_user_roles":
                return await self._list_user_roles(arguments)
            elif tool_name == "vibemk_show_user_role":
                return await self._show_user_role(arguments)
            elif tool_name == "vibemk_create_user_role":
                return await self._create_user_role(arguments)
            elif tool_name == "vibemk_update_user_role":
                return await self._update_user_role(arguments)
            elif tool_name == "vibemk_delete_user_role":
                return await self._delete_user_role(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _list_user_roles(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all available user roles"""
        show_builtin = arguments.get("show_builtin", True)

        self.logger.debug("Listing user roles")

        try:
            result = self.client.get("domain-types/user_role/collections/all")
            roles = result["data"].get("value", [])

            if not roles:
                return [
                    {
                        "type": "text",
                        "text": (
                            "👥 **No User Roles Found**\n\n"
                            "No user roles are available in this CheckMK instance.\n\n"
                            "💡 This might indicate a permissions issue or API access problem."
                        ),
                    }
                ]

            return [
                {
                    "type": "text",
                    "text": self._format_roles_list(roles, show_builtin),
                }
            ]

        except CheckMKError as e:
            http_status = getattr(e, "status_code", 0)

            if http_status == 403:
                return self.error_response(
                    "Permission Denied", "Access denied. You need 'wato.users' permission for user role management."
                )
            elif http_status == 406:
                return self.error_response("Accept Header Error", "API cannot satisfy the requested content type.")
            else:
                return self.error_response("Failed to list user roles", str(e))

    async def _show_user_role(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Show detailed information about a specific user role"""
        role_id = arguments.get("role_id")

        if not role_id:
            return self.error_response("Missing parameter", "role_id is required")

        self.logger.debug(f"Showing user role: {role_id}")

        try:
            result = self.client.get(f"objects/user_role/{role_id}")
            role_data = result["data"]

            return [
                {
                    "type": "text",
                    "text": self._format_role_details(role_id, role_data),
                }
            ]

        except CheckMKError as e:
            http_status = getattr(e, "status_code", 0)

            if http_status == 403:
                return self.error_response(
                    "Permission Denied", "Access denied. You need 'wato.users' permission for user role management."
                )
            elif http_status == 404:
                return self.error_response(
                    "Role Not Found", f"User role '{role_id}' not found. Check the role ID and try again."
                )
            else:
                return self.error_response("Failed to retrieve user role", str(e))

    async def _create_user_role(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create/clone a new user role from an existing one"""
        base_role_id = arguments.get("base_role_id")
        new_role_id = arguments.get("new_role_id")
        new_alias = arguments.get("new_alias", "")

        if not base_role_id or not new_role_id:
            return self.error_response("Missing parameters", "base_role_id and new_role_id are required")

        self.logger.debug(f"Creating user role '{new_role_id}' from '{base_role_id}'")

        # Prepare the request data
        data = {
            "role_id": base_role_id,
            "new_role_id": new_role_id,
        }

        if new_alias:
            data["new_alias"] = new_alias

        try:
            result = self.client.post("domain-types/user_role/collections/all", data=data)

            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **User Role Created Successfully**\n\n"
                        f"**New Role Details:**\n"
                        f"• **Role ID**: `{new_role_id}`\n"
                        f"• **Cloned from**: `{base_role_id}`\n"
                        f"• **Alias**: {new_alias if new_alias else 'Not specified'}\n\n"
                        f"**Inherited Permissions:**\n"
                        f"The new role inherits all permissions from the '{base_role_id}' role.\n\n"
                        f"💡 **Next Steps:**\n"
                        f"• Use `vibemk_show_user_role` to view detailed permissions\n"
                        f"• Use `vibemk_update_user_role` to customize permissions\n"
                        f"• Assign this role to users in user management"
                    ),
                }
            ]

        except CheckMKError as e:
            http_status = getattr(e, "status_code", 0)
            error_data = getattr(e, "error_data", {})

            if http_status == 400:
                return self.error_response(
                    "Invalid Parameters", f"Invalid role parameters: {error_data.get('detail', str(e))}"
                )
            elif http_status == 403:
                return self.error_response(
                    "Permission Denied",
                    "Access denied. You need 'wato.edit' and 'wato.users' permissions for role creation.",
                )
            elif http_status == 409:
                return self.error_response(
                    "Role Already Exists", f"Role '{new_role_id}' already exists. Choose a different role ID."
                )
            else:
                return self.error_response("Failed to create user role", str(e))

    async def _update_user_role(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update an existing user role"""
        role_id = arguments.get("role_id")
        alias = arguments.get("alias")
        permissions = arguments.get("permissions", {})

        if not role_id:
            return self.error_response("Missing parameter", "role_id is required")

        self.logger.debug(f"Updating user role: {role_id}")

        # Prepare the request data
        data = {}
        if alias:
            data["new_alias"] = alias  # CheckMK API expects 'new_alias' not 'alias'
        if permissions:
            data["permissions"] = permissions

        if not data:
            return self.error_response(
                "No updates specified", "At least one of 'alias' or 'permissions' must be provided"
            )

        try:
            result = self.client.put(f"objects/user_role/{role_id}", data=data)

            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **User Role Updated Successfully**\n\n"
                        f"**Updated Role**: `{role_id}`\n\n"
                        f"**Changes Applied:**\n"
                        f"{'• **Alias**: ' + alias if alias else ''}\n"
                        f"{'• **Permissions**: Updated ' + str(len(permissions)) + ' permissions' if permissions else ''}\n\n"
                        f"💡 **Use `vibemk_show_user_role` to view the updated role details**"
                    ),
                }
            ]

        except CheckMKError as e:
            http_status = getattr(e, "status_code", 0)
            error_data = getattr(e, "error_data", {})

            if http_status == 400:
                return self.error_response(
                    "Invalid Parameters", f"Invalid role parameters: {error_data.get('detail', str(e))}"
                )
            elif http_status == 403:
                return self.error_response(
                    "Permission Denied",
                    "Access denied. You need 'wato.edit' and 'wato.users' permissions for role updates.",
                )
            elif http_status == 404:
                return self.error_response("Role Not Found", f"User role '{role_id}' not found.")
            else:
                return self.error_response("Failed to update user role", str(e))

    async def _delete_user_role(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a custom user role"""
        role_id = arguments.get("role_id")

        if not role_id:
            return self.error_response("Missing parameter", "role_id is required")

        # Check if it's a built-in role
        builtin_roles = ["admin", "user", "guest"]
        if role_id in builtin_roles:
            return self.error_response(
                "Cannot Delete Built-in Role",
                f"The role '{role_id}' is a built-in role and cannot be deleted. " "Only custom roles can be deleted.",
            )

        self.logger.debug(f"Deleting user role: {role_id}")

        try:
            result = self.client.delete(f"objects/user_role/{role_id}")

            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **User Role Deleted Successfully**\n\n"
                        f"**Deleted Role**: `{role_id}`\n\n"
                        f"⚠️ **Important Notes:**\n"
                        f"• Users with this role will need to be reassigned to other roles\n"
                        f"• Built-in roles (admin, user, guest) cannot be deleted\n"
                        f"• This action cannot be undone\n\n"
                        f"💡 **Use `vibemk_list_user_roles` to view remaining roles**"
                    ),
                }
            ]

        except CheckMKError as e:
            http_status = getattr(e, "status_code", 0)

            if http_status == 400:
                return self.error_response(
                    "Cannot Delete Role", f"Role '{role_id}' cannot be deleted. It may still be in use by users."
                )
            elif http_status == 403:
                return self.error_response(
                    "Permission Denied",
                    "Access denied. You need 'wato.edit' and 'wato.users' permissions for role deletion.",
                )
            elif http_status == 404:
                return self.error_response("Role Not Found", f"User role '{role_id}' not found.")
            else:
                return self.error_response("Failed to delete user role", str(e))

    def _format_roles_list(self, roles: List[Dict], show_builtin: bool) -> str:
        """Format user roles list for display"""
        response = "👥 **User Roles**\n\n"

        # Separate built-in and custom roles
        builtin_roles = []
        custom_roles = []

        for role in roles:
            role_id = role.get("id", "Unknown")
            extensions = role.get("extensions", {})
            alias = extensions.get("alias", role_id)
            builtin = extensions.get("builtin", False)

            permissions = extensions.get("permissions", [])
            role_info = {"id": role_id, "alias": alias, "builtin": builtin, "permissions_count": len(permissions)}

            if builtin or role_id in ["admin", "user", "guest"]:
                builtin_roles.append(role_info)
            else:
                custom_roles.append(role_info)

        if show_builtin and builtin_roles:
            response += "**🏗️ Built-in Roles** (cannot be deleted):\n"
            for role in builtin_roles:
                icon = self._get_role_icon(role["id"])
                response += f"{icon} **{role['id']}** - {role['alias']}\n"
                response += f"   📊 {role['permissions_count']} permissions\n"
                response += f"   💡 {self._get_role_description(role['id'])}\n\n"

        if custom_roles:
            response += "**🎨 Custom Roles**:\n"
            for role in custom_roles:
                response += f"✏️ **{role['id']}** - {role['alias']}\n"
                response += f"   📊 {role['permissions_count']} permissions\n\n"
        elif not builtin_roles:
            response += "No custom roles found.\n\n"

        response += "**💡 Available Operations:**\n"
        response += "• `vibemk_show_user_role` - View detailed role information\n"
        response += "• `vibemk_create_user_role` - Clone an existing role\n"
        response += "• `vibemk_update_user_role` - Modify custom role permissions\n"
        response += "• `vibemk_delete_user_role` - Delete custom roles\n"

        return response

    def _format_role_details(self, role_id: str, role_data: Dict) -> str:
        """Format detailed role information"""
        extensions = role_data.get("extensions", {})

        alias = extensions.get("alias", role_id)
        builtin = extensions.get("builtin", False) or role_id in ["admin", "user", "guest"]
        permissions = extensions.get("permissions", {})

        response = f"👥 **User Role Details: {role_id}**\n\n"

        if builtin:
            response += "🏗️ **Built-in Role** (cannot be deleted)\n\n"
        else:
            response += "🎨 **Custom Role**\n\n"

        response += f"**Role Information:**\n"
        response += f"• **ID**: `{role_id}`\n"
        response += f"• **Alias**: {alias}\n"
        response += f"• **Type**: {'Built-in' if builtin else 'Custom'}\n"
        response += f"• **Permissions**: {len(permissions)} total\n\n"

        if role_id in ["admin", "user", "guest"]:
            response += f"**Description:**\n{self._get_role_description(role_id)}\n\n"

        # Show key permissions (first 10 for brevity)
        if permissions:
            response += "**Key Permissions** (showing first 10):\n"
            if isinstance(permissions, list):
                # Permissions is a list of permission names
                for i, perm_id in enumerate(permissions[:10]):
                    response += f"✅ `{perm_id}`\n"

                if len(permissions) > 10:
                    response += f"... and {len(permissions) - 10} more permissions\n"
            else:
                # Permissions is a dictionary (fallback for older API versions)
                for i, (perm_id, enabled) in enumerate(list(permissions.items())[:10]):
                    status = "✅" if enabled else "❌"
                    response += f"{status} `{perm_id}`\n"

                if len(permissions) > 10:
                    response += f"... and {len(permissions) - 10} more permissions\n"

        response += f"\n**Available Operations:**\n"
        if not builtin:
            response += f"• `vibemk_update_user_role` - Modify this role\n"
            response += f"• `vibemk_delete_user_role` - Delete this role\n"
        response += f"• `vibemk_create_user_role` - Clone this role to create a new one\n"

        return response

    def _get_role_icon(self, role_id: str) -> str:
        """Get appropriate icon for role type"""
        icons = {"admin": "👑", "user": "👤", "guest": "👁️"}
        return icons.get(role_id, "🎭")

    def _get_role_description(self, role_id: str) -> str:
        """Get description for built-in roles"""
        descriptions = {
            "admin": "Full CheckMK administrator with all permissions",
            "user": "Normal user - can only see own hosts/services, limited changes",
            "guest": "Read-only access - can see everything but change nothing",
        }
        return descriptions.get(role_id, "Custom user role")
