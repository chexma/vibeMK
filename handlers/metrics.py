"""
Metrics and performance data handlers for RRD access
"""

from typing import Dict, Any, List
from handlers.base import BaseHandler
from api.exceptions import CheckMKError
import datetime


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
        """Parse time range string into start/end timestamps"""
        now = datetime.datetime.now()
        
        if time_range == "1h":
            start = now - datetime.timedelta(hours=1)
        elif time_range == "4h":
            start = now - datetime.timedelta(hours=4)
        elif time_range == "24h":
            start = now - datetime.timedelta(hours=24)
        elif time_range == "7d":
            start = now - datetime.timedelta(days=7)
        elif time_range == "30d":
            start = now - datetime.timedelta(days=30)
        else:
            # Default to 1 hour
            start = now - datetime.timedelta(hours=1)
        
        return {
            "start": start.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "end": now.strftime("%Y-%m-%d %H:%M:%S.%f")
        }
    
    async def _get_host_metrics(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get host metrics from RRD data"""
        host_name = arguments.get("host_name")
        metric_name = arguments.get("metric_name")
        time_range = arguments.get("time_range", "1h")
        reduce_function = arguments.get("reduce", "max")
        
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")
        
        # Parse time range
        time_data = self._parse_time_range(time_range)
        
        data = {
            "time_range": time_data,
            "reduce": reduce_function,
            "site": self.client.config.site,
            "host_name": host_name,
            "type": "single_metric" if metric_name else "predefined_graph"
        }
        
        if metric_name:
            data["metric_name"] = metric_name
        else:
            # Get default host metrics (CPU, Memory, etc.)
            data["graph_id"] = "cpu_utilization_simple"
        
        result = self.client.post("domain-types/metric/actions/get/invoke", data=data)
        
        if not result.get("success"):
            return self.error_response("Failed to retrieve host metrics", f"Could not get metrics for host '{host_name}'")
        
        metrics_data = result["data"]
        
        # Format metrics response
        return [{
            "type": "text",
            "text": self._format_metrics_response(host_name, "host", metrics_data, time_range)
        }]
    
    async def _get_service_metrics(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get service metrics from RRD data"""
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")
        metric_name = arguments.get("metric_name")
        time_range = arguments.get("time_range", "1h")
        reduce_function = arguments.get("reduce", "max")
        
        if not host_name or not service_description:
            return self.error_response("Missing parameters", "host_name and service_description are required")
        
        # Parse time range
        time_data = self._parse_time_range(time_range)
        
        data = {
            "time_range": time_data,
            "reduce": reduce_function,
            "site": getattr(self.client.config, 'site', 'cmk'),  # Fallback to 'cmk' if not configured
            "host_name": host_name,
            "service_description": service_description,
            "type": "single_metric" if metric_name else "predefined_graph"
        }
        
        if metric_name:
            data["metric_id"] = metric_name  # Changed from metric_name to metric_id to match cURL example
        
        self.logger.debug(f"Requesting metrics with data: {data}")
        result = self.client.post("domain-types/metric/actions/get/invoke", data=data)
        
        if result.get("success"):
            metrics_data = result["data"]
            
            # Format metrics response
            return [{
                "type": "text",
                "text": self._format_metrics_response(f"{host_name}/{service_description}", "service", metrics_data, time_range)
            }]
        else:
            # If specific metric failed, try to get available metrics for the service
            error_data = result.get("data", {})
            self.logger.debug(f"Metrics request failed: {error_data}")
            
            # Try to get service performance data to show available metrics
            try:
                services_result = self.client.post(f"objects/host/{host_name}/actions/show_service/invoke", data={})
                
                if services_result.get("success"):
                    services_data = services_result.get("data", {})
                    
                    if isinstance(services_data, dict) and "value" in services_data:
                        services = services_data["value"]
                        target_service = None
                        
                        # Find the specific service
                        for service in services:
                            if isinstance(service, dict):
                                extensions = service.get("extensions", {})
                                if extensions.get("description") == service_description:
                                    target_service = service
                                    break
                        
                        if target_service:
                            extensions = target_service.get("extensions", {})
                            perf_data = extensions.get("perf_data", {})
                            
                            if perf_data:
                                # Show available performance data as potential metric IDs
                                available_metrics = list(perf_data.keys())
                                
                                return [{
                                    "type": "text",
                                    "text": (
                                        f"❌ **Service Metrics Request Failed**\\n\\n"
                                        f"Service: {host_name}/{service_description}\\n"
                                        f"Error: {error_data.get('title', 'Unknown error')}\\n\\n"
                                        f"✅ **Available Metrics:** {', '.join(available_metrics)}\\n\\n"
                                        f"💡 **Try again with metric_name parameter:**\\n"
                                        f"Example metric IDs: {', '.join(available_metrics[:3])}\\n\\n"
                                        f"📊 **Current Performance Data:**\\n"
                                        + "\\n".join([f"• {k}: {v}" for k, v in list(perf_data.items())[:5]])
                                    )
                                }]
            except Exception as e:
                self.logger.debug(f"Service lookup for available metrics failed: {e}")
            
            return self.error_response("Failed to retrieve service metrics", 
                                     f"Could not get metrics for service '{host_name}/{service_description}': {error_data.get('title', str(error_data))}")
    
    async def _get_custom_graph(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get custom graph data"""
        custom_graph_id = arguments.get("custom_graph_id")
        time_range = arguments.get("time_range", "1h")
        reduce_function = arguments.get("reduce", "max")
        
        if not custom_graph_id:
            return self.error_response("Missing parameter", "custom_graph_id is required")
        
        # Parse time range
        time_data = self._parse_time_range(time_range)
        
        data = {
            "time_range": time_data,
            "reduce": reduce_function,
            "custom_graph_id": custom_graph_id
        }
        
        result = self.client.post("domain-types/metric/actions/get_custom_graph/invoke", data=data)
        
        if not result.get("success"):
            return self.error_response("Failed to retrieve custom graph", 
                                     f"Could not get custom graph '{custom_graph_id}'")
        
        metrics_data = result["data"]
        
        return [{
            "type": "text",
            "text": self._format_custom_graph_response(custom_graph_id, metrics_data, time_range)
        }]
    
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
        filter_data = {
            "siteopt": {"site": site_filter},
            "host": {"host": host_filter}
        }
        
        if service_filter:
            filter_data["service"] = {"service": service_filter}
        
        data = {
            "time_range": time_data,
            "reduce": reduce_function,
            "filter": filter_data,
            "type": "predefined_graph"
        }
        
        result = self.client.post("domain-types/metric/actions/filter/invoke", data=data)
        
        if not result.get("success"):
            return self.error_response("Failed to search metrics", "Metrics search failed")
        
        metrics_data = result["data"]
        
        return [{
            "type": "text",
            "text": self._format_search_results(host_filter, service_filter, metrics_data, time_range)
        }]
    
    async def _list_available_metrics(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List available metrics for a host/service"""
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")
        
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")
        
        # Get host with metrics column to see available metrics
        query_data = {
            "query": f'{{"op": "=", "left": "name", "right": "{host_name}"}}'
        }
        
        if service_description:
            # Get service metrics
            query_data["query"] = f'{{"op": "and", "expr": [{{"op": "=", "left": "host_name", "right": "{host_name}"}}, {{"op": "=", "left": "description", "right": "{service_description}"}}]}}'
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
            return [{
                "type": "text",
                "text": f"📊 **No Metrics Available**\n\nNo historical metrics found for {host_name}" + 
                       (f"/{service_description}" if service_description else "")
            }]
        
        metric_list = "\n".join([f"📈 {metric}" for metric in available_metrics[:20]])
        
        return [{
            "type": "text",
            "text": (
                f"📊 **Available Metrics**\n\n"
                f"Target: {host_name}" + (f"/{service_description}" if service_description else "") + f"\n"
                f"Metrics ({len(available_metrics)} total):\n\n"
                f"{metric_list}" +
                (f"\n\n... and {len(available_metrics) - 20} more metrics" if len(available_metrics) > 20 else "")
            )
        }]
    
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
        curves = metrics_data.get("curves", [])
        
        if not curves:
            return f"📊 **No Metrics Data**\n\nNo data available for {target} in the last {time_range}"
        
        response = f"📊 **{target_type.title()} Metrics: {target}**\n\n"
        response += f"Time Range: {time_range}\n"
        response += f"Data Points: {len(curves)} curves\n\n"
        
        for i, curve in enumerate(curves[:5]):  # Limit to 5 curves
            title = curve.get("title", f"Metric {i+1}")
            color = curve.get("color", "#000000")
            points = curve.get("points", [])
            
            if points:
                latest_value = points[-1] if points else "No data"
                response += f"📈 **{title}**\n"
                response += f"   Latest: {latest_value}\n"
                response += f"   Data points: {len(points)}\n"
                response += f"   Color: {color}\n\n"
        
        if len(curves) > 5:
            response += f"... and {len(curves) - 5} more curves\n"
        
        response += f"\n💡 **Use specific metric_name for detailed data**"
        
        return response
    
    def _format_custom_graph_response(self, graph_id: str, metrics_data: Dict, time_range: str) -> str:
        """Format custom graph response"""
        return f"📊 **Custom Graph: {graph_id}**\n\nTime Range: {time_range}\n\n" + \
               self._format_metrics_response(graph_id, "custom graph", metrics_data, time_range)
    
    def _format_search_results(self, host_filter: str, service_filter: str, metrics_data: Dict, time_range: str) -> str:
        """Format search results"""
        target = f"{host_filter}" + (f"/{service_filter}" if service_filter else "")
        return f"🔍 **Metrics Search Results**\n\nFilter: {target}\n\n" + \
               self._format_metrics_response(target, "search", metrics_data, time_range)