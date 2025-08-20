"""
Folder management handlers
"""

from typing import Dict, Any, List
from handlers.base import BaseHandler
from api.exceptions import CheckMKError


class FolderHandler(BaseHandler):
    """Handle folder management operations"""
    
    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle folder-related tool calls"""
        
        try:
            if tool_name == "vibemk_get_folders":
                return await self._get_folders(arguments)
            elif tool_name == "vibemk_create_folder":
                return await self._create_folder(arguments)
            elif tool_name == "vibemk_delete_folder":
                return await self._delete_folder(arguments)
            elif tool_name == "vibemk_update_folder":
                return await self._update_folder(arguments)
            elif tool_name == "vibemk_move_folder":
                return await self._move_folder(arguments)
            elif tool_name == "vibemk_get_folder_hosts":
                return await self._get_folder_hosts(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")
                
        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))
    
    async def _get_folders(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of folders"""
        params = {}
        if parent := arguments.get("parent"):
            params["parent"] = parent
        
        result = self.client.get("domain-types/folder_config/collections/all", params=params)
        
        if not result.get("success"):
            return self.error_response("Failed to retrieve folders")
        
        folders = result["data"].get("value", [])
        if not folders:
            return [{"type": "text", "text": "📁 No folders found"}]
        
        folder_list = []
        for folder in folders[:50]:  # Limit display
            folder_id = folder.get("id", "Unknown")
            title = folder.get("title", folder_id)
            extensions = folder.get("extensions", {})
            path = extensions.get("path", folder_id)
            folder_list.append(f"📁 {path} - {title}")
        
        return [{
            "type": "text",
            "text": (
                f"📁 **CheckMK Folders** ({len(folders)} total, showing first {len(folder_list)}):\n\n" + 
                "\n".join(folder_list)
            )
        }]
    
    async def _create_folder(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new folder"""
        folder = arguments.get("folder")
        title = arguments.get("title")
        parent = arguments.get("parent", "/")
        
        if not folder or not title:
            return self.error_response("Missing parameters", "folder and title are required")
        
        # Convert parent path format: "/" -> "~" for root folder
        if parent == "/":
            parent = "~"
        
        data = {
            "name": folder,  # Changed from "folder" to "name"
            "title": title,
            "parent": parent,
            "attributes": {}  # Required field for CheckMK 2.3+
        }
        
        result = self.client.post("domain-types/folder_config/collections/all", data=data)
        
        if result.get("success"):
            return [{
                "type": "text",
                "text": (
                    f"✅ **Folder Created Successfully**\n\n"
                    f"Folder: {folder}\n"
                    f"Title: {title}\n"
                    f"Parent: {parent}\n\n"
                    f"⚠️ **Remember to activate changes!**"
                )
            }]
        else:
            return self.error_response("Folder creation failed", f"Could not create folder '{folder}'")
    
    async def _delete_folder(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a folder"""
        folder = arguments.get("folder")
        delete_mode = arguments.get("delete_mode", "abort_on_nonempty")
        
        if not folder:
            return self.error_response("Missing parameter", "folder is required")
        
        # Convert folder path to CheckMK API format
        # /api -> ~api, /test/subfolder -> ~test~subfolder
        if folder.startswith("/"):
            encoded_folder = "~" + folder[1:].replace("/", "~")
        else:
            encoded_folder = "~" + folder.replace("/", "~")
        
        params = {"delete_mode": delete_mode}
        result = self.client.delete(f"objects/folder_config/{encoded_folder}", params=params)
        
        if result.get("success"):
            return [{
                "type": "text",
                "text": (
                    f"✅ **Folder Deleted Successfully**\n\n"
                    f"Folder: {folder}\n"
                    f"Delete mode: {delete_mode}\n\n"
                    f"📝 **Next Steps:**\n"
                    f"1️⃣ Use 'get_pending_changes' to review the deletion\n"
                    f"2️⃣ Use 'activate_changes' to apply the configuration\n\n"
                    f"💡 **Important:** The folder is only marked for deletion until you activate changes!"
                )
            }]
        else:
            return self.error_response("Folder deletion failed", f"Could not delete folder '{folder}'")
    
    async def _update_folder(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update folder properties"""
        folder = arguments.get("folder")
        title = arguments.get("title")
        attributes = arguments.get("attributes", {})
        
        if not folder:
            return self.error_response("Missing parameter", "folder is required")
        
        # Convert folder path to CheckMK API format
        if folder.startswith("/"):
            encoded_folder = "~" + folder[1:].replace("/", "~")
        else:
            encoded_folder = "~" + folder.replace("/", "~")
        
        data = {}
        if title:
            data["title"] = title
        if attributes:
            data["attributes"] = attributes
        
        result = self.client.put(f"objects/folder_config/{encoded_folder}", data=data)
        
        if result.get("success"):
            return self.success_response(
                "Folder Updated Successfully", 
                {"folder": folder, "message": "Remember to activate changes!"}
            )
        else:
            return self.error_response("Folder update failed", f"Could not update folder '{folder}'")
    
    async def _move_folder(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Move folder to different parent"""
        folder = arguments.get("folder")
        destination = arguments.get("destination")
        
        if not folder or not destination:
            return self.error_response("Missing parameters", "folder and destination are required")
        
        # Convert folder path to CheckMK API format
        if folder.startswith("/"):
            encoded_folder = "~" + folder[1:].replace("/", "~")
        else:
            encoded_folder = "~" + folder.replace("/", "~")
        
        data = {"destination": destination}
        result = self.client.post(f"objects/folder_config/{encoded_folder}/actions/move/invoke", data=data)
        
        if result.get("success"):
            return self.success_response(
                "Folder Moved Successfully", 
                {"folder": folder, "destination": destination, "message": "Remember to activate changes!"}
            )
        else:
            return self.error_response("Folder move failed", f"Could not move folder '{folder}'")
    
    async def _get_folder_hosts(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all hosts in a specific folder"""
        folder = arguments.get("folder")
        
        if not folder:
            return self.error_response("Missing parameter", "folder is required")
        
        # Convert folder path to CheckMK API format
        if folder.startswith("/"):
            encoded_folder = "~" + folder[1:].replace("/", "~")
        else:
            encoded_folder = "~" + folder.replace("/", "~")
        
        result = self.client.get(f"objects/folder_config/{encoded_folder}/collections/hosts")
        
        if not result.get("success"):
            return self.error_response("Failed to retrieve folder hosts", f"Could not access folder '{folder}'")
        
        hosts = result["data"].get("value", [])
        if not hosts:
            return [{
                "type": "text", 
                "text": f"📁 **Folder '{folder}' is empty**\n\nNo hosts found in this folder."
            }]
        
        host_list = []
        for host in hosts:
            host_id = host.get("id", "Unknown")
            host_list.append(f"🖥️ {host_id}")
        
        return [{
            "type": "text",
            "text": (
                f"📁 **Hosts in Folder '{folder}'** ({len(hosts)} total):\n\n" + 
                "\n".join(host_list)
            )
        }]