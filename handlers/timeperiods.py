"""
Time period management handlers for CheckMK scheduling
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class TimePeriodsHandler(BaseHandler):
    """Handle time period management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle time period-related tool calls"""

        try:
            if tool_name == "vibemk_get_timeperiods":
                return await self._get_timeperiods(arguments)
            elif tool_name == "vibemk_create_timeperiod":
                return await self._create_timeperiod(arguments)
            elif tool_name == "vibemk_update_timeperiod":
                return await self._update_timeperiod(arguments)
            elif tool_name == "vibemk_delete_timeperiod":
                return await self._delete_timeperiod(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _get_timeperiods(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of time periods"""
        result = self.client.get("domain-types/time_period/collections/all")

        if not result.get("success"):
            return self.error_response("Failed to retrieve time periods")

        timeperiods = result["data"].get("value", [])
        if not timeperiods:
            return [{"type": "text", "text": "⏰ **No Time Periods Found**\n\nNo time periods are configured."}]

        period_list = []
        for period in timeperiods:
            period_id = period.get("id", "Unknown")
            extensions = period.get("extensions", {})
            alias = extensions.get("alias", period_id)
            active_ranges = extensions.get("active_time_ranges", [])
            exceptions = extensions.get("exceptions", [])

            ranges_summary = f"{len(active_ranges)} active ranges"
            if exceptions:
                ranges_summary += f", {len(exceptions)} exceptions"

            period_list.append(f"⏰ **{period_id}** - {alias}\n   {ranges_summary}")

        return [
            {"type": "text", "text": f"⏰ **Time Periods** ({len(timeperiods)} total):\n\n" + "\n\n".join(period_list)}
        ]

    async def _create_timeperiod(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new time period"""
        name = arguments.get("name")
        alias = arguments.get("alias")
        active_time_ranges = arguments.get("active_time_ranges", [])
        exceptions = arguments.get("exceptions", [])
        exclude = arguments.get("exclude", [])

        if not name:
            return self.error_response("Missing parameter", "name is required")

        data = {"name": name, "active_time_ranges": active_time_ranges}

        if alias:
            data["alias"] = alias
        if exceptions:
            data["exceptions"] = exceptions
        if exclude:
            data["exclude"] = exclude

        # Validate time range structure
        for time_range in active_time_ranges:
            if not self._validate_time_range(time_range):
                return self.error_response("Invalid time range", "Time ranges must have 'day' and 'time_ranges' fields")

        result = self.client.post("domain-types/time_period/collections/all", data=data)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Time Period Created Successfully**\n\n"
                        f"Name: {name}\n"
                        f"Alias: {alias or 'None'}\n"
                        f"Active ranges: {len(active_time_ranges)}\n"
                        f"Exceptions: {len(exceptions)}\n"
                        f"Exclusions: {len(exclude)}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("Time period creation failed", f"Could not create time period '{name}'")

    async def _update_timeperiod(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update an existing time period"""
        name = arguments.get("name")
        alias = arguments.get("alias")
        active_time_ranges = arguments.get("active_time_ranges")
        exceptions = arguments.get("exceptions")
        exclude = arguments.get("exclude")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        # Check if time period exists
        check_result = self.client.get(f"objects/time_period/{name}")
        if not check_result.get("success"):
            return self.error_response("Time period not found", f"Time period '{name}' does not exist")

        # Build update data
        data = {}
        if alias is not None:
            data["alias"] = alias
        if active_time_ranges is not None:
            # Validate time range structure
            for time_range in active_time_ranges:
                if not self._validate_time_range(time_range):
                    return self.error_response(
                        "Invalid time range", "Time ranges must have 'day' and 'time_ranges' fields"
                    )
            data["active_time_ranges"] = active_time_ranges
        if exceptions is not None:
            data["exceptions"] = exceptions
        if exclude is not None:
            data["exclude"] = exclude

        if not data:
            return self.error_response("No data to update", "At least one field must be provided")

        # Use ETag for optimistic locking
        headers = {"If-Match": "*"}
        result = self.client.put(f"objects/time_period/{name}", data=data, headers=headers)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Time Period Updated Successfully**\n\n"
                        f"Name: {name}\n"
                        f"Updated fields: {', '.join(data.keys())}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            return self.error_response("Time period update failed", f"Could not update time period '{name}'")

    async def _delete_timeperiod(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a time period"""
        name = arguments.get("name")

        if not name:
            return self.error_response("Missing parameter", "name is required")

        # Check if time period exists
        check_result = self.client.get(f"objects/time_period/{name}")
        if not check_result.get("success"):
            return self.error_response("Time period not found", f"Time period '{name}' does not exist")

        result = self.client.delete(f"objects/time_period/{name}")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Time Period Deleted Successfully**\n\n"
                        f"Name: {name}\n\n"
                        f"📝 **Next Steps:**\n"
                        f"1️⃣ Use 'get_pending_changes' to review the deletion\n"
                        f"2️⃣ Use 'activate_changes' to apply the configuration\n\n"
                        f"💡 **Important:** The time period is only marked for deletion until you activate changes!"
                    ),
                }
            ]
        else:
            return self.error_response("Time period deletion failed", f"Could not delete time period '{name}'")

    def _validate_time_range(self, time_range: Dict[str, Any]) -> bool:
        """Validate time range structure"""
        if not isinstance(time_range, dict):
            return False

        if "day" not in time_range or "time_ranges" not in time_range:
            return False

        # Validate time ranges format
        ranges = time_range.get("time_ranges", [])
        if not isinstance(ranges, list):
            return False

        for tr in ranges:
            if not isinstance(tr, dict) or "start" not in tr or "end" not in tr:
                return False

        return True
