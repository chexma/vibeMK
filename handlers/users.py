"""
User management handlers
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class UserHandler(BaseHandler):
    """Handle user management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle user-related tool calls"""

        try:
            if tool_name == "vibemk_get_users":
                return await self._get_users(arguments)
            elif tool_name == "vibemk_create_user":
                return await self._create_user(arguments)
            elif tool_name == "vibemk_update_user":
                return await self._update_user(arguments)
            elif tool_name == "vibemk_delete_user":
                return await self._delete_user(arguments)
            elif tool_name == "vibemk_get_contact_groups":
                return await self._get_contact_groups(arguments)
            elif tool_name == "vibemk_create_contact_group":
                return await self._create_contact_group(arguments)
            elif tool_name == "vibemk_update_contact_group":
                return await self._update_contact_group(arguments)
            elif tool_name == "vibemk_delete_contact_group":
                return await self._delete_contact_group(arguments)
            elif tool_name == "vibemk_add_user_to_group":
                return await self._add_user_to_group(arguments)
            elif tool_name == "vibemk_remove_user_from_group":
                return await self._remove_user_from_group(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _get_users(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of CheckMK users"""
        result = self.client.get("domain-types/user_config/collections/all")

        if not result.get("success"):
            return self.error_response("Failed to retrieve users")

        users = result["data"].get("value", [])
        if not users:
            return [{"type": "text", "text": "👥 **No Users Found**\n\nNo CheckMK users are configured."}]

        user_list = []
        for user in users:
            user_id = user.get("id", "Unknown")
            extensions = user.get("extensions", {})
            fullname = extensions.get("fullname", user_id)
            email = extensions.get("contact_options", {}).get("email", "No email")
            roles = ", ".join(extensions.get("roles", []))
            disable_login = extensions.get("disable_login", False)

            status = "🔒 Disabled" if disable_login else "✅ Active"
            user_list.append(f"👤 **{user_id}** ({fullname})\n   📧 {email}\n   🔑 Roles: {roles}\n   {status}")

        return [{"type": "text", "text": f"👥 **CheckMK Users** ({len(users)} total):\n\n" + "\n\n".join(user_list)}]

    async def _create_user(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new CheckMK user"""
        username = arguments.get("username")
        fullname = arguments.get("fullname")
        email = arguments.get("email", "")
        password = arguments.get("password", "")
        roles = arguments.get("roles", ["user"])
        contactgroups = arguments.get("contactgroups", ["all"])

        if not username or not fullname:
            return self.error_response("Missing parameters", "username and fullname are required")

        # Build minimal user data structure based on CheckMK API requirements
        data = {"username": username, "fullname": fullname, "disable_notifications": {}, "interface_options": {}}

        # Add authentication if password provided
        if password:
            data["auth_option"] = {"auth_type": "password", "password": password}

        # Add email if provided
        if email:
            data["contact_options"] = {"email": email}

        # Add roles if provided
        if roles:
            data["roles"] = roles

        # Add contact groups - important for user-to-group assignments
        if contactgroups:
            data["contactgroups"] = contactgroups

        self.logger.debug(f"Creating user with data: {data}")
        result = self.client.post("domain-types/user_config/collections/all", data=data)

        # Enhanced error reporting for debugging
        if not result.get("success"):
            error_details = result.get("data", {})
            if isinstance(error_details, dict):
                error_msg = error_details.get("detail", error_details.get("message", "Unknown error"))
                title = error_details.get("title", "API Error")
                return [
                    {
                        "type": "text",
                        "text": (
                            f"❌ **User Creation Failed**\n\n"
                            f"Error: {title}\n"
                            f"Details: {error_msg}\n\n"
                            f"Request data sent: {data}\n\n"
                            f"Full response: {result}"
                        ),
                    }
                ]
            else:
                return self.error_response("User creation failed", f"API Error: {error_details}")

        return [
            {
                "type": "text",
                "text": (
                    f"✅ **User Created Successfully**\n\n"
                    f"Username: {username}\n"
                    f"Full Name: {fullname}\n"
                    f"Email: {email or 'Not set'}\n"
                    f"Roles: {', '.join(roles)}\n"
                    f"Contact Groups: {', '.join(contactgroups)}\n"
                    f"Login: {'Enabled' if password else 'Disabled'}\n\n"
                    f"⚠️ **Remember to activate changes!**"
                ),
            }
        ]

    async def _update_user(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update an existing CheckMK user"""
        username = arguments.get("username")
        fullname = arguments.get("fullname")
        email = arguments.get("email")
        roles = arguments.get("roles")
        contactgroups = arguments.get("contactgroups")

        if not username:
            return self.error_response("Missing parameter", "username is required")

        # First get the current user to get ETag
        current_user_result = self.client.get(f"objects/user_config/{username}")
        if not current_user_result.get("success"):
            return self.error_response("User not found", f"User '{username}' does not exist")

        # Build update data
        data = {}
        if fullname:
            data["fullname"] = fullname
        if email:
            data["contact_options"] = {"email": email}
        if roles:
            data["roles"] = roles
        if contactgroups is not None:  # Allow empty list to remove all groups
            data["contactgroups"] = contactgroups

        # Use ETag for optimistic locking (use wildcard for simplicity)
        headers = {"If-Match": "*"}
        result = self.client.put(f"objects/user_config/{username}", data=data, headers=headers)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **User Updated Successfully**\n\n"
                        f"Username: {username}\n"
                        f"Updated fields: {', '.join(data.keys())}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("User update failed", f"Could not update user '{username}'")

    async def _delete_user(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a CheckMK user"""
        username = arguments.get("username")

        if not username:
            return self.error_response("Missing parameter", "username is required")

        # Check if user exists
        check_result = self.client.get(f"objects/user_config/{username}")
        if not check_result.get("success"):
            return self.error_response("User not found", f"User '{username}' does not exist")

        result = self.client.delete(f"objects/user_config/{username}")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **User Deleted Successfully**\n\n"
                        f"Username: {username}\n\n"
                        f"📝 **Next Steps:**\n"
                        f"1️⃣ Use 'get_pending_changes' to review the deletion\n"
                        f"2️⃣ Use 'activate_changes' to apply the configuration\n\n"
                        f"💡 **Important:** The user is only marked for deletion until you activate changes!"
                    ),
                }
            ]
        else:
            return self.error_response("User deletion failed", f"Could not delete user '{username}'")

    async def _get_contact_groups(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of contact groups"""
        result = self.client.get("domain-types/contact_group_config/collections/all")

        if not result.get("success"):
            return self.error_response("Failed to retrieve contact groups")

        groups = result["data"].get("value", [])
        if not groups:
            return [{"type": "text", "text": "👥 **No Contact Groups Found**\n\nNo contact groups are configured."}]

        group_list = []
        for group in groups:
            group_id = group.get("id", "Unknown")
            extensions = group.get("extensions", {})
            alias = extensions.get("alias", group_id)

            group_list.append(f"👥 **{group_id}** - {alias}")

        return [{"type": "text", "text": f"👥 **Contact Groups** ({len(groups)} total):\n\n" + "\n".join(group_list)}]

    async def _create_contact_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new contact group"""
        name = arguments.get("name")
        alias = arguments.get("alias")
        members = arguments.get("members", [])

        if not name or not alias:
            return self.error_response("Missing parameters", "name and alias are required")

        # CheckMK API structure for contact groups
        data = {"name": name, "alias": alias}

        # Note: Contact groups don't directly support members in creation
        # Members are managed through user configurations
        if members:
            self.logger.debug(f"Note: Contact group members ({members}) will need to be set via user management")

        self.logger.debug(f"Creating contact group with data: {data}")
        result = self.client.post("domain-types/contact_group_config/collections/all", data=data)

        # Enhanced error reporting for debugging
        if not result.get("success"):
            error_details = result.get("data", {})
            if isinstance(error_details, dict):
                error_msg = error_details.get("detail", error_details.get("message", "Unknown error"))
                title = error_details.get("title", "API Error")
                return [
                    {
                        "type": "text",
                        "text": (
                            f"❌ **Contact Group Creation Failed**\n\n"
                            f"Error: {title}\n"
                            f"Details: {error_msg}\n\n"
                            f"Request data sent: {data}\n\n"
                            f"Full response: {result}"
                        ),
                    }
                ]
            else:
                return self.error_response("Contact group creation failed", f"API Error: {error_details}")

        return [
            {
                "type": "text",
                "text": (
                    f"✅ **Contact Group Created Successfully**\n\n"
                    f"Name: {name}\n"
                    f"Alias: {alias}\n"
                    f"Members: {len(members)} users\n\n"
                    f"⚠️ **Remember to activate changes!**"
                ),
            }
        ]

    async def _update_contact_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update an existing contact group"""
        name = arguments.get("name")
        alias = arguments.get("alias")
        members = arguments.get("members")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        # First get the current contact group to check if it exists
        current_group_result = self.client.get(f"objects/contact_group_config/{name}")
        if not current_group_result.get("success"):
            return self.error_response("Contact group not found", f"Contact group '{name}' does not exist")

        # Build update data for contact group
        data = {}
        if alias:
            data["alias"] = alias

        # Note: Contact group members are managed through user assignments, not directly
        if members is not None:
            self.logger.debug(f"Note: Contact group members should be managed via user configurations")

        if not data:
            return self.error_response("No data to update", "At least alias must be provided")

        # Use ETag for optimistic locking
        headers = {"If-Match": "*"}
        result = self.client.put(f"objects/contact_group_config/{name}", data=data, headers=headers)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Contact Group Updated Successfully**\\n\\n"
                        f"Name: {name}\\n"
                        f"Updated fields: {', '.join(data.keys())}\\n\\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("Contact group update failed", f"Could not update contact group '{name}'")

    async def _delete_contact_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a contact group"""
        name = arguments.get("name")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        # Check if contact group exists
        check_result = self.client.get(f"objects/contact_group_config/{name}")
        if not check_result.get("success"):
            return self.error_response("Contact group not found", f"Contact group '{name}' does not exist")

        result = self.client.delete(f"objects/contact_group_config/{name}")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Contact Group Deleted Successfully**\\n\\n"
                        f"Name: {name}\\n\\n"
                        f"📝 **Next Steps:**\\n"
                        f"1️⃣ Use 'get_pending_changes' to review the deletion\\n"
                        f"2️⃣ Use 'activate_changes' to apply the configuration\\n\\n"
                        f"💡 **Important:** The contact group is only marked for deletion until you activate changes!"
                    ),
                }
            ]
        else:
            return self.error_response("Contact group deletion failed", f"Could not delete contact group '{name}'")

    async def _add_user_to_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add a user to a contact group"""
        username = arguments.get("username")
        group_name = arguments.get("group_name")

        if not username or not group_name:
            return self.error_response("Missing parameters", "username and group_name are required")

        # First get current user to retrieve existing contact groups
        user_result = self.client.get(f"objects/user_config/{username}")
        if not user_result.get("success"):
            return self.error_response("User not found", f"User '{username}' does not exist")

        user_data = user_result["data"]
        extensions = user_data.get("extensions", {})
        current_groups = extensions.get("contactgroups", [])

        # Add group if not already present
        if group_name not in current_groups:
            new_groups = current_groups + [group_name]

            # Update user with new contact groups
            update_data = {"contactgroups": new_groups}
            headers = {"If-Match": "*"}
            result = self.client.put(f"objects/user_config/{username}", data=update_data, headers=headers)

            if result.get("success"):
                return [
                    {
                        "type": "text",
                        "text": (
                            f"✅ **User Added to Contact Group**\n\n"
                            f"Username: {username}\n"
                            f"Added to group: {group_name}\n"
                            f"Total groups: {', '.join(new_groups)}\n\n"
                            f"⚠️ **Remember to activate changes!**"
                        ),
                    }
                ]
            else:
                return self.error_response("Failed to add user to group", f"Could not update user '{username}'")
        else:
            return [
                {
                    "type": "text",
                    "text": (
                        f"ℹ️ **User Already in Group**\n\n"
                        f"Username: {username}\n"
                        f"Group: {group_name}\n\n"
                        f"User is already a member of this contact group."
                    ),
                }
            ]

    async def _remove_user_from_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Remove a user from a contact group"""
        username = arguments.get("username")
        group_name = arguments.get("group_name")

        if not username or not group_name:
            return self.error_response("Missing parameters", "username and group_name are required")

        # First get current user to retrieve existing contact groups
        user_result = self.client.get(f"objects/user_config/{username}")
        if not user_result.get("success"):
            return self.error_response("User not found", f"User '{username}' does not exist")

        user_data = user_result["data"]
        extensions = user_data.get("extensions", {})
        current_groups = extensions.get("contactgroups", [])

        # Remove group if present
        if group_name in current_groups:
            new_groups = [g for g in current_groups if g != group_name]

            # Update user with new contact groups
            update_data = {"contactgroups": new_groups}
            headers = {"If-Match": "*"}
            result = self.client.put(f"objects/user_config/{username}", data=update_data, headers=headers)

            if result.get("success"):
                return [
                    {
                        "type": "text",
                        "text": (
                            f"✅ **User Removed from Contact Group**\n\n"
                            f"Username: {username}\n"
                            f"Removed from group: {group_name}\n"
                            f"Remaining groups: {', '.join(new_groups) if new_groups else 'None'}\n\n"
                            f"⚠️ **Remember to activate changes!**"
                        ),
                    }
                ]
            else:
                return self.error_response("Failed to remove user from group", f"Could not update user '{username}'")
        else:
            return [
                {
                    "type": "text",
                    "text": (
                        f"ℹ️ **User Not in Group**\n\n"
                        f"Username: {username}\n"
                        f"Group: {group_name}\n\n"
                        f"User is not a member of this contact group."
                    ),
                }
            ]
