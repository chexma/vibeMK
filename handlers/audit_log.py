"""
Audit log handler — read CheckMK configuration change history.
"""

import datetime
from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class AuditLogHandler(BaseHandler):
    """Handle audit log queries"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            if tool_name == "vibemk_get_audit_log":
                result = await self._get_audit_log(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

        return result

    async def _get_audit_log(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        date = arguments.get("date") or datetime.date.today().isoformat()
        object_type = arguments.get("object_type")
        object_id = arguments.get("object_id")
        user_id = arguments.get("user_id")
        regexp = arguments.get("regexp")
        limit = int(arguments.get("limit", 50))

        params: Dict[str, Any] = {"date": date}
        if object_type:
            params["object_type"] = object_type
        if object_id:
            params["object_id"] = object_id
        if user_id:
            params["user_id"] = user_id
        if regexp:
            params["regexp"] = regexp

        result = self.client.get("domain-types/audit_log/collections/all", params=params)
        if not result.get("success"):
            return self.error_response("Could not retrieve the audit log")

        entries = result["data"].get("value", [])
        if not entries:
            return [{"type": "text", "text": f"📋 No audit log entries for {date}."}]

        lines = [f"📋 **Audit Log — {date} ({len(entries)} entries)**\n"]
        for entry in entries[:limit]:
            ext = entry.get("extensions", {})
            time_ts = ext.get("time", 0)
            time_str = datetime.datetime.fromtimestamp(time_ts).strftime("%H:%M:%S") if time_ts else "?"
            user = ext.get("user_id", "?")
            action = ext.get("action", "?")
            obj_type = ext.get("object_type", "")
            obj_name = ext.get("object_name", "")
            title = entry.get("title", "")
            lines.append(
                f"• `{time_str}` **{user}** — {action}"
                + (f" [{obj_type}: {obj_name}]" if obj_type else "")
                + (f"\n  {title}" if title else "")
            )

        if len(entries) > limit:
            lines.append(f"\n…{len(entries) - limit} more entries (raise limit to see them).")
        return [{"type": "text", "text": "\n".join(lines)}]
