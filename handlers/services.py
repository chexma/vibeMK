"""
Service management handlers
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from api.exceptions import CheckMKError
from api.paths import path_segment
from handlers.base import BaseHandler, time_ago

# Keyed by Optional[int]: Method 3's column-array shape can leave state
# genuinely absent (short row -> None), and that None is looked up as-is rather
# than substituted, so the lookup key really can be None, not just int.
_STATUS_MAP: Dict[Optional[int], str] = {0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}
_STATUS_ICONS: Dict[int, str] = {0: "✅", 1: "⚠️", 2: "🔴"}

_MAX_SERVICES_DISPLAYED = 50
_PLUGIN_OUTPUT_PREVIEW_LENGTH = 50

# Column positions in Method 3's array-shaped rows: ["host_name", "description",
# "state", "plugin_output", "last_check", "last_state_change"]
_COL_STATE = 2
_COL_PLUGIN_OUTPUT = 3
_COL_LAST_CHECK = 4
_COL_LAST_STATE_CHANGE = 5
_MIN_COLUMNS_FOR_STATE = _COL_STATE + 1


class ServiceHandler(BaseHandler):
    """Handle service management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle service-related tool calls"""

        try:
            if tool_name == "vibemk_get_checkmk_services":
                response = await self._get_services(arguments)
            elif tool_name == "vibemk_get_service_status":
                response = await self._get_service_status(arguments)
            else:
                response = self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception("Error in %s", tool_name)
            return self.error_response("Unexpected Error", str(e))
        else:
            return response

    async def _get_services(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of services with optional host filtering - IMPROVED VERSION"""
        host_name = arguments.get("host_name")

        # The collection takes the host filter itself and returns plugin_output.
        # The show_service action used to run first here, but POSTing to it
        # answers 405 on 2.4 — it is a GET action — so that path never worked.
        return self._services_via_collection(host_name)

    def _services_via_collection(self, host_name: Optional[str]) -> List[Dict[str, Any]]:
        """Method 2: the domain-types service collection (all services, or one host)"""
        # This is the last fallback, so the try has to wrap the processing
        # below too: an exception there must still produce the specific
        # "Service retrieval failed" message, not propagate past _get_services
        # into handle()'s generic catch-all.
        try:
            # Request the state/plugin_output columns explicitly — without them the
            # collection endpoint omits 'state' and every service shows as UNKNOWN.
            params: Dict[str, Any] = {"columns": ["host_name", "description", "state", "plugin_output"]}
            if host_name:
                params["host_name"] = host_name

            result = self.client.get("domain-types/service/collections/all", params=params)

            if not result.get("success"):
                return self.error_response("Failed to retrieve services")

            services = result["data"].get("value", [])
            if not services:
                return [{"type": "text", "text": "📭 No services found"}]

            service_list = []
            for service in services[:_MAX_SERVICES_DISPLAYED]:
                service_host = service.get("extensions", {}).get("host_name", "Unknown")
                description = service.get("extensions", {}).get("description", "Unknown")
                state = service.get("extensions", {}).get("state")
                status = _STATUS_MAP.get(state, f"UNKNOWN({state})")
                service_list.append(f"🔧 {service_host}/{description} (Status: {status})")

            return [
                {
                    "type": "text",
                    "text": (
                        f"🔧 **CheckMK Services** ({len(services)} total, showing first {len(service_list)}):\n\n"
                        + "\n".join(service_list)
                    ),
                }
            ]
        except Exception as e:
            self.logger.debug("Service collection fallback failed: %s", e)
            return self.error_response(
                "Service retrieval failed", "Could not retrieve services using any available method"
            )

    async def _get_service_status(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get service status information using documented CheckMK REST API"""
        host_name = arguments.get("host_name")
        service_description = arguments.get("service_description")

        if not host_name or not service_description:
            return self.error_response("Missing parameters", "host_name and service_description are required")

        self.logger.debug("Getting service status for: %s/%s", host_name, service_description)

        for fallback in (
            self._service_status_via_collection,
            self._service_status_via_show_service,
            self._service_status_via_query_api,
            self._service_status_via_legacy_query,
        ):
            response = fallback(host_name, service_description)
            if response is not None:
                return response

        # If all methods failed, return comprehensive error information
        return [
            {
                "type": "text",
                "text": (
                    f"❌ **Service Status Retrieval Failed**\n\n"
                    f"Service: {host_name}/{service_description}\n\n"
                    f"**Tried Methods:**\n"
                    f"1️⃣ Service collection with check output\n"
                    f"2️⃣ show_service action (state only)\n"
                    f"3️⃣ Query API\n\n"
                    f"**Possible Issues:**\n"
                    f"• Service not found in monitoring system\n"
                    f"• Service description name mismatch\n"
                    f"• CheckMK API version compatibility\n"
                    f"• Monitoring data not yet available\n\n"
                    f"**Recommendation:**\n"
                    f"Verify the service exists in CheckMK GUI and is being monitored."
                ),
            }
        ]

    def _service_status_via_collection(
        self, host_name: str, service_description: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Ask the monitoring service collection, which carries the check output.

        The show_service action does not return plugin_output — verified against
        2.4.0p2 CRE, where its extensions are exactly description, host_name,
        last_check, state and state_type. Without the output a status lookup
        cannot say *why* a service is failing, which is the whole question.
        """
        try:
            result = self.client.get(
                "domain-types/service/collections/all",
                params={
                    "columns": ["host_name", "description", "state", "plugin_output", "last_state_change"],
                    "host_name": host_name,
                },
            )
            if not result.get("success"):
                return None

            for entry in result.get("data", {}).get("value", []):
                extensions = entry.get("extensions", {})
                if extensions.get("description") != service_description:
                    continue
                return [{"type": "text", "text": self._format_service_status(extensions)}]
        except Exception as e:
            self.logger.debug("Service collection lookup failed: %s", e)
            return None
        return None

    def _format_service_status(self, extensions: Dict[str, Any]) -> str:
        """Render one service's state, its check output and when it last changed."""
        state = extensions.get("state")
        if isinstance(state, int):
            status_text = _STATUS_MAP.get(state, f"UNKNOWN({state})")
            icon = {0: "✅", 1: "⚠️", 2: "❌", 3: "❓"}.get(state, "❓")
        else:
            status_text, icon = f"UNKNOWN({state})", "❓"

        lines = [
            f"{icon} **Service Status: {extensions.get('host_name')}/{extensions.get('description')}**",
            "",
            f"**Status:** {status_text}",
            f"**State Code:** {state}",
        ]
        output = (extensions.get("plugin_output") or "").strip()
        if output:
            lines.append(f"**Output:** {output}")
        changed = extensions.get("last_state_change")
        if changed:
            since = datetime.fromtimestamp(changed, tz=timezone.utc)
            lines.append(f"**Since:** {since:%Y-%m-%d %H:%M} UTC")
        return "\n".join(lines)

    def _service_status_via_show_service(
        self, host_name: str, service_description: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Fallback: the documented show_service action, state only.

        Unlike the other three fallbacks, a well-formed but unsuccessful or
        unexpectedly shaped response is treated as terminal here — it returns an
        error instead of falling through to the next method.
        """
        # The try wraps the call *and* every bit of response processing below,
        # not just the request: a malformed response (an unhashable or
        # otherwise unexpected 'state', a shape nothing here anticipates) has
        # to fall through to the next method exactly like a request failure
        # does, rather than aborting the whole four-method chain. The explicit
        # "unsuccessful" / "wrong shape" returns just below are not exceptions
        # -- they stay terminal on purpose (see the docstring above).
        try:
            endpoint = f"objects/host/{path_segment(host_name)}/actions/show_service/invoke"
            params = {"service_description": service_description}

            result = self.client.get(endpoint, params=params)
            self.logger.debug("CheckMK show_service API result: %s", result)

            if not result.get("success"):
                # Not terminal any more: the collection above is the primary
                # lookup, so an unsuccessful answer here just means try the next
                # method rather than ending the chain.
                self.logger.debug("show_service returned no result: %s", result.get("data"))
                return None

            data = result.get("data", {})
            if not (isinstance(data, dict) and "extensions" in data):
                return self.error_response(
                    "Unexpected response format",
                    f"Expected extensions in response, got: "
                    f"{list(data.keys()) if isinstance(data, dict) else type(data)}",
                )

            extensions = data["extensions"]
            state = extensions.get("state")
            description = extensions.get("description", service_description)

            if state is None:
                return [
                    {
                        "type": "text",
                        "text": (
                            f"📊 **Service Found: {host_name}/{description}**\n\n"
                            f"❌ **No state information available**\n"
                            f"Available fields: {list(extensions.keys())}"
                        ),
                    }
                ]

            host_name_from_api = extensions.get("host_name", host_name)
            last_check = extensions.get("last_check")
            state_type = extensions.get("state_type")

            status_text = _STATUS_MAP.get(state, f"UNKNOWN({state})")
            status_icon = _STATUS_ICONS.get(state, "❓")
            last_check_text = self._format_last_check(last_check)
        except Exception as e:
            self.logger.debug("CheckMK show_service API failed: %s", e)
            return None
        else:
            return [
                {
                    "type": "text",
                    "text": (
                        f"{status_icon} **Service Status: {host_name_from_api}/{description}**\n\n"
                        f"**Status:** {status_text}\n"
                        f"**State Code:** {state}\n"
                        f"**Last Check:** {last_check_text}\n"
                        f"**State Type:** {'Hard' if state_type == 1 else 'Soft'}\n\n"
                        f"✅ **Live monitoring data from CheckMK REST API**"
                    ),
                }
            ]

    @staticmethod
    def _format_last_check(last_check: Any) -> str:
        """Format a Unix timestamp as a human-relative 'time ago' string"""
        return time_ago(last_check) or "Unknown"

    def _service_status_via_query_api(self, host_name: str, service_description: str) -> Optional[List[Dict[str, Any]]]:
        """Method 3: the CheckMK query API with explicit columns and a query filter"""
        # See _service_status_via_show_service: the try covers the calls to
        # the formatting helpers below too, so an exception raised while
        # building either response shape falls through to Method 4 instead of
        # aborting the whole chain.
        try:
            params = {
                "columns": ["host_name", "description", "state", "plugin_output", "last_check", "last_state_change"],
                "query": {
                    "op": "and",
                    "expr": [
                        {"op": "=", "left": "host_name", "right": host_name},
                        {"op": "=", "left": "description", "right": service_description},
                    ],
                },
            }

            result = self.client.get("domain-types/service/collections/all", params=params)
            self.logger.debug("Correct service query format result: %s", result)

            if not result.get("success"):
                return None

            services_data = result.get("data", {})
            if not services_data.get("value"):
                return None

            service_data = services_data["value"][0]

            response: Optional[List[Dict[str, Any]]]
            if isinstance(service_data, list) and len(service_data) >= _MIN_COLUMNS_FOR_STATE:
                response = self._service_status_from_columns(host_name, service_description, service_data)
            elif isinstance(service_data, dict):
                response = self._service_status_from_dict(host_name, service_description, service_data)
            else:
                response = None
        except Exception as e:
            self.logger.debug("Correct service query format failed: %s", e)
            return None
        else:
            return response

    def _service_status_from_columns(
        self, host_name: str, service_description: str, service_data: List[Any]
    ) -> List[Dict[str, Any]]:
        """Format Method 3's column-array response shape"""
        state = service_data[_COL_STATE] if len(service_data) > _COL_STATE else None
        plugin_output = service_data[_COL_PLUGIN_OUTPUT] if len(service_data) > _COL_PLUGIN_OUTPUT else "No output"
        last_check = service_data[_COL_LAST_CHECK] if len(service_data) > _COL_LAST_CHECK else "Never"
        last_state_change = (
            service_data[_COL_LAST_STATE_CHANGE] if len(service_data) > _COL_LAST_STATE_CHANGE else "Unknown"
        )

        status = _STATUS_MAP.get(state, f"UNKNOWN({state})")

        return [
            {
                "type": "text",
                "text": (
                    f"📊 **Service Status: {host_name}/{service_description}** (Correct API Query)\n\n"
                    f"Status: {status}\n"
                    f"Output: {plugin_output}\n"
                    f"Last Check: {last_check}\n"
                    f"Last State Change: {last_state_change}\n\n"
                    f"🔍 **Debug Info:**\n"
                    f"Raw State: {state}\n"
                    f"Query Result: {service_data}\n"
                    f"✅ **Data Source:** Correct CheckMK Query API"
                ),
            }
        ]

    def _service_status_from_dict(
        self, host_name: str, service_description: str, service_data: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """Format Method 3's dict-object response shape"""
        extensions = service_data.get("extensions", {})
        state = extensions.get("state")
        if state is None:
            return None

        status = _STATUS_MAP.get(state, f"UNKNOWN({state})")
        plugin_output = extensions.get("plugin_output", "No output available")
        last_check = extensions.get("last_check", "Never")

        return [
            {
                "type": "text",
                "text": (
                    f"📊 **Service Status: {host_name}/{service_description}** (Dict Format)\n\n"
                    f"Status: {status}\n"
                    f"Output: {plugin_output}\n"
                    f"Last Check: {last_check}\n\n"
                    f"🔍 **Debug Info:**\n"
                    f"Raw State: {state}\n"
                    f"Extensions: {list(extensions.keys())}"
                ),
            }
        ]

    def _service_status_via_legacy_query(
        self, host_name: str, service_description: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Method 4: the older string-encoded query format, as a last resort"""
        # See _service_status_via_show_service: the try covers response
        # processing too. This is the last fallback, so an uncaught exception
        # here would otherwise skip the "all methods failed" summary entirely
        # and surface as a generic error instead.
        try:
            # A dict, not a hand-built JSON string: a service description
            # containing a quotation mark otherwise produces a broken query.
            query_data = {
                "query": {
                    "op": "and",
                    "expr": [
                        {"op": "=", "left": "host_name", "right": host_name},
                        {"op": "=", "left": "description", "right": service_description},
                    ],
                }
            }
            result = self.client.get("domain-types/service/collections/all", params=query_data)
            self.logger.debug("Service collection query result: %s", result)

            if not result.get("success"):
                return None

            services = result["data"].get("value", [])
            if not services:
                return None

            extensions = services[0].get("extensions", {})
            state = extensions.get("state")
            if state is None:
                return None

            status = _STATUS_MAP.get(state, f"UNKNOWN({state})")
            plugin_output = extensions.get("plugin_output", "No output available")
            last_check = extensions.get("last_check", "Never")

            return [
                {
                    "type": "text",
                    "text": (
                        f"📊 **Service Status: {host_name}/{service_description}** (Fallback Query)\n\n"
                        f"Status: {status}\n"
                        f"Output: {plugin_output}\n"
                        f"Last Check: {last_check}\n\n"
                        f"🔍 **Debug Info:**\n"
                        f"Raw State: {state}\n"
                        f"Extensions: {list(extensions.keys())}"
                    ),
                }
            ]
        except Exception as e:
            self.logger.debug("Service collection query failed: %s", e)
            return None
