"""
Auxiliary tag management handlers.
Aux tags are simple labels that can be automatically assigned to hosts
based on their tag group memberships.
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class AuxTagsHandler(BaseHandler):
    """Handle auxiliary tag CRUD"""

    _WRITE_TOOLS = frozenset({
        "vibemk_create_aux_tag", "vibemk_update_aux_tag", "vibemk_delete_aux_tag",
    })

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            if tool_name == "vibemk_get_aux_tags":
                result = await self._get_aux_tags(arguments)
            elif tool_name == "vibemk_create_aux_tag":
                result = await self._create_aux_tag(arguments)
            elif tool_name == "vibemk_update_aux_tag":
                result = await self._update_aux_tag(arguments)
            elif tool_name == "vibemk_delete_aux_tag":
                result = await self._delete_aux_tag(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

        if (tool_name in self._WRITE_TOOLS
                and arguments.get("activate_changes")
                and result
                and "❌" not in result[-1].get("text", "")):
            result[-1]["text"] += "\n" + self._run_activation()
        return result

    async def _get_aux_tags(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = self.client.get("domain-types/aux_tag/collections/all")
        if not result.get("success"):
            return self.error_response("Aux-Tags konnten nicht abgerufen werden")

        tags = result["data"].get("value", [])
        if not tags:
            return [{"type": "text", "text": "🏷️ Keine Aux-Tags vorhanden."}]

        lines = [f"🏷️ **Aux Tags ({len(tags)})**\n"]
        for tag in tags:
            tag_id = tag.get("id", "?")
            title = tag.get("title", "")
            ext = tag.get("extensions", {})
            topic = ext.get("topic", "")
            lines.append(f"• **{tag_id}** — {title}" + (f" [{topic}]" if topic else ""))

        return [{"type": "text", "text": "\n".join(lines)}]

    async def _create_aux_tag(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        tag_id = arguments.get("tag_id", "")
        title = arguments.get("title", "")
        topic = arguments.get("topic", "")
        help_text = arguments.get("help", "")

        if not tag_id or not title:
            return self.error_response("Missing parameter", "tag_id and title are required")

        body: Dict[str, Any] = {"aux_tag_id": tag_id, "title": title}
        if topic:
            body["topic"] = topic
        if help_text:
            body["help"] = help_text

        result = self.client.post("domain-types/aux_tag/collections/all", body)
        if result.get("success"):
            return [{"type": "text", "text": f"✅ Aux-Tag '{tag_id}' ({title}) angelegt."}]
        return self.error_response("Aux-Tag anlegen fehlgeschlagen", str(result.get("data", {})))

    async def _update_aux_tag(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        tag_id = arguments.get("tag_id", "")
        if not tag_id:
            return self.error_response("Missing parameter", "tag_id is required")

        body: Dict[str, Any] = {}
        if title := arguments.get("title"):
            body["title"] = title
        if topic := arguments.get("topic"):
            body["topic"] = topic
        if help_text := arguments.get("help"):
            body["help"] = help_text

        if not body:
            return self.error_response("Missing parameter", "At least one field to update is required")

        result = self.client.put(f"objects/aux_tag/{tag_id}", body)
        if result.get("success"):
            return [{"type": "text", "text": f"✅ Aux-Tag '{tag_id}' aktualisiert."}]
        return self.error_response("Aux-Tag aktualisieren fehlgeschlagen", str(result.get("data", {})))

    async def _delete_aux_tag(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        tag_id = arguments.get("tag_id", "")
        if not tag_id:
            return self.error_response("Missing parameter", "tag_id is required")

        result = self.client.post(f"objects/aux_tag/{tag_id}/actions/delete/invoke", {})
        if result.get("success"):
            return [{"type": "text", "text": f"✅ Aux-Tag '{tag_id}' gelöscht."}]
        return self.error_response("Aux-Tag löschen fehlgeschlagen", str(result.get("data", {})))
