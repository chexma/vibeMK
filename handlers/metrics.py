"""
Metrics and performance data handlers for RRD access
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class MetricsHandler(BaseHandler):
    """Handle metrics and performance data operations"""

    # CheckMK REST API status codes with dedicated diagnostics.
    _HTTP_BAD_REQUEST = 400
    _HTTP_NOT_ACCEPTABLE = 406
    _HTTP_UNSUPPORTED_MEDIA_TYPE = 415

    # Display/formatting limits for large responses.
    _MAX_DISPLAYED_METRICS = 5
    _MAX_PERF_DATA_ITEMS = 10
    _MAX_LISTED_METRICS = 20

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle metrics-related tool calls"""

        try:
            if tool_name == "vibemk_get_host_metrics":
                return await self._get_host_metrics(arguments)
            if tool_name == "vibemk_get_service_metrics":
                return await self._get_service_metrics(arguments)
            if tool_name == "vibemk_get_custom_graph":
                return await self._get_custom_graph(arguments)
            if tool_name == "vibemk_search_metrics":
                return await self._search_metrics(arguments)
            if tool_name == "vibemk_list_available_metrics":
                return await self._list_available_metrics(arguments)
            return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception("Error in %s", tool_name)
            return self.error_response("Unexpected Error", str(e))

    def _parse_time_range(self, time_range: str) -> Dict[str, str]:
        """Build the UTC window CheckMK expects for a named range.

        A timestamp without an offset is read as site local time, so a server
        whose host runs in a different zone than the site silently asks for the
        wrong window. UTC with a Z suffix — the form CheckMK's own
        reorganize_time_range docstring uses — removes that coupling.
        """
        spans = {
            "1h": timedelta(hours=1),
            "4h": timedelta(hours=4),
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        now = datetime.now(timezone.utc)
        start = now - spans.get(time_range, timedelta(hours=1))
        return {
            "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def _http_error_message(
        self,
        http_status: int,
        error_data: Dict[str, Any],
        host_name: str = "",
        service_description: str = "",
        metric_name: str = "",
    ) -> Optional[str]:
        """Map a recognized CheckMK HTTP error status to a diagnostic message.

        Returns None when the status isn't one of the specifically handled
        codes, so callers can fall back to their own generic message.
        """
        if http_status == self._HTTP_BAD_REQUEST:
            return self._handle_400_error(error_data, host_name, service_description, metric_name)
        if http_status == self._HTTP_NOT_ACCEPTABLE:
            return self._handle_406_error(error_data)
        if http_status == self._HTTP_UNSUPPORTED_MEDIA_TYPE:
            return self._handle_415_error(error_data)
        return None

    async def _get_host_metrics(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get host metrics using CheckMK REST API metrics endpoint"""
        host_name = arguments.get("host_name")
        metric_name = arguments.get("metric_name")
        time_range = arguments.get("time_range", "1h")
        reduce_function = arguments.get("reduce", "max")

        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        # Parse time range to Unix timestamps
        time_data = self._parse_time_range(time_range)

        # For host metrics, we need a different approach since hosts don't have services
        # Try common host metric IDs or get available host metrics
        if not metric_name:
            return [
                {
                    "type": "text",
                    "text": (
                        f"📊 **Host Metrics for {host_name}**\n\n"
                        f"**Common Host Metric IDs:**\n"
                        f"• cpu_util_guest - Guest CPU utilization\n"
                        f"• cpu_util_steal - Stolen CPU time\n"
                        f"• cpu_util_system - System CPU utilization\n"
                        f"• cpu_util_user - User CPU utilization\n"
                        f"• cpu_util_wait - CPU wait time\n"
                        f"• load1 - 1-minute load average\n"
                        f"• load15 - 15-minute load average\n"
                        f"• load5 - 5-minute load average\n\n"
                        f"💡 **Usage:** Specify metric_name parameter with one of these IDs\n"
                        f"📝 **Note:** Host metrics depend on which services are configured for this host"
                    ),
                }
            ]

        # Build metrics request for specific host metric
        data = {
            "time_range": time_data,
            "reduce": reduce_function,
            "site": getattr(self.client.config, "site", "cmk"),
            "host_name": host_name,
            "type": "single_metric",
            "metric_id": metric_name,
        }

        self.logger.debug("Requesting host metrics with data: %s", data)

        try:
            result = self.client.post("domain-types/metric/actions/get/invoke", data=data)
            metrics_data = result["data"]

            # Format metrics response
            return [
                {
                    "type": "text",
                    "text": self._format_host_metrics_response(host_name, metric_name, metrics_data, time_range),
                }
            ]
        except CheckMKError as e:
            # Handle host metrics request failure with detailed HTTP status analysis
            http_status = getattr(e, "status_code", 0)
            error_data = getattr(e, "error_data", {})
            self.logger.debug("Host metrics request failed: HTTP %s, %s", http_status, error_data)

            error_msg = (
                self._http_error_message(http_status, error_data, host_name, "", metric_name)
                or f"HTTP {http_status}: {error_data.get('title', str(e))}"
            )

            return self.error_response(
                "Failed to retrieve host metrics",
                f"Could not get metric '{metric_name}' for host '{host_name}': {error_msg}",
            )

    async def _get_service_metrics(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get service metrics using CheckMK REST API metrics endpoint"""
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")
        metric_name = arguments.get("metric_name")
        time_range = arguments.get("time_range", "1h")
        reduce_function = arguments.get("reduce", "max")

        if not host_name or not service_description:
            return self.error_response("Missing parameters", "host_name and service_description are required")

        # Parse time range to Unix timestamps
        time_data = self._parse_time_range(time_range)

        # If no specific metric requested, try to get available metrics first
        if not metric_name:
            try:
                # Get service info to find available metrics
                service_result = self.client.get(
                    f"objects/host/{host_name}/actions/show_service/invoke",
                    params={"service_description": service_description},
                )

                if service_result.get("success") and "extensions" in service_result.get("data", {}):
                    extensions = service_result["data"]["extensions"]
                    perf_data = extensions.get("perf_data", {})

                    if perf_data:
                        available_metrics = list(perf_data.keys())
                        return [
                            {
                                "type": "text",
                                "text": (
                                    f"📊 **Available Metrics for {host_name}/{service_description}**\n\n"
                                    f"**Available Metric IDs:** {', '.join(available_metrics)}\n\n"
                                    f"💡 **Usage:** Specify metric_name parameter with one of these IDs\n\n"
                                    f"**Current Performance Data:**\n"
                                    + "\n".join(
                                        [f"• {k}: {v}" for k, v in list(perf_data.items())[: self._MAX_PERF_DATA_ITEMS]]
                                    )
                                ),
                            }
                        ]
                    return self.error_response(
                        "No Metrics Available",
                        f"Service '{service_description}' has no performance metrics available",
                    )
            except Exception as e:
                self.logger.debug("Could not retrieve available metrics: %s", e)
                return self.error_response(
                    "Service Lookup Failed",
                    f"Could not get service information for '{host_name}/{service_description}'",
                )

        # Build metrics request for specific metric
        data = {
            "time_range": time_data,
            "reduce": reduce_function,
            "site": getattr(self.client.config, "site", "cmk"),
            "host_name": host_name,
            "service_description": service_description,
            "type": "single_metric",
            "metric_id": metric_name,
        }

        self.logger.debug("Requesting metrics with data: %s", data)

        try:
            result = self.client.post("domain-types/metric/actions/get/invoke", data=data)
            metrics_data = result["data"]

            # Format metrics response
            return [
                {
                    "type": "text",
                    "text": self._format_service_metrics_response(
                        host_name, service_description, metric_name or "", metrics_data, time_range
                    ),
                }
            ]
        except CheckMKError as e:
            # Handle metrics request failure with detailed HTTP status analysis
            http_status = getattr(e, "status_code", 0)
            error_data = getattr(e, "error_data", {})
            self.logger.debug("Metrics request failed: HTTP %s, %s", http_status, error_data)

            error_msg = (
                self._http_error_message(http_status, error_data, host_name, service_description, metric_name or "")
                or f"HTTP {http_status}: {error_data.get('title', str(e))}"
            )

            # Try to get available metrics for helpful error message
            try:
                service_result = self.client.get(
                    f"objects/host/{host_name}/actions/show_service/invoke",
                    params={"service_description": service_description},
                )

                extensions = service_result["data"]["extensions"]
                perf_data = extensions.get("perf_data", {})

                if perf_data:
                    available_metrics = list(perf_data.keys())

                    return [
                        {
                            "type": "text",
                            "text": (
                                f"❌ **Metrics Request Failed**\n\n"
                                f"Service: {host_name}/{service_description}\n"
                                f"Requested metric: {metric_name}\n"
                                f"Error: {error_msg}\n\n"
                                f"✅ **Available Metrics:** {', '.join(available_metrics)}\n\n"
                                f"💡 **Suggestion:** Try one of these metric IDs instead"
                            ),
                        }
                    ]
            except Exception as e2:
                self.logger.debug("Service lookup for error message failed: %s", e2)

            return self.error_response(
                "Failed to retrieve service metrics",
                f"Could not get metrics for '{metric_name}' on '{host_name}/{service_description}': {error_msg}",
            )

    async def _list_available_metrics(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List available metrics for a host/service"""
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")

        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        # Get host with metrics column to see available metrics
        query_data = {"query": {"op": "=", "left": "name", "right": host_name}}

        if service_description:
            # Get service metrics
            query_data["query"] = {
                "op": "and",
                "expr": [
                    {"op": "=", "left": "host_name", "right": host_name},
                    {"op": "=", "left": "description", "right": service_description},
                ],
            }
            result = self.client.get("domain-types/service/collections/all", params=query_data)
        else:
            # Get host metrics
            result = self.client.get("domain-types/host/collections/all", params=query_data)

        if not result.get("success"):
            return self.error_response("Failed to retrieve metrics list")

        items = result["data"].get("value", [])
        if not items:
            return self.error_response("Host/service not found", f"No data found for {host_name}")

        item = items[0]
        extensions = item.get("extensions", {})
        available_metrics = extensions.get("metrics", [])

        if not available_metrics:
            return [
                {
                    "type": "text",
                    "text": f"📊 **No Metrics Available**\n\nNo historical metrics found for {host_name}"
                    + (f"/{service_description}" if service_description else ""),
                }
            ]

        metric_list = "\n".join([f"📈 {metric}" for metric in available_metrics[: self._MAX_LISTED_METRICS]])

        return [
            {
                "type": "text",
                "text": (
                    f"📊 **Available Metrics**\n\n"
                    f"Target: {host_name}" + (f"/{service_description}" if service_description else "") + f"\n"
                    f"Metrics ({len(available_metrics)} total):\n\n"
                    f"{metric_list}"
                    + (
                        f"\n\n... and {len(available_metrics) - self._MAX_LISTED_METRICS} more metrics"
                        if len(available_metrics) > self._MAX_LISTED_METRICS
                        else ""
                    )
                ),
            }
        ]

    def _format_metrics_response(
        self, target: str, target_type: str, metrics_data: Dict[str, Any], time_range: str
    ) -> str:
        """Format metrics data into readable text"""
        # CheckMK API returns metrics as a list, not curves
        metrics = metrics_data.get("metrics", [])

        if not metrics:
            return f"📊 **No Metrics Data**\n\nNo data available for {target} in the last {time_range}"

        response = f"📊 **{target_type.title()} Metrics: {target}**\n\n"
        response += f"Time Range: {time_range}\n"
        response += f"Metrics: {len(metrics)} found\n\n"

        for i, metric in enumerate(metrics[: self._MAX_DISPLAYED_METRICS]):
            title = metric.get("title", f"Metric {i+1}")
            color = metric.get("color", "#000000")
            line_type = metric.get("line_type", "line")
            data_points = metric.get("data_points", [])

            if data_points:
                latest_value = data_points[-1] if data_points else "No data"
                response += f"📈 **{title}**\n"
                response += f"   Latest: {latest_value}\n"
                response += f"   Data points: {len(data_points)}\n"
                response += f"   Line type: {line_type}\n"
                response += f"   Color: {color}\n\n"

        if len(metrics) > self._MAX_DISPLAYED_METRICS:
            response += f"... and {len(metrics) - self._MAX_DISPLAYED_METRICS} more metrics\n"

        response += "\n💡 **Use specific metric_name for detailed data**"

        return response

    def _format_service_metrics_response(
        self, host_name: str, service_description: str, metric_name: str, metrics_data: Dict[str, Any], time_range: str
    ) -> str:
        """Format service metrics response with detailed information"""
        # CheckMK API returns metrics as a list, not curves
        metrics = metrics_data.get("metrics", [])

        if not metrics:
            return (
                f"📊 **No Metrics Data**\n\n"
                f"No data available for metric '{metric_name}' on {host_name}/{service_description} "
                f"in the last {time_range}"
            )

        response = f"📊 **Service Metrics: {host_name}/{service_description}**\n\n"
        response += f"Metric: {metric_name}\n"
        response += f"Time Range: {time_range}\n"
        response += f"Metrics: {len(metrics)}\n\n"

        for i, metric in enumerate(metrics):
            title = metric.get("title", f"Metric {i+1}")
            color = metric.get("color", "#000000")
            line_type = metric.get("line_type", "line")
            data_points = metric.get("data_points", [])

            if data_points:
                # Filter out None values for calculations
                valid_points = [p for p in data_points if p is not None]

                latest_value = data_points[-1] if data_points else "No data"
                if valid_points:
                    min_value = min(valid_points)
                    max_value = max(valid_points)
                    avg_value = sum(valid_points) / len(valid_points)
                else:
                    min_value = max_value = avg_value = "N/A"

                response += f"📈 **{title}**\n"
                response += f"   Latest Value: {latest_value}\n"
                response += f"   Min/Max/Avg: {min_value} / {max_value} / {avg_value:.2f}\n"
                response += f"   Data Points: {len(data_points)}\n"
                response += f"   Line Type: {line_type}\n"
                response += f"   Color: {color}\n\n"

        response += "💡 **Tip:** Use different time_range values (4h, 24h, 7d, 30d) for longer periods"

        return response

    def _format_host_metrics_response(
        self, host_name: str, metric_name: str, metrics_data: Dict[str, Any], time_range: str
    ) -> str:
        """Format host metrics response with detailed information"""
        # CheckMK API returns metrics as a list, not curves
        metrics = metrics_data.get("metrics", [])

        if not metrics:
            return (
                f"📊 **No Metrics Data**\n\n"
                f"No data available for metric '{metric_name}' on host {host_name} in the last {time_range}"
            )

        response = f"📊 **Host Metrics: {host_name}**\n\n"
        response += f"Metric: {metric_name}\n"
        response += f"Time Range: {time_range}\n"
        response += f"Metrics: {len(metrics)}\n\n"

        for i, metric in enumerate(metrics):
            title = metric.get("title", f"Metric {i+1}")
            color = metric.get("color", "#000000")
            line_type = metric.get("line_type", "line")
            data_points = metric.get("data_points", [])

            if data_points:
                # Filter out None values for calculations
                valid_points = [p for p in data_points if p is not None]

                latest_value = data_points[-1] if data_points else "No data"
                if valid_points:
                    min_value = min(valid_points)
                    max_value = max(valid_points)
                    avg_value = sum(valid_points) / len(valid_points)
                else:
                    min_value = max_value = avg_value = "N/A"

                response += f"📈 **{title}**\n"
                response += f"   Latest Value: {latest_value}\n"
                response += f"   Min/Max/Avg: {min_value} / {max_value} / {avg_value:.2f}\n"
                response += f"   Data Points: {len(data_points)}\n"
                response += f"   Line Type: {line_type}\n"
                response += f"   Color: {color}\n\n"

        response += "💡 **Tip:** Use different time_range values (4h, 24h, 7d, 30d) for longer periods"

        return response

    def _handle_400_error(
        self, error_data: Dict[str, Any], host_name: str, service_description: str, metric_name: str
    ) -> str:
        """Handle HTTP 400 Bad Request errors with specific diagnostics"""
        title = error_data.get("title", "Bad Request")
        detail = error_data.get("detail", "")

        # Check for specific parameter validation issues
        if "time_range" in detail or "start" in detail or "end" in detail:
            return (
                f"Time range parameter error: {detail}. "
                "Timestamps are sent as ISO-8601 UTC, e.g. 2026-09-14T12:00:00Z"
            )
        if "metric_id" in detail or metric_name in detail:
            return f"Invalid metric ID '{metric_name}': {detail}. Metric may not exist for this service"
        if "host_name" in detail or host_name in detail:
            return f"Host parameter error: {detail}. Host '{host_name}' may not exist"
        if "service_description" in detail or service_description in detail:
            return (
                f"Service parameter error: {detail}. "
                f"Service '{service_description}' may not exist on host '{host_name}'"
            )
        if "site" in detail:
            return f"Site parameter error: {detail}. Check CheckMK site configuration"
        return f"Parameter validation failed: {title} - {detail}"

    def _handle_406_error(self, error_data: Dict[str, Any]) -> str:
        """Handle HTTP 406 Not Acceptable errors"""
        title = error_data.get("title", "Not Acceptable")
        detail = error_data.get("detail", "")

        return f"Accept header issue: {title}. CheckMK API cannot satisfy the requested content type. Detail: {detail}"

    def _handle_415_error(self, error_data: Dict[str, Any]) -> str:
        """Handle HTTP 415 Unsupported Media Type errors"""
        title = error_data.get("title", "Unsupported Media Type")
        detail = error_data.get("detail", "")

        return f"Content-Type issue: {title}. Request content type not supported by CheckMK API. Detail: {detail}"

    async def _get_custom_graph(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get custom graph data"""
        custom_graph_id = arguments.get("custom_graph_id")
        time_range = arguments.get("time_range", "1h")
        reduce_function = arguments.get("reduce", "max")

        if not custom_graph_id:
            return self.error_response("Missing parameter", "custom_graph_id is required")

        # Parse time range
        time_data = self._parse_time_range(time_range)

        data = {"time_range": time_data, "reduce": reduce_function, "custom_graph_id": custom_graph_id}

        try:
            result = self.client.post("domain-types/metric/actions/get_custom_graph/invoke", data=data)
            metrics_data = result["data"]
            return [
                {"type": "text", "text": self._format_custom_graph_response(custom_graph_id, metrics_data, time_range)}
            ]
        except CheckMKError as e:
            http_status = getattr(e, "status_code", 0)
            error_data = getattr(e, "error_data", {})

            if http_status == 400:
                error_msg = self._handle_400_error(error_data, "", "", custom_graph_id)
            elif http_status == 406:
                error_msg = self._handle_406_error(error_data)
            elif http_status == 415:
                error_msg = self._handle_415_error(error_data)
            else:
                error_msg = f"HTTP {http_status}: {str(e)}"

            return self.error_response(
                "Failed to retrieve custom graph", f"Could not get custom graph '{custom_graph_id}': {error_msg}"
            )

    async def _search_metrics(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for metrics using filters"""
        host_filter = arguments.get("host_filter")
        service_filter = arguments.get("service_filter")
        site_filter = arguments.get("site_filter", self.client.config.site)
        time_range = arguments.get("time_range", "1h")
        reduce_function = arguments.get("reduce", "max")

        if not host_filter:
            return self.error_response("Missing parameter", "host_filter is required")

        # Parse time range
        time_data = self._parse_time_range(time_range)

        # Build filter
        filter_data = {"siteopt": {"site": site_filter}, "host": {"host": host_filter}}

        if service_filter:
            filter_data["service"] = {"service": service_filter}

        data = {"time_range": time_data, "reduce": reduce_function, "filter": filter_data, "type": "predefined_graph"}

        result = self.client.post("domain-types/metric/actions/filter/invoke", data=data)

        if not result.get("success"):
            return self.error_response("Failed to search metrics", "Metrics search failed")

        metrics_data = result["data"]

        return [
            {"type": "text", "text": self._format_search_results(host_filter, service_filter, metrics_data, time_range)}
        ]
