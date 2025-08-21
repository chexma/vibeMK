"""
Password management handlers for CheckMK credential storage
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class PasswordsHandler(BaseHandler):
    """Handle password management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle password-related tool calls"""

        try:
            if tool_name == "vibemk_get_passwords":
                return await self._get_passwords(arguments)
            elif tool_name == "vibemk_create_password":
                return await self._create_password(arguments)
            elif tool_name == "vibemk_update_password":
                return await self._update_password(arguments)
            elif tool_name == "vibemk_delete_password":
                return await self._delete_password(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _get_passwords(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of stored passwords"""
        result = self.client.get("domain-types/password/collections/all")

        if not result.get("success"):
            return self.error_response("Failed to retrieve passwords")

        passwords = result["data"].get("value", [])
        if not passwords:
            return [{"type": "text", "text": "🔐 **No Passwords Found**\n\nNo stored passwords are configured."}]

        password_list = []
        for password in passwords:
            password_id = password.get("id", "Unknown")
            extensions = password.get("extensions", {})
            title = extensions.get("title", password_id)
            comment = extensions.get("comment", "No description")
            owner = extensions.get("owner", "Unknown")
            shared = extensions.get("shared", [])

            shared_info = f"Shared with {len(shared)} users/groups" if shared else "Not shared"
            password_list.append(
                f"🔐 **{password_id}** - {title}\n   Owner: {owner}\n   {shared_info}\n   Comment: {comment[:50]}..."
            )

        return [
            {
                "type": "text",
                "text": f"🔐 **Stored Passwords** ({len(passwords)} total):\n\n" + "\n\n".join(password_list),
            }
        ]

    async def _create_password(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new stored password"""
        ident = arguments.get("ident")
        title = arguments.get("title")
        password = arguments.get("password")
        comment = arguments.get("comment", "")
        documentation_url = arguments.get("documentation_url", "")
        owner = arguments.get("owner", "admin")
        shared = arguments.get("shared", [])

        if not ident:
            return self.error_response("Missing parameter", "ident is required")

        if not password:
            return self.error_response("Missing parameter", "password is required")

        data = {"ident": ident, "password": password, "owner": owner}

        if title:
            data["title"] = title
        if comment:
            data["comment"] = comment
        if documentation_url:
            data["documentation_url"] = documentation_url
        if shared:
            data["shared"] = shared

        result = self.client.post("domain-types/password/collections/all", data=data)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Password Created Successfully**\n\n"
                        f"Identifier: {ident}\n"
                        f"Title: {title or 'None'}\n"
                        f"Owner: {owner}\n"
                        f"Shared with: {len(shared)} users/groups\n"
                        f"Comment: {comment or 'None'}\n\n"
                        f"🔒 **Security Note:** The password is now securely stored in CheckMK\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("Password creation failed", f"Could not create password '{ident}'")

    async def _update_password(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update an existing stored password"""
        ident = arguments.get("ident")
        title = arguments.get("title")
        password = arguments.get("password")
        comment = arguments.get("comment")
        documentation_url = arguments.get("documentation_url")
        owner = arguments.get("owner")
        shared = arguments.get("shared")

        if not ident:
            return self.error_response("Missing parameter", "ident is required")

        # Check if password exists
        check_result = self.client.get(f"objects/password/{ident}")
        if not check_result.get("success"):
            return self.error_response("Password not found", f"Password '{ident}' does not exist")

        # Build update data
        data = {}
        if title is not None:
            data["title"] = title
        if password is not None:
            data["password"] = password
        if comment is not None:
            data["comment"] = comment
        if documentation_url is not None:
            data["documentation_url"] = documentation_url
        if owner is not None:
            data["owner"] = owner
        if shared is not None:
            data["shared"] = shared

        if not data:
            return self.error_response("No data to update", "At least one field must be provided")

        # Use ETag for optimistic locking
        headers = {"If-Match": "*"}
        result = self.client.put(f"objects/password/{ident}", data=data, headers=headers)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Password Updated Successfully**\n\n"
                        f"Identifier: {ident}\n"
                        f"Updated fields: {', '.join(data.keys())}\n\n"
                        f"🔒 **Security Note:** Changes are securely stored in CheckMK\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("Password update failed", f"Could not update password '{ident}'")

    async def _delete_password(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a stored password"""
        ident = arguments.get("ident")

        if not ident:
            return self.error_response("Missing parameter", "ident is required")

        # Check if password exists
        check_result = self.client.get(f"objects/password/{ident}")
        if not check_result.get("success"):
            return self.error_response("Password not found", f"Password '{ident}' does not exist")

        result = self.client.delete(f"objects/password/{ident}")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Password Deleted Successfully**\n\n"
                        f"Identifier: {ident}\n\n"
                        f"🔒 **Security Note:** The password has been securely removed\n\n"
                        f"📝 **Next Steps:**\n"
                        f"1️⃣ Use 'get_pending_changes' to review the deletion\n"
                        f"2️⃣ Use 'activate_changes' to apply the configuration\n\n"
                        f"💡 **Important:** The password is only marked for deletion until you activate changes!"
                    ),
                }
            ]
        else:
            return self.error_response("Password deletion failed", f"Could not delete password '{ident}'")
