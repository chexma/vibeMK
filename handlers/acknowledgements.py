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

            if not host_name:
                return [{"type": "text", "text": "❌ Error: host_name is required"}]

            # Use CheckMK REST API action endpoint for host acknowledgement
            endpoint = f"objects/host/{host_name}/actions/acknowledge_problem/invoke"

            data = {
                "acknowledge_type": "host",
                "sticky": sticky,
                "persistent": persistent,
                "notify": notify,
                "comment": comment,
                "host_name": host_name,
            }

            result = self.client.post(endpoint, data=data)

            if result.get("success"):
                return [
                    {
                        "type": "text",
                        "text": f"✅ **Host Acknowledgement Created**\n\n"
                        f"Host: **{host_name}**\n"
                        f"Comment: {comment}\n"
                        f"Sticky: {sticky}\n"
                        f"Persistent: {persistent}\n"
                        f"Notify: {notify}\n\n"
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

            if not host_name or not service_description:
                return [{"type": "text", "text": "❌ Error: host_name and service_description are required"}]

            # URL encode the service description for the query parameter
            encoded_service = urllib.parse.quote(service_description, safe="")
            endpoint = f"objects/host/{host_name}/actions/acknowledge_service_problem/invoke?service_description={encoded_service}"

            data = {
                "acknowledge_type": "service",
                "sticky": sticky,
                "persistent": persistent,
                "notify": notify,
                "comment": comment,
                "host_name": host_name,
                "service_description": service_description,
            }

            result = self.client.post(endpoint, data=data)

            if result.get("success"):
                return [
                    {
                        "type": "text",
                        "text": f"✅ **Service Acknowledgement Created**\n\n"
                        f"Host: **{host_name}**\n"
                        f"Service: **{service_description}**\n"
                        f"Comment: {comment}\n"
                        f"Sticky: {sticky}\n"
                        f"Persistent: {persistent}\n"
                        f"Notify: {notify}\n\n"
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
            # Get acknowledgements from CheckMK API
            endpoint = "domain-types/acknowledge/collections/all"
            result = self.client.get(endpoint)

            if not result.get("success"):
                # Try alternative endpoint if the primary one doesn't exist
                endpoint = "domain-types/comment/collections/all"
                result = self.client.get(endpoint)

                if result.get("success"):
                    # Filter for acknowledgement comments
                    comments = result.get("data", {}).get("value", [])
                    acknowledgements = [
                        comment for comment in comments if comment.get("extensions", {}).get("comment_type") == "ack"
                    ]
                else:
                    return [{"type": "text", "text": "❌ Unable to retrieve acknowledgements from CheckMK API"}]
            else:
                acknowledgements = result.get("data", {}).get("value", [])

            if not acknowledgements:
                return [{"type": "text", "text": "✅ **Acknowledgements List**\n\nNo active acknowledgements found."}]

            # Format acknowledgements list
            ack_list = ["✅ **Current Acknowledgements**\n"]

            for i, ack in enumerate(acknowledgements, 1):
                extensions = ack.get("extensions", {})
                ack_id = ack.get("id", f"ack-{i}")
                host_name = extensions.get("host_name", "Unknown")
                service_desc = extensions.get("service_description", "")
                comment = extensions.get("comment", "No comment")
                author = extensions.get("author", "Unknown")

                ack_type = "Service" if service_desc else "Host"
                service_info = f"\nService: **{service_desc}**" if service_desc else ""

                ack_list.append(
                    f"\n**{i}. Acknowledgement #{ack_id}**\n"
                    f"Type: {ack_type}\n"
                    f"Host: **{host_name}**{service_info}\n"
                    f"Comment: {comment}\n"
                    f"Author: {author}\n"
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

            if ack_id:
                # Remove by acknowledgement ID
                endpoint = f"objects/acknowledge/{ack_id}"
                result = self.client.delete(endpoint)

                if result.get("success"):
                    return [{"type": "text", "text": f"✅ Successfully removed acknowledgement #{ack_id}"}]
                else:
                    # Try comment endpoint instead
                    endpoint = f"objects/comment/{ack_id}"
                    result = self.client.delete(endpoint)

                    if result.get("success"):
                        return [{"type": "text", "text": f"✅ Successfully removed acknowledgement #{ack_id}"}]
                    else:
                        error_msg = result.get("data", {}).get("detail", "Unknown error")
                        return [{"type": "text", "text": f"❌ Failed to remove acknowledgement: {error_msg}"}]

            elif host_name:
                # Remove by host (and optionally service)
                if service_description:
                    # Remove service acknowledgement using action endpoint
                    encoded_service = urllib.parse.quote(service_description, safe="")
                    endpoint = f"objects/host/{host_name}/actions/remove_service_acknowledgement/invoke?service_description={encoded_service}"
                else:
                    # Remove host acknowledgement using action endpoint
                    endpoint = f"objects/host/{host_name}/actions/remove_acknowledgement/invoke"

                result = self.client.post(endpoint, data={})

                if result.get("success"):
                    target = f"{host_name}/{service_description}" if service_description else host_name
                    return [{"type": "text", "text": f"✅ Successfully removed acknowledgement for {target}"}]
                else:
                    error_msg = result.get("data", {}).get("detail", "Unknown error")
                    return [{"type": "text", "text": f"❌ Failed to remove acknowledgement: {error_msg}"}]

            else:
                return [{"type": "text", "text": "❌ Error: acknowledgement_id or host_name is required"}]

        except Exception as e:
            logger.exception("Error removing acknowledgement")
            return [{"type": "text", "text": f"❌ Error removing acknowledgement: {str(e)}"}]
