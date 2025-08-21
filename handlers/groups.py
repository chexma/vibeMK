"""
Host and service group management handlers
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class GroupsHandler(BaseHandler):
    """Handle host and service group management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle group-related tool calls"""

        try:
            # Host groups
            if tool_name == "vibemk_get_host_groups":
                return await self._get_host_groups(arguments)
            elif tool_name == "vibemk_create_host_group":
                return await self._create_host_group(arguments)
            elif tool_name == "vibemk_update_host_group":
                return await self._update_host_group(arguments)
            elif tool_name == "vibemk_delete_host_group":
                return await self._delete_host_group(arguments)
            # Service groups
            elif tool_name == "vibemk_get_service_groups":
                return await self._get_service_groups(arguments)
            elif tool_name == "vibemk_create_service_group":
                return await self._create_service_group(arguments)
            elif tool_name == "vibemk_update_service_group":
                return await self._update_service_group(arguments)
            elif tool_name == "vibemk_delete_service_group":
                return await self._delete_service_group(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    # Host Groups Management
    async def _get_host_groups(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of CheckMK host groups"""
        result = self.client.get("domain-types/host_group_config/collections/all")

        if not result.get("success"):
            return self.error_response("Failed to retrieve host groups")

        groups = result["data"].get("value", [])
        if not groups:
            return [{"type": "text", "text": "🏠 **No Host Groups Found**\n\nNo host groups are configured."}]

        group_list = []
        for group in groups:
            group_id = group.get("id", "Unknown")
            extensions = group.get("extensions", {})
            alias = extensions.get("alias", group_id)

            group_list.append(f"🏠 **{group_id}** - {alias}")

        return [{"type": "text", "text": f"🏠 **Host Groups** ({len(groups)} total):\n\n" + "\n".join(group_list)}]

    async def _create_host_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new host group"""
        name = arguments.get("name")
        alias = arguments.get("alias")

        if not name or not alias:
            return self.error_response("Missing parameters", "name and alias are required")

        # CheckMK API structure for host groups
        data = {"name": name, "alias": alias}

        result = self.client.post("domain-types/host_group_config/collections/all", data=data)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Host Group Created Successfully**\n\n"
                        f"Name: {name}\n"
                        f"Alias: {alias}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("Host group creation failed", f"Could not create host group '{name}'")

    async def _update_host_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update an existing host group"""
        name = arguments.get("name")
        alias = arguments.get("alias")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        # First get the current host group to check if it exists
        current_group_result = self.client.get(f"objects/host_group_config/{name}")
        if not current_group_result.get("success"):
            return self.error_response("Host group not found", f"Host group '{name}' does not exist")

        # Build update data for group
        data = {}
        if alias:
            data["alias"] = alias

        if not data:
            return self.error_response("No data to update", "At least one field (alias) must be provided")

        # Use ETag for optimistic locking
        headers = {"If-Match": "*"}
        result = self.client.put(f"objects/host_group_config/{name}", data=data, headers=headers)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Host Group Updated Successfully**\n\n"
                        f"Name: {name}\n"
                        f"Updated fields: {', '.join(data.keys())}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("Host group update failed", f"Could not update host group '{name}'")

    async def _delete_host_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a host group"""
        name = arguments.get("name")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        # Check if host group exists
        check_result = self.client.get(f"objects/host_group_config/{name}")
        if not check_result.get("success"):
            return self.error_response("Host group not found", f"Host group '{name}' does not exist")

        result = self.client.delete(f"objects/host_group_config/{name}")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Host Group Deleted Successfully**\n\n"
                        f"Name: {name}\n\n"
                        f"📝 **Next Steps:**\n"
                        f"1️⃣ Use 'get_pending_changes' to review the deletion\n"
                        f"2️⃣ Use 'activate_changes' to apply the configuration\n\n"
                        f"💡 **Important:** The host group is only marked for deletion until you activate changes!"
                    ),
                }
            ]
        else:
            return self.error_response("Host group deletion failed", f"Could not delete host group '{name}'")

    # Service Groups Management
    async def _get_service_groups(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of CheckMK service groups"""
        result = self.client.get("domain-types/service_group_config/collections/all")

        if not result.get("success"):
            return self.error_response("Failed to retrieve service groups")

        groups = result["data"].get("value", [])
        if not groups:
            return [{"type": "text", "text": "🔧 **No Service Groups Found**\n\nNo service groups are configured."}]

        group_list = []
        for group in groups:
            group_id = group.get("id", "Unknown")
            extensions = group.get("extensions", {})
            alias = extensions.get("alias", group_id)

            group_list.append(f"🔧 **{group_id}** - {alias}")

        return [{"type": "text", "text": f"🔧 **Service Groups** ({len(groups)} total):\n\n" + "\n".join(group_list)}]

    async def _create_service_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new service group"""
        name = arguments.get("name")
        alias = arguments.get("alias")

        if not name or not alias:
            return self.error_response("Missing parameters", "name and alias are required")

        # CheckMK API structure for service groups
        data = {"name": name, "alias": alias}

        result = self.client.post("domain-types/service_group_config/collections/all", data=data)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Service Group Created Successfully**\n\n"
                        f"Name: {name}\n"
                        f"Alias: {alias}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("Service group creation failed", f"Could not create service group '{name}'")

    async def _update_service_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update an existing service group"""
        name = arguments.get("name")
        alias = arguments.get("alias")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        # First get the current service group to check if it exists
        current_group_result = self.client.get(f"objects/service_group_config/{name}")
        if not current_group_result.get("success"):
            return self.error_response("Service group not found", f"Service group '{name}' does not exist")

        # Build update data for group
        data = {}
        if alias:
            data["alias"] = alias

        if not data:
            return self.error_response("No data to update", "At least one field (alias) must be provided")

        # Use ETag for optimistic locking
        headers = {"If-Match": "*"}
        result = self.client.put(f"objects/service_group_config/{name}", data=data, headers=headers)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Service Group Updated Successfully**\n\n"
                        f"Name: {name}\n"
                        f"Updated fields: {', '.join(data.keys())}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("Service group update failed", f"Could not update service group '{name}'")

    async def _delete_service_group(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a service group"""
        name = arguments.get("name")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        # Check if service group exists
        check_result = self.client.get(f"objects/service_group_config/{name}")
        if not check_result.get("success"):
            return self.error_response("Service group not found", f"Service group '{name}' does not exist")

        result = self.client.delete(f"objects/service_group_config/{name}")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Service Group Deleted Successfully**\n\n"
                        f"Name: {name}\n\n"
                        f"📝 **Next Steps:**\n"
                        f"1️⃣ Use 'get_pending_changes' to review the deletion\n"
                        f"2️⃣ Use 'activate_changes' to apply the configuration\n\n"
                        f"💡 **Important:** The service group is only marked for deletion until you activate changes!"
                    ),
                }
            ]
        else:
            return self.error_response("Service group deletion failed", f"Could not delete service group '{name}'")
