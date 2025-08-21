"""
Metrics and performance data handlers for RRD access
"""

import datetime
from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class MetricsHandler(BaseHandler):
    """Handle metrics and performance data operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle metrics-related tool calls"""

        try:
            if tool_name == "vibemk_get_host_metrics":
                return await self._get_host_metrics(arguments)
            elif tool_name == "vibemk_get_service_metrics":
                return await self._get_service_metrics(arguments)
            elif tool_name == "vibemk_get_custom_graph":
                return await self._get_custom_graph(arguments)
            elif tool_name == "vibemk_search_metrics":
                return await self._search_metrics(arguments)
            elif tool_name == "vibemk_list_available_metrics":
                return await self._list_available_metrics(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    def _parse_time_range(self, time_range: str) -> Dict[str, str]:
        """Parse time range string into start/end datetime strings for CheckMK API"""
        import datetime

        now = datetime.datetime.now()

        if time_range == "1h":
            start_time = now - datetime.timedelta(hours=1)
        elif time_range == "4h":
            start_time = now - datetime.timedelta(hours=4)
        elif time_range == "24h":
            start_time = now - datetime.timedelta(days=1)
        elif time_range == "7d":
            start_time = now - datetime.timedelta(days=7)
        elif time_range == "30d":
            start_time = now - datetime.timedelta(days=30)
        else:
            # Default to 1 hour
            start_time = now - datetime.timedelta(hours=1)

        # Format as strings without microseconds (CheckMK requirement)
        return {"start": start_time.strftime("%Y-%m-%d %H:%M:%S"), "end": now.strftime("%Y-%m-%d %H:%M:%S")}

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

        self.logger.debug(f"Requesting host metrics with data: {data}")
        result = self.client.post("domain-types/metric/actions/get/invoke", data=data)

        if result.get("success"):
            metrics_data = result["data"]

            # Format metrics response
            return [
                {
                    "type": "text",
                    "text": self._format_host_metrics_response(host_name, metric_name, metrics_data, time_range),
                }
            ]
        else:
            error_data = result.get("data", {})
            return self.error_response(
                "Failed to retrieve host metrics",
                f"Could not get metric '{metric_name}' for host '{host_name}': {error_data.get('title', str(error_data))}",
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
                                    f"📊 **Available Metrics for {host_name}/{service_description}**\\n\\n"
                                    f"**Available Metric IDs:** {', '.join(available_metrics)}\\n\\n"
                                    f"💡 **Usage:** Specify metric_name parameter with one of these IDs\\n\\n"
                                    f"**Current Performance Data:**\\n"
                                    + "\\n".join([f"• {k}: {v}" for k, v in list(perf_data.items())[:10]])
                                ),
                            }
                        ]
                    else:
                        return self.error_response(
                            "No Metrics Available",
                            f"Service '{service_description}' has no performance metrics available",
                        )
            except Exception as e:
                self.logger.debug(f"Could not retrieve available metrics: {e}")
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

        self.logger.debug(f"Requesting metrics with data: {data}")
        result = self.client.post("domain-types/metric/actions/get/invoke", data=data)

        if result.get("success"):
            metrics_data = result["data"]

            # Format metrics response
            return [
                {
                    "type": "text",
                    "text": self._format_service_metrics_response(
                        host_name, service_description, metric_name, metrics_data, time_range
                    ),
                }
            ]
        else:
            # Handle metrics request failure
            error_data = result.get("data", {})
            self.logger.debug(f"Metrics request failed: {error_data}")

            # Try to get available metrics for helpful error message
            try:
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
                                    f"❌ **Metrics Request Failed**\\n\\n"
                                    f"Service: {host_name}/{service_description}\\n"
                                    f"Requested metric: {metric_name}\\n"
                                    f"Error: {error_data.get('title', 'Unknown error')}\\n\\n"
                                    f"✅ **Available Metrics:** {', '.join(available_metrics)}\\n\\n"
                                    f"💡 **Suggestion:** Try one of these metric IDs instead"
                                ),
                            }
                        ]
            except Exception as e:
                self.logger.debug(f"Service lookup for error message failed: {e}")

            return self.error_response(
                "Failed to retrieve service metrics",
                f"Could not get metrics for '{metric_name}' on '{host_name}/{service_description}': {error_data.get('title', str(error_data))}",
            )

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

        result = self.client.post("domain-types/metric/actions/get_custom_graph/invoke", data=data)

        if not result.get("success"):
            return self.error_response(
                "Failed to retrieve custom graph", f"Could not get custom graph '{custom_graph_id}'"
            )

        metrics_data = result["data"]

        return [{"type": "text", "text": self._format_custom_graph_response(custom_graph_id, metrics_data, time_range)}]

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

    async def _list_available_metrics(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List available metrics for a host/service"""
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")

        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        # Get host with metrics column to see available metrics
        query_data = {"query": f'{{"op": "=", "left": "name", "right": "{host_name}"}}'}

        if service_description:
            # Get service metrics
            query_data["query"] = (
                f'{{"op": "and", "expr": [{{"op": "=", "left": "host_name", "right": "{host_name}"}}, {{"op": "=", "left": "description", "right": "{service_description}"}}]}}'
            )
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

        metric_list = "\n".join([f"📈 {metric}" for metric in available_metrics[:20]])

        return [
            {
                "type": "text",
                "text": (
                    f"📊 **Available Metrics**\n\n"
                    f"Target: {host_name}" + (f"/{service_description}" if service_description else "") + f"\n"
                    f"Metrics ({len(available_metrics)} total):\n\n"
                    f"{metric_list}"
                    + (f"\n\n... and {len(available_metrics) - 20} more metrics" if len(available_metrics) > 20 else "")
                ),
            }
        ]

    def _format_metric_data(self, metric_data: Dict) -> str:
        """Format individual metric data for display"""
        if not metric_data:
            return "No data available"

        # Handle different response formats from CheckMK metrics API
        if "curves" in metric_data:
            curves = metric_data.get("curves", [])
            if curves:
                result = []
                for i, curve in enumerate(curves[:3]):  # Show first 3 curves
                    title = curve.get("title", f"Curve {i+1}")
                    points = curve.get("points", [])
                    if points:
                        latest_value = points[-1] if isinstance(points[-1], (int, float)) else points[-1]
                        result.append(f"{title}: {latest_value} ({len(points)} data points)")
                    else:
                        result.append(f"{title}: No data points")
                return "\\n".join(result)

        elif "values" in metric_data:
            values = metric_data.get("values", [])
            if values:
                return f"Values: {values[:5]}{'...' if len(values) > 5 else ''}"

        elif "value" in metric_data:
            return f"Value: {metric_data['value']}"

        # Fallback: show raw data structure
        return str(metric_data)[:200] + ("..." if len(str(metric_data)) > 200 else "")

    def _format_metrics_response(self, target: str, target_type: str, metrics_data: Dict, time_range: str) -> str:
        """Format metrics data into readable text"""
        # CheckMK API returns metrics as a list, not curves
        metrics = metrics_data.get("metrics", [])

        if not metrics:
            return f"📊 **No Metrics Data**\n\nNo data available for {target} in the last {time_range}"

        response = f"📊 **{target_type.title()} Metrics: {target}**\n\n"
        response += f"Time Range: {time_range}\n"
        response += f"Metrics: {len(metrics)} found\n\n"

        for i, metric in enumerate(metrics[:5]):  # Limit to 5 metrics
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

        if len(metrics) > 5:
            response += f"... and {len(metrics) - 5} more metrics\n"

        response += f"\n💡 **Use specific metric_name for detailed data**"

        return response

    def _format_custom_graph_response(self, graph_id: str, metrics_data: Dict, time_range: str) -> str:
        """Format custom graph response"""
        return f"📊 **Custom Graph: {graph_id}**\n\nTime Range: {time_range}\n\n" + self._format_metrics_response(
            graph_id, "custom graph", metrics_data, time_range
        )

    def _format_search_results(self, host_filter: str, service_filter: str, metrics_data: Dict, time_range: str) -> str:
        """Format search results"""
        target = f"{host_filter}" + (f"/{service_filter}" if service_filter else "")
        return f"🔍 **Metrics Search Results**\n\nFilter: {target}\n\n" + self._format_metrics_response(
            target, "search", metrics_data, time_range
        )

    def _format_service_metrics_response(
        self, host_name: str, service_description: str, metric_name: str, metrics_data: Dict, time_range: str
    ) -> str:
        """Format service metrics response with detailed information"""
        # CheckMK API returns metrics as a list, not curves
        metrics = metrics_data.get("metrics", [])

        if not metrics:
            return f"📊 **No Metrics Data**\n\nNo data available for metric '{metric_name}' on {host_name}/{service_description} in the last {time_range}"

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

        response += f"💡 **Tip:** Use different time_range values (4h, 24h, 7d, 30d) for longer periods"

        return response

    def _format_host_metrics_response(
        self, host_name: str, metric_name: str, metrics_data: Dict, time_range: str
    ) -> str:
        """Format host metrics response with detailed information"""
        # CheckMK API returns metrics as a list, not curves
        metrics = metrics_data.get("metrics", [])

        if not metrics:
            return f"📊 **No Metrics Data**\n\nNo data available for metric '{metric_name}' on host {host_name} in the last {time_range}"

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

        response += f"💡 **Tip:** Use different time_range values (4h, 24h, 7d, 30d) for longer periods"

        return response
