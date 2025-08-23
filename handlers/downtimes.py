"""
Downtime management handlers for CheckMK maintenance scheduling
"""

import datetime
from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class DowntimeHandler(BaseHandler):
    """Handle downtime operations for hosts and services"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle downtime-related tool calls"""

        try:
            if tool_name == "vibemk_schedule_host_downtime":
                return await self._schedule_host_downtime(arguments)
            elif tool_name == "vibemk_schedule_service_downtime":
                return await self._schedule_service_downtime(arguments)
            elif tool_name == "vibemk_list_downtimes":
                return await self._list_downtimes(arguments)
            elif tool_name == "vibemk_delete_downtime":
                return await self._delete_downtime(arguments)
            elif tool_name == "vibemk_get_active_downtimes":
                return await self._get_active_downtimes(arguments)
            elif tool_name == "vibemk_check_host_downtime_status":
                return await self._check_host_downtime_status(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _schedule_host_downtime(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Schedule downtime for a host using CheckMK API"""
        host_name = arguments.get("host_name")
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        # Parse time parameters - support both string durations and explicit times
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        duration = arguments.get("duration", "60m")  # Default 1 hour, support string format
        comment = arguments.get("comment", "Scheduled maintenance")
        author = arguments.get("author", "vibeMK")  # Optional author field

        # Convert duration to minutes if it's a string
        if isinstance(duration, str):
            duration_minutes = self._parse_time_delta(duration)
        else:
            duration_minutes = int(duration) if duration else 60

        # Parse timestamps
        downtime_times = self._parse_downtime_times(start_time, end_time, duration_minutes)

        # Check for existing downtimes (optional - based on working example)
        existing_downtimes = await self._get_current_downtimes(host_name, [], comment)
        force = arguments.get("force", False)

        if existing_downtimes and not force:
            self.logger.info(f"Host {host_name} already has downtime with comment '{comment}'")
            response = f"⚠️ **Downtime Already Exists**\n\n"
            response += f"**Host:** {host_name}\n"
            response += f"**Existing Comment:** {comment}\n"
            response += f"**Status:** Not creating duplicate downtime\n\n"
            response += f"💡 **Tip:** Use `force=true` parameter to create anyway, or use different comment"
            return [{"type": "text", "text": response}]

        # Build downtime request data with correct CheckMK format
        downtime_data = {
            "downtime_type": "host",
            "host_name": host_name,
            "start_time": downtime_times["start_time"],
            "end_time": downtime_times["end_time"],
            "comment": comment,
        }

        self.logger.debug(f"Scheduling host downtime with data: {downtime_data}")

        # Schedule the downtime
        result = self.client.post("domain-types/downtime/collections/host", data=downtime_data)

        # Check for successful creation (expect 204 No Content or 200 OK)
        success = result.get("success") or (result.get("status_code") in [200, 204])

        if success:
            downtime_info = result.get("data", {})
            downtime_id = downtime_info.get("id", "Unknown")

            # Verify downtime creation with retry logic (based on working example)
            verified = await self._verify_downtime_creation(host_name, comment, max_retries=5)

            response = f"✅ **Host Downtime Scheduled Successfully**\n\n"
            response += f"**Host:** {host_name}\n"
            if downtime_id != "Unknown":
                response += f"**Downtime ID:** {downtime_id}\n"
            response += f"**Start:** {downtime_times['start_time']}\n"
            response += f"**End:** {downtime_times['end_time']}\n"
            response += f"**Duration:** {duration_minutes} minutes\n"
            response += f"**Comment:** {comment}\n"
            response += f"**Verification:** {'✅ Confirmed' if verified else '⚠️ Pending (may take a moment)'}\n"
            response += f"\n💡 **Tip:** Use `vibemk_list_downtimes` to view all active downtimes"

            return [{"type": "text", "text": response}]
        else:
            error_data = result.get("data", {})
            return self.error_response(
                "Failed to schedule host downtime",
                f"Could not schedule downtime for host '{host_name}': {error_data.get('title', str(error_data))}",
            )

    async def _schedule_service_downtime(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Schedule downtime for service(s) on a host using CheckMK API"""
        host_name = arguments.get("host_name")

        # Accept both singular and plural forms
        service_descriptions = arguments.get("service_descriptions", [])
        if not service_descriptions:
            service_description = arguments.get("service_description")
            if service_description:
                service_descriptions = [service_description]

        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")
        if not service_descriptions:
            return self.error_response("Missing parameter", "service_description or service_descriptions is required")

        # Ensure service_descriptions is a list
        if isinstance(service_descriptions, str):
            service_descriptions = [service_descriptions]

        # Parse time parameters - support both string durations and explicit times
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        duration = arguments.get("duration", "60m")  # Default 1 hour, support string format
        comment = arguments.get("comment", "Scheduled service maintenance")
        author = arguments.get("author", "vibeMK")  # Optional author field

        # Convert duration to minutes if it's a string
        if isinstance(duration, str):
            duration_minutes = self._parse_time_delta(duration)
        else:
            duration_minutes = int(duration) if duration else 60

        # Parse timestamps
        downtime_times = self._parse_downtime_times(start_time, end_time, duration_minutes)

        # Check for existing downtimes for services (based on working example)
        existing_downtimes = await self._get_current_downtimes(host_name, service_descriptions, comment)
        force = arguments.get("force", False)

        # Filter out services that already have downtimes (unless force=true)
        if not force:
            services_to_schedule = [s for s in service_descriptions if s not in existing_downtimes]
            if not services_to_schedule:
                response = f"⚠️ **All Services Already Have Downtime**\n\n"
                response += f"**Host:** {host_name}\n"
                response += f"**Services:** {', '.join(service_descriptions)}\n"
                response += f"**Existing Comment:** {comment}\n"
                response += f"**Status:** Not creating duplicate downtimes\n\n"
                response += f"💡 **Tip:** Use `force=true` parameter to create anyway, or use different comment"
                return [{"type": "text", "text": response}]
        else:
            services_to_schedule = service_descriptions

        # Build downtime request data with correct CheckMK format
        downtime_data = {
            "downtime_type": "service",
            "host_name": host_name,
            "service_descriptions": services_to_schedule,
            "start_time": downtime_times["start_time"],
            "end_time": downtime_times["end_time"],
            "comment": comment,
        }

        self.logger.debug(f"Scheduling service downtime with data: {downtime_data}")

        # Schedule the downtime
        result = self.client.post("domain-types/downtime/collections/service", data=downtime_data)

        # Check for successful creation (expect 204 No Content or 200 OK)
        success = result.get("success") or (result.get("status_code") in [200, 204])

        if success:
            downtime_info = result.get("data", {})
            downtime_id = downtime_info.get("id", "Unknown")

            # Verify downtime creation with retry logic for services
            verified = await self._verify_downtime_creation(
                host_name, comment, max_retries=5, services=services_to_schedule
            )

            response = f"✅ **Service Downtime Scheduled Successfully**\n\n"
            response += f"**Host:** {host_name}\n"
            response += f"**Services:** {', '.join(services_to_schedule)}\n"
            if downtime_id != "Unknown":
                response += f"**Downtime ID:** {downtime_id}\n"
            response += f"**Start:** {downtime_times['start_time']}\n"
            response += f"**End:** {downtime_times['end_time']}\n"
            response += f"**Duration:** {duration_minutes} minutes\n"
            response += f"**Comment:** {comment}\n"
            response += f"**Verification:** {'✅ Confirmed' if verified else '⚠️ Pending (may take a moment)'}\n"

            if len(services_to_schedule) != len(service_descriptions):
                skipped = [s for s in service_descriptions if s not in services_to_schedule]
                response += f"**Skipped (existing):** {', '.join(skipped)}\n"

            response += f"\n💡 **Tip:** Use `vibemk_list_downtimes` to view all active downtimes"

            return [{"type": "text", "text": response}]
        else:
            error_data = result.get("data", {})
            return self.error_response(
                "Failed to schedule service downtime",
                f"Could not schedule downtime for services on '{host_name}': {error_data.get('title', str(error_data))}",
            )

    async def _list_downtimes(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all downtimes or filter by host/service"""
        host_name = arguments.get("host_name")  # Optional filter
        service_description = arguments.get("service_description")  # Optional filter
        show_only_active = arguments.get("active_only", True)  # Show only active by default

        self.logger.debug(f"Listing downtimes - host: {host_name}, service: {service_description}")

        # Get all downtimes
        result = self.client.get("domain-types/downtime/collections/all")

        if result.get("success"):
            downtimes = result["data"].get("value", [])

            # Filter downtimes if requested
            filtered_downtimes = []
            for downtime in downtimes:
                extensions = downtime.get("extensions", {})

                # Filter by host if specified
                if host_name and extensions.get("host_name") != host_name:
                    continue

                # Filter by service if specified
                if service_description and extensions.get("service_description") != service_description:
                    continue

                # Filter by active status if requested
                if show_only_active and extensions.get("is_pending", 0) == 1:
                    continue

                filtered_downtimes.append(downtime)

            return [{"type": "text", "text": self._format_downtimes_list(filtered_downtimes, host_name)}]
        else:
            error_data = result.get("data", {})
            return self.error_response(
                "Failed to retrieve downtimes",
                f"Could not get downtime list: {error_data.get('title', str(error_data))}",
            )

    async def _delete_downtime(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete downtimes using query-based deletion (based on working CheckMK example)"""
        # Support both specific downtime_id deletion and bulk deletion by criteria
        downtime_id = arguments.get("downtime_id")
        host_name = arguments.get("host_name")
        service_descriptions = arguments.get("service_descriptions", [])
        service_description = arguments.get("service_description")
        comment = arguments.get("comment")

        # Convert single service to list
        if service_description and not service_descriptions:
            service_descriptions = [service_description]

        # If downtime_id is provided, get the specific downtime details first
        if downtime_id:
            self.logger.debug(f"Getting downtime details for ID: {downtime_id}")

            # Get all downtimes to find the specific one and extract required info
            list_result = self.client.get("domain-types/downtime/collections/all")
            if not list_result.get("success"):
                return self.error_response("Failed to get downtime info", "Could not retrieve downtime details")

            downtimes = list_result["data"].get("value", [])
            target_downtime = None

            for downtime in downtimes:
                if str(downtime.get("id")) == str(downtime_id):
                    target_downtime = downtime
                    break

            if not target_downtime:
                return self.error_response("Downtime not found", f"No downtime found with ID {downtime_id}")

            # Extract information from the specific downtime for query-based deletion
            extensions = target_downtime.get("extensions", {})
            host_name = extensions.get("host_name")
            service_desc = extensions.get("service_description")
            comment = comment or extensions.get("comment")  # Use existing comment if not provided
            is_service_raw = extensions.get("is_service", 0)
            is_service = is_service_raw == 1 or is_service_raw == "yes"

            if is_service and service_desc:
                service_descriptions = [service_desc]

            if not host_name:
                return self.error_response("Invalid downtime", "Could not determine host name for downtime")

        elif not host_name:
            return self.error_response("Missing parameter", "host_name or downtime_id is required")

        # Check existing downtimes before deletion (based on working example)
        existing_downtimes = await self._get_current_downtimes(host_name, service_descriptions, comment)
        is_service = len(service_descriptions) > 0

        if not existing_downtimes:
            item = f"{host_name}/[{', '.join(service_descriptions)}]" if is_service else host_name
            return [
                {
                    "type": "text",
                    "text": f"ℹ️ **No Matching Downtimes**\n\n'{item}' has no downtimes with comment '{comment}'",
                }
            ]

        # Build query filters for deletion (based on working CheckMK example)
        query_filters = []

        if is_service:
            # Handle service downtime deletion
            if len(service_descriptions) > 1:
                # Multiple services - use OR filter
                service_filter_parts = [
                    f'{{"op": "~", "left": "service_description", "right": "{s}"}}' for s in service_descriptions
                ]
                query_filters.append(f'{{"op": "or", "expr": [{", ".join(service_filter_parts)}]}}')
            else:
                # Single service
                query_filters.append(
                    f'{{"op": "~", "left": "service_description", "right": "{service_descriptions[0]}"}}'
                )

        # Add host name filter
        query_filters.append(f'{{"op": "~", "left": "host_name", "right": "{host_name}"}}')

        # Add comment filter if provided
        if comment:
            query_filters.append(f'{{"op": "~", "left": "comment", "right": "{comment}"}}')

        # Build delete request data using query-based deletion (working CheckMK format)
        delete_data = {"delete_type": "query", "query": f'{{"op": "and", "expr": [{", ".join(query_filters)}]}}'}

        self.logger.debug(f"Deleting downtime with query data: {delete_data}")

        result = self.client.post("domain-types/downtime/actions/delete/invoke", data=delete_data)

        if result.get("success"):
            item = f"{host_name}/[{', '.join(service_descriptions)}]" if is_service else host_name
            downtime_type = "Service" if is_service else "Host"

            response = f"✅ **Downtime Deleted Successfully**\n\n"
            if downtime_id:
                response += f"**Downtime ID:** {downtime_id}\n"
            response += f"**Type:** {downtime_type} downtime\n"
            response += f"**Target:** {item}\n"
            if comment:
                response += f"**Comment:** {comment}\n"
            response += f"**Status:** Removed from monitoring schedule\n"
            response += f"\n💡 **Tip:** Use `vibemk_list_downtimes` to view remaining active downtimes"

            return [{"type": "text", "text": response}]
        else:
            error_data = result.get("data", {})
            item = f"{host_name}/[{', '.join(service_descriptions)}]" if is_service else host_name
            return self.error_response(
                "Failed to delete downtime",
                f"Could not delete downtime for '{item}' with comment '{comment}': {error_data.get('title', str(error_data))}",
            )

    async def _get_active_downtimes(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get only currently active downtimes"""
        host_name = arguments.get("host_name")  # Optional filter

        # Get all downtimes first
        result = self.client.get("domain-types/downtime/collections/all")

        if result.get("success"):
            all_downtimes = result["data"].get("value", [])

            # Filter for active downtimes only
            active_downtimes = []
            now = datetime.datetime.now().timestamp()

            for downtime in all_downtimes:
                extensions = downtime.get("extensions", {})

                # Skip pending downtimes
                if extensions.get("is_pending", 0) == 1:
                    continue

                # Check if downtime is currently active (between start_time and end_time)
                start_time = self._timestamp_to_unix(extensions.get("start_time", 0))
                end_time = self._timestamp_to_unix(extensions.get("end_time", 0))

                if start_time <= now <= end_time:
                    # Filter by host if specified
                    if not host_name or extensions.get("host_name") == host_name:
                        active_downtimes.append(downtime)

            return [{"type": "text", "text": self._format_active_downtimes(active_downtimes, host_name)}]
        else:
            error_data = result.get("data", {})
            return self.error_response(
                "Failed to retrieve active downtimes",
                f"Could not get active downtimes: {error_data.get('title', str(error_data))}",
            )

    def _parse_downtime_times(self, start_time: str, end_time: str, duration_minutes: int) -> Dict[str, str]:
        """Parse and convert downtime start/end times to ISO format with enhanced natural language support"""
        import re
        from datetime import datetime, timedelta

        # Use datetime.utcnow() to match CheckMK working example
        default_start_time = datetime.utcnow()
        default_end_time = default_start_time + timedelta(minutes=duration_minutes or 30)

        # Parse start time with enhanced natural language support
        if not start_time or start_time == "" or start_time == "now":
            start_dt = default_start_time
        elif start_time.startswith("+"):
            # Relative time like "+1h", "+30m" - parse as start_after
            delta_minutes = self._parse_time_delta(start_time)
            start_dt = datetime.utcnow() + timedelta(minutes=delta_minutes)
        else:
            # Enhanced natural language parsing for user-friendly formats
            start_dt = self._parse_natural_time(start_time)
            if start_dt is None:
                # Try to parse as ISO format (fallback)
                try:
                    if start_time.endswith("Z"):
                        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    else:
                        start_dt = datetime.fromisoformat(start_time)
                except ValueError:
                    # Fallback to default start time if parsing fails
                    self.logger.warning(f"Could not parse start_time '{start_time}', using default")
                    start_dt = default_start_time

        # Parse end time with enhanced natural language support
        if not end_time or end_time == "":
            # If no end time specified, use start_time + duration (end_after pattern)
            end_dt = start_dt + timedelta(minutes=duration_minutes or 30)
        elif end_time.startswith("+"):
            # Relative to start time (end_after pattern)
            delta_minutes = self._parse_time_delta(end_time)
            end_dt = start_dt + timedelta(minutes=delta_minutes)
        else:
            # Enhanced natural language parsing for end time
            end_dt = self._parse_natural_time(end_time)
            if end_dt is None:
                # Try to parse as ISO format (fallback)
                try:
                    if end_time.endswith("Z"):
                        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    else:
                        end_dt = datetime.fromisoformat(end_time)
                except ValueError:
                    # Fallback to start + duration
                    self.logger.warning(f"Could not parse end_time '{end_time}', using start + duration")
                    end_dt = start_dt + timedelta(minutes=duration_minutes or 30)

        # Ensure end time is after start time
        if end_dt <= start_dt:
            self.logger.warning("End time is before start time, adjusting")
            end_dt = start_dt + timedelta(minutes=duration_minutes or 30)

        # Return in CheckMK API format (ISO with Z suffix)
        return {
            "start_time": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_time": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def _parse_natural_time(self, time_str: str) -> "datetime.datetime":
        """
        Parse natural language time expressions into datetime objects.

        Supports formats like:
        - "22:00 today" / "22:00" (today at specified time)
        - "14:00 tomorrow" / "tomorrow at 14:00"
        - "monday at 09:00" / "next monday at 09:00"
        - "2024-08-23 at 22:00" (specific date)
        - "in 2 hours" / "in 30 minutes"
        """
        import re
        from datetime import datetime, timedelta

        if not time_str:
            return None

        time_str = time_str.strip().lower()
        now = datetime.now()

        # Pattern 1: "HH:MM today" or "HH:MM" or "today at HH:MM"
        time_pattern = r"(?:today\s+at\s+|at\s+)?(\d{1,2}):(\d{2})(?:\s+today)?"
        match = re.search(time_pattern, time_str)
        if (
            match
            and "today" in time_str
            or (
                match
                and not any(
                    word in time_str
                    for word in [
                        "tomorrow",
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                        "sunday",
                    ]
                )
            )
        ):
            hour, minute = int(match.group(1)), int(match.group(2))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                # If the time has already passed today, schedule for tomorrow
                if target_time <= now:
                    target_time += timedelta(days=1)
                return target_time

        # Pattern 2: "HH:MM tomorrow" or "tomorrow at HH:MM"
        tomorrow_pattern = (
            r"(?:tomorrow\s+at\s+|at\s+)?(\d{1,2}):(\d{2})(?:\s+tomorrow)?|tomorrow(?:\s+at\s+(\d{1,2}):(\d{2}))?"
        )
        match = re.search(tomorrow_pattern, time_str)
        if match and "tomorrow" in time_str:
            if match.group(1) and match.group(2):  # "HH:MM tomorrow"
                hour, minute = int(match.group(1)), int(match.group(2))
            elif match.group(3) and match.group(4):  # "tomorrow at HH:MM"
                hour, minute = int(match.group(3)), int(match.group(4))
            else:  # just "tomorrow" - default to same time tomorrow
                hour, minute = now.hour, now.minute

            if 0 <= hour <= 23 and 0 <= minute <= 59:
                tomorrow = now + timedelta(days=1)
                return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Pattern 3: Specific date formats "YYYY-MM-DD at HH:MM"
        date_time_pattern = r"(\d{4})-(\d{1,2})-(\d{1,2})(?:\s+at\s+(\d{1,2}):(\d{2}))?"
        match = re.search(date_time_pattern, time_str)
        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            hour = int(match.group(4)) if match.group(4) else now.hour
            minute = int(match.group(5)) if match.group(5) else now.minute

            try:
                return datetime(year, month, day, hour, minute)
            except ValueError:
                pass  # Invalid date, fall through

        # Pattern 4: "in X hours/minutes"
        relative_pattern = r"in\s+(\d+)\s+(hour|hours|minute|minutes|min)"
        match = re.search(relative_pattern, time_str)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if "hour" in unit:
                return now + timedelta(hours=amount)
            elif "minute" in unit or "min" in unit:
                return now + timedelta(minutes=amount)

        # Pattern 5: Day names "monday at 09:00", "next tuesday at 14:30"
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day_name in enumerate(weekdays):
            day_pattern = rf"(?:next\s+)?{day_name}(?:\s+at\s+(\d{{1,2}}):(\d{{2}}))?"
            match = re.search(day_pattern, time_str)
            if match:
                # Calculate days until target weekday
                days_ahead = i - now.weekday()
                if days_ahead <= 0 or "next" in time_str:  # Target day already passed this week or "next" specified
                    days_ahead += 7

                target_date = now + timedelta(days=days_ahead)

                # Extract time if provided, otherwise use current time
                if match.group(1) and match.group(2):
                    hour, minute = int(match.group(1)), int(match.group(2))
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

                return target_date

        # If no pattern matched, return None to use fallback parsing
        return None

    def _parse_time_delta(self, delta_str: str) -> int:
        """Parse relative time string like '+1h', '+30m', '1h30m' into minutes"""
        delta_str = delta_str.strip("+")
        total_minutes = 0

        # Handle complex formats like "1h30m", "2d4h", etc.
        import re

        # Extract all time components
        time_pattern = r"(\d+)([dhm])"
        matches = re.findall(time_pattern, delta_str.lower())

        if matches:
            for value, unit in matches:
                value = int(value)
                if unit == "m":
                    total_minutes += value
                elif unit == "h":
                    total_minutes += value * 60
                elif unit == "d":
                    total_minutes += value * 24 * 60
            return total_minutes

        # Fallback to simple format
        if delta_str.endswith("m"):
            return int(delta_str[:-1])
        elif delta_str.endswith("h"):
            return int(delta_str[:-1]) * 60
        elif delta_str.endswith("d"):
            return int(delta_str[:-1]) * 24 * 60
        else:
            # Default to minutes if no unit specified
            try:
                return int(delta_str)
            except ValueError:
                return 60  # Default 1 hour

    def _format_timestamp(self, timestamp) -> str:
        """Format timestamp to readable string, handling both Unix timestamps and ISO format"""
        if not timestamp:
            return "Unknown"

        try:
            # If it's already a string, try to parse as ISO format
            if isinstance(timestamp, str):
                dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M")
            # If it's a number, treat as Unix timestamp
            elif isinstance(timestamp, (int, float)):
                dt = datetime.datetime.fromtimestamp(timestamp)
                return dt.strftime("%Y-%m-%d %H:%M")
            else:
                return "Unknown"
        except (ValueError, TypeError):
            return "Unknown"

    def _timestamp_to_unix(self, timestamp) -> float:
        """Convert timestamp to Unix timestamp for comparison"""
        if not timestamp:
            return 0.0

        try:
            # If it's already a string, try to parse as ISO format
            if isinstance(timestamp, str):
                dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return dt.timestamp()
            # If it's a number, return as-is
            elif isinstance(timestamp, (int, float)):
                return float(timestamp)
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.0

    def _get_time_only(self, timestamp) -> str:
        """Extract time-only format (HH:MM) from various timestamp formats"""
        try:
            if isinstance(timestamp, str):
                dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return dt.strftime("%H:%M")
            elif isinstance(timestamp, (int, float)):
                dt = datetime.datetime.fromtimestamp(timestamp)
                return dt.strftime("%H:%M")
            else:
                # Fallback: try to extract from formatted string
                timestamp_str = self._format_timestamp(timestamp)
                return timestamp_str.split()[-1] if " " in timestamp_str else timestamp_str[:5]
        except (ValueError, TypeError, AttributeError):
            return str(timestamp)[:5]  # Return first 5 chars as fallback

    def _format_downtimes_list(self, downtimes: List[Dict], host_filter: str = None) -> str:
        """Format downtimes list for display, clearly distinguishing host downtimes vs service downtimes"""
        if not downtimes:
            filter_text = f" for host '{host_filter}'" if host_filter else ""
            return f"📋 **No Downtimes Found**\n\nNo active downtimes{filter_text}"

        filter_text = f" for host '{host_filter}'" if host_filter else ""
        response = f"📋 **Downtimes List{filter_text}**\n\n"

        # Separate host downtimes from service downtimes
        host_downtimes = []
        service_downtimes = []

        for downtime in downtimes[:30]:  # Increased limit for better visibility
            extensions = downtime.get("extensions", {})
            # Handle different API response formats for is_service
            is_service_raw = extensions.get("is_service", 0)
            is_service = is_service_raw == 1 or is_service_raw == "yes" or is_service_raw == "1"

            if is_service:
                service_downtimes.append(downtime)
            else:
                host_downtimes.append(downtime)

        # Show summary counts
        total_count = len(host_downtimes) + len(service_downtimes)
        response += f"Found {total_count} downtimes: "
        response += f"**{len(host_downtimes)} Host-Level** + **{len(service_downtimes)} Service-Level**\n\n"

        # Section 1: HOST DOWNTIMES (suppress all host and service alerts)
        if host_downtimes:
            response += "🏠 **HOST DOWNTIMES** (suppress ALL alerts for these hosts)\n"
            response += "=" * 60 + "\n\n"

            # Group host downtimes by host
            host_grouped = {}
            for downtime in host_downtimes:
                extensions = downtime.get("extensions", {})
                host_name = extensions.get("host_name", "Unknown")

                if host_name not in host_grouped:
                    host_grouped[host_name] = []
                host_grouped[host_name].append(downtime)

            for host_name, host_dt_list in sorted(host_grouped.items()):
                response += (
                    f"**{host_name}** ({len(host_dt_list)} host downtime{'s' if len(host_dt_list) != 1 else ''})\n"
                )
                for downtime in host_dt_list:
                    extensions = downtime.get("extensions", {})
                    downtime_id = downtime.get("id", "Unknown")
                    comment = extensions.get("comment", "No comment")

                    start_time = extensions.get("start_time", 0)
                    end_time = extensions.get("end_time", 0)
                    start_time_only = self._get_time_only(start_time)
                    end_time_only = self._get_time_only(end_time)

                    response += f"  • Downtime #{downtime_id}: {start_time_only} - {end_time_only}\n"
                    response += f'    Comment: "{comment}"\n'
                    response += f"    **Effect**: Host DOWN/UNREACHABLE + ALL service alerts suppressed\n\n"

        # Section 2: SERVICE DOWNTIMES (only suppress specific service alerts)
        if service_downtimes:
            response += "🔧 **SERVICE DOWNTIMES** (suppress only specific service alerts)\n"
            response += "=" * 60 + "\n\n"

            # Group service downtimes by host, then by service
            service_grouped = {}
            for downtime in service_downtimes:
                extensions = downtime.get("extensions", {})
                host_name = extensions.get("host_name", "Unknown")
                service_description = extensions.get("service_description", "Unknown Service")

                if host_name not in service_grouped:
                    service_grouped[host_name] = {}
                if service_description not in service_grouped[host_name]:
                    service_grouped[host_name][service_description] = []

                service_grouped[host_name][service_description].append(downtime)

            for host_name, services_dict in sorted(service_grouped.items()):
                response += f"**{host_name}** ({len(services_dict)} service{'s' if len(services_dict) != 1 else ''} with downtimes)\n"

                for service_name, service_dt_list in sorted(services_dict.items()):
                    response += f"  📋 **{service_name}** ({len(service_dt_list)} downtime{'s' if len(service_dt_list) != 1 else ''})\n"

                    for downtime in service_dt_list:
                        extensions = downtime.get("extensions", {})
                        downtime_id = downtime.get("id", "Unknown")
                        comment = extensions.get("comment", "No comment")

                        start_time = extensions.get("start_time", 0)
                        end_time = extensions.get("end_time", 0)
                        start_time_only = self._get_time_only(start_time)
                        end_time_only = self._get_time_only(end_time)

                        response += f"    • Downtime #{downtime_id}: {start_time_only} - {end_time_only}\n"
                        response += f'      Comment: "{comment}"\n'
                        response += (
                            f"      **Effect**: Only '{service_name}' alerts suppressed, host alerts STILL FIRE\n\n"
                        )

                response += "\n"  # Extra space between hosts

        # Show additional context if needed
        if len(downtimes) > 30:
            response += f"... and {len(downtimes) - 30} more downtimes (showing first 30)\n\n"

        # Add helpful footer explaining the distinction
        response += "💡 **Key Distinction:**\n"
        response += "   • **Host Downtimes**: Suppress both host alerts (DOWN/UNREACHABLE) AND all service alerts\n"
        response += (
            "   • **Service Downtimes**: Suppress only the specific service alerts, host alerts continue to fire\n"
        )

        response += "💡 **Tip:** Use `vibemk_delete_downtime` with downtime ID to cancel a downtime"
        return response

    def _format_active_downtimes(self, active_downtimes: List[Dict], host_filter: str = None) -> str:
        """Format currently active downtimes"""
        if not active_downtimes:
            filter_text = f" on host '{host_filter}'" if host_filter else ""
            return f"🟢 **No Active Downtimes**\n\nNo downtimes are currently active{filter_text}"

        filter_text = f" on host '{host_filter}'" if host_filter else ""
        response = f"🔴 **Currently Active Downtimes{filter_text}**\n\n"
        response += f"Found {len(active_downtimes)} active downtimes:\n\n"

        for i, downtime in enumerate(active_downtimes, 1):
            extensions = downtime.get("extensions", {})

            downtime_id = downtime.get("id", "Unknown")
            host_name = extensions.get("host_name", "Unknown")
            comment = extensions.get("comment", "No comment")
            is_service = extensions.get("is_service", 0) == 1

            # Calculate remaining time
            end_time = extensions.get("end_time", 0)
            now = datetime.datetime.now().timestamp()

            # Handle different timestamp formats from CheckMK API
            if isinstance(end_time, str):
                try:
                    # Try parsing ISO format timestamp
                    end_time_dt = datetime.datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    end_time = end_time_dt.timestamp()
                except (ValueError, AttributeError):
                    # Fallback: assume it's already a Unix timestamp string
                    try:
                        end_time = float(end_time)
                    except (ValueError, TypeError):
                        end_time = now  # Default to now if parsing fails

            remaining_minutes = max(0, int((end_time - now) / 60))

            response += f"**{i}. Downtime #{downtime_id}**\n"
            response += f"   🏠 Host: {host_name}\n"
            response += f"   🔧 Type: {'Service' if is_service else 'Host'}\n"
            response += f"   ⏰ Remaining: {remaining_minutes} minutes\n"
            response += f"   💬 Comment: {comment}\n"

            if is_service and extensions.get("service_description"):
                response += f"   🔧 Service: {extensions.get('service_description')}\n"

            response += "\n"

        response += "💡 **Info:** These downtimes are currently suppressing alerts"
        return response

    async def _get_host_downtime_status(self, host_name: str) -> Dict[str, Any]:
        """
        Get detailed downtime status for a specific host using precise CheckMK queries.
        This method properly distinguishes between host-level and service-level downtimes
        using the CheckMK Livestatus query format for maximum accuracy.

        Returns:
            Dict containing:
            - has_host_downtime: bool - True if the host object itself has a downtime
            - has_service_downtimes: bool - True if any services on the host have downtimes
            - host_downtime_count: int - Number of host-level downtimes
            - service_downtime_count: int - Number of service-level downtimes
            - active_host_downtimes: List[Dict] - Active host downtimes
            - active_service_downtimes: List[Dict] - Active service downtimes
        """
        try:
            # Query 1: Get host-level downtimes only (is_service = 0)
            host_query = {
                "op": "and",
                "expr": [
                    {"op": "=", "left": "host_name", "right": host_name},
                    {"op": "=", "left": "is_service", "right": "0"},
                ],
            }

            # Query 2: Get service-level downtimes only (is_service = 1)
            service_query = {
                "op": "and",
                "expr": [
                    {"op": "=", "left": "host_name", "right": host_name},
                    {"op": "=", "left": "is_service", "right": "1"},
                ],
            }

            # Execute both queries in parallel for better performance
            import json

            host_params = {"query": json.dumps(host_query)}
            service_params = {"query": json.dumps(service_query)}

            # Get host downtimes
            host_result = self.client.get("domain-types/downtime/collections/all", params=host_params)
            if not host_result.get("success"):
                raise Exception(
                    f"Failed to query host downtimes: {host_result.get('data', {}).get('title', 'Unknown error')}"
                )

            # Get service downtimes
            service_result = self.client.get("domain-types/downtime/collections/all", params=service_params)
            if not service_result.get("success"):
                raise Exception(
                    f"Failed to query service downtimes: {service_result.get('data', {}).get('title', 'Unknown error')}"
                )

            # Process results
            host_downtimes = host_result["data"].get("value", [])
            service_downtimes = service_result["data"].get("value", [])

            now = datetime.datetime.now().timestamp()
            active_host_downtimes = []
            active_service_downtimes = []

            # Filter for currently active host downtimes
            for downtime in host_downtimes:
                if self._is_downtime_active(downtime, now):
                    active_host_downtimes.append(downtime)

            # Filter for currently active service downtimes
            for downtime in service_downtimes:
                if self._is_downtime_active(downtime, now):
                    active_service_downtimes.append(downtime)

            return {
                "has_host_downtime": len(active_host_downtimes) > 0,
                "has_service_downtimes": len(active_service_downtimes) > 0,
                "host_downtime_count": len(active_host_downtimes),
                "service_downtime_count": len(active_service_downtimes),
                "active_host_downtimes": active_host_downtimes,
                "active_service_downtimes": active_service_downtimes,
                "total_host_downtimes": len(host_downtimes),
                "total_service_downtimes": len(service_downtimes),
            }

        except Exception as e:
            self.logger.error(f"Error getting host downtime status for {host_name}: {e}")
            return {
                "has_host_downtime": False,
                "has_service_downtimes": False,
                "host_downtime_count": 0,
                "service_downtime_count": 0,
                "active_host_downtimes": [],
                "active_service_downtimes": [],
                "error": str(e),
            }

    def _is_downtime_active(self, downtime: Dict[str, Any], current_timestamp: float) -> bool:
        """
        Check if a downtime is currently active based on its start and end times.

        Args:
            downtime: Downtime object from CheckMK API
            current_timestamp: Current Unix timestamp to compare against

        Returns:
            True if the downtime is currently active, False otherwise
        """
        try:
            extensions = downtime.get("extensions", {})
            start_time = extensions.get("start_time", 0)
            end_time = extensions.get("end_time", 0)

            # Handle different timestamp formats from CheckMK API
            if isinstance(start_time, str):
                try:
                    start_time_dt = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    start_time = start_time_dt.timestamp()
                except (ValueError, AttributeError):
                    try:
                        start_time = float(start_time)
                    except (ValueError, TypeError):
                        return False

            if isinstance(end_time, str):
                try:
                    end_time_dt = datetime.datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    end_time = end_time_dt.timestamp()
                except (ValueError, AttributeError):
                    try:
                        end_time = float(end_time)
                    except (ValueError, TypeError):
                        return False

            # Check if current time is within the downtime window
            return start_time <= current_timestamp <= end_time

        except Exception as e:
            self.logger.warning(f"Error checking downtime active status: {e}")
            return False

    async def _check_host_downtime_status(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check the downtime status for a specific host, properly distinguishing between
        host-level downtimes and service-level downtimes.
        """
        host_name = arguments.get("host_name")
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        # Get detailed downtime status
        status = await self._get_host_downtime_status(host_name)

        if "error" in status:
            return self.error_response("Error checking downtime status", status["error"])

        # Build response message
        response = f"🔍 **Downtime Status for Host: {host_name}**\n\n"

        # Host-level downtime status
        if status["has_host_downtime"]:
            response += f"🏠 **Host Object Downtime:** ✅ **YES** - Host is covered by {status['host_downtime_count']} active host-level downtime(s)\n"
        else:
            response += f"🏠 **Host Object Downtime:** ❌ **NO** - Host object has no active downtimes\n"

        # Service-level downtime status
        if status["has_service_downtimes"]:
            response += f"🔧 **Service Downtimes:** ✅ **YES** - {status['service_downtime_count']} service(s) on this host have active downtimes\n"
        else:
            response += f"🔧 **Service Downtimes:** ❌ **NO** - No services on this host have active downtimes\n"

        response += "\n"

        # Summary interpretation with clear distinction
        if status["has_host_downtime"]:
            response += "🎯 **CRITICAL DISTINCTION:** This host HAS host-level downtimes.\n"
            response += "   ✅ Host alerts (host DOWN, UNREACHABLE) are SUPPRESSED\n"
            response += "   ✅ All service alerts on this host are also SUPPRESSED\n"
            response += "   📊 Alert Status: HOST and SERVICE alerts both suppressed\n"
        elif status["has_service_downtimes"]:
            response += "⚠️ **CRITICAL DISTINCTION:** This host has NO host-level downtimes.\n"
            response += "   ❌ Host alerts (host DOWN, UNREACHABLE) will FIRE normally\n"
            response += "   ✅ Only specific service alerts are suppressed by service downtimes\n"
            response += "   📊 Alert Status: HOST alerts ACTIVE, some SERVICE alerts suppressed\n"
            response += "   💡 To suppress host alerts, you need a separate HOST downtime\n"
        else:
            response += "🔴 **NO DOWNTIMES:** This host has neither host nor service downtimes.\n"
            response += "   ❌ Host alerts (host DOWN, UNREACHABLE) will FIRE normally\n"
            response += "   ❌ All service alerts will FIRE normally\n"
            response += "   📊 Alert Status: ALL alerts are ACTIVE\n"

        response += "\n"

        # Details section
        if status["active_host_downtimes"]:
            response += "📋 **Active Host Downtimes:**\n"
            for downtime in status["active_host_downtimes"]:
                extensions = downtime.get("extensions", {})
                comment = extensions.get("comment", "No comment")
                response += f"   • Downtime #{downtime.get('id')}: {comment}\n"
            response += "\n"

        if status["active_service_downtimes"]:
            response += "📋 **Active Service Downtimes:**\n"
            for downtime in status["active_service_downtimes"]:
                extensions = downtime.get("extensions", {})
                service = extensions.get("service_description", "Unknown")
                comment = extensions.get("comment", "No comment")
                response += f"   • Service '{service}' (#{downtime.get('id')}): {comment}\n"
            response += "\n"

        response += "💡 **Usage:** This tool helps distinguish between host-level and service-level downtimes\n"
        response += "   for proper alerting analysis and downtime troubleshooting."

        return [{"type": "text", "text": response}]

    async def has_host_level_downtime(self, host_name: str) -> bool:
        """
        Simple method to check if a host has HOST-level downtimes (not service downtimes).
        This can be used by other handlers that need to know if host alerts are suppressed.

        Args:
            host_name: Name of the host to check

        Returns:
            True if the host has active HOST-level downtimes, False otherwise
        """
        try:
            # Use precise query to get only host-level downtimes
            import json

            host_query = {
                "op": "and",
                "expr": [
                    {"op": "=", "left": "host_name", "right": host_name},
                    {"op": "=", "left": "is_service", "right": "0"},
                ],
            }

            host_params = {"query": json.dumps(host_query)}
            host_result = self.client.get("domain-types/downtime/collections/all", params=host_params)

            if not host_result.get("success"):
                self.logger.warning(f"Failed to query host downtimes for {host_name}")
                return False

            host_downtimes = host_result["data"].get("value", [])
            current_time = datetime.datetime.now().timestamp()

            # Check if any host downtime is currently active
            for downtime in host_downtimes:
                if self._is_downtime_active(downtime, current_time):
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking host-level downtime for {host_name}: {e}")
            return False

    async def _get_current_downtimes(
        self, host_name: str, service_descriptions: List[str], comment: str = None
    ) -> List[str]:
        """Get current downtimes for a host/services, based on working CheckMK example"""
        filters = []
        is_service = len(service_descriptions) > 0

        if is_service:
            # Handle list of service descriptions with proper filtering
            if len(service_descriptions) > 1:
                # Create OR filter for multiple services
                service_filters = [
                    f'{{"op": "~", "left": "service_description", "right": "{s}"}}' for s in service_descriptions
                ]
                filters.append(f'{{"op": "or", "expr": [{", ".join(service_filters)}]}}')
            else:
                # Single service filter
                filters.append(f'{{"op": "~", "left": "service_description", "right": "{service_descriptions[0]}"}}')
            filters.append('{"op": "=", "left": "is_service", "right": "1"}')
        else:
            # Host downtime filter
            filters.append('{"op": "=", "left": "is_service", "right": "0"}')

        # Add host name filter
        filters.append(f'{{"op": "~", "left": "host_name", "right": "{host_name}"}}')

        # Add comment filter if provided
        if comment:
            filters.append(f'{{"op": "~", "left": "comment", "right": "{comment}"}}')

        # Build query parameters
        query = f'{{"op": "and", "expr": [{", ".join(filters)}]}}'
        params = {"query": query}

        try:
            # Query existing downtimes
            result = self.client.get("domain-types/downtime/collections/all", params=params)

            if result.get("success"):
                downtimes = result["data"].get("value", [])

                if is_service:
                    # Return list of service descriptions that already have downtimes
                    existing_services = []
                    for dt in downtimes:
                        extensions = dt.get("extensions", {})
                        service_desc = extensions.get("service_description")
                        if service_desc and service_desc not in existing_services:
                            existing_services.append(service_desc)
                    return existing_services
                else:
                    # For hosts, return ["HOST"] if downtime exists, empty list if not
                    return ["HOST"] if len(downtimes) > 0 else []
            else:
                self.logger.warning(f"Failed to query existing downtimes: {result.get('data', {})}")
                return []

        except Exception as e:
            self.logger.warning(f"Error querying existing downtimes: {e}")
            return []

    async def _verify_downtime_creation(
        self, host_name: str, comment: str, max_retries: int = 5, services: List[str] = None
    ) -> bool:
        """
        Verify downtime creation with retry logic (based on working CheckMK example).
        Retry up to max_retries times at 5-second intervals.
        """
        import asyncio

        is_service = services and len(services) > 0

        for retry in range(max_retries):
            try:
                # Enhanced query parameters based on working example
                query_filters = []

                # Host name filter
                query_filters.append(f'{{"op": "=", "left": "host_name", "right": "{host_name}"}}')

                # Comment filter
                if comment:
                    query_filters.append(f'{{"op": "=", "left": "comment", "right": "{comment}"}}')

                # Type filter (based on working example pattern)
                if is_service:
                    query_filters.append('{"op": "=", "left": "type", "right": "3"}')  # Service downtime type
                else:
                    query_filters.append('{"op": "=", "left": "type", "right": "2"}')  # Host downtime type

                # Build query
                query = f'{{"op": "and", "expr": [{", ".join(query_filters)}]}}'

                # Enhanced parameters based on working example
                params = {"host_name": host_name, "query": query}

                # Add service-specific parameters
                if is_service:
                    params["downtime_type"] = "service"
                else:
                    params["downtime_type"] = "host"

                # Add site_id if available (based on working example)
                if hasattr(self.client, "config") and hasattr(self.client.config, "site"):
                    params["site_id"] = self.client.config.site

                self.logger.debug(f"Verification attempt {retry + 1}/{max_retries} with params: {params}")

                # Check if downtime was created
                result = self.client.get("domain-types/downtime/collections/all", params=params)

                if result.get("success"):
                    downtimes = result["data"].get("value", [])
                    if len(downtimes) > 0:
                        self.logger.info(f"Downtime verification successful after {retry + 1} attempts")
                        return True

                # Wait 5 seconds before next retry (except on last attempt)
                if retry < max_retries - 1:
                    self.logger.debug(f"Verification attempt {retry + 1} failed, retrying in 5 seconds...")
                    await asyncio.sleep(5)

            except Exception as e:
                self.logger.warning(f"Error during verification attempt {retry + 1}: {e}")
                if retry < max_retries - 1:
                    await asyncio.sleep(5)

        self.logger.warning(f"Downtime verification failed after {max_retries} attempts")
        return False
