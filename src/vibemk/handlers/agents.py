"""
Agent bakery handlers (CheckMK CEE/Cloud only).
Provides bake, status, and download operations for the agent bakery.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlencode

from vibemk.api.exceptions import CheckMKError, CheckMKNotFoundError
from vibemk.handlers.base import BaseHandler

# The Raw/Community edition has no bakery: its endpoints answer a bare 404.
_NO_BAKERY = (
    "This CheckMK edition has no agent bakery -- it is part of the commercial editions only. "
    "On Raw/Community, install the vanilla agent from Setup > Agents > Linux / Windows."
)


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
        except CheckMKNotFoundError:
            return self.error_response("Agent bakery not available", _NO_BAKERY)
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
            # The job sits in result.value; reading the top level found no state at all.
            data = result.get("data", {})
            job = data.get("result", {}).get("value") or data
            state = job.get("state", "unknown")
            lines = ["🍞 **Agent Baking Status**\n", f"State: {state}"]
            started = job.get("started")
            if isinstance(started, (int, float)):
                lines.append(f"Started: {datetime.fromtimestamp(started, tz=timezone.utc):%Y-%m-%d %H:%M:%S} UTC")
            duration = job.get("duration")
            if isinstance(duration, (int, float)):
                lines.append(f"Duration: {duration:.1f}s")
            loginfo = job.get("loginfo", {})
            for label, key in (("Result", "JobResult"), ("Error", "JobException")):
                for line in loginfo.get(key, []):
                    lines.append(f"{label}: {line}")
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
        # agent_type=host_name asks for the agent baked for this host, not the vanilla one.
        query = urlencode({"os_type": os_type, "host_name": host_name, "agent_type": "host_name"})
        url = f"{self.client.api_base_url}/domain-types/agent/actions/download_by_host/invoke?{query}"
        return [
            {
                "type": "text",
                "text": (
                    f"📦 **Agent Download URL**\n\n"
                    f"Host: {host_name}\n"
                    f"OS type: {os_type}\n"
                    f"URL: {url}\n\n"
                    f"Use curl with your bearer token to download:\n"
                    f"  curl -H 'Authorization: Bearer USER PASS' '{url}' -o agent.{os_type}\n\n"
                    f"ℹ️ Commercial editions only; bake first with vibemk_bake_agents if the host's agent changed."
                ),
            }
        ]
