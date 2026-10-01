"""
Site management handlers — list and manage distributed CheckMK site connections.
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class SitesHandler(BaseHandler):
    """Handle monitoring site management"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            if tool_name == "vibemk_get_sites":
                result = await self._get_sites(arguments)
            elif tool_name == "vibemk_login_site":
                result = await self._login_site(arguments)
            elif tool_name == "vibemk_logout_site":
                result = await self._logout_site(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

        return result

    async def _get_sites(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = self.client.get("domain-types/site_connection/collections/all")
        if not result.get("success"):
            return self.error_response("Sites konnten nicht abgerufen werden")

        sites = result["data"].get("value", [])
        if not sites:
            return [{"type": "text", "text": "🌐 Keine Sites gefunden."}]

        lines = [f"🌐 **Monitoring Sites ({len(sites)})**\n"]
        for site in sites:
            site_id = site.get("id", "?")
            title = site.get("title", "")
            ext = site.get("extensions", {})
            basic = ext.get("basic_settings", {})
            alias = basic.get("alias", title)
            logged_in = ext.get("logged_in", False)
            cfg = ext.get("configuration_connection", {})
            url = cfg.get("url_of_remote_site", "")
            replication = cfg.get("enable_replication", False)
            status = "🟢 connected" if logged_in else "🔴 not connected"
            lines.append(
                f"• **{site_id}** — {alias} [{status}]"
                + (f"\n  URL: {url}" if url else "")
                + (f"\n  Replication: {'enabled' if replication else 'disabled'}")
            )

        return [{"type": "text", "text": "\n".join(lines)}]

    async def _login_site(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        site_id = arguments.get("site_id", "")
        username = arguments.get("username", "")
        password = arguments.get("password", "")

        if not site_id or not username or not password:
            return self.error_response("Missing parameter", "site_id, username and password are required")

        result = self.client.post(
            f"objects/site_connection/{site_id}/actions/login/invoke",
            {"username": username, "password": password},
        )
        if result.get("success"):
            return [{"type": "text", "text": f"✅ Login auf Site '{site_id}' erfolgreich."}]
        return self.error_response("Login fehlgeschlagen", str(result.get("data", {})))

    async def _logout_site(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        site_id = arguments.get("site_id", "")
        if not site_id:
            return self.error_response("Missing parameter", "site_id is required")

        result = self.client.post(
            f"objects/site_connection/{site_id}/actions/logout/invoke", {}
        )
        if result.get("success"):
            return [{"type": "text", "text": f"✅ Logout von Site '{site_id}' erfolgreich."}]
        return self.error_response("Logout fehlgeschlagen", str(result.get("data", {})))
