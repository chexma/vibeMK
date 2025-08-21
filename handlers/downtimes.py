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

        if result.get("success"):
            downtime_info = result.get("data", {})
            downtime_id = downtime_info.get("id", "Unknown")

            response = f"✅ **Host Downtime Scheduled Successfully**\n\n"
            response += f"**Host:** {host_name}\n"
            response += f"**Downtime ID:** {downtime_id}\n"
            response += f"**Start:** {downtime_times['start_time']}\n"
            response += f"**End:** {downtime_times['end_time']}\n"
            response += f"**Duration:** {duration_minutes} minutes\n"
            response += f"**Comment:** {comment}\n"
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

        if result.get("success"):
            downtime_info = result.get("data", {})
            downtime_id = downtime_info.get("id", "Unknown")

            response = f"✅ **Service Downtime Scheduled Successfully**\n\n"
            response += f"**Host:** {host_name}\n"
            response += f"**Services:** {', '.join(services_to_schedule)}\n"
            response += f"**Downtime ID:** {downtime_id}\n"
            response += f"**Start:** {downtime_times['start_time']}\n"
            response += f"**End:** {downtime_times['end_time']}\n"
            response += f"**Duration:** {duration_minutes} minutes\n"
            response += f"**Comment:** {comment}\n"

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
        """Parse and convert downtime start/end times to ISO format using CheckMK pattern"""
        from datetime import datetime, timedelta

        # Use datetime.utcnow() to match CheckMK working example
        default_start_time = datetime.utcnow()
        default_end_time = default_start_time + timedelta(minutes=duration_minutes or 30)

        # Parse start time
        if not start_time or start_time == "" or start_time == "now":
            start_dt = default_start_time
        elif start_time.startswith("+"):
            # Relative time like "+1h", "+30m" - parse as start_after
            delta_minutes = self._parse_time_delta(start_time)
            start_dt = datetime.utcnow() + timedelta(minutes=delta_minutes)
        else:
            # Try to parse as ISO format
            try:
                if start_time.endswith("Z"):
                    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                else:
                    start_dt = datetime.fromisoformat(start_time)
            except ValueError:
                # Fallback to default start time if parsing fails
                self.logger.warning(f"Could not parse start_time '{start_time}', using default")
                start_dt = default_start_time

        # Parse end time
        if not end_time or end_time == "":
            # If no end time specified, use start_time + duration (end_after pattern)
            end_dt = start_dt + timedelta(minutes=duration_minutes or 30)
        elif end_time.startswith("+"):
            # Relative to start time (end_after pattern)
            delta_minutes = self._parse_time_delta(end_time)
            end_dt = start_dt + timedelta(minutes=delta_minutes)
        else:
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

    def _format_downtimes_list(self, downtimes: List[Dict], host_filter: str = None) -> str:
        """Format downtimes list for display"""
        if not downtimes:
            filter_text = f" for host '{host_filter}'" if host_filter else ""
            return f"📋 **No Downtimes Found**\n\nNo active downtimes{filter_text}"

        filter_text = f" for host '{host_filter}'" if host_filter else ""
        response = f"📋 **Downtimes List{filter_text}**\n\n"
        response += f"Found {len(downtimes)} downtimes:\n\n"

        for i, downtime in enumerate(downtimes[:10], 1):  # Limit to 10 for readability
            extensions = downtime.get("extensions", {})

            downtime_id = downtime.get("id", "Unknown")
            host_name = extensions.get("host_name", "Unknown")
            comment = extensions.get("comment", "No comment")
            is_service = extensions.get("is_service", 0) == 1
            is_pending = extensions.get("is_pending", 0) == 1

            # Format times (handle both Unix timestamps and ISO format)
            start_time = extensions.get("start_time", 0)
            end_time = extensions.get("end_time", 0)
            start_str = self._format_timestamp(start_time)
            end_str = self._format_timestamp(end_time)

            # Status
            if is_pending:
                status = "🟡 Pending"
            else:
                now = datetime.datetime.now().timestamp()
                start_unix = self._timestamp_to_unix(start_time)
                end_unix = self._timestamp_to_unix(end_time)

                if start_unix <= now <= end_unix:
                    status = "🔴 Active"
                elif now < start_unix:
                    status = "🟡 Scheduled"
                else:
                    status = "✅ Completed"

            response += f"**{i}. Downtime #{downtime_id}**\n"
            response += f"   Host: {host_name}\n"
            response += f"   Type: {'Service' if is_service else 'Host'}\n"
            response += f"   Status: {status}\n"
            response += f"   Start: {start_str}\n"
            response += f"   End: {end_str}\n"
            response += f"   Comment: {comment}\n"

            if is_service and extensions.get("service_description"):
                response += f"   Service: {extensions.get('service_description')}\n"

            response += "\n"

        if len(downtimes) > 10:
            response += f"... and {len(downtimes) - 10} more downtimes\n"

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
