"""
Folder management handlers
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler
from utils.folder_validator import FolderValidator, validate_folder_path


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

        return [
            {
                "type": "text",
                "text": (
                    f"📁 **CheckMK Folders** ({len(folders)} total, showing first {len(folder_list)}):\n\n"
                    + "\n".join(folder_list)
                ),
            }
        ]

    async def _create_folder(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new folder with enhanced validation"""
        folder = arguments.get("folder")
        title = arguments.get("title")
        parent = arguments.get("parent", "/")

        if not folder or not title:
            return self.error_response("Missing parameters", "folder and title are required")

        # Convert folder name to lowercase for consistency
        folder = folder.lower()

        # Validate and convert parent folder path
        parent_validation = validate_folder_path(parent, "create")
        if not parent_validation["is_valid"]:
            return self.error_response("Invalid parent folder", parent_validation["error_message"])

        parent_checkmk = parent_validation["checkmk_path"]

        # Validate folder name (single folder name, not a path)
        if "/" in folder or "~" in folder:
            return self.error_response(
                "Invalid folder name",
                "Folder name cannot contain path separators. Use 'parent' parameter for folder hierarchy.",
            )

        # Build the full path for validation
        full_path = f"{parent_validation['display_path']}/{folder}".replace("//", "/")
        path_validation = validate_folder_path(full_path, "create")

        if not path_validation["is_valid"]:
            return self.error_response("Invalid folder path", path_validation["error_message"])

        data = {
            "name": folder,
            "title": title,
            "parent": parent_checkmk,
            "attributes": {},
        }

        result = self.client.post("domain-types/folder_config/collections/all", data=data)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Folder Created Successfully**\n\n"
                        f"📁 **Folder:** {folder}\n"
                        f"📝 **Title:** {title}\n"
                        f"📂 **Parent:** {parent_validation['display_path']}\n"
                        f"🔗 **Full Path:** {path_validation['display_path']}\n"
                        f"⚙️ **API Path:** {path_validation['checkmk_path']}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            error_data = result.get("data", {})
            error_msg = error_data.get("detail", "Unknown error") if isinstance(error_data, dict) else str(error_data)
            return self.error_response("Folder creation failed", f"Could not create folder '{folder}': {error_msg}")

    async def _delete_folder(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a folder with enhanced path validation"""
        folder = arguments.get("folder")
        delete_mode = arguments.get("delete_mode", "abort_on_nonempty")

        if not folder:
            return self.error_response("Missing parameter", "folder is required")

        # Validate and convert folder path using the new validator
        path_validation = validate_folder_path(folder, "delete")

        if not path_validation["is_valid"]:
            return self.error_response("Invalid folder path", path_validation["error_message"])

        encoded_folder = path_validation["checkmk_path"]
        params = {"delete_mode": delete_mode}
        result = self.client.delete(f"objects/folder_config/{encoded_folder}", params=params)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Folder Deleted Successfully**\n\n"
                        f"📁 **Folder:** {path_validation['display_path']}\n"
                        f"⚙️ **API Path:** {encoded_folder}\n"
                        f"🗑️ **Delete Mode:** {delete_mode}\n\n"
                        f"📝 **Next Steps:**\n"
                        f"1️⃣ Use 'get_pending_changes' to review the deletion\n"
                        f"2️⃣ Use 'activate_changes' to apply the configuration\n\n"
                        f"💡 **Important:** The folder is only marked for deletion until you activate changes!"
                    ),
                }
            ]
        else:
            error_data = result.get("data", {})
            error_msg = error_data.get("detail", "Unknown error") if isinstance(error_data, dict) else str(error_data)
            return self.error_response("Folder deletion failed", f"Could not delete folder '{folder}': {error_msg}")

    async def _update_folder(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update folder properties with enhanced path validation"""
        folder = arguments.get("folder")
        title = arguments.get("title")
        attributes = arguments.get("attributes", {})

        if not folder:
            return self.error_response("Missing parameter", "folder is required")

        # Validate and convert folder path
        path_validation = validate_folder_path(folder, "update")

        if not path_validation["is_valid"]:
            return self.error_response("Invalid folder path", path_validation["error_message"])

        encoded_folder = path_validation["checkmk_path"]

        data = {}
        if title:
            data["title"] = title
        if attributes:
            data["attributes"] = attributes

        if not data:
            return self.error_response("Missing parameters", "At least one of 'title' or 'attributes' is required")

        headers = self._if_match_header(f"objects/folder_config/{encoded_folder}")
        result = self.client.put(f"objects/folder_config/{encoded_folder}", data=data, headers=headers)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Folder Updated Successfully**\n\n"
                        f"📁 **Folder:** {path_validation['display_path']}\n"
                        f"⚙️ **API Path:** {encoded_folder}\n"
                        + (f"📝 **New Title:** {title}\n" if title else "")
                        + (f"⚙️ **Attributes Updated:** {len(attributes)} items\n" if attributes else "")
                        + "\n⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            error_data = result.get("data", {})
            error_msg = error_data.get("detail", "Unknown error") if isinstance(error_data, dict) else str(error_data)
            return self.error_response("Folder update failed", f"Could not update folder '{folder}': {error_msg}")

    async def _move_folder(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Move folder to different parent with enhanced path validation"""
        folder = arguments.get("folder")
        destination = arguments.get("destination")

        if not folder or not destination:
            return self.error_response("Missing parameters", "folder and destination are required")

        # Validate source folder path
        source_validation = validate_folder_path(folder, "move")
        if not source_validation["is_valid"]:
            return self.error_response("Invalid source folder path", source_validation["error_message"])

        # Validate destination folder path
        dest_validation = validate_folder_path(destination, "general")
        if not dest_validation["is_valid"]:
            return self.error_response("Invalid destination folder path", dest_validation["error_message"])

        encoded_folder = source_validation["checkmk_path"]
        destination_checkmk = dest_validation["checkmk_path"]

        data = {"destination": destination_checkmk}
        result = self.client.post(f"objects/folder_config/{encoded_folder}/actions/move/invoke", data=data)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Folder Moved Successfully**\n\n"
                        f"📁 **Source:** {source_validation['display_path']}\n"
                        f"📂 **Destination:** {dest_validation['display_path']}\n"
                        f"⚙️ **API Paths:**\n"
                        f"   • From: {encoded_folder}\n"
                        f"   • To: {destination_checkmk}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            error_data = result.get("data", {})
            error_msg = error_data.get("detail", "Unknown error") if isinstance(error_data, dict) else str(error_data)
            return self.error_response("Folder move failed", f"Could not move folder '{folder}': {error_msg}")

    async def _get_folder_hosts(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all hosts in a specific folder with enhanced path validation"""
        folder = arguments.get("folder")

        if not folder:
            return self.error_response("Missing parameter", "folder is required")

        # Validate and convert folder path
        path_validation = validate_folder_path(folder, "general")

        if not path_validation["is_valid"]:
            return self.error_response("Invalid folder path", path_validation["error_message"])

        encoded_folder = path_validation["checkmk_path"]
        result = self.client.get(f"objects/folder_config/{encoded_folder}/collections/hosts")

        if not result.get("success"):
            error_data = result.get("data", {})
            error_msg = error_data.get("detail", "Unknown error") if isinstance(error_data, dict) else str(error_data)
            return self.error_response(
                "Failed to retrieve folder hosts",
                f"Could not access folder '{path_validation['display_path']}': {error_msg}",
            )

        hosts = result["data"].get("value", [])
        if not hosts:
            return [
                {
                    "type": "text",
                    "text": (
                        f"📁 **Folder '{path_validation['display_path']}' is empty**\n\n"
                        f"⚙️ **API Path:** {encoded_folder}\n\n"
                        f"No hosts found in this folder."
                    ),
                }
            ]

        host_list = []
        for host in hosts[:50]:  # Limit display for performance
            host_id = host.get("id", "Unknown")
            extensions = host.get("extensions", {})
            alias = extensions.get("alias", "")
            host_display = f"🖥️ {host_id}" + (f" ({alias})" if alias else "")
            host_list.append(host_display)

        return [
            {
                "type": "text",
                "text": (
                    f"📁 **Hosts in Folder '{path_validation['display_path']}'** ({len(hosts)} total"
                    + (", showing first 50" if len(hosts) > 50 else "")
                    + "):\n\n"
                    + f"⚙️ **API Path:** {encoded_folder}\n\n"
                    + "\n".join(host_list)
                ),
            }
        ]
