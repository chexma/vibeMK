"""
Host management handlers
"""

from typing import Dict, Any, List
from handlers.base import BaseHandler
from api.exceptions import CheckMKError, CheckMKNotFoundError


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
        
        return [{
            "type": "text",
            "text": (
                f"🖥️ **CheckMK Hosts** ({len(hosts)} total, showing first {len(host_list)}):\\n\\n" + 
                "\\n".join(host_list)
            )
        }]
    
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
                'columns': ['name', 'state', 'hard_state', 'state_type', 'plugin_output', 'last_check', 'last_state_change', 'has_been_checked']
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
                                last_check_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_check))
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
                        
                        return [{
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
                            )
                        }]
                    else:
                        return self.error_response("No state data", f"Host '{host_name}' found but no state information available")
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
                                
                                return [{
                                    "type": "text",
                                    "text": (
                                        f"✅ **Host Status: {host_name}** (Fallback Method)\\n\\n"
                                        f"**Status:** {status_display}\\n"
                                        f"**State Code:** {state}\\n\\n"
                                        f"✅ **Data from CheckMK host collections API**"
                                    )
                                }]
                    
                    # Host not found in collections
                    return self.error_response("Host not found", f"Host '{host_name}' not found in host collections")
        except Exception as e:
            self.logger.debug(f"Fallback method failed: {e}")
        
        # Method 3: Final fallback - check if host exists in configuration
        try:
            host_config = self.client.get(f"objects/host_config/{host_name}")
            if host_config.get("success"):
                return [{
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
                    )
                }]
            else:
                return self.error_response("Host not found", f"Host '{host_name}' not found in CheckMK")
        except Exception as e:
            self.logger.debug(f"Host config check failed: {e}")
        
        # If all methods failed, return comprehensive error information
        return [{
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
            )
        }]
    
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
        
        return [{
            "type": "text",
            "text": (
                f"🔍 **Host Details: {host_name}**\\n\\n"
                f"Folder: {extensions.get('folder', '/')}\\n"
                f"IP Address: {attributes.get('ipaddress', 'Not set')}\\n"
                f"Alias: {attributes.get('alias', 'Not set')}\\n"
                f"Agent Type: {attributes.get('tag_agent', 'Unknown')}\\n"
                f"Site: {attributes.get('site', 'Not set')}"
            )
        }]
    
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
        """Create a new host"""
        host_name = arguments.get("host_name")
        folder = arguments.get("folder", "/")
        attributes = arguments.get("attributes", {})
        
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")
        
        data = {
            "folder": folder,
            "host_name": host_name,
            "attributes": attributes
        }
        
        result = self.client.post("domain-types/host_config/collections/all", data=data)
        
        if result.get("success"):
            return [{
                "type": "text",
                "text": (
                    f"✅ **Host Created Successfully**\\n\\n"
                    f"Host: {host_name}\\n"
                    f"Folder: {folder}\\n\\n"
                    f"⚠️ **Remember to activate changes!**"
                )
            }]
        else:
            return self.error_response("Host creation failed", f"Could not create host '{host_name}'")
    
    async def _update_host(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update host configuration"""
        host_name = arguments.get("host_name")
        attributes = arguments.get("attributes", {})
        
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")
        
        data = {"attributes": attributes}
        result = self.client.put(f"objects/host_config/{host_name}", data=data)
        
        if result.get("success"):
            return self.success_response(
                "Host Updated Successfully", 
                {"host": host_name, "message": "Remember to activate changes!"}
            )
        else:
            return self.error_response("Host update failed", f"Could not update host '{host_name}'")
    
    async def _delete_host(self, host_name: str) -> List[Dict[str, Any]]:
        """Delete a host"""
        if not host_name:
            return self.error_response("Missing parameter", "host_name is required")
        
        result = self.client.delete(f"objects/host_config/{host_name}")
        
        if result.get("success"):
            return [{
                "type": "text",
                "text": (
                    f"✅ **Host Deleted Successfully**\\n\\n"
                    f"Host: {host_name}\\n\\n"
                    f"📝 **Next Steps:**\\n"
                    f"1️⃣ Use 'get_pending_changes' to review the deletion\\n"
                    f"2️⃣ Use 'activate_changes' to apply the configuration\\n\\n"
                    f"💡 **Important:** The host is only marked for deletion until you activate changes!"
                )
            }]
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
                {"host": host_name, "folder": target_folder, "message": "Remember to activate changes!"}
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
                "Bulk Update Successful", 
                {"updated": len(entries), "message": "Remember to activate changes!"}
            )
        else:
            return self.error_response("Bulk update failed", "Could not update hosts")