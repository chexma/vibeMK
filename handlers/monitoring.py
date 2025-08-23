"""
Monitoring and problem management handlers

Copyright (C) 2024 Andre <andre@example.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import urllib.parse
from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class MonitoringHandler(BaseHandler):
    """Handle monitoring and problem management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle monitoring-related tool calls"""

        try:
            if tool_name == "vibemk_get_current_problems":
                return await self._get_current_problems(arguments)
            elif tool_name == "vibemk_acknowledge_problem":
                return await self._acknowledge_problem(arguments)
            elif tool_name == "vibemk_schedule_downtime":
                return await self._schedule_downtime(arguments)
            elif tool_name == "vibemk_get_downtimes":
                return await self._get_downtimes(arguments)
            elif tool_name == "vibemk_delete_downtime":
                return await self._delete_downtime(arguments)
            elif tool_name == "vibemk_reschedule_check":
                return await self._reschedule_check(arguments)
            elif tool_name == "vibemk_get_comments":
                return await self._get_comments(arguments)
            elif tool_name == "vibemk_add_comment":
                return await self._add_comment(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _get_current_problems(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get current problems (hosts and services with issues)"""
        target_host = arguments.get("host_name")
        problems = []

        try:
            # First get list of all hosts to check their live status
            host_list_result = self.client.get("domain-types/host_config/collections/all")

            if host_list_result.get("success"):
                hosts = host_list_result["data"].get("value", [])

                # Filter to specific host if requested
                if target_host:
                    hosts = [h for h in hosts if h.get("id") == target_host]

                # Check each host's live status using the documented endpoint
                for host in hosts[:20]:  # Limit processing
                    host_name = host.get("id", "Unknown")

                    # Get live host status with columns parameter (as documented in CLAUDE.md)
                    host_status = self.client.get(
                        f"objects/host/{host_name}",
                        params={"columns": ["state", "hard_state", "state_type", "plugin_output"]},
                    )

                    if host_status.get("success"):
                        extensions = host_status["data"].get("extensions", {})
                        state = extensions.get("state", 0)
                        hard_state = extensions.get("hard_state", 0)
                        state_type = extensions.get("state_type", 0)

                        # Use hard_state if state_type = 1 (hard state), otherwise soft state
                        current_state = hard_state if state_type == 1 else state

                        # Only include hosts with problems (state != 0)
                        if current_state != 0:
                            state_name = {1: "DOWN", 2: "UNREACHABLE"}.get(current_state, f"STATE({current_state})")
                            problems.append(f"🖥️ HOST: {host_name} - {state_name}")

            # Get list of all services to check their live status
            service_list_result = self.client.get("domain-types/service/collections/all")

            if service_list_result.get("success"):
                services = service_list_result["data"].get("value", [])

                # Filter to specific host if requested
                if target_host:
                    services = [s for s in services if s.get("extensions", {}).get("host_name") == target_host]

                # Check each service's live status using the documented endpoint
                for service in services[:50]:  # Limit processing
                    service_ext = service.get("extensions", {})
                    host_name = service_ext.get("host_name", "Unknown")
                    description = service_ext.get("description", "Unknown")

                    if host_name != "Unknown" and description != "Unknown":
                        # Get live service status using show_service action (as documented in CLAUDE.md)
                        service_status = self.client.get(
                            f"objects/host/{host_name}/actions/show_service/invoke",
                            params={"service_description": description},
                        )

                        if service_status.get("success"):
                            extensions = service_status["data"].get("extensions", {})
                            state = extensions.get("state", 0)
                            state_type = extensions.get("state_type", 0)

                            # For services, use state directly (hard_state may not be available in service API)
                            current_state = state

                            # Only include services with problems (state != 0)
                            if current_state != 0:
                                state_name = {1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}.get(
                                    current_state, f"STATE({current_state})"
                                )
                                problems.append(f"🔧 SERVICE: {host_name}/{description} - {state_name}")

        except Exception as e:
            self.logger.error(f"Error getting current problems: {e}")
            return self.error_response("Error retrieving problems", str(e))

        if not problems:
            return [{"type": "text", "text": "✅ No current problems found"}]

        return [{"type": "text", "text": f"🚨 **Current Problems** ({len(problems)} total):\n\n" + "\n".join(problems)}]

    async def _acknowledge_problem(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Acknowledge a host or service problem"""
        ack_type = arguments.get("acknowledge_type")
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")
        comment = arguments.get("comment")

        if not ack_type or not host_name or not comment:
            return self.error_response("Missing parameters", "acknowledge_type, host_name, and comment are required")

        if ack_type == "host":
            data = {
                "acknowledge_type": "host",
                "host_name": host_name,
                "comment": comment,
                "sticky": True,
                "notify": True,
            }
            result = self.client.post("domain-types/acknowledge/collections/host", data=data)
            target = f"host '{host_name}'"

        elif ack_type == "service":
            if not service_description:
                return self.error_response(
                    "Missing parameter", "service_description is required for service acknowledgment"
                )

            data = {
                "acknowledge_type": "service",
                "host_name": host_name,
                "service_description": service_description,
                "comment": comment,
                "sticky": True,
                "notify": True,
            }
            result = self.client.post("domain-types/acknowledge/collections/service", data=data)
            target = f"service '{host_name}/{service_description}'"
        else:
            return self.error_response("Invalid acknowledge_type", "acknowledge_type must be 'host' or 'service'")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (f"✅ **Problem Acknowledged**\n\n" f"Target: {target}\n" f"Comment: {comment}"),
                }
            ]
        else:
            return self.error_response("Acknowledgment failed", f"Could not acknowledge {target}")

    async def _schedule_downtime(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Schedule maintenance downtime"""
        downtime_type = arguments.get("downtime_type")
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        comment = arguments.get("comment")

        if not downtime_type or not start_time or not end_time or not comment:
            return self.error_response(
                "Missing parameters", "downtime_type, start_time, end_time, and comment are required"
            )

        data = {"downtime_type": downtime_type, "start_time": start_time, "end_time": end_time, "comment": comment}

        if downtime_type == "host" and host_name:
            data["host_name"] = host_name
            target = f"host '{host_name}'"
        elif downtime_type == "service" and host_name and service_description:
            data["host_name"] = host_name
            data["service_description"] = service_description
            target = f"service '{host_name}/{service_description}'"
        else:
            return self.error_response(
                "Invalid parameters", "Invalid downtime_type or missing host/service information"
            )

        result = self.client.post("domain-types/downtime/collections/all", data=data)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"⏰ **Downtime Scheduled**\n\n"
                        f"Target: {target}\n"
                        f"Start: {start_time}\n"
                        f"End: {end_time}\n"
                        f"Comment: {comment}"
                    ),
                }
            ]
        else:
            return self.error_response("Downtime scheduling failed", f"Could not schedule downtime for {target}")

    async def _get_downtimes(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of scheduled downtimes"""
        params = {}
        if host_name := arguments.get("host_name"):
            params["host_name"] = host_name

        result = self.client.get("domain-types/downtime/collections/all", params=params)

        if not result.get("success"):
            return self.error_response("Failed to retrieve downtimes")

        downtimes = result["data"].get("value", [])
        if not downtimes:
            return [{"type": "text", "text": "ℹ️ No scheduled downtimes"}]

        downtime_list = []
        for downtime in downtimes[:20]:
            extensions = downtime.get("extensions", {})
            downtime_id = downtime.get("id", "Unknown")
            host = extensions.get("host_name", "Unknown")
            service = extensions.get("service_description", "")
            comment = extensions.get("comment", "No comment")
            start_time = extensions.get("start_time", "Unknown")
            end_time = extensions.get("end_time", "Unknown")

            target = f"{host}/{service}" if service else host
            downtime_list.append(f"⏰ ID:{downtime_id} - {target} ({start_time} - {end_time}) - {comment}")

        return [
            {
                "type": "text",
                "text": f"⏰ **Scheduled Downtimes** ({len(downtimes)} total):\n\n" + "\n".join(downtime_list),
            }
        ]

    async def _delete_downtime(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a scheduled downtime"""
        downtime_id = arguments.get("downtime_id")

        if not downtime_id:
            return self.error_response("Missing parameter", "downtime_id is required")

        result = self.client.delete(f"objects/downtime/{downtime_id}")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": f"✅ **Downtime Deleted**\n\nDowntime ID: {downtime_id}\nThe downtime has been removed.",
                }
            ]
        else:
            return self.error_response("Downtime deletion failed", f"Could not delete downtime '{downtime_id}'")

    async def _reschedule_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Force immediate check execution"""
        check_type = arguments.get("check_type")
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")

        if not check_type or not host_name:
            return self.error_response("Missing parameters", "check_type and host_name are required")

        if check_type == "host":
            # Host check reschedule
            data = {"host_name": host_name}
            result = self.client.post(f"objects/host/{host_name}/actions/reschedule_check/invoke", data=data)
            target = f"host '{host_name}'"
        elif check_type == "service":
            if not service_description:
                return self.error_response("Missing parameter", "service_description is required for service checks")
            data = {"host_name": host_name, "service_description": service_description}
            # URL-encode the service description to handle spaces and special characters
            encoded_service = urllib.parse.quote(service_description, safe="")
            result = self.client.post(
                f"objects/service/{host_name}/{encoded_service}/actions/reschedule_check/invoke", data=data
            )
            target = f"service '{host_name}/{service_description}'"
        else:
            return self.error_response("Invalid check_type", "check_type must be 'host' or 'service'")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": f"🔄 **Check Rescheduled**\n\nTarget: {target}\nImmediate check has been scheduled.",
                }
            ]
        else:
            return self.error_response("Check reschedule failed", f"Could not reschedule check for {target}")

    async def _get_comments(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of comments"""
        params = {}
        if host_name := arguments.get("host_name"):
            params["host_name"] = host_name
        if service_description := arguments.get("service_description"):
            params["service_description"] = service_description

        # Try host comments
        host_result = self.client.get("domain-types/comment/collections/host", params=params)
        service_result = self.client.get("domain-types/comment/collections/service", params=params)

        comments = []

        if host_result.get("success"):
            host_comments = host_result["data"].get("value", [])
            for comment in host_comments:
                extensions = comment.get("extensions", {})
                comment_id = comment.get("id", "Unknown")
                host = extensions.get("host_name", "Unknown")
                comment_text = extensions.get("comment", "No comment")
                author = extensions.get("author", "Unknown")
                comments.append(f"💬 HOST:{comment_id} - {host} - {comment_text} (by {author})")

        if service_result.get("success"):
            service_comments = service_result["data"].get("value", [])
            for comment in service_comments:
                extensions = comment.get("extensions", {})
                comment_id = comment.get("id", "Unknown")
                host = extensions.get("host_name", "Unknown")
                service = extensions.get("service_description", "Unknown")
                comment_text = extensions.get("comment", "No comment")
                author = extensions.get("author", "Unknown")
                comments.append(f"💬 SERVICE:{comment_id} - {host}/{service} - {comment_text} (by {author})")

        if not comments:
            return [{"type": "text", "text": "💬 No comments found"}]

        return [{"type": "text", "text": f"💬 **Comments** ({len(comments)} total):\n\n" + "\n".join(comments[:20])}]

    async def _add_comment(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add comment to host or service"""
        comment_type = arguments.get("comment_type")
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")
        comment = arguments.get("comment")
        persistent = arguments.get("persistent", True)

        if not comment_type or not host_name or not comment:
            return self.error_response("Missing parameters", "comment_type, host_name, and comment are required")

        data = {"host_name": host_name, "comment": comment, "persistent": persistent}

        if comment_type == "host":
            result = self.client.post("domain-types/comment/collections/host", data=data)
            target = f"host '{host_name}'"
        elif comment_type == "service":
            if not service_description:
                return self.error_response("Missing parameter", "service_description is required for service comments")
            data["service_description"] = service_description
            result = self.client.post("domain-types/comment/collections/service", data=data)
            target = f"service '{host_name}/{service_description}'"
        else:
            return self.error_response("Invalid comment_type", "comment_type must be 'host' or 'service'")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"💬 **Comment Added**\n\n"
                        f"Target: {target}\n"
                        f"Comment: {comment}\n"
                        f"Persistent: {persistent}"
                    ),
                }
            ]
        else:
            return self.error_response("Comment creation failed", f"Could not add comment to {target}")
