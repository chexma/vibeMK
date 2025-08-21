"""
Debug handler for CheckMK API analysis
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class DebugHandler(BaseHandler):
    """Handle debug operations for CheckMK API analysis"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle debug-related tool calls"""

        try:
            if tool_name == "vibemk_debug_api_endpoints":
                return await self._debug_api_endpoints(arguments)
            elif tool_name == "vibemk_debug_host_data_structure":
                return await self._debug_host_data_structure(arguments)
            elif tool_name == "vibemk_debug_service_data_structure":
                return await self._debug_service_data_structure(arguments)
            elif tool_name == "vibemk_debug_permissions":
                return await self._debug_permissions(arguments)
            elif tool_name == "vibemk_test_all_host_endpoints":
                return await self._test_all_host_endpoints(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _debug_api_endpoints(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Debug available API endpoints and their structure"""

        # Test various API endpoints to understand structure
        endpoints_to_test = [
            "domain-types",
            "domain-types/host",
            "domain-types/host/collections/all",
            "domain-types/service",
            "domain-types/service/collections/all",
            "objects",
        ]

        results = []
        for endpoint in endpoints_to_test:
            try:
                result = self.client.get(endpoint)
                success = result.get("success", False)

                if success:
                    data = result.get("data", {})
                    if isinstance(data, dict):
                        keys = list(data.keys())
                        first_items = []

                        # Get sample data
                        if "value" in data and isinstance(data["value"], list) and data["value"]:
                            first_items = data["value"][:2]  # First 2 items
                        elif "domain_type" in data and isinstance(data["domain_type"], list) and data["domain_type"]:
                            first_items = data["domain_type"][:2]

                        results.append(f"✅ **{endpoint}**\\n   Keys: {keys}\\n   Sample: {str(first_items)[:200]}...")
                    else:
                        results.append(
                            f"✅ **{endpoint}**\\n   Data type: {type(data)}\\n   Content: {str(data)[:200]}..."
                        )
                else:
                    error_info = result.get("data", {})
                    results.append(f"❌ **{endpoint}**\\n   Error: {error_info}")

            except Exception as e:
                results.append(f"💥 **{endpoint}**\\n   Exception: {str(e)}")

        return [{"type": "text", "text": (f"🔍 **CheckMK API Endpoints Debug**\\n\\n" + "\\n\\n".join(results))}]

    async def _test_all_host_endpoints(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Test all possible host-related endpoints for a specific host"""
        host_name = arguments.get("host_name", "www.google.de")

        # Test various host endpoints
        host_endpoints = [
            f"objects/host/{host_name}",
            f"objects/host_config/{host_name}",
            f"domain-types/host/collections/all",
            f"domain-types/host_config/collections/all",
            f"objects/host/{host_name}/actions/show_service/invoke",
        ]

        # Test with different query parameters
        query_variations = [
            {},
            {"host_name": host_name},
            {"q": f"hosts.name = '{host_name}'"},
            {"query": f'{{"op": "=", "left": "name", "right": "{host_name}"}}'},
        ]

        results = []

        for endpoint in host_endpoints:
            results.append(f"\\n🎯 **Testing endpoint: {endpoint}**")

            # Test GET requests
            for i, params in enumerate(query_variations):
                try:
                    if "actions" in endpoint:
                        # POST request for actions
                        result = self.client.post(endpoint, data=params)
                        method = "POST"
                    else:
                        # GET request for regular endpoints
                        result = self.client.get(endpoint, params=params)
                        method = "GET"

                    success = result.get("success", False)

                    if success:
                        data = result.get("data", {})

                        # Analyze the data structure
                        if isinstance(data, dict):
                            keys = list(data.keys())

                            # Look for monitoring data indicators
                            monitoring_indicators = []
                            if "extensions" in data:
                                ext_keys = (
                                    list(data["extensions"].keys()) if isinstance(data["extensions"], dict) else []
                                )
                                monitoring_indicators.extend(
                                    [
                                        k
                                        for k in ext_keys
                                        if any(
                                            word in k.lower() for word in ["state", "status", "check", "plugin", "last"]
                                        )
                                    ]
                                )

                            if "value" in data and isinstance(data["value"], list):
                                value_count = len(data["value"])
                                if data["value"] and isinstance(data["value"][0], dict):
                                    sample_keys = list(data["value"][0].keys())
                                    monitoring_indicators.extend(
                                        [
                                            k
                                            for k in sample_keys
                                            if any(
                                                word in k.lower()
                                                for word in ["state", "status", "check", "plugin", "last"]
                                            )
                                        ]
                                    )
                                results.append(
                                    f"   ✅ {method} Query {i+1}: {value_count} items, Keys: {keys}, Sample: {sample_keys[:5]}"
                                )
                            else:
                                results.append(f"   ✅ {method} Query {i+1}: Keys: {keys}")

                            if monitoring_indicators:
                                results.append(f"      🎯 Monitoring data found: {monitoring_indicators}")

                                # If we found actual monitoring data, show sample
                                if "extensions" in data and "state" in str(data["extensions"]):
                                    results.append(f"      📊 Sample data: {str(data)[:300]}...")
                                elif "value" in data and data["value"]:
                                    sample_item = data["value"][0]
                                    if "extensions" in sample_item:
                                        results.append(
                                            f"      📊 Sample extensions: {str(sample_item['extensions'])[:200]}..."
                                        )
                        else:
                            results.append(f"   ✅ {method} Query {i+1}: Data type: {type(data)}")
                    else:
                        error_data = result.get("data", {})
                        results.append(f"   ❌ {method} Query {i+1}: {error_data}")

                except Exception as e:
                    results.append(f"   💥 {method} Query {i+1}: Exception: {str(e)}")

        return [{"type": "text", "text": (f"🔍 **Host Endpoints Test for: {host_name}**\\n" + "\\n".join(results))}]

    async def _debug_host_data_structure(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze the actual data structure returned by host APIs"""
        host_name = arguments.get("host_name", "www.google.de")

        results = []

        # Test the most promising endpoints
        test_scenarios = [
            ("GET all hosts", "domain-types/host_config/collections/all", "GET", {}),
            ("GET all monitoring hosts", "domain-types/host/collections/all", "GET", {}),
            ("GET specific host config", f"objects/host_config/{host_name}", "GET", {}),
            ("GET specific host object", f"objects/host/{host_name}", "GET", {}),
            ("POST show services", f"objects/host/{host_name}/actions/show_service/invoke", "POST", {}),
        ]

        for description, endpoint, method, data in test_scenarios:
            results.append(f"\\n🧪 **{description}**")
            try:
                if method == "POST":
                    result = self.client.post(endpoint, data=data)
                else:
                    result = self.client.get(endpoint)

                success = result.get("success", False)

                if success:
                    response_data = result.get("data", {})

                    # Deep analysis of the response structure
                    results.append(f"   ✅ Success!")
                    results.append(f"   📋 Response type: {type(response_data)}")

                    if isinstance(response_data, dict):
                        keys = list(response_data.keys())
                        results.append(f"   🔑 Top-level keys: {keys}")

                        # Look for our target host
                        if "value" in response_data and isinstance(response_data["value"], list):
                            items = response_data["value"]
                            results.append(f"   📊 Found {len(items)} items")

                            # Find our specific host
                            target_host = None
                            for item in items:
                                if isinstance(item, dict) and item.get("id") == host_name:
                                    target_host = item
                                    break

                            if target_host:
                                results.append(f"   🎯 Found target host: {host_name}")
                                results.append(f"   🔑 Host keys: {list(target_host.keys())}")

                                if "extensions" in target_host:
                                    ext = target_host["extensions"]
                                    results.append(
                                        f"   🔧 Extensions keys: {list(ext.keys()) if isinstance(ext, dict) else type(ext)}"
                                    )

                                    # Look for state/status information
                                    state_fields = (
                                        [
                                            k
                                            for k in ext.keys()
                                            if any(
                                                word in k.lower()
                                                for word in ["state", "status", "check", "plugin", "last", "output"]
                                            )
                                        ]
                                        if isinstance(ext, dict)
                                        else []
                                    )
                                    if state_fields:
                                        results.append(f"   📈 State/monitoring fields: {state_fields}")
                                        for field in state_fields:
                                            value = ext.get(field)
                                            results.append(f"      {field}: {value} ({type(value)})")
                                    else:
                                        results.append(f"   ⚠️ No obvious state fields found")
                                        # Show all extension data for analysis
                                        results.append(f"   🔍 All extensions: {str(ext)[:400]}...")
                                else:
                                    results.append(f"   ⚠️ No extensions found")
                            else:
                                results.append(f"   ❌ Host {host_name} not found in response")
                                if items:
                                    sample_ids = [
                                        item.get("id", "no-id") for item in items[:3] if isinstance(item, dict)
                                    ]
                                    results.append(f"   📝 Sample IDs: {sample_ids}")

                        elif response_data.get("id") == host_name:
                            # Direct host object
                            results.append(f"   🎯 Direct host object found")
                            results.append(f"   🔑 Host keys: {list(response_data.keys())}")

                            if "extensions" in response_data:
                                ext = response_data["extensions"]
                                results.append(f"   🔧 Extensions: {str(ext)[:400]}...")
                        else:
                            results.append(f"   🔍 Response structure: {str(response_data)[:300]}...")
                    else:
                        results.append(f"   🔍 Response: {str(response_data)[:300]}...")
                else:
                    error_data = result.get("data", {})
                    results.append(f"   ❌ Failed: {error_data}")

            except Exception as e:
                results.append(f"   💥 Exception: {str(e)}")

        return [
            {"type": "text", "text": (f"🔬 **Host Data Structure Analysis for: {host_name}**\\n" + "\\n".join(results))}
        ]

    async def _debug_service_data_structure(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze service data structure for debugging"""
        host_name = arguments.get("host_name", "www.google.de")
        service_name = arguments.get("service_name", "Check_MK")

        results = []

        # Test service-related endpoints
        import urllib.parse

        encoded_service = urllib.parse.quote(service_name, safe="")

        test_scenarios = [
            ("GET all services", "domain-types/service/collections/all", "GET", {}),
            ("GET host services", "domain-types/service/collections/all", "GET", {"host_name": host_name}),
            ("GET specific service", f"objects/service/{host_name}/{encoded_service}", "GET", {}),
            ("POST show host services", f"objects/host/{host_name}/actions/show_service/invoke", "POST", {}),
        ]

        for description, endpoint, method, params in test_scenarios:
            results.append(f"\\n🧪 **{description}**")
            try:
                if method == "POST":
                    result = self.client.post(endpoint, data=params)
                else:
                    result = self.client.get(endpoint, params=params)

                success = result.get("success", False)

                if success:
                    response_data = result.get("data", {})
                    results.append(f"   ✅ Success!")

                    if isinstance(response_data, dict) and "value" in response_data:
                        services = response_data["value"]
                        results.append(f"   📊 Found {len(services)} services")

                        if services:
                            # Analyze first service
                            first_service = services[0]
                            if isinstance(first_service, dict):
                                results.append(f"   🔑 Service keys: {list(first_service.keys())}")

                                if "extensions" in first_service:
                                    ext = first_service["extensions"]
                                    results.append(
                                        f"   🔧 Extensions keys: {list(ext.keys()) if isinstance(ext, dict) else type(ext)}"
                                    )

                                    # Look for state information
                                    if isinstance(ext, dict):
                                        state_info = {}
                                        for key in ["state", "description", "host_name", "plugin_output", "last_check"]:
                                            if key in ext:
                                                state_info[key] = ext[key]
                                        results.append(f"   📈 State info: {state_info}")
                    else:
                        results.append(f"   🔍 Response: {str(response_data)[:300]}...")
                else:
                    error_data = result.get("data", {})
                    results.append(f"   ❌ Failed: {error_data}")

            except Exception as e:
                results.append(f"   💥 Exception: {str(e)}")

        return [{"type": "text", "text": (f"🔬 **Service Data Structure Analysis**\\n" + "\\n".join(results))}]

    async def _debug_permissions(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Debug automation user permissions"""

        results = []

        # Test basic API access
        basic_tests = [
            ("API Version", "version", "GET"),
            ("Domain Types", "domain-types", "GET"),
            ("User Info", "objects/user_config", "GET"),
        ]

        for description, endpoint, method in basic_tests:
            results.append(f"\\n🧪 **{description}**")
            try:
                result = self.client.get(endpoint)
                success = result.get("success", False)

                if success:
                    results.append(f"   ✅ Access granted")
                else:
                    error_data = result.get("data", {})
                    results.append(f"   ❌ Access denied: {error_data}")

            except Exception as e:
                results.append(f"   💥 Exception: {str(e)}")

        # Test monitoring-specific permissions
        monitoring_tests = [
            ("Host Monitoring", "domain-types/host/collections/all"),
            ("Service Monitoring", "domain-types/service/collections/all"),
            ("Host Config", "domain-types/host_config/collections/all"),
        ]

        for description, endpoint in monitoring_tests:
            results.append(f"\\n🔒 **{description} Permissions**")
            try:
                result = self.client.get(endpoint)
                success = result.get("success", False)

                if success:
                    data = result.get("data", {})
                    if "value" in data:
                        count = len(data["value"]) if isinstance(data["value"], list) else "unknown"
                        results.append(f"   ✅ Access granted - {count} items")
                    else:
                        results.append(
                            f"   ✅ Access granted - structure: {list(data.keys()) if isinstance(data, dict) else type(data)}"
                        )
                else:
                    error_data = result.get("data", {})
                    error_title = (
                        error_data.get("title", "Unknown error") if isinstance(error_data, dict) else str(error_data)
                    )
                    results.append(f"   ❌ Access issue: {error_title}")

                    # Check for permission-related errors
                    if any(
                        word in str(error_data).lower()
                        for word in ["permission", "forbidden", "unauthorized", "access"]
                    ):
                        results.append(f"   🚫 Likely permission issue detected")

            except Exception as e:
                results.append(f"   💥 Exception: {str(e)}")

        return [{"type": "text", "text": (f"🔐 **Permissions Debug**\\n" + "\\n".join(results))}]
