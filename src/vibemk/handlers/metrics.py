"""
Metrics and performance data handlers for RRD access
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from vibemk.api.exceptions import CheckMKError
from vibemk.handlers.base import BaseHandler


def series_summary(metric: Dict[str, Any]) -> Dict[str, Any]:
    """One curve of a metric answer, reduced to what a reader compares.

    CheckMK's newest bucket is usually still empty, so the latest value is the
    last point that carries one, not the last point.
    """
    points = metric.get("data_points") or []
    values = [p for p in points if isinstance(p, (int, float)) and not isinstance(p, bool)]
    return {
        "title": str(metric.get("title", "")),
        "points": len(points),
        "latest": values[-1] if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "avg": round(sum(values) / len(values), 4) if values else None,
    }


class MetricsHandler(BaseHandler):
    """Handle metrics and performance data operations"""

    # CheckMK REST API status codes with dedicated diagnostics.
    _HTTP_BAD_REQUEST = 400
    _HTTP_NOT_ACCEPTABLE = 406
    _HTTP_UNSUPPORTED_MEDIA_TYPE = 415

    # Display/formatting limits for large responses.
    _MAX_DISPLAYED_METRICS = 5
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

        if not metric_name:
            return self._metric_listing(host_name, None)

        # Build metrics request for specific host metric
        data = {
            "time_range": time_data,
            "reduce": reduce_function,
            "site": getattr(self.client.config, "site", "cmk"),
            "host_name": host_name,
            # The endpoint requires a service; a host's own metrics (the host
            # check's rta, pl, ...) sit under CheckMK's pseudo-service _HOST_.
            # Without it every host metric request answered 400.
            "service_description": "_HOST_",
            "type": "single_metric",
            "metric_id": metric_name,
        }

        self.logger.debug("Requesting host metrics with data: %s", data)

        try:
            result = self.client.post("domain-types/metric/actions/get/invoke", data=data)
            metrics_data = result["data"]

            # Format metrics response
            return self.structured_response(
                self._format_host_metrics_response(host_name, metric_name, metrics_data, time_range),
                self._series_data(host_name, None, metric_name, time_range, metrics_data),
            )
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

        # Without a metric, say which ones the service has. show_service cannot
        # answer that: on 2.5 it returns no perf_data at all, so this used to
        # report "no performance metrics" for every service.
        if not metric_name:
            return self._metric_listing(host_name, service_description)

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
            return self.structured_response(
                self._format_service_metrics_response(
                    host_name, service_description, metric_name or "", metrics_data, time_range
                ),
                self._series_data(host_name, service_description, metric_name, time_range, metrics_data),
            )
        except CheckMKError as e:
            # Handle metrics request failure with detailed HTTP status analysis
            http_status = getattr(e, "status_code", 0)
            error_data = getattr(e, "error_data", {})
            self.logger.debug("Metrics request failed: HTTP %s, %s", http_status, error_data)

            error_msg = (
                self._http_error_message(http_status, error_data, host_name, service_description, metric_name or "")
                or f"HTTP {http_status}: {error_data.get('title', str(e))}"
            )

            # Name the metrics the service does have, so the next attempt can succeed
            try:
                available_metrics = self._available_metrics(host_name, service_description)
                if available_metrics:
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

        return self._metric_listing(host_name, service_description)

    def _available_metrics(self, host_name: str, service_description: Optional[str]) -> Optional[List[str]]:
        """The metric IDs CheckMK records for a host or service; None when it does not exist.

        The monitoring collections answer this in their `metrics` column, but
        only when it is asked for: without `columns` they return host_name and
        description alone, which is why the listing reported no metrics anywhere.
        """
        if service_description:
            result = self.client.get(
                "domain-types/service/collections/all",
                params={
                    "columns": ["host_name", "description", "metrics"],
                    "query": {
                        "op": "and",
                        "expr": [
                            {"op": "=", "left": "host_name", "right": host_name},
                            {"op": "=", "left": "description", "right": service_description},
                        ],
                    },
                },
            )
        else:
            result = self.client.get(
                "domain-types/host/collections/all",
                params={"columns": ["name", "metrics"], "query": {"op": "=", "left": "name", "right": host_name}},
            )

        if not result.get("success"):
            raise CheckMKError("Failed to retrieve metrics list")

        items = result.get("data", {}).get("value", [])
        if not items:
            return None
        metrics = items[0].get("extensions", {}).get("metrics") or []
        return [str(metric) for metric in metrics]

    def _metric_listing(self, host_name: str, service_description: Optional[str]) -> List[Dict[str, Any]]:
        """Answer "which metrics are there" for a host or one of its services."""
        target = f"{host_name}/{service_description}" if service_description else host_name
        available_metrics = self._available_metrics(host_name, service_description)
        if available_metrics is None:
            return self.error_response("Host/service not found", f"No data found for {target}")

        data = {
            "host_name": host_name,
            "service_description": service_description,
            "metric_id": None,
            "available_metrics": available_metrics,
            "series": [],
        }
        if not available_metrics:
            return self.structured_response(
                f"📊 **No Metrics Available**\n\nNo historical metrics found for {target}", data
            )

        metric_list = "\n".join([f"📈 {metric}" for metric in available_metrics[: self._MAX_LISTED_METRICS]])
        more = len(available_metrics) - self._MAX_LISTED_METRICS
        return self.structured_response(
            (
                f"📊 **Available Metrics**\n\n"
                f"Target: {target}\n"
                f"Metrics ({len(available_metrics)} total):\n\n"
                f"{metric_list}"
                + (f"\n\n... and {more} more metrics" if more > 0 else "")
                + "\n\n💡 **Usage:** pass one of these as metric_name to get its values"
            ),
            data,
        )

    def _series_data(
        self,
        host_name: str,
        service_description: Optional[str],
        metric_id: str,
        time_range: str,
        metrics_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """The METRIC_DATA object for a metric answer."""
        window = metrics_data.get("time_range") or {}
        step = metrics_data.get("step")
        return {
            "host_name": host_name,
            "service_description": service_description,
            "metric_id": metric_id,
            "time_range": time_range,
            "start": window.get("start"),
            "end": window.get("end"),
            "step": step if isinstance(step, int) else None,
            "series": [series_summary(metric) for metric in metrics_data.get("metrics", [])],
        }

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
                # The most recent bucket is often still empty, so report the
                # last point that actually carries a value.
                latest_value = next((point for point in reversed(data_points) if point is not None), "No data")
                response += f"📈 **{title}**\n"
                response += f"   Latest: {latest_value}\n"
                response += f"   Data points: {len(data_points)}\n"
                response += f"   Line type: {line_type}\n"
                response += f"   Color: {color}\n\n"

        if len(metrics) > self._MAX_DISPLAYED_METRICS:
            response += f"... and {len(metrics) - self._MAX_DISPLAYED_METRICS} more metrics\n"

        response += "\n💡 **Use specific metric_name for detailed data**"

        return response

    def _format_custom_graph_response(self, graph_id: str, metrics_data: Dict[str, Any], time_range: str) -> str:
        """Format custom graph response"""
        return f"📊 **Custom Graph: {graph_id}**\n\nTime Range: {time_range}\n\n" + self._format_metrics_response(
            graph_id, "custom graph", metrics_data, time_range
        )

    def _format_search_results(
        self, host_filter: str, service_filter: Optional[str], metrics_data: Dict[str, Any], time_range: str
    ) -> str:
        """Format search results"""
        target = f"{host_filter}" + (f"/{service_filter}" if service_filter else "")
        return f"🔍 **Metrics Search Results**\n\nFilter: {target}\n\n" + self._format_metrics_response(
            target, "search", metrics_data, time_range
        )

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
                summary = series_summary(metric)
                if summary["latest"] is None:
                    stats = "N/A (no values in this window)"
                else:
                    stats = f"{summary['min']} / {summary['max']} / {summary['avg']:.2f}"

                response += f"📈 **{title}**\n"
                response += f"   Latest Value: {summary['latest'] if summary['latest'] is not None else 'No data'}\n"
                response += f"   Min/Max/Avg: {stats}\n"
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
                summary = series_summary(metric)
                if summary["latest"] is None:
                    stats = "N/A (no values in this window)"
                else:
                    stats = f"{summary['min']} / {summary['max']} / {summary['avg']:.2f}"

                response += f"📈 **{title}**\n"
                response += f"   Latest Value: {summary['latest'] if summary['latest'] is not None else 'No data'}\n"
                response += f"   Min/Max/Avg: {stats}\n"
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

        graph_id = arguments.get("graph_id")
        metric_id = arguments.get("metric_id")

        if not host_filter:
            return self.error_response("Missing parameter", "host_filter is required")

        # The endpoint returns one named graph or one named metric across every
        # host the filter matches; it has no mode that searches without one.
        if graph_id and metric_id:
            return self.error_response("Conflicting parameters", "Give either graph_id or metric_id, not both")
        if not graph_id and not metric_id:
            return self.error_response(
                "Missing parameter",
                "Either graph_id or metric_id is required. Both are shown in the service view "
                "once 'Show internal IDs' is enabled in its display options — a graph ID in the "
                "graph title, a metric ID in the legend.",
            )

        # Parse time range
        time_data = self._parse_time_range(time_range)

        # Build filter
        filter_data = {"siteopt": {"site": site_filter}, "host": {"host": host_filter}}

        if service_filter:
            filter_data["service"] = {"service": service_filter}

        data: Dict[str, Any] = {"time_range": time_data, "reduce": reduce_function, "filter": filter_data}
        if graph_id:
            data["type"] = "predefined_graph"
            data["graph_id"] = graph_id
        else:
            data["type"] = "single_metric"
            data["metric_id"] = metric_id

        result = self.client.post("domain-types/metric/actions/filter/invoke", data=data)

        if not result.get("success"):
            return self.error_response("Failed to search metrics", "Metrics search failed")

        metrics_data = result["data"]

        return [
            {"type": "text", "text": self._format_search_results(host_filter, service_filter, metrics_data, time_range)}
        ]
