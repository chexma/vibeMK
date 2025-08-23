"""
Host management handlers with enhanced features for CheckMK integration
"""

import json
import time
from typing import Any, Dict, List, Optional, Union

from api.exceptions import CheckMKError, CheckMKNotFoundError
from handlers.base import BaseHandler


class HostHandler(BaseHandler):
    """Handle host management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle host-related tool calls"""

        try:
            if tool_name == "vibemk_get_checkmk_hosts":
                return await self._get_hosts(arguments)
            elif tool_name == "vibemk_get_host_status":
                return await self._get_host_status(arguments.get("host_name"))
            elif tool_name == "vibemk_get_host_details":
                return await self._get_host_details(arguments.get("host_name"))
            elif tool_name == "vibemk_get_host_config":
                return await self._get_host_config(arguments.get("host_name"))
            elif tool_name == "vibemk_create_host":
                return await self._create_host(arguments)
            elif tool_name == "vibemk_update_host":
                return await self._update_host(arguments)
            elif tool_name == "vibemk_delete_host":
                return await self._delete_host(arguments.get("host_name"))
            elif tool_name == "vibemk_move_host":
                return await self._move_host(arguments)
            elif tool_name == "vibemk_bulk_update_hosts":
                return await self._bulk_update_hosts(arguments)
            elif tool_name == "vibemk_create_cluster_host":
                return await self._create_cluster_host(arguments)
            elif tool_name == "vibemk_validate_host_config":
                return await self._validate_host_config(arguments)
            elif tool_name == "vibemk_compare_host_states":
                return await self._compare_host_states(arguments)
            elif tool_name == "vibemk_get_host_effective_attributes":
                return await self._get_host_effective_attributes(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _get_hosts(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of hosts with optional filtering"""
        params = {}
        if folder := arguments.get("folder"):
            params["folder"] = folder

        result = self.client.get("domain-types/host_config/collections/all", params=params)

        if not result.get("success"):
            return self.error_response("Failed to retrieve hosts")

        hosts = result["data"].get("value", [])
        if not hosts:
            return [{"type": "text", "text": "📭 No hosts found"}]

        host_list = []
        for host in hosts[:50]:  # Limit display
            host_id = host.get("id", "Unknown")
            folder_path = host.get("extensions", {}).get("folder", "/")
            host_list.append(f"🖥️ {host_id} (Folder: {folder_path})")

        return [
            {
                "type": "text",
                "text": (
                    f"🖥️ **CheckMK Hosts** ({len(hosts)} total, showing first {len(host_list)}):\\n\\n"
                    + "\\n".join(host_list)
                ),
            }
        ]

    async def _get_host_status(self, host_name: str) -> List[Dict[str, Any]]:
        """Get host status information using the correct CheckMK API"""
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        self.logger.debug(f"Getting host status for: {host_name} (using correct API method)")

        # Method 1: Use the documented CheckMK API with columns parameter
        # This is the correct approach similar to the service status fix
        try:
            # Use the documented CheckMK API format: objects/host/{name}?columns=...
            # Include hard_state and state_type to get the correct monitoring state
            params = {
                "columns": [
                    "name",
                    "state",
                    "hard_state",
                    "state_type",
                    "plugin_output",
                    "last_check",
                    "last_state_change",
                    "has_been_checked",
                ]
            }

            result = self.client.get(f"objects/host/{host_name}", params=params)
            self.logger.debug(f"Host status API result: {result}")

            if result.get("success"):
                data = result.get("data", {})

                if isinstance(data, dict) and "extensions" in data:
                    extensions = data["extensions"]

                    # Extract host state and other information
                    # Use hard_state for the actual monitoring status (more reliable than soft state)
                    state = extensions.get("state")  # Soft state
                    hard_state = extensions.get("hard_state")  # Hard state
                    state_type = extensions.get("state_type")  # 0=soft, 1=hard
                    has_been_checked = extensions.get("has_been_checked", 0)
                    plugin_output = extensions.get("plugin_output", "No output available")
                    last_check = extensions.get("last_check")
                    last_state_change = extensions.get("last_state_change")

                    # Use the appropriate state based on state_type
                    # If it's a hard state (state_type=1), use hard_state, otherwise use state
                    if hard_state is not None and state_type == 1:
                        effective_state = hard_state
                        state_info = f"Hard State: {hard_state}"
                    elif state is not None:
                        effective_state = state
                        state_info = f"Soft State: {state}"
                    else:
                        effective_state = None

                    if effective_state is not None:
                        # Map numeric state to human-readable status
                        state_map = {0: "UP", 1: "DOWN", 2: "UNREACHABLE"}
                        status = state_map.get(effective_state, f"UNKNOWN({effective_state})")

                        # Format timestamps if available
                        import time

                        if isinstance(last_check, (int, float)):
                            try:
                                last_check_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_check))
                                time_diff = int(time.time() - last_check)
                                if time_diff < 60:
                                    last_check_display = f"{time_diff}s ago"
                                elif time_diff < 3600:
                                    last_check_display = f"{time_diff // 60}m ago"
                                else:
                                    last_check_display = f"{time_diff // 3600}h ago"
                            except:
                                last_check_display = str(last_check)
                        else:
                            last_check_display = str(last_check) if last_check else "Never"

                        if isinstance(last_state_change, (int, float)):
                            try:
                                change_diff = int(time.time() - last_state_change)
                                if change_diff < 60:
                                    change_display = f"{change_diff}s ago"
                                elif change_diff < 3600:
                                    change_display = f"{change_diff // 60}m ago"
                                else:
                                    change_display = f"{change_diff // 3600}h ago"
                            except:
                                change_display = str(last_state_change)
                        else:
                            change_display = str(last_state_change) if last_state_change else "Unknown"

                        # Choose appropriate emoji based on status
                        if status == "UP":
                            status_emoji = "🟢"
                            status_display = f"{status_emoji} **{status}**"
                        elif status == "DOWN":
                            status_emoji = "🔴"
                            status_display = f"{status_emoji} **{status}**"
                        elif status == "UNREACHABLE":
                            status_emoji = "🟡"
                            status_display = f"{status_emoji} **{status}**"
                        else:
                            status_emoji = "⚪"
                            status_display = f"{status_emoji} **{status}**"

                        return [
                            {
                                "type": "text",
                                "text": (
                                    f"✅ **Host Status: {host_name}**\\n\\n"
                                    f"**Status:** {status_display}\\n"
                                    f"**State Code:** {effective_state} ({state_info})\\n"
                                    f"**Has Been Checked:** {'Yes' if has_been_checked else 'No'}\\n"
                                    f"**Last Check:** {last_check_display}\\n"
                                    f"**Last State Change:** {change_display}\\n\\n"
                                    f"**Plugin Output:** {plugin_output}\\n\\n"
                                    f"✅ **Live monitoring data from CheckMK REST API**"
                                ),
                            }
                        ]
                    else:
                        return self.error_response(
                            "No state data", f"Host '{host_name}' found but no state information available"
                        )
                else:
                    return self.error_response("Unexpected response", "Host data structure not as expected")
            else:
                # Host not found or API error
                error_data = result.get("data", {})
                if "Host does not exist" in str(error_data):
                    return self.error_response("Host not found", f"Host '{host_name}' not found in CheckMK")
                else:
                    return self.error_response("API Error", f"Failed to retrieve host status: {error_data}")

        except Exception as e:
            self.logger.exception(f"Host status API call failed: {e}")
            # Fall back to alternative methods if the main API fails

        # Method 2: Fallback using host collections endpoint
        try:
            self.logger.debug("Trying fallback method: host collections")
            result = self.client.get("domain-types/host/collections/all")

            if result.get("success"):
                data = result.get("data", {})
                if "value" in data:
                    hosts = data["value"]

                    # Find the specific host
                    for host in hosts:
                        if isinstance(host, dict) and host.get("id") == host_name:
                            extensions = host.get("extensions", {})
                            state = extensions.get("state")

                            if state is not None:
                                state_map = {0: "UP", 1: "DOWN", 2: "UNREACHABLE"}
                                status = state_map.get(state, f"UNKNOWN({state})")

                                if status == "UP":
                                    status_display = f"🟢 **{status}**"
                                elif status == "DOWN":
                                    status_display = f"🔴 **{status}**"
                                elif status == "UNREACHABLE":
                                    status_display = f"🟡 **{status}**"
                                else:
                                    status_display = f"⚪ **{status}**"

                                return [
                                    {
                                        "type": "text",
                                        "text": (
                                            f"✅ **Host Status: {host_name}** (Fallback Method)\\n\\n"
                                            f"**Status:** {status_display}\\n"
                                            f"**State Code:** {state}\\n\\n"
                                            f"✅ **Data from CheckMK host collections API**"
                                        ),
                                    }
                                ]

                    # Host not found in collections
                    return self.error_response("Host not found", f"Host '{host_name}' not found in host collections")
        except Exception as e:
            self.logger.debug(f"Fallback method failed: {e}")

        # Method 3: Final fallback - check if host exists in configuration
        try:
            host_config = self.client.get(f"objects/host_config/{host_name}")
            if host_config.get("success"):
                return [
                    {
                        "type": "text",
                        "text": (
                            f"⚪ **Host Status: {host_name}**\\n\\n"
                            f"**Status:** MONITORING DATA UNAVAILABLE\\n\\n"
                            f"✅ Host is configured in CheckMK\\n"
                            f"❌ Live monitoring state not accessible\\n\\n"
                            f"**Possible Issues:**\\n"
                            f"• Host not actively monitored\\n"
                            f"• Monitoring core not running\\n"
                            f"• API permissions insufficient\\n\\n"
                            f"**Recommendation:**\\n"
                            f"Check CheckMK GUI for actual status"
                        ),
                    }
                ]
            else:
                return self.error_response("Host not found", f"Host '{host_name}' not found in CheckMK")
        except Exception as e:
            self.logger.debug(f"Host config check failed: {e}")

        # If all methods failed, return comprehensive error information
        return [
            {
                "type": "text",
                "text": (
                    f"❌ **Host Status Retrieval Failed**\\n\\n"
                    f"Host: {host_name}\\n\\n"
                    f"**Tried Methods:**\\n"
                    f"1️⃣ Direct host object API (objects/host/)\\n"
                    f"2️⃣ Host collections query (real-time data)\\n"
                    f"3️⃣ Host configuration check\\n\\n"
                    f"**Possible Issues:**\\n"
                    f"• Host not found in monitoring system\\n"
                    f"• Host name mismatch\\n"
                    f"• CheckMK API version compatibility\\n"
                    f"• Monitoring data not yet available\\n\\n"
                    f"**Recommendation:**\\n"
                    f"Verify the host exists in CheckMK GUI and is being monitored."
                ),
            }
        ]

    async def _get_host_details(self, host_name: str) -> List[Dict[str, Any]]:
        """Get detailed host information"""
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        result = self.client.get(f"objects/host_config/{host_name}")

        if not result.get("success"):
            return self.error_response("Host not found", f"Host '{host_name}' not found")

        host = result["data"]
        extensions = host.get("extensions", {})
        attributes = extensions.get("attributes", {})

        return [
            {
                "type": "text",
                "text": (
                    f"🔍 **Host Details: {host_name}**\\n\\n"
                    f"Folder: {extensions.get('folder', '/')}\\n"
                    f"IP Address: {attributes.get('ipaddress', 'Not set')}\\n"
                    f"Alias: {attributes.get('alias', 'Not set')}\\n"
                    f"Agent Type: {attributes.get('tag_agent', 'Unknown')}\\n"
                    f"Site: {attributes.get('site', 'Not set')}"
                ),
            }
        ]

    async def _get_host_config(self, host_name: str) -> List[Dict[str, Any]]:
        """Get host configuration"""
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        result = self.client.get(f"objects/host_config/{host_name}")

        if not result.get("success"):
            return self.error_response("Host not found", f"Host '{host_name}' not found")

        host = result["data"]
        return self.info_response(f"Host Configuration: {host_name}", host)

    async def _create_host(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new host with enhanced validation"""
        host_name = arguments.get("host_name")
        folder = arguments.get("folder", "/")
        attributes = arguments.get("attributes", {})

        # Enhanced validation with comprehensive checks
        validation_result = self._validate_host_creation_params(host_name, folder, attributes)
        if validation_result:
            return validation_result

        # Check if host already exists
        existing_host = self.client.get(f"objects/host_config/{host_name}")
        if existing_host.get("success"):
            return self.error_response(
                "Host already exists", f"Host '{host_name}' already exists. Use update_host to modify it."
            )

        # Convert folder format if needed (~ for root per CheckMK API)
        if folder == "/":
            folder = "~"

        data = {"folder": folder, "host_name": host_name, "attributes": attributes}

        result = self.client.post("domain-types/host_config/collections/all", data=data)

        if result.get("success"):
            # Enhanced success response with more details
            attribute_count = len(attributes)
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Host Created Successfully**\\n\\n"
                        f"**Host:** {host_name}\\n"
                        f"**Folder:** {folder}\\n"
                        f"**Attributes Set:** {attribute_count}\\n\\n"
                        f"📋 **Host Details:**\\n"
                        + (
                            f"• IP Address: {attributes.get('ipaddress', 'Not set')}\\n"
                            if attributes.get("ipaddress")
                            else ""
                        )
                        + (f"• Alias: {attributes.get('alias', 'Not set')}\\n" if attributes.get("alias") else "")
                        + (f"• Site: {attributes.get('site', 'Default')}\\n" if attributes.get("site") else "")
                        + f"\\n⚠️ **Remember to activate changes!**\\n\\n"
                        f"💡 **Next Steps:**\\n"
                        f"1️⃣ Use 'get_pending_changes' to review\\n"
                        f"2️⃣ Use 'activate_changes' to apply configuration"
                    ),
                }
            ]
        else:
            error_details = result.get("data", {})
            return self.error_response("Host creation failed", f"Could not create host '{host_name}': {error_details}")

    async def _update_host(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update host configuration with proper CheckMK API compliance"""
        host_name = arguments.get("host_name")
        attributes = arguments.get("attributes", {})
        update_mode = arguments.get("update_mode", "update")  # update, overwrite, remove
        remove_attributes = arguments.get("remove_attributes", [])

        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        # Validate specific attributes (alias, tag, ipaddress, site)
        validation_errors = self._validate_host_update_attributes(attributes)
        if validation_errors:
            return self.error_response("Validation failed", "\\n".join(validation_errors))

        # Get current host configuration with ETag for proper concurrency control
        current_config = self.client.get(f"objects/host_config/{host_name}")
        if not current_config.get("success"):
            return self.error_response("Host not found", f"Host '{host_name}' not found")

        # Extract ETag for If-Match header (required by CheckMK API)
        etag = current_config.get("headers", {}).get("ETag")
        if not etag:
            # Fallback: try legacy location or warn
            etag = current_config["data"].get("extensions", {}).get("meta_data", {}).get("etag")
            if not etag:
                self.logger.debug("No ETag found in host config, this may cause issues with concurrent updates")

        current_attributes = current_config["data"].get("extensions", {}).get("attributes", {})

        # Build proper CheckMK API request based on update mode
        # Note: CheckMK 2.2.0p7+ does not support simultaneous use of attributes, update_attributes, and remove_attributes
        if update_mode == "overwrite":
            # Use 'attributes' to completely replace all attributes
            if remove_attributes:
                return self.error_response(
                    "Invalid combination",
                    "Cannot use 'remove_attributes' with 'overwrite' mode. Use 'remove' mode instead.",
                )
            data = {"attributes": attributes}
            operation_description = "Complete replacement of host attributes"

        elif update_mode == "remove":
            # Use 'remove_attributes' to remove specific attributes
            if attributes:
                return self.error_response(
                    "Invalid combination", "Cannot specify 'attributes' with 'remove' mode. Use 'update' mode instead."
                )
            if not remove_attributes:
                return self.error_response("Missing parameter", "remove_attributes is required for 'remove' mode")
            data = {"remove_attributes": remove_attributes}
            operation_description = f"Removing attributes: {', '.join(remove_attributes)}"

        else:  # update mode (default)
            # Use 'update_attributes' to merge with existing attributes
            if remove_attributes:
                return self.error_response(
                    "Invalid combination",
                    "Cannot use 'remove_attributes' with 'update' mode. Use 'remove' mode instead.",
                )
            data = {"update_attributes": attributes}
            operation_description = "Merging with existing host attributes"

        # Prepare headers with ETag if available
        headers = {}
        if etag:
            headers["If-Match"] = etag

        # Perform the update with proper error handling
        try:
            result = self.client.put(f"objects/host_config/{host_name}", data=data, headers=headers)

            if result.get("success"):
                # Calculate what actually changed for better user feedback
                if update_mode == "update":
                    changes = self._compare_attributes(current_attributes, {**current_attributes, **attributes})
                elif update_mode == "overwrite":
                    changes = self._compare_attributes(current_attributes, attributes)
                else:  # remove
                    removed_attrs = {
                        attr: current_attributes.get(attr) for attr in remove_attributes if attr in current_attributes
                    }
                    changes = {
                        "has_changes": bool(removed_attrs),
                        "removed": removed_attrs,
                        "added": {},
                        "modified": {},
                    }

                return [
                    {
                        "type": "text",
                        "text": (
                            f"✅ **Host Updated Successfully**\\n\\n"
                            f"**Host:** {host_name}\\n"
                            f"**Update Mode:** {update_mode}\\n"
                            f"**Operation:** {operation_description}\\n\\n"
                            f"📋 **Changes Applied:**\\n"
                            + (
                                self._format_attribute_changes(changes)
                                if changes["has_changes"]
                                else "No changes detected"
                            )
                            + f"\\n\\n⚠️ **Remember to activate changes!**\\n"
                            f"💡 Use 'vibemk_activate_changes' to apply the configuration"
                        ),
                    }
                ]
            else:
                error_details = result.get("data", {})
                # Enhanced error handling for common CheckMK API issues
                error_message = str(error_details)

                if "ETag" in error_message or "If-Match" in error_message:
                    return self.error_response(
                        "Concurrent modification detected",
                        f"Host '{host_name}' was modified by another process. Please retry the operation.",
                    )
                elif "400" in str(result.get("status", "")):
                    return self.error_response(
                        "Invalid request", f"CheckMK API validation failed for host '{host_name}': {error_details}"
                    )
                else:
                    return self.error_response(
                        "Host update failed", f"Could not update host '{host_name}': {error_details}"
                    )

        except Exception as e:
            self.logger.exception(f"Host update operation failed for {host_name}")
            return self.error_response(
                "Update operation failed", f"Unexpected error updating host '{host_name}': {str(e)}"
            )

    async def _delete_host(self, host_name: str) -> List[Dict[str, Any]]:
        """Delete a host"""
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        result = self.client.delete(f"objects/host_config/{host_name}")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Host Deleted Successfully**\\n\\n"
                        f"Host: {host_name}\\n\\n"
                        f"📝 **Next Steps:**\\n"
                        f"1️⃣ Use 'get_pending_changes' to review the deletion\\n"
                        f"2️⃣ Use 'activate_changes' to apply the configuration\\n\\n"
                        f"💡 **Important:** The host is only marked for deletion until you activate changes!"
                    ),
                }
            ]
        else:
            return self.error_response("Host deletion failed", f"Could not delete host '{host_name}'")

    async def _move_host(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Move host to different folder"""
        host_name = arguments.get("host_name")
        target_folder = arguments.get("target_folder")

        if not host_name or not target_folder:
            return self.error_response("Missing parameters", "host_name and target_folder are required")

        data = {"target_folder": target_folder}
        result = self.client.post(f"objects/host_config/{host_name}/actions/move/invoke", data=data)

        if result.get("success"):
            return self.success_response(
                "Host Moved Successfully",
                {"host": host_name, "folder": target_folder, "message": "Remember to activate changes!"},
            )
        else:
            return self.error_response("Host move failed", f"Could not move host '{host_name}'")

    async def _bulk_update_hosts(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Bulk update multiple hosts"""
        entries = arguments.get("entries", [])

        if not entries:
            return self.error_response("Missing parameter", "entries list is required")

        data = {"entries": entries}
        result = self.client.put("domain-types/host_config/actions/bulk-update/invoke", data=data)

        if result.get("success"):
            return self.success_response(
                "Bulk Update Successful", {"updated": len(entries), "message": "Remember to activate changes!"}
            )
        else:
            return self.error_response("Bulk update failed", "Could not update hosts")

    async def _create_cluster_host(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a cluster host with nodes"""
        host_name = arguments.get("host_name")
        folder = arguments.get("folder", "/")
        nodes = arguments.get("nodes", [])
        attributes = arguments.get("attributes", {})

        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        if not nodes:
            return self.error_response("Missing parameter", "nodes list is required for cluster hosts")

        # Convert folder format
        if folder == "/":
            folder = "~"

        # Set cluster-specific attributes
        cluster_attributes = attributes.copy()
        cluster_attributes.update(
            {"tag_agent": "no-agent", "nodes": nodes}  # Cluster hosts typically don't have agents
        )

        data = {"folder": folder, "host_name": host_name, "attributes": cluster_attributes}

        result = self.client.post("domain-types/host_config/collections/all", data=data)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Cluster Host Created Successfully**\\n\\n"
                        f"**Cluster Host:** {host_name}\\n"
                        f"**Folder:** {folder}\\n"
                        f"**Nodes:** {', '.join(nodes)}\\n\\n"
                        f"📋 **Cluster Configuration:**\\n"
                        f"• Node Count: {len(nodes)}\\n"
                        f"• Agent Type: No Agent (Cluster)\\n\\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            error_details = result.get("data", {})
            return self.error_response(
                "Cluster host creation failed", f"Could not create cluster host '{host_name}': {error_details}"
            )

    async def _validate_host_config(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate host configuration before applying changes"""
        host_name = arguments.get("host_name")
        attributes = arguments.get("attributes", {})
        operation = arguments.get("operation", "create")

        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        validation_errors = []
        warnings = []

        # Host name validation
        if not self._validate_host_name(host_name):
            validation_errors.append("Invalid host name format")

        # IP address validation
        if "ipaddress" in attributes:
            if not self._validate_ip_address(attributes["ipaddress"]):
                validation_errors.append("Invalid IP address format")

        # Folder validation
        folder = arguments.get("folder", "/")
        if not self._validate_folder_exists(folder):
            warnings.append(f"Folder '{folder}' may not exist")

        # Operation-specific validation
        if operation == "create":
            existing_host = self.client.get(f"objects/host_config/{host_name}")
            if existing_host.get("success"):
                validation_errors.append("Host already exists")

        # Compile validation results
        status = "valid" if not validation_errors else "invalid"

        response_text = f"🔍 **Host Configuration Validation**\\n\\n"
        response_text += f"**Host:** {host_name}\\n"
        response_text += f"**Operation:** {operation}\\n"
        response_text += f"**Status:** {'✅ Valid' if status == 'valid' else '❌ Invalid'}\\n\\n"

        if validation_errors:
            response_text += "🚨 **Errors:**\\n"
            for error in validation_errors:
                response_text += f"• {error}\\n"
            response_text += "\\n"

        if warnings:
            response_text += "⚠️ **Warnings:**\\n"
            for warning in warnings:
                response_text += f"• {warning}\\n"
            response_text += "\\n"

        if status == "valid":
            response_text += "✅ Configuration is valid and ready for deployment"

        return [{"type": "text", "text": response_text}]

    async def _compare_host_states(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compare desired vs current host state"""
        host_name = arguments.get("host_name")
        desired_attributes = arguments.get("desired_attributes", {})

        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        # Get current configuration
        current_config = self.client.get(f"objects/host_config/{host_name}")
        if not current_config.get("success"):
            return self.error_response("Host not found", f"Host '{host_name}' not found")

        current_attributes = current_config["data"].get("extensions", {}).get("attributes", {})

        # Compare states
        comparison = self._compare_attributes(current_attributes, desired_attributes)

        response_text = f"🔄 **Host State Comparison**\\n\\n"
        response_text += f"**Host:** {host_name}\\n"
        response_text += f"**Changes Required:** {'Yes' if comparison['has_changes'] else 'No'}\\n\\n"

        if comparison["has_changes"]:
            response_text += "📋 **Detected Changes:**\\n"
            response_text += self._format_attribute_changes(comparison)
        else:
            response_text += "✅ Host is already in the desired state"

        return [{"type": "text", "text": response_text}]

    async def _get_host_effective_attributes(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get effective host attributes including inherited values"""
        host_name = arguments.get("host_name")

        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        # Get host configuration
        host_config = self.client.get(f"objects/host_config/{host_name}")
        if not host_config.get("success"):
            return self.error_response("Host not found", f"Host '{host_name}' not found")

        host_data = host_config["data"]
        extensions = host_data.get("extensions", {})
        attributes = extensions.get("attributes", {})
        folder_path = extensions.get("folder", "/")

        # Get folder configuration for inherited attributes
        folder_config = None
        if folder_path != "/":
            folder_config = self.client.get(f"objects/folder_config/{folder_path}")

        effective_attributes = {}
        inherited_attributes = {}

        # Add folder attributes if available
        if folder_config and folder_config.get("success"):
            folder_attrs = folder_config["data"].get("extensions", {}).get("attributes", {})
            inherited_attributes.update(folder_attrs)

        # Host attributes override folder attributes
        effective_attributes.update(inherited_attributes)
        effective_attributes.update(attributes)

        response_text = f"📋 **Effective Host Attributes**\\n\\n"
        response_text += f"**Host:** {host_name}\\n"
        response_text += f"**Folder:** {folder_path}\\n\\n"

        if effective_attributes:
            response_text += "🎯 **Effective Attributes:**\\n"
            for key, value in effective_attributes.items():
                source = "Host" if key in attributes else "Inherited"
                response_text += f"• **{key}:** {value} _{source}_\\n"
        else:
            response_text += "ℹ️ No attributes configured"

        return [{"type": "text", "text": response_text}]

    def _validate_host_creation_params(
        self, host_name: str, folder: str, attributes: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """Validate parameters for host creation"""
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")

        if not self._validate_host_name(host_name):
            return self.error_response(
                "Invalid host name", "Host name must contain only letters, numbers, hyphens, and underscores"
            )

        # Validate IP address if provided
        if "ipaddress" in attributes and not self._validate_ip_address(attributes["ipaddress"]):
            return self.error_response("Invalid IP address", "IP address format is invalid")

        return None

    def _validate_host_name(self, host_name: str) -> bool:
        """Validate host name format"""
        if not host_name:
            return False

        import re

        # CheckMK host name pattern: letters, numbers, hyphens, underscores, dots
        pattern = r"^[a-zA-Z0-9._-]+$"
        return re.match(pattern, host_name) is not None

    def _validate_ip_address(self, ip_address: str) -> bool:
        """Validate IP address format"""
        try:
            import ipaddress

            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False

    def _validate_folder_exists(self, folder: str) -> bool:
        """Check if folder exists (basic validation)"""
        try:
            folder_path = folder if folder != "/" else "~"
            result = self.client.get(f"objects/folder_config/{folder_path}")
            return result.get("success", False)
        except:
            return False

    def _compare_attributes(self, current: Dict[str, Any], desired: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current and desired attributes"""
        changes = {"has_changes": False, "added": {}, "modified": {}, "removed": {}}

        # Find added and modified attributes
        for key, value in desired.items():
            if key not in current:
                changes["added"][key] = value
                changes["has_changes"] = True
            elif current[key] != value:
                changes["modified"][key] = {"old": current[key], "new": value}
                changes["has_changes"] = True

        # Find removed attributes
        for key in current:
            if key not in desired:
                changes["removed"][key] = current[key]
                changes["has_changes"] = True

        return changes

    def _format_attribute_changes(self, changes: Dict[str, Any]) -> str:
        """Format attribute changes for display"""
        output = ""

        if changes["added"]:
            output += "**Added:**\\n"
            for key, value in changes["added"].items():
                output += f"• {key}: {value}\\n"

        if changes["modified"]:
            output += "**Modified:**\\n"
            for key, change in changes["modified"].items():
                output += f"• {key}: {change['old']} → {change['new']}\\n"

        if changes["removed"]:
            output += "**Removed:**\\n"
            for key, value in changes["removed"].items():
                output += f"• {key}: {value}\\n"

        return output

    def _validate_host_update_attributes(self, attributes: Dict[str, Any]) -> List[str]:
        """Validate host update attributes for common CheckMK attributes"""
        errors = []

        # Validate IP address
        if "ipaddress" in attributes:
            ip_address = attributes["ipaddress"]
            if not self._validate_ip_address(ip_address):
                errors.append(f"Invalid IP address format: '{ip_address}'")

        # Validate site
        if "site" in attributes:
            site = attributes["site"]
            if not isinstance(site, str) or not site.strip():
                errors.append("Site must be a non-empty string")
            elif not self._validate_site_name(site):
                errors.append(
                    f"Invalid site name format: '{site}'. Must contain only letters, numbers, and underscores"
                )

        # Validate alias
        if "alias" in attributes:
            alias = attributes["alias"]
            if not isinstance(alias, str):
                errors.append("Alias must be a string")
            elif len(alias) > 255:
                errors.append("Alias cannot be longer than 255 characters")

        # Validate tag attributes (tags must be prefixed with 'tag_')
        for key, value in attributes.items():
            if key.startswith("tag_"):
                tag_name = key[4:]  # Remove 'tag_' prefix
                if not self._validate_tag_name(tag_name):
                    errors.append(
                        f"Invalid tag name: '{tag_name}'. Must contain only letters, numbers, and underscores"
                    )
                if not isinstance(value, str):
                    errors.append(f"Tag value for '{key}' must be a string")
            elif key in ["tag", "tags"]:
                errors.append(f"Tag attributes must be prefixed with 'tag_'. Use 'tag_{key}' instead of '{key}'")

        return errors

    def _validate_site_name(self, site_name: str) -> bool:
        """Validate CheckMK site name format"""
        if not site_name:
            return False

        import re

        # CheckMK site name pattern: letters, numbers, underscores
        pattern = r"^[a-zA-Z0-9_]+$"
        return re.match(pattern, site_name) is not None

    def _validate_tag_name(self, tag_name: str) -> bool:
        """Validate CheckMK tag name format"""
        if not tag_name:
            return False

        import re

        # CheckMK tag name pattern: letters, numbers, underscores
        pattern = r"^[a-zA-Z0-9_]+$"
        return re.match(pattern, tag_name) is not None
