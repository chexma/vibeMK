"""
Service groups management handlers for CheckMK integration
"""

import json
from typing import Any, Dict, List, Optional

from api.exceptions import CheckMKError, CheckMKNotFoundError
from handlers.base import BaseHandler


class ServiceGroupHandler(BaseHandler):
    """Handle service group management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle service group tool calls"""
        try:
            if tool_name == "vibemk_create_service_group":
                return await self._create_service_group(arguments)
            elif tool_name == "vibemk_list_service_groups":
                return await self._list_service_groups(arguments)
            elif tool_name == "vibemk_get_service_group":
                return await self._get_service_group(arguments)
            elif tool_name == "vibemk_update_service_group":
                return await self._update_service_group(arguments)
            elif tool_name == "vibemk_delete_service_group":
                return await self._delete_service_group(arguments)
            elif tool_name == "vibemk_bulk_create_service_groups":
                return await self._bulk_create_service_groups(arguments)
            elif tool_name == "vibemk_bulk_update_service_groups":
                return await self._bulk_update_service_groups(arguments)
            elif tool_name == "vibemk_bulk_delete_service_groups":
                return await self._bulk_delete_service_groups(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' not supported by service group handler")

        except CheckMKNotFoundError as e:
            return self.error_response("Service group not found", str(e))
        except CheckMKError as e:
            return self.error_response("CheckMK API error", str(e))
        except Exception as e:
            return self.error_response("Operation failed", f"Unexpected error: {str(e)}")

    async def _create_service_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a single service group"""
        name = arguments.get("name")
        alias = arguments.get("alias")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        if not alias:
            return self.error_response("Missing parameter", "alias is required")

        # Validate service group name
        if not self._validate_service_group_name(name):
            return self.error_response(
                "Invalid name", "Service group name must contain only letters, numbers, hyphens, and underscores"
            )

        # Check if service group already exists
        try:
            existing_group = self.client.get(f"objects/service_group_config/{name}")
            if existing_group.get("success"):
                return self.error_response(
                    "Service group already exists", f"Service group '{name}' already exists. Use update to modify it."
                )
        except CheckMKNotFoundError:
            # Service group doesn't exist, which is what we want for creation
            pass

        data = {"name": name, "alias": alias}

        result = self.client.post("domain-types/service_group_config/collections/all", data=data)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Service Group Created Successfully**\n\n"
                        f"**Name:** {name}\n"
                        f"**Alias:** {alias}\n\n"
                        f"⚠️ **Remember to activate changes!**\n\n"
                        f"💡 **Next Steps:**\n"
                        f"1️⃣ Use 'list_service_groups' to view all groups\n"
                        f"2️⃣ Use 'activate_changes' to apply configuration"
                    ),
                }
            ]
        else:
            error_details = result.get("data", {})
            return self.error_response(
                "Service group creation failed", f"Could not create service group '{name}': {error_details}"
            )

    async def _list_service_groups(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all service groups"""
        result = self.client.get("domain-types/service_group_config/collections/all")

        if not result.get("success"):
            return self.error_response("Failed to retrieve service groups", result.get("data", {}))

        service_groups = result.get("data", {}).get("value", [])

        if not service_groups:
            return [
                {"type": "text", "text": "ℹ️ **No Service Groups Found**\n\nUse 'create_service_group' to create one."}
            ]

        response_text = f"📋 **Service Groups List** ({len(service_groups)} total)\n\n"

        for i, group in enumerate(service_groups, 1):
            group_id = group.get("id", "Unknown")
            extensions = group.get("extensions", {})
            alias = extensions.get("alias", "No alias")

            response_text += f"**{i}. Service Group: {group_id}**\n"
            response_text += f"   Alias: {alias}\n"
            response_text += f"   ID: {group_id}\n\n"

        response_text += "💡 Use 'get_service_group' with a name to see detailed information"

        return [{"type": "text", "text": response_text}]

    async def _get_service_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get detailed information about a specific service group"""
        name = arguments.get("name")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        result = self.client.get(f"objects/service_group_config/{name}")

        if not result.get("success"):
            return self.error_response("Service group not found", f"Service group '{name}' not found")

        group_data = result.get("data", {})
        extensions = group_data.get("extensions", {})

        response_text = f"📋 **Service Group Details**\n\n"
        response_text += f"**Name:** {name}\n"
        response_text += f"**Alias:** {extensions.get('alias', 'No alias')}\n"
        response_text += f"**Type:** Service Group Configuration\n\n"

        # Show links if available
        links = group_data.get("links", [])
        if links:
            response_text += "🔗 **Available Operations:**\n"
            for link in links:
                rel = link.get("rel", "").split("/")[-1] if "/" in link.get("rel", "") else link.get("rel", "")
                if rel in ["update", "delete"]:
                    response_text += f"• {rel.title()}\n"

        response_text += f"\n💡 Use 'update_service_group' or 'delete_service_group' to modify this group"

        return [{"type": "text", "text": response_text}]

    async def _update_service_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update an existing service group"""
        name = arguments.get("name")
        alias = arguments.get("alias")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        if not alias:
            return self.error_response("Missing parameter", "alias is required")

        # Check if service group exists
        try:
            existing_group = self.client.get(f"objects/service_group_config/{name}")
            if not existing_group.get("success"):
                return self.error_response("Service group not found", f"Service group '{name}' not found")
        except CheckMKNotFoundError:
            return self.error_response("Service group not found", f"Service group '{name}' not found")

        data = {"alias": alias}

        # Get ETag for If-Match header requirement
        headers = {}
        if existing_group.get("success"):
            etag_headers = existing_group.get("headers", {})
            if "ETag" in etag_headers:
                headers["If-Match"] = etag_headers["ETag"]
            else:
                # If no ETag available, use wildcard
                headers["If-Match"] = "*"

        result = self.client.put(f"objects/service_group_config/{name}", data=data, headers=headers)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Service Group Updated Successfully**\n\n"
                        f"**Name:** {name}\n"
                        f"**New Alias:** {alias}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            error_details = result.get("data", {})
            return self.error_response(
                "Service group update failed", f"Could not update service group '{name}': {error_details}"
            )

    async def _delete_service_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a service group"""
        name = arguments.get("name")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        # Check if service group exists
        try:
            existing_group = self.client.get(f"objects/service_group_config/{name}")
            if not existing_group.get("success"):
                return self.error_response("Service group not found", f"Service group '{name}' not found")
        except CheckMKNotFoundError:
            return self.error_response("Service group not found", f"Service group '{name}' not found")

        result = self.client.delete(f"objects/service_group_config/{name}")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Service Group Deleted Successfully**\n\n"
                        f"**Deleted:** {name}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            error_details = result.get("data", {})
            return self.error_response(
                "Service group deletion failed", f"Could not delete service group '{name}': {error_details}"
            )

    async def _bulk_create_service_groups(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Bulk create multiple service groups"""
        entries = arguments.get("entries", [])

        if not entries:
            return self.error_response("Missing parameter", "entries list is required")

        if not isinstance(entries, list):
            return self.error_response("Invalid parameter", "entries must be a list")

        # Validate all entries
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                return self.error_response("Invalid entry", f"Entry {i+1} must be a dictionary")

            if not entry.get("name"):
                return self.error_response("Invalid entry", f"Entry {i+1} is missing 'name'")

            if not entry.get("alias"):
                return self.error_response("Invalid entry", f"Entry {i+1} is missing 'alias'")

            if not self._validate_service_group_name(entry["name"]):
                return self.error_response(
                    "Invalid name", f"Entry {i+1}: Service group name '{entry['name']}' contains invalid characters"
                )

        data = {"entries": entries}

        result = self.client.post("domain-types/service_group_config/actions/bulk-create/invoke", data=data)

        if result.get("success"):
            created_count = len(entries)
            group_names = [entry["name"] for entry in entries]

            response_text = f"✅ **Bulk Service Groups Created Successfully**\n\n"
            response_text += f"**Created:** {created_count} service groups\n\n"
            response_text += "📋 **Created Groups:**\n"

            for entry in entries:
                response_text += f"• {entry['name']} ({entry['alias']})\n"

            response_text += f"\n⚠️ **Remember to activate changes!**"

            return [{"type": "text", "text": response_text}]
        else:
            error_details = result.get("data", {})
            return self.error_response("Bulk creation failed", f"Could not create service groups: {error_details}")

    async def _bulk_update_service_groups(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Bulk update multiple service groups"""
        entries = arguments.get("entries", [])

        if not entries:
            return self.error_response("Missing parameter", "entries list is required")

        if not isinstance(entries, list):
            return self.error_response("Invalid parameter", "entries must be a list")

        # Validate all entries
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                return self.error_response("Invalid entry", f"Entry {i+1} must be a dictionary")

            if not entry.get("name"):
                return self.error_response("Invalid entry", f"Entry {i+1} is missing 'name'")

            if not entry.get("attributes") or not entry["attributes"].get("alias"):
                return self.error_response("Invalid entry", f"Entry {i+1} is missing 'attributes.alias'")

        data = {"entries": entries}

        result = self.client.put("domain-types/service_group_config/actions/bulk-update/invoke", data=data)

        if result.get("success"):
            updated_count = len(entries)

            response_text = f"✅ **Bulk Service Groups Updated Successfully**\n\n"
            response_text += f"**Updated:** {updated_count} service groups\n\n"
            response_text += "📋 **Updated Groups:**\n"

            for entry in entries:
                alias = entry["attributes"]["alias"]
                response_text += f"• {entry['name']} → {alias}\n"

            response_text += f"\n⚠️ **Remember to activate changes!**"

            return [{"type": "text", "text": response_text}]
        else:
            error_details = result.get("data", {})
            return self.error_response("Bulk update failed", f"Could not update service groups: {error_details}")

    async def _bulk_delete_service_groups(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Bulk delete multiple service groups"""
        entries = arguments.get("entries", [])

        if not entries:
            return self.error_response("Missing parameter", "entries list is required")

        if not isinstance(entries, list):
            return self.error_response("Invalid parameter", "entries must be a list")

        # Validate all entries are strings (service group names)
        for i, entry in enumerate(entries):
            if not isinstance(entry, str):
                return self.error_response("Invalid entry", f"Entry {i+1} must be a string (service group name)")

            if not entry.strip():
                return self.error_response("Invalid entry", f"Entry {i+1} cannot be empty")

        data = {"entries": entries}

        result = self.client.post("domain-types/service_group_config/actions/bulk-delete/invoke", data=data)

        if result.get("success"):
            deleted_count = len(entries)

            response_text = f"✅ **Bulk Service Groups Deleted Successfully**\n\n"
            response_text += f"**Deleted:** {deleted_count} service groups\n\n"
            response_text += "📋 **Deleted Groups:**\n"

            for entry in entries:
                response_text += f"• {entry}\n"

            response_text += f"\n⚠️ **Remember to activate changes!**"

            return [{"type": "text", "text": response_text}]
        else:
            error_details = result.get("data", {})
            return self.error_response("Bulk deletion failed", f"Could not delete service groups: {error_details}")

    def _validate_service_group_name(self, name: str) -> bool:
        """Validate service group name format"""
        if not name:
            return False

        import re

        # CheckMK service group name pattern: letters, numbers, hyphens, underscores
        pattern = r"^[a-zA-Z0-9._-]+$"
        return re.match(pattern, name) is not None
