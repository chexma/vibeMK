"""
Connection and diagnostics handlers
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, List
from handlers.base import BaseHandler
from api.exceptions import CheckMKError


class ConnectionHandler(BaseHandler):
    """Handle connection and diagnostic operations"""
    
    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle connection-related tool calls"""
        
        try:
            if tool_name == "vibemk_debug_checkmk_connection":
                return await self._debug_connection()
            elif tool_name == "vibemk_debug_url_detection":
                return await self._debug_url_detection()
            elif tool_name == "vibemk_test_direct_url":
                return await self._test_direct_url(arguments.get("test_url"))
            elif tool_name == "vibemk_test_all_endpoints":
                return await self._test_all_endpoints()
            elif tool_name == "vibemk_get_checkmk_version":
                return await self._get_version()
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")
                
        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))
    
    async def _debug_connection(self) -> List[Dict[str, Any]]:
        """Debug CheckMK connection"""
        try:
            result = self.client.get("version")
            
            if result.get("success"):
                data = result["data"]
                return [{
                    "type": "text",
                    "text": (
                        f"✅ **CheckMK Connection Successful**\n\n"
                        f"🌐 Server: {self.client.config.server_url}\n"
                        f"🏢 Site: {self.client.config.site}\n"
                        f"👤 User: {self.client.config.username}\n"
                        f"🔒 SSL Verify: {self.client.config.verify_ssl}\n"
                        f"🔗 API Base URL: {self.client.api_base_url}\n"
                        f"📊 Version: {data.get('version', 'Unknown')}\n"
                        f"📦 Edition: {data.get('edition', 'Unknown')}"
                    )
                }]
            else:
                return self.error_response("Connection Failed", f"API Base URL: {self.client.api_base_url}")
                
        except Exception as e:
            return self.error_response("Connection Failed", f"Error: {str(e)}")
    
    async def _debug_url_detection(self) -> List[Dict[str, Any]]:
        """Show URL detection debug information"""
        debug_info = self.client.get_debug_results()
        
        return [{
            "type": "text", 
            "text": (
                f"🔍 **URL Detection Debug Results**\n\n"
                f"🌐 Server URL: {self.client.config.server_url}\n"
                f"🏢 Site: {self.client.config.site}\n"
                f"🔗 Selected API URL: {self.client.api_base_url}\n\n"
                f"**Test Results:**\n" + "\n".join(debug_info)
            )
        }]
    
    async def _test_direct_url(self, test_url: str) -> List[Dict[str, Any]]:
        """Test a specific URL directly"""
        if not test_url:
            return self.error_response("Missing URL", "test_url parameter is required")
        
        try:
            req = urllib.request.Request(test_url, headers=self.client.headers)
            with urllib.request.urlopen(req, context=self.client._ssl_context, timeout=self.client.config.timeout) as response:
                response_data = response.read().decode()
                
                try:
                    parsed_data = json.loads(response_data) if response_data else {}
                except json.JSONDecodeError:
                    parsed_data = {"raw": response_data}
                
                return [{
                    "type": "text",
                    "text": (
                        f"✅ **Direct URL Test Successful**\n\n"
                        f"URL: {test_url}\n"
                        f"Status: {response.status}\n"
                        f"Response: {json.dumps(parsed_data, indent=2)}"
                    )
                }]
                
        except urllib.error.HTTPError as e:
            try:
                error_data = json.loads(e.read().decode())
            except:
                error_data = {"error": e.reason}
                
            return [{
                "type": "text",
                "text": (
                    f"❌ **HTTP Error {e.code}**\n\n"
                    f"URL: {test_url}\n"
                    f"Error: {e.reason}\n"
                    f"Response: {json.dumps(error_data, indent=2)}"
                )
            }]
            
        except Exception as e:
            return [{
                "type": "text",
                "text": (
                    f"❌ **Request Failed**\n\n"
                    f"URL: {test_url}\n"
                    f"Error: {str(e)}"
                )
            }]
    
    async def _test_all_endpoints(self) -> List[Dict[str, Any]]:
        """Test all major API endpoints"""
        endpoints = [
            ("version", "Version info"),
            ("domain-types/host_config/collections/all", "Host Configs"),
            ("domain-types/service/collections/all", "Services"), 
            ("domain-types/folder_config/collections/all", "Folders"),
            ("domain-types/downtime/collections/all", "Downtimes"),
            ("domain-types/acknowledge/collections/all", "Acknowledgments"),
            ("domain-types/activation_run/collections/all", "Activations"),
            ("domain-types/user_config/collections/all", "Users"),
            ("domain-types/host_group_config/collections/all", "Host Groups"),
            ("domain-types/service_group_config/collections/all", "Service Groups")
        ]
        
        results = []
        for endpoint, desc in endpoints:
            try:
                result = self.client.get(endpoint)
                status = "✅" if result.get("success") else "❌"
                results.append(f"{status} {endpoint} - {desc} (HTTP {result.get('status', 'unknown')})")
            except Exception as e:
                results.append(f"❌ {endpoint} - {desc} (Error: {str(e)})")
        
        return [{
            "type": "text", 
            "text": f"🧪 **API Endpoint Test Results**\n\n" + "\n".join(results)
        }]
    
    async def _get_version(self) -> List[Dict[str, Any]]:
        """Get CheckMK version information"""
        result = self.client.get("version")
        
        if result.get("success"):
            data = result["data"]
            return [{
                "type": "text",
                "text": (
                    f"📋 **CheckMK Version Information**\n\n"
                    f"Version: {data.get('version', 'Unknown')}\n"
                    f"Edition: {data.get('edition', 'Unknown')}\n"
                    f"Site: {self.client.config.site}\n"
                    f"Server: {self.client.config.server_url}"
                )
            }]
        else:
            return self.error_response("Version Error", "Could not retrieve version information")