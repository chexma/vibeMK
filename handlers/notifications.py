"""
Notification rule handlers for CheckMK

Endpoints follow cmk/gui/openapi/endpoints/notification_rules as of CheckMK
2.4: the collection is read and created at
domain-types/notification_rule/collections/all, a single rule lives at
objects/notification_rule/{rule_id}, and deletion is modelled as a POST
action rather than an HTTP DELETE. None of them declares an ETag, so no
If-Match is required.
"""

import json
from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler

COLLECTION = "domain-types/notification_rule/collections/all"


def _object(rule_id: str) -> str:
    return f"objects/notification_rule/{rule_id}"


class NotificationHandler(BaseHandler):
    """Handle notification rule operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle notification-related tool calls"""
        try:
            if tool_name == "vibemk_get_notification_rules":
                return await self._list_rules()
            if tool_name == "vibemk_get_notification_rule":
                return await self._show_rule(arguments)
            if tool_name == "vibemk_create_notification_rule":
                return await self._create_rule(arguments)
            if tool_name == "vibemk_update_notification_rule":
                return await self._update_rule(arguments)
            if tool_name == "vibemk_delete_notification_rule":
                return await self._delete_rule(arguments)
            return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception("Error in %s", tool_name)
            return self.error_response("Unexpected Error", str(e))

    async def _list_rules(self) -> List[Dict[str, Any]]:
        result = self.client.get(COLLECTION)
        if not result.get("success"):
            return self.error_response("Failed to retrieve notification rules", str(result.get("data")))

        rules = result.get("data", {}).get("value", [])
        if not rules:
            return self.info_response(
                "No notification rules configured",
                {"hint": "CheckMK falls back to its built-in notification behaviour"},
            )

        lines = [f"📢 **Notification Rules** ({len(rules)})", ""]
        for rule in rules:
            config = rule.get("extensions", {}).get("rule_config", {})
            description = config.get("description") or "(no description)"
            state = "disabled" if config.get("disabled") else "enabled"
            plugin = config.get("notification_method", {}).get("notify_plugin", {}).get("option", "unknown")
            lines.append(f"• **{description}** — id `{rule.get('id', '?')}`, {state}, via `{plugin}`")

        return [{"type": "text", "text": "\n".join(lines)}]

    async def _show_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        rule_id = arguments.get("rule_id")
        if not rule_id:
            return self.error_response("Missing parameter", "rule_id is required")

        result = self.client.get(_object(rule_id))
        if not result.get("success"):
            return self.error_response(f"Failed to retrieve notification rule '{rule_id}'", str(result.get("data")))

        config = result.get("data", {}).get("extensions", {}).get("rule_config", {})
        description = config.get("description") or "(no description)"
        return [
            {
                "type": "text",
                "text": (
                    f"📢 **Notification Rule `{rule_id}`**\n\n"
                    f"Description: {description}\n\n"
                    f"Full rule_config — reuse this structure when creating or updating a rule:\n\n"
                    f"```json\n{self._as_json(config)}\n```"
                ),
            }
        ]

    async def _create_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        rule_config = arguments.get("rule_config")
        if not rule_config:
            return self.error_response("Missing parameter", "rule_config is required")

        result = self.client.post(COLLECTION, data={"rule_config": rule_config})
        if not result.get("success"):
            return self.error_response("Failed to create notification rule", str(result.get("data")))

        rule_id = result.get("data", {}).get("id", "unknown")
        return self.success_response(
            "Notification rule created",
            {"rule_id": rule_id, "next step": "activate changes to apply it"},
        )

    async def _update_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        rule_id = arguments.get("rule_id")
        rule_config = arguments.get("rule_config")
        if not rule_id:
            return self.error_response("Missing parameter", "rule_id is required")
        if not rule_config:
            return self.error_response("Missing parameter", "rule_config is required")

        result = self.client.put(_object(rule_id), data={"rule_config": rule_config})
        if not result.get("success"):
            return self.error_response(f"Failed to update notification rule '{rule_id}'", str(result.get("data")))

        return self.success_response(
            f"Notification rule '{rule_id}' updated",
            {"next step": "activate changes to apply it"},
        )

    async def _delete_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        rule_id = arguments.get("rule_id")
        if not rule_id:
            return self.error_response("Missing parameter", "rule_id is required")

        # CheckMK models deletion as an action, not as an HTTP DELETE.
        result = self.client.post(f"{_object(rule_id)}/actions/delete/invoke")
        if not result.get("success"):
            return self.error_response(f"Failed to delete notification rule '{rule_id}'", str(result.get("data")))

        return self.success_response(
            f"Notification rule '{rule_id}' deleted",
            {"next step": "activate changes to apply it"},
        )

    @staticmethod
    def _as_json(value: Any) -> str:
        return json.dumps(value, indent=2, ensure_ascii=False)
