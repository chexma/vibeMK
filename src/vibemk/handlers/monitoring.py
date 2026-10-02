"""
Monitoring and problem management handlers

Copyright (C) 2024 Andre <chexma@gmx.de>

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

from datetime import datetime, timezone
from typing import Any, Dict, List

from vibemk.api.exceptions import CheckMKError
from vibemk.handlers.base import BaseHandler
from vibemk.handlers.downtimes import downtime_record


def _handling(extensions: Dict[str, Any]) -> Dict[str, bool]:
    """Whether someone already deals with a problem: acknowledged, or inside a downtime."""
    return {
        "acknowledged": bool(extensions.get("acknowledged")),
        "in_downtime": bool(extensions.get("scheduled_downtime_depth")),
    }


def _handling_note(extensions: Dict[str, Any]) -> str:
    """The same in prose, for clients that pass only the text on to the model."""
    handling = _handling(extensions)
    notes = [
        label for key, label in (("acknowledged", "acknowledged"), ("in_downtime", "in downtime")) if handling[key]
    ]
    return f" ({', '.join(notes)})" if notes else ""


class MonitoringHandler(BaseHandler):
    """Handle monitoring and problem management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle monitoring-related tool calls"""

        try:
            if tool_name == "vibemk_get_current_problems":
                return await self._get_current_problems(arguments)
            if tool_name == "vibemk_acknowledge_problem":
                return await self._acknowledge_problem(arguments)
            if tool_name == "vibemk_get_downtimes":
                return await self._get_downtimes(arguments)
            if tool_name == "vibemk_delete_comment":
                return await self._delete_comment(arguments)
            if tool_name == "vibemk_get_comments":
                return await self._get_comments(arguments)
            if tool_name == "vibemk_add_comment":
                return await self._add_comment(arguments)
            return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception("Error in %s", tool_name)
            return self.error_response("Unexpected Error", str(e))

    @staticmethod
    def _format_service_problem(
        host_name: str, description: str, state_name: str, plugin_output: str, last_state_change: int
    ) -> str:
        """One problem line, carrying why it is failing and since when.

        Without the check output the answer to "what is wrong" is only a list
        of names, and the caller has to ask again per service — CheckMK's
        show_service action does not return the output at all, so that second
        question has no good answer. The collection already returns it here.
        """
        line = f"🔧 SERVICE: {host_name}/{description} - {state_name}"
        if plugin_output:
            line += f"\n    {plugin_output.strip()}"
        if last_state_change:
            since = datetime.fromtimestamp(last_state_change, tz=timezone.utc)
            line += f"\n    since {since:%Y-%m-%d %H:%M} UTC"
        return line

    async def _get_current_problems(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get current problems (hosts and services with issues)"""
        target_host = arguments.get("host_name")
        problems = []
        host_problems: List[Dict[str, Any]] = []
        service_problems: List[Dict[str, Any]] = []

        try:
            # Hosts: query the monitoring 'host' collection ONCE with the state
            # column. (The old code looped one HTTP call per host against the
            # Setup 'host_config' collection, which is empty for a Guest account —
            # so it silently missed every DOWN host.)
            host_list_result = self.client.get(
                "domain-types/host/collections/all",
                params={"columns": ["name", "state", "acknowledged", "scheduled_downtime_depth"]},
            )

            if host_list_result.get("success"):
                for host in host_list_result["data"].get("value", []):
                    ext = host.get("extensions", {})
                    host_name = ext.get("name") or host.get("id", "Unknown")

                    # Filter to specific host if requested
                    if target_host and host_name != target_host:
                        continue

                    state = ext.get("state", 0)
                    if state != 0:
                        state_name = {1: "DOWN", 2: "UNREACHABLE"}.get(state, f"STATE({state})")
                        problems.append(f"🖥️ HOST: {host_name} - {state_name}{_handling_note(ext)}")
                        host_problems.append(
                            {
                                "host_name": host_name,
                                "state": state_name,
                                "state_code": state,
                                **_handling(ext),
                            }
                        )

            # Services: query the monitoring 'service' collection ONCE with the
            # state column and filter in memory. (The old code fired a separate
            # show_service call per service and only looked at the first 50 of
            # ~1500 services — slow and incomplete.)
            service_list_result = self.client.get(
                "domain-types/service/collections/all",
                params={
                    "columns": [
                        "host_name",
                        "description",
                        "state",
                        "plugin_output",
                        "last_state_change",
                        "acknowledged",
                        "scheduled_downtime_depth",
                    ]
                },
            )

            if service_list_result.get("success"):
                for service in service_list_result["data"].get("value", []):
                    ext = service.get("extensions", {})
                    host_name = ext.get("host_name", "Unknown")

                    # Filter to specific host if requested
                    if target_host and host_name != target_host:
                        continue

                    state = ext.get("state", 0)
                    if state != 0:
                        description = ext.get("description", "Unknown")
                        state_name = {1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}.get(state, f"STATE({state})")
                        problems.append(
                            self._format_service_problem(
                                host_name,
                                description,
                                state_name + _handling_note(ext),
                                ext.get("plugin_output", ""),
                                ext.get("last_state_change", 0),
                            )
                        )
                        changed = ext.get("last_state_change")
                        service_problems.append(
                            {
                                "host_name": host_name,
                                "service_description": description,
                                "state": state_name,
                                "state_code": state,
                                "plugin_output": (ext.get("plugin_output") or "").strip(),
                                "last_state_change": changed if isinstance(changed, int) and changed > 0 else None,
                                **_handling(ext),
                            }
                        )

        except Exception as e:
            self.logger.exception("Error getting current problems")
            return self.error_response("Error retrieving problems", str(e))

        data = {"total": len(problems), "host_problems": host_problems, "service_problems": service_problems}
        if not problems:
            return self.structured_response("✅ No current problems found", data)

        return self.structured_response(
            f"🚨 **Current Problems** ({len(problems)} total):\n\n" + "\n".join(problems), data
        )

    async def _acknowledge_problem(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Acknowledge a host or service problem"""
        ack_type = arguments.get("acknowledge_type")
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")
        comment = arguments.get("comment")

        if not ack_type or not host_name or not comment:
            return self.error_response("Missing parameters", "acknowledge_type, host_name, and comment are required")

        # CheckMK's own defaults, and steerable. These used to be wired to True
        # with no way to change them, and the schema mentioned neither -- so a
        # caller who wanted a silent acknowledgement had no way to ask, and no
        # way to find out that the flags existed.
        sticky = arguments.get("sticky", True)
        notify = arguments.get("notify", True)
        persistent = arguments.get("persistent", False)

        if ack_type == "host":
            data = {
                "acknowledge_type": "host",
                "host_name": host_name,
                "comment": comment,
                "sticky": sticky,
                "notify": notify,
                "persistent": persistent,
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
                "sticky": sticky,
                "notify": notify,
                "persistent": persistent,
            }
            result = self.client.post("domain-types/acknowledge/collections/service", data=data)
            target = f"service '{host_name}/{service_description}'"
        else:
            return self.error_response("Invalid acknowledge_type", "acknowledge_type must be 'host' or 'service'")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": f"✅ **Problem Acknowledged**\n\nTarget: {target}\nComment: {comment}",
                }
            ]
        return self.error_response("Acknowledgment failed", f"Could not acknowledge {target}")

    async def _get_downtimes(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of scheduled downtimes"""
        params = {}
        if host_name := arguments.get("host_name"):
            params["host_name"] = host_name

        result = self.client.get("domain-types/downtime/collections/all", params=params)

        if not result.get("success"):
            return self.error_response("Failed to retrieve downtimes")

        downtimes = result["data"].get("value", [])
        now = datetime.now().timestamp()
        data = {"total": len(downtimes), "downtimes": [downtime_record(downtime, now) for downtime in downtimes]}
        if not downtimes:
            return self.structured_response("ℹ️ No scheduled downtimes", data)

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

        return self.structured_response(
            f"⏰ **Scheduled Downtimes** ({len(downtimes)} total):\n\n" + "\n".join(downtime_list), data
        )

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
        return self.error_response("Comment creation failed", f"Could not add comment to {target}")

    async def _delete_comment(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a host or service comment."""
        delete_type = arguments.get("delete_type", "by_id")
        comment_id = arguments.get("comment_id")
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")
        site_id = arguments.get("site_id", self.client.config.site)

        if delete_type == "by_id":
            if not comment_id:
                return self.error_response("Missing parameter", "comment_id is required for delete_type=by_id")
            data: Dict[str, Any] = {
                "delete_type": "by_id",
                "comment_id": int(comment_id),
                "site_id": site_id,
            }
        elif delete_type == "by_query":
            if not host_name:
                return self.error_response("Missing parameter", "host_name is required for delete_type=by_query")
            data = {"delete_type": "by_query", "host_name": host_name}
            if service_description:
                data["service_description"] = service_description
        else:
            return self.error_response("Invalid delete_type", "delete_type must be 'by_id' or 'by_query'")

        result = self.client.post("domain-types/comment/actions/delete/invoke", data=data)

        if result.get("success"):
            if delete_type == "by_id":
                target = f"comment #{comment_id}"
            else:
                target = f"{host_name}" + (f"/{service_description}" if service_description else "")
            return [{"type": "text", "text": f"💬 **Comment Deleted**\n\nTarget: {target}"}]
        else:
            detail = result.get("data", {})
            return self.error_response("Comment deletion failed", str(detail))
