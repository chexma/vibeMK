"""
Configuration management handlers
"""

from typing import Dict, Any, List
from handlers.base import BaseHandler
from api.exceptions import CheckMKError


class ConfigurationHandler(BaseHandler):
    """Handle configuration management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle configuration-related tool calls"""

        try:
            if tool_name == "vibemk_activate_changes":
                return await self._activate_changes(arguments)
            elif tool_name == "vibemk_get_pending_changes":
                return await self._get_pending_changes()
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _activate_changes(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Activate pending configuration changes"""
        sites = arguments.get("sites", [])
        force = arguments.get("force_foreign_changes", False)

        # First, check pending changes to get current state
        pending_result = self.client.get("domain-types/activation_run/collections/pending_changes")

        if not pending_result.get("success"):
            return self.error_response("Cannot check pending changes", "Unable to verify current configuration state")

        pending_changes = pending_result["data"].get("value", [])
        if not pending_changes:
            return [
                {"type": "text", "text": "ℹ️ **No Pending Changes**\n\nThere are no configuration changes to activate."}
            ]

        # Prepare activation data
        data = {
            "redirect": False,
            "sites": sites if sites else [self.client.config.site],
            "force_foreign_changes": force,
        }

        # Use wildcard ETag to bypass precondition requirement
        headers = {"If-Match": "*"}

        # Make activation request with proper headers
        try:
            # Custom request with headers
            import urllib.request
            import json

            url = f"{self.client.api_base_url}/domain-types/activation_run/actions/activate-changes/invoke"

            # Prepare request
            req_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, method="POST")

            # Add all necessary headers
            for key, value in self.client.headers.items():
                req.add_header(key, value)
            req.add_header("If-Match", "*")  # Critical for activation!

            # Execute request
            with urllib.request.urlopen(
                req, context=self.client._ssl_context, timeout=self.client.config.timeout
            ) as response:
                response_data = response.read().decode()
                result = {
                    "status": response.status,
                    "data": json.loads(response_data) if response_data else {},
                    "success": True,
                }

        except urllib.error.HTTPError as e:
            error_data = e.read().decode()
            return self.error_response(
                f"Activation failed (HTTP {e.code})", f"Error: {e.reason}\n\nDetails: {error_data}"
            )
        except Exception as e:
            return self.error_response("Activation failed", f"Network error: {str(e)}")

        if result.get("success"):
            activation_id = result["data"].get("id", "unknown")
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Changes Activation Started Successfully**\n\n"
                        f"Activation ID: {activation_id}\n"
                        f"Sites: {', '.join(sites) if sites else self.client.config.site}\n"
                        f"Force foreign changes: {force}\n"
                        f"Changes to activate: {len(pending_changes)}\n\n"
                        f"⏳ Activation is now running...\n"
                        f"💡 Check the CheckMK GUI for progress details."
                    ),
                }
            ]
        else:
            return self.error_response("Activation failed", "Could not activate changes despite proper headers")

    async def _get_pending_changes(self) -> List[Dict[str, Any]]:
        """Get list of pending configuration changes"""
        result = self.client.get("domain-types/activation_run/collections/pending_changes")

        if not result.get("success"):
            status_code = result.get("status", "unknown")
            return self.error_response(
                f"Failed to retrieve pending changes (HTTP {status_code})", "Check CheckMK permissions and API access"
            )

        changes = result["data"].get("value", [])
        if not changes:
            return [
                {
                    "type": "text",
                    "text": (
                        "ℹ️ **No Pending Changes**\n\n"
                        "All configuration changes have been activated.\n"
                        "The CheckMK configuration is up to date."
                    ),
                }
            ]

        change_list = []
        change_summary = {"create": 0, "edit": 0, "delete": 0, "move": 0, "other": 0}

        for change in changes:
            extensions = change.get("extensions", {})
            action = extensions.get("action_name", "Unknown")
            obj_type = extensions.get("object_type", "Unknown")
            obj_name = extensions.get("object_name", "Unknown")
            user = extensions.get("user_id", "unknown")

            # Categorize changes
            if "create" in action.lower():
                change_summary["create"] += 1
                icon = "➕"
            elif "edit" in action.lower() or "update" in action.lower():
                change_summary["edit"] += 1
                icon = "📝"
            elif "delete" in action.lower():
                change_summary["delete"] += 1
                icon = "🗑️"
            elif "move" in action.lower():
                change_summary["move"] += 1
                icon = "📁"
            else:
                change_summary["other"] += 1
                icon = "⚙️"

            change_list.append(f"{icon} {action}: {obj_type} '{obj_name}' (by {user})")

        # Create summary
        summary_parts = []
        for action_type, count in change_summary.items():
            if count > 0:
                summary_parts.append(f"{action_type}: {count}")

        summary_text = ", ".join(summary_parts)

        return [
            {
                "type": "text",
                "text": (
                    f"📋 **Pending Changes** ({len(changes)} total)\n\n"
                    f"**Summary:** {summary_text}\n\n"
                    f"**Details:**\n"
                    + "\n".join(change_list[:15])
                    + (f"\n\n... and {len(changes) - 15} more changes" if len(changes) > 15 else "")
                    + "\n\n⚠️ **Use 'activate_changes' to apply these changes.**"
                ),
            }
        ]
