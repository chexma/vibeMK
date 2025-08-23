"""
CheckMK Acknowledgement Handler
Handles problem acknowledgements for hosts and services
"""

import urllib.parse
from typing import Any, Dict, List

from api import CheckMKClient
from utils import get_logger

logger = get_logger(__name__)


class AcknowledgementHandler:
    """Handler for CheckMK acknowledgement operations"""

    def __init__(self, client: CheckMKClient):
        self.client = client
        self._checkMK_version = None
        self._endpoints_tested = False

    async def _detect_checkMK_version(self) -> str:
        """Detect CheckMK version to use appropriate endpoints"""
        if self._checkMK_version is not None and self._endpoints_tested:
            return self._checkMK_version

        try:
            # Get version info from the API
            version_result = self.client.get("version")
            if version_result.get("success"):
                version_data = version_result.get("data", {})
                versions = version_data.get("versions", {})
                checkmk_version = versions.get("checkmk", "")

                if checkmk_version.startswith("2.4") or checkmk_version.startswith("2.5"):
                    self._checkMK_version = "2.4+"
                    logger.info(f"Detected CheckMK {checkmk_version} - using 2.4+ acknowledge endpoints")
                else:
                    self._checkMK_version = "2.3"
                    logger.info(f"Detected CheckMK {checkmk_version} - using 2.3 acknowledge endpoints")
            else:
                # Fallback: try server URL port to guess version
                server_url = self.client.config.server_url
                if ":8081" in server_url:
                    self._checkMK_version = "2.4+"
                    logger.info("Port 8081 detected - assuming CheckMK 2.4+")
                else:
                    self._checkMK_version = "2.3"
                    logger.info("Port 8080 detected - assuming CheckMK 2.3")

        except Exception as e:
            logger.warning(f"Could not detect CheckMK version, using port fallback: {e}")
            # Fallback: try server URL port to guess version
            try:
                server_url = self.client.config.server_url
                if ":8081" in server_url:
                    self._checkMK_version = "2.4+"
                    logger.info("Port 8081 detected - assuming CheckMK 2.4+")
                else:
                    self._checkMK_version = "2.3"
                    logger.info("Port 8080 detected - assuming CheckMK 2.3")
            except:
                self._checkMK_version = "2.3"

        self._endpoints_tested = True
        return self._checkMK_version

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, str]]:
        """Route acknowledgement tool calls to appropriate methods"""
        method_map = {
            "vibemk_acknowledge_host_problem": self.acknowledge_host_problem,
            "vibemk_acknowledge_service_problem": self.acknowledge_service_problem,
            "vibemk_list_acknowledgements": self.list_acknowledgements,
            "vibemk_remove_acknowledgement": self.remove_acknowledgement,
        }

        if tool_name not in method_map:
            return [{"type": "text", "text": f"❌ Unknown acknowledgement tool: {tool_name}"}]

        return await method_map[tool_name](arguments)

    async def acknowledge_host_problem(self, args: Dict[str, Any]) -> List[Dict[str, str]]:
        """Acknowledge a host problem"""
        try:
            host_name = args.get("host_name")
            comment = args.get("comment", "Problem acknowledged via vibeMK")
            sticky = args.get("sticky", False)
            persistent = args.get("persistent", False)
            notify = args.get("notify", False)
            expire_on = args.get("expire_on")  # Optional expiration time

            if not host_name:
                return [{"type": "text", "text": "❌ Error: host_name is required"}]

            # Detect CheckMK version and use appropriate endpoint
            version = await self._detect_checkMK_version()

            # Both CheckMK 2.3 and 2.4+ support the same endpoint
            endpoint = "domain-types/acknowledge/collections/host"

            data = {
                "acknowledge_type": "host",
                "sticky": sticky,
                "persistent": persistent,
                "notify": notify,
                "comment": comment,
                "host_name": host_name,
            }

            # Add expiration time if provided (2.4+ feature)
            if expire_on and version == "2.4+":
                data["expire_on"] = expire_on

            result = self.client.post(endpoint, data=data)

            if result.get("success"):
                expire_info = f"Expire on: {expire_on or 'Never'}\n" if version == "2.4+" else ""
                return [
                    {
                        "type": "text",
                        "text": f"✅ **Host Acknowledgement Created**\n\n"
                        f"Host: **{host_name}**\n"
                        f"Comment: {comment}\n"
                        f"Sticky: {sticky}\n"
                        f"Persistent: {persistent}\n"
                        f"Notify: {notify}\n"
                        f"{expire_info}\n"
                        f"CheckMK Version: {version}\n\n"
                        f"The host problem has been acknowledged and will not generate further alerts.",
                    }
                ]
            else:
                error_msg = result.get("data", {}).get("detail", "Unknown error")
                return [{"type": "text", "text": f"❌ Failed to acknowledge host problem: {error_msg}"}]

        except Exception as e:
            logger.exception(f"Error acknowledging host problem for {host_name}")
            return [{"type": "text", "text": f"❌ Error acknowledging host problem: {str(e)}"}]

    async def acknowledge_service_problem(self, args: Dict[str, Any]) -> List[Dict[str, str]]:
        """Acknowledge a service problem"""
        try:
            host_name = args.get("host_name")
            service_description = args.get("service_description")
            comment = args.get("comment", "Problem acknowledged via vibeMK")
            sticky = args.get("sticky", False)
            persistent = args.get("persistent", False)
            notify = args.get("notify", False)
            expire_on = args.get("expire_on")  # Optional expiration time

            if not host_name or not service_description:
                return [{"type": "text", "text": "❌ Error: host_name and service_description are required"}]

            # Detect CheckMK version and use appropriate endpoint
            version = await self._detect_checkMK_version()

            # Both CheckMK 2.3 and 2.4+ support the same endpoint
            endpoint = "domain-types/acknowledge/collections/service"

            data = {
                "acknowledge_type": "service",
                "sticky": sticky,
                "persistent": persistent,
                "notify": notify,
                "comment": comment,
                "host_name": host_name,
                "service_description": service_description,
            }

            # Add expiration time if provided (2.4+ feature)
            if expire_on and version == "2.4+":
                data["expire_on"] = expire_on

            result = self.client.post(endpoint, data=data)

            if result.get("success"):
                expire_info = f"Expire on: {expire_on or 'Never'}\n" if version == "2.4+" else ""
                return [
                    {
                        "type": "text",
                        "text": f"✅ **Service Acknowledgement Created**\n\n"
                        f"Host: **{host_name}**\n"
                        f"Service: **{service_description}**\n"
                        f"Comment: {comment}\n"
                        f"Sticky: {sticky}\n"
                        f"Persistent: {persistent}\n"
                        f"Notify: {notify}\n"
                        f"{expire_info}\n"
                        f"CheckMK Version: {version}\n\n"
                        f"The service problem has been acknowledged and will not generate further alerts.",
                    }
                ]
            else:
                error_msg = result.get("data", {}).get("detail", "Unknown error")
                return [{"type": "text", "text": f"❌ Failed to acknowledge service problem: {error_msg}"}]

        except Exception as e:
            logger.exception(f"Error acknowledging service problem for {host_name}/{service_description}")
            return [{"type": "text", "text": f"❌ Error acknowledging service problem: {str(e)}"}]

    async def list_acknowledgements(self, args: Dict[str, Any]) -> List[Dict[str, str]]:
        """List all current acknowledgements"""
        try:
            # Use CheckMK 2.4 compatible endpoint - acknowledgements are stored as comments
            endpoint = "domain-types/comment/collections/all"
            result = self.client.get(endpoint)

            if not result.get("success"):
                return [{"type": "text", "text": "❌ Unable to retrieve acknowledgements from CheckMK API"}]

            comments = result.get("data", {}).get("value", [])

            # Filter for acknowledgement comments (they have specific characteristics)
            acknowledgements = []
            for comment in comments:
                extensions = comment.get("extensions", {})
                # Acknowledgements typically have certain markers or are persistent comments
                # In CheckMK 2.4, we filter by comment content or other indicators
                comment_text = extensions.get("comment", "").lower()
                if "acknowledge" in comment_text or "ack" in comment_text or extensions.get("persistent", False):
                    acknowledgements.append(comment)

            if not acknowledgements:
                return [{"type": "text", "text": "✅ **Acknowledgements List**\n\nNo active acknowledgements found."}]

            # Format acknowledgements list
            ack_list = ["✅ **Current Acknowledgements**\n"]

            for i, ack in enumerate(acknowledgements, 1):
                extensions = ack.get("extensions", {})
                ack_id = ack.get("id", f"ack-{i}")
                host_name = extensions.get("host_name", "Unknown")
                is_service = extensions.get("is_service", False)
                comment = extensions.get("comment", "No comment")
                author = extensions.get("author", "Unknown")
                entry_time = extensions.get("entry_time", "Unknown")
                persistent = extensions.get("persistent", False)

                ack_type = "Service" if is_service else "Host"
                service_info = ""
                if is_service:
                    # For service acknowledgements, we might need to infer service name from comment
                    # or use additional API calls if needed
                    service_info = f"\nType: Service acknowledgement"

                ack_list.append(
                    f"\n**{i}. Acknowledgement #{ack_id}**\n"
                    f"Type: {ack_type}\n"
                    f"Host: **{host_name}**{service_info}\n"
                    f"Comment: {comment}\n"
                    f"Author: {author}\n"
                    f"Entry time: {entry_time}\n"
                    f"Persistent: {persistent}\n"
                )

            return [{"type": "text", "text": "".join(ack_list)}]

        except Exception as e:
            logger.exception("Error listing acknowledgements")
            return [{"type": "text", "text": f"❌ Error listing acknowledgements: {str(e)}"}]

    async def remove_acknowledgement(self, args: Dict[str, Any]) -> List[Dict[str, str]]:
        """Remove an acknowledgement"""
        try:
            # Support multiple removal methods
            ack_id = args.get("acknowledgement_id")
            host_name = args.get("host_name")
            service_description = args.get("service_description")
            comment_pattern = args.get("comment_pattern")
            delete_all_matching = args.get("delete_all_matching", False)

            if ack_id:
                # Remove by acknowledgement ID (stored as comment in CheckMK 2.4)
                endpoint = f"objects/comment/{ack_id}"
                result = self.client.delete(endpoint)

                if result.get("success"):
                    return [{"type": "text", "text": f"✅ Successfully removed acknowledgement #{ack_id}"}]
                else:
                    error_msg = result.get("data", {}).get("detail", "Unknown error")
                    return [{"type": "text", "text": f"❌ Failed to remove acknowledgement: {error_msg}"}]

            elif comment_pattern and delete_all_matching:
                # Remove all acknowledgements matching comment pattern
                # First get all comments
                list_result = self.client.get("domain-types/comment/collections/all")
                if not list_result.get("success"):
                    return [{"type": "text", "text": "❌ Unable to retrieve comments for pattern matching"}]

                comments = list_result.get("data", {}).get("value", [])
                deleted_count = 0

                for comment in comments:
                    extensions = comment.get("extensions", {})
                    comment_text = extensions.get("comment", "")
                    comment_id = comment.get("id")

                    # Check if comment matches pattern and appears to be an acknowledgement
                    if comment_pattern.lower() in comment_text.lower() and (
                        "acknowledge" in comment_text.lower() or "ack" in comment_text.lower()
                    ):

                        delete_result = self.client.delete(f"objects/comment/{comment_id}")
                        if delete_result.get("success"):
                            deleted_count += 1

                if deleted_count > 0:
                    return [
                        {
                            "type": "text",
                            "text": f"✅ Successfully removed {deleted_count} acknowledgements matching pattern '{comment_pattern}'",
                        }
                    ]
                else:
                    return [
                        {"type": "text", "text": f"❌ No acknowledgements found matching pattern '{comment_pattern}'"}
                    ]

            elif host_name:
                # For CheckMK 2.4, we need to find and delete acknowledgements by comment ID
                # since there are no direct host/service action endpoints for removal
                list_result = self.client.get("domain-types/comment/collections/all")
                if not list_result.get("success"):
                    return [{"type": "text", "text": "❌ Unable to retrieve acknowledgements for removal"}]

                comments = list_result.get("data", {}).get("value", [])
                deleted_count = 0

                for comment in comments:
                    extensions = comment.get("extensions", {})
                    comment_host = extensions.get("host_name", "")
                    comment_text = extensions.get("comment", "").lower()
                    comment_id = comment.get("id")
                    is_service = extensions.get("is_service", False)

                    # Check if this is an acknowledgement for the specified host/service
                    if comment_host == host_name and ("acknowledge" in comment_text or "ack" in comment_text):

                        # If service_description is specified, only match service acknowledgements
                        if service_description and not is_service:
                            continue
                        # If no service_description, only match host acknowledgements
                        if not service_description and is_service:
                            continue

                        delete_result = self.client.delete(f"objects/comment/{comment_id}")
                        if delete_result.get("success"):
                            deleted_count += 1

                if deleted_count > 0:
                    target = f"{host_name}/{service_description}" if service_description else host_name
                    return [
                        {
                            "type": "text",
                            "text": f"✅ Successfully removed {deleted_count} acknowledgements for {target}",
                        }
                    ]
                else:
                    target = f"{host_name}/{service_description}" if service_description else host_name
                    return [{"type": "text", "text": f"❌ No acknowledgements found for {target}"}]

            else:
                return [
                    {"type": "text", "text": "❌ Error: acknowledgement_id, host_name, or comment_pattern is required"}
                ]

        except Exception as e:
            logger.exception("Error removing acknowledgement")
            return [{"type": "text", "text": f"❌ Error removing acknowledgement: {str(e)}"}]
