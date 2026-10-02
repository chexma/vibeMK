"""
Event Console handlers — read and manage CheckMK Event Console (EC) events.
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler

# The Event Console's numeric states. A constant rather than a local, which is
# what it was: a fixed lookup table rebuilt on every call.
_STATE = {0: "OK", 1: "⚠️ WARN", 2: "🔴 CRIT", 3: "❓ UNKNOWN"}


class EventConsoleHandler(BaseHandler):
    """Handle Event Console operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            if tool_name == "vibemk_get_events":
                result = await self._get_events(arguments)
            elif tool_name == "vibemk_acknowledge_event":
                result = await self._acknowledge_event(arguments)
            elif tool_name == "vibemk_change_event_state":
                result = await self._change_event_state(arguments)
            elif tool_name == "vibemk_delete_events":
                result = await self._delete_events(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

        return result

    async def _get_events(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if phase := arguments.get("phase"):
            params["phase"] = phase
        if state := arguments.get("state"):
            params["state"] = state
        if host := arguments.get("host"):
            params["host"] = host
        if application := arguments.get("application"):
            params["application"] = application
        if site_id := arguments.get("site_id"):
            params["site_id"] = site_id

        result = self.client.get("domain-types/event_console/collections/all", params=params)
        if not result.get("success"):
            return self.error_response("EC-Events konnten nicht abgerufen werden")

        events = result["data"].get("value", [])
        if not events:
            return [{"type": "text", "text": "📭 Keine Event-Console-Events gefunden."}]

        lines = [f"🗃️ **Event Console — {len(events)} Events**\n"]
        for ev in events[:50]:
            ext = ev.get("extensions", ev)
            eid = ev.get("id", ext.get("id", "?"))
            host_name = ext.get("host", "?")
            app = ext.get("application", "")
            text = ext.get("text", "")
            phase_val = ext.get("phase", "?")
            state_val = ext.get("state", 0)
            state_label = _STATE.get(state_val, str(state_val))
            lines.append(
                f"• **{eid}** [{state_label}] [{phase_val}] `{host_name}`"
                + (f" — {app}" if app else "")
                + (f"\n  {text[:200]}" if text else "")
            )

        if len(events) > 50:
            lines.append(f"\n…und {len(events) - 50} weitere Events.")
        return [{"type": "text", "text": "\n".join(lines)}]

    async def _acknowledge_event(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        event_id = arguments.get("event_id")
        comment = arguments.get("comment", "Acknowledged via vibeMK")

        if not event_id:
            return self.error_response("Missing parameter", "event_id is required")

        result = self.client.post(
            f"objects/event_console/{event_id}/actions/update_and_acknowledge/invoke",
            {"change_comment": comment},
        )
        if result.get("success"):
            return [{"type": "text", "text": f"✅ Event {event_id} wurde quittiert."}]
        return self.error_response("Quittierung fehlgeschlagen", str(result.get("data", {})))

    async def _change_event_state(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        event_id = arguments.get("event_id")
        new_state = arguments.get("new_state")

        if not event_id or new_state is None:
            return self.error_response("Missing parameter", "event_id and new_state are required")

        result = self.client.post(
            f"objects/event_console/{event_id}/actions/change_state/invoke",
            {"new_state": new_state},
        )
        if result.get("success"):
            return [{"type": "text", "text": f"✅ Event {event_id}: Status auf '{new_state}' gesetzt."}]
        return self.error_response("Statusänderung fehlgeschlagen", str(result.get("data", {})))

    async def _delete_events(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        event_ids = arguments.get("event_ids")

        if event_ids:
            result = self.client.post(
                "domain-types/event_console/actions/delete/invoke",
                {"event_ids": event_ids},
            )
        else:
            phase = arguments.get("phase", "open")
            host = arguments.get("host")
            body: Dict[str, Any] = {"phase": phase}
            if host:
                body["host"] = host
            result = self.client.post(
                "domain-types/event_console/actions/delete/invoke",
                body,
            )

        if result.get("success"):
            count = len(event_ids) if event_ids else "alle"
            return [{"type": "text", "text": f"✅ {count} Event(s) gelöscht."}]
        return self.error_response("Löschen fehlgeschlagen", str(result.get("data", {})))
