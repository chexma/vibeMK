"""
Tag group management handlers for CheckMK host and service tags
"""

from typing import Dict, Any, List
from handlers.base import BaseHandler
from api.exceptions import CheckMKError


class TagsHandler(BaseHandler):
    """Handle tag group management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle tag-related tool calls"""

        try:
            if tool_name == "vibemk_get_host_tags":
                return await self._get_host_tags(arguments)
            elif tool_name == "vibemk_create_host_tag":
                return await self._create_host_tag(arguments)
            elif tool_name == "vibemk_update_host_tag":
                return await self._update_host_tag(arguments)
            elif tool_name == "vibemk_delete_host_tag":
                return await self._delete_host_tag(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _get_host_tags(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of host tag groups"""
        result = self.client.get("domain-types/host_tag_group/collections/all")

        if not result.get("success"):
            return self.error_response("Failed to retrieve host tag groups")

        tag_groups = result["data"].get("value", [])
        if not tag_groups:
            return [{"type": "text", "text": "🏷️ **No Host Tag Groups Found**\n\nNo host tag groups are configured."}]

        tag_list = []
        for tag_group in tag_groups:
            group_id = tag_group.get("id", "Unknown")
            extensions = tag_group.get("extensions", {})
            title = extensions.get("title", group_id)
            tags = extensions.get("tags", [])

            tag_names = [tag.get("title", tag.get("id", "Unknown")) for tag in tags[:3]]
            tag_preview = ", ".join(tag_names)
            if len(tags) > 3:
                tag_preview += f", ... (+{len(tags) - 3} more)"

            tag_list.append(f"🏷️ **{group_id}** - {title}\n   Tags: {tag_preview}\n   Total: {len(tags)} tags")

        return [
            {"type": "text", "text": f"🏷️ **Host Tag Groups** ({len(tag_groups)} total):\n\n" + "\n\n".join(tag_list)}
        ]

    async def _create_host_tag(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new host tag group"""
        tag_id = arguments.get("tag_id")
        title = arguments.get("title")
        topic = arguments.get("topic", "")
        tags = arguments.get("tags", [])
        help_text = arguments.get("help", "")

        if not tag_id or not title:
            return self.error_response("Missing parameters", "tag_id and title are required")

        if not tags:
            return self.error_response("Missing parameter", "tags list is required (at least one tag)")

        # Validate tag structure
        for tag in tags:
            if not isinstance(tag, dict) or "id" not in tag or "title" not in tag:
                return self.error_response("Invalid tag structure", "Each tag must have 'id' and 'title' fields")

        data = {"ident": tag_id, "title": title, "tags": tags}

        if topic:
            data["topic"] = topic
        if help_text:
            data["help"] = help_text

        result = self.client.post("domain-types/host_tag_group/collections/all", data=data)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Host Tag Group Created Successfully**\n\n"
                        f"Tag ID: {tag_id}\n"
                        f"Title: {title}\n"
                        f"Topic: {topic or 'None'}\n"
                        f"Tags: {len(tags)} configured\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("Host tag group creation failed", f"Could not create tag group '{tag_id}'")

    async def _update_host_tag(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update an existing host tag group"""
        tag_id = arguments.get("tag_id")
        title = arguments.get("title")
        topic = arguments.get("topic")
        tags = arguments.get("tags")
        help_text = arguments.get("help")
        repair = arguments.get("repair", False)

        if not tag_id:
            return self.error_response("Missing parameter", "tag_id is required")

        # First check if tag group exists
        check_result = self.client.get(f"objects/host_tag_group/{tag_id}")
        if not check_result.get("success"):
            return self.error_response("Host tag group not found", f"Tag group '{tag_id}' does not exist")

        # Build update data
        data = {}
        if title:
            data["title"] = title
        if topic is not None:
            data["topic"] = topic
        if tags:
            # Validate tag structure
            for tag in tags:
                if not isinstance(tag, dict) or "id" not in tag or "title" not in tag:
                    return self.error_response("Invalid tag structure", "Each tag must have 'id' and 'title' fields")
            data["tags"] = tags
        if help_text is not None:
            data["help"] = help_text
        if repair:
            data["repair"] = repair

        if not data:
            return self.error_response("No data to update", "At least one field must be provided")

        # Use ETag for optimistic locking
        headers = {"If-Match": "*"}
        result = self.client.put(f"objects/host_tag_group/{tag_id}", data=data, headers=headers)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Host Tag Group Updated Successfully**\n\n"
                        f"Tag ID: {tag_id}\n"
                        f"Updated fields: {', '.join(data.keys())}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("Host tag group update failed", f"Could not update tag group '{tag_id}'")

    async def _delete_host_tag(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a host tag group"""
        tag_id = arguments.get("tag_id")
        repair = arguments.get("repair", False)

        if not tag_id:
            return self.error_response("Missing parameter", "tag_id is required")

        # Check if tag group exists
        check_result = self.client.get(f"objects/host_tag_group/{tag_id}")
        if not check_result.get("success"):
            return self.error_response("Host tag group not found", f"Tag group '{tag_id}' does not exist")

        params = {}
        if repair:
            params["repair"] = "true"

        result = self.client.delete(f"objects/host_tag_group/{tag_id}", params=params)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Host Tag Group Deleted Successfully**\n\n"
                        f"Tag ID: {tag_id}\n"
                        f"Repair mode: {'Enabled' if repair else 'Disabled'}\n\n"
                        f"📝 **Next Steps:**\n"
                        f"1️⃣ Use 'get_pending_changes' to review the deletion\n"
                        f"2️⃣ Use 'activate_changes' to apply the configuration\n\n"
                        f"💡 **Important:** The tag group is only marked for deletion until you activate changes!"
                    ),
                }
            ]
        else:
            return self.error_response("Host tag group deletion failed", f"Could not delete tag group '{tag_id}'")
