"""
Agent bakery handlers (CheckMK CEE/Cloud only).
Provides bake, status, and download operations for the agent bakery.
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class AgentHandler(BaseHandler):
    """Handle agent bakery operations (CEE/Cloud edition only)."""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            if tool_name == "vibemk_bake_agents":
                return await self._bake_agents()
            elif tool_name == "vibemk_baking_status":
                return await self._baking_status()
            elif tool_name == "vibemk_download_agent_by_host":
                return await self._download_agent_by_host(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")
        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _bake_agents(self) -> List[Dict[str, Any]]:
        """Trigger agent baking for all hosts (CEE/Cloud only)."""
        result = self.client.post("domain-types/agent/actions/bake/invoke")
        if result.get("success"):
            return [
                {"type": "text", "text": "🍞 **Agent Baking Started**\n\nUse vibemk_baking_status to check progress."}
            ]
        detail = result.get("data", {})
        return self.error_response("Agent baking failed", str(detail))

    async def _baking_status(self) -> List[Dict[str, Any]]:
        """Get current agent baking status."""
        result = self.client.get("domain-types/agent/actions/baking_status/invoke")
        if result.get("success"):
            data = result["data"]
            state = data.get("state", "unknown")
            started = data.get("started", "")
            finished = data.get("finished", "")
            lines = [
                "🍞 **Agent Baking Status**\n",
                f"State: {state}",
            ]
            if started:
                lines.append(f"Started: {started}")
            if finished:
                lines.append(f"Finished: {finished}")
            return [{"type": "text", "text": "\n".join(lines)}]
        detail = result.get("data", {})
        return self.error_response("Baking status failed", str(detail))

    async def _download_agent_by_host(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return the download URL for the agent package of a specific host."""
        host_name = arguments.get("host_name")
        os_type = arguments.get("os_type", "linux_deb")

        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        # The API returns the binary directly — we can only return the URL for the caller to fetch.
        url = f"{self.client.api_base_url}/objects/agent/download_by_host" f"?os_type={os_type}&host_name={host_name}"
        return [
            {
                "type": "text",
                "text": (
                    f"📦 **Agent Download URL**\n\n"
                    f"Host: {host_name}\n"
                    f"OS type: {os_type}\n"
                    f"URL: {url}\n\n"
                    f"Use curl with your bearer token to download:\n"
                    f"  curl -H 'Authorization: Bearer USER PASS' '{url}' -o agent.{os_type}"
                ),
            }
        ]
