"""
CheckMK Host Discovery Handler
Handles service discovery operations for hosts
"""

from typing import Any, Dict, List

from api import CheckMKClient
from utils import get_logger

logger = get_logger(__name__)


class DiscoveryHandler:
    """Handler for CheckMK host discovery operations"""

    def __init__(self, client: CheckMKClient):
        self.client = client

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, str]]:
        """Route discovery tool calls to appropriate methods"""
        method_map = {
            "vibemk_start_service_discovery": self.start_service_discovery,
            "vibemk_start_bulk_discovery": self.start_bulk_discovery,
            "vibemk_get_discovery_status": self.get_discovery_status,
            "vibemk_get_bulk_discovery_status": self.get_bulk_discovery_status,
            "vibemk_get_discovery_result": self.get_discovery_result,
            "vibemk_wait_for_discovery": self.wait_for_discovery,
            "vibemk_get_discovery_background_job": self.get_discovery_background_job,
        }

        if tool_name not in method_map:
            return [{"type": "text", "text": f"❌ Unknown discovery tool: {tool_name}"}]

        return await method_map[tool_name](arguments)

    async def start_service_discovery(self, args: Dict[str, Any]) -> List[Dict[str, str]]:
        """Start service discovery for a single host"""
        try:
            host_name = args.get("host_name")
            mode = args.get("mode", "refresh")  # Default to refresh mode

            if not host_name:
                return [{"type": "text", "text": "❌ Error: host_name is required"}]

            # Validate mode
            valid_modes = ["new", "remove", "fix_all", "refresh", "only_host_labels"]
            if mode not in valid_modes:
                return [{"type": "text", "text": f"❌ Error: mode must be one of {valid_modes}"}]

            data = {"host_name": host_name, "mode": mode}

            try:
                result = self.client.post("domain-types/service_discovery_run/actions/start/invoke", data=data)

                if result.get("success"):
                    return [
                        {
                            "type": "text",
                            "text": f"✅ **Service Discovery Started**\n\n"
                            f"Host: **{host_name}**\n"
                            f"Mode: {mode}\n\n"
                            f"🔄 Discovery is running in the background.\n"
                            f"Use 'wait_for_discovery' or 'get_discovery_status' to check progress.",
                        }
                    ]
                else:
                    # If single host discovery fails, fall back to bulk discovery
                    logger.warning(f"Single host discovery failed for {host_name}, falling back to bulk discovery")
                    return await self._fallback_to_bulk_discovery(host_name, mode)

            except Exception as api_error:
                # If single host discovery API has issues (like redirect loops), fall back to bulk discovery
                logger.warning(
                    f"Single host discovery API error for {host_name}: {api_error}. Falling back to bulk discovery"
                )
                return await self._fallback_to_bulk_discovery(host_name, mode)

        except Exception as e:
            logger.exception(f"Error starting service discovery for {host_name}")
            return [{"type": "text", "text": f"❌ Error starting service discovery: {str(e)}"}]

    async def _fallback_to_bulk_discovery(self, host_name: str, mode: str) -> List[Dict[str, str]]:
        """Fallback to bulk discovery for single host when individual discovery fails"""
        try:
            # Map single host discovery modes to bulk discovery options
            bulk_options = {
                "monitor_undecided_services": mode in ["new", "refresh", "fix_all"],
                "remove_vanished_services": mode in ["remove", "fix_all"],
                "update_service_labels": mode in ["refresh", "fix_all"],
                "update_host_labels": mode in ["refresh", "fix_all", "only_host_labels"],
            }

            bulk_data = {
                "hostnames": [host_name],
                "options": bulk_options,
                "do_full_scan": mode in ["refresh", "fix_all"],
                "bulk_size": 1,
                "ignore_errors": False,
            }

            result = self.client.post("domain-types/discovery_run/actions/bulk-discovery-start/invoke", data=bulk_data)

            if result.get("success"):
                job_id = result.get("data", {}).get("id", "Unknown")
                return [
                    {
                        "type": "text",
                        "text": f"✅ **Service Discovery Started** (via bulk discovery)\n\n"
                        f"Host: **{host_name}**\n"
                        f"Mode: {mode} (mapped to bulk options)\n"
                        f"Job ID: {job_id}\n\n"
                        f"🔄 Discovery is running in the background.\n"
                        f"Use 'get_bulk_discovery_status' with Job ID {job_id} or 'get_discovery_status' to check progress.\n\n"
                        f"💡 Note: Used bulk discovery as fallback due to API limitations.",
                    }
                ]
            else:
                error_msg = result.get("data", {}).get("detail", "Unknown error")
                return [
                    {
                        "type": "text",
                        "text": f"❌ Failed to start discovery (both single and bulk methods failed): {error_msg}",
                    }
                ]

        except Exception as e:
            logger.exception(f"Error in fallback bulk discovery for {host_name}")
            return [{"type": "text", "text": f"❌ Error in fallback discovery method: {str(e)}"}]

    async def start_bulk_discovery(self, args: Dict[str, Any]) -> List[Dict[str, str]]:
        """Start bulk discovery for multiple hosts"""
        try:
            hostnames = args.get("hostnames", [])
            options = args.get("options", {})
            do_full_scan = args.get("do_full_scan", True)
            bulk_size = args.get("bulk_size", 10)
            ignore_errors = args.get("ignore_errors", True)

            if not hostnames:
                return [{"type": "text", "text": "❌ Error: hostnames list is required"}]

            # Set default options if not provided
            default_options = {
                "monitor_undecided_services": True,
                "remove_vanished_services": True,
                "update_service_labels": True,
                "update_host_labels": True,
            }

            # Merge with provided options
            final_options = {**default_options, **options}

            data = {
                "hostnames": hostnames,
                "options": final_options,
                "do_full_scan": do_full_scan,
                "bulk_size": bulk_size,
                "ignore_errors": ignore_errors,
            }

            result = self.client.post("domain-types/discovery_run/actions/bulk-discovery-start/invoke", data=data)

            if result.get("success"):
                job_id = result.get("data", {}).get("id", "Unknown")
                return [
                    {
                        "type": "text",
                        "text": f"✅ **Bulk Discovery Started**\n\n"
                        f"Job ID: **{job_id}**\n"
                        f"Hosts: {len(hostnames)} hosts\n"
                        f"  • {', '.join(hostnames[:5])}"
                        f"{'...' if len(hostnames) > 5 else ''}\n"
                        f"Options:\n"
                        f"  • Full scan: {do_full_scan}\n"
                        f"  • Bulk size: {bulk_size}\n"
                        f"  • Ignore errors: {ignore_errors}\n"
                        f"  • Monitor undecided: {final_options['monitor_undecided_services']}\n"
                        f"  • Remove vanished: {final_options['remove_vanished_services']}\n\n"
                        f"🔄 Bulk discovery is running in the background.\n"
                        f"Use 'get_bulk_discovery_status' with Job ID {job_id} to check progress.",
                    }
                ]
            else:
                error_msg = result.get("data", {}).get("detail", "Unknown error")
                return [{"type": "text", "text": f"❌ Failed to start bulk discovery: {error_msg}"}]

        except Exception as e:
            logger.exception("Error starting bulk discovery")
            return [{"type": "text", "text": f"❌ Error starting bulk discovery: {str(e)}"}]

    async def get_discovery_status(self, args: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get current service discovery result for a host"""
        try:
            host_name = args.get("host_name")

            if not host_name:
                return [{"type": "text", "text": "❌ Error: host_name is required"}]

            result = self.client.get(f"objects/service_discovery/{host_name}")

            if result.get("success"):
                data = result.get("data", {})
                extensions = data.get("extensions", {})

                # Extract discovery information
                check_table = extensions.get("check_table", [])
                host_labels = extensions.get("host_labels", {})

                # Count services by state
                new_services = sum(1 for item in check_table if isinstance(item, dict) and item.get("state") == "new")
                unchanged_services = sum(
                    1 for item in check_table if isinstance(item, dict) and item.get("state") == "unchanged"
                )
                vanished_services = sum(
                    1 for item in check_table if isinstance(item, dict) and item.get("state") == "vanished"
                )

                output = [
                    f"📊 **Service Discovery Status**\n\n"
                    f"Host: **{host_name}**\n\n"
                    f"📋 **Service Summary:**\n"
                    f"  • New services: {new_services}\n"
                    f"  • Unchanged services: {unchanged_services}\n"
                    f"  • Vanished services: {vanished_services}\n"
                    f"  • Total services: {len(check_table)}\n\n"
                ]

                if host_labels:
                    output.append(f"🏷️ **Host Labels:** {len(host_labels)} labels\n\n")

                # Show new services if any
                if new_services > 0:
                    output.append("🆕 **New Services Found:**\n")
                    for item in check_table:
                        if item.get("state") == "new":
                            service_name = item.get("service_name", "Unknown")
                            output.append(f"  • {service_name}\n")
                    output.append("\n")

                # Show vanished services if any
                if vanished_services > 0:
                    output.append("👻 **Vanished Services:**\n")
                    for item in check_table:
                        if item.get("state") == "vanished":
                            service_name = item.get("service_name", "Unknown")
                            output.append(f"  • {service_name}\n")
                    output.append("\n")

                return [{"type": "text", "text": "".join(output)}]
            else:
                error_msg = result.get("data", {}).get("detail", "Unknown error")
                return [{"type": "text", "text": f"❌ Failed to get discovery status: {error_msg}"}]

        except Exception as e:
            logger.exception(f"Error getting discovery status for {host_name}")
            return [{"type": "text", "text": f"❌ Error getting discovery status: {str(e)}"}]

    async def get_bulk_discovery_status(self, args: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get status of a bulk discovery job"""
        try:
            job_id = args.get("job_id")

            if not job_id:
                return [{"type": "text", "text": "❌ Error: job_id is required"}]

            result = self.client.get(f"objects/discovery_run/{job_id}")

            if result.get("success"):
                data = result.get("data", {})
                extensions = data.get("extensions", {})

                # Extract job information
                job_state = extensions.get("state", "unknown")
                started = extensions.get("started", "Unknown")
                duration = extensions.get("duration", "Unknown")
                progress = extensions.get("progress", {})

                # Format progress information
                progress_text = ""
                if progress:
                    total = progress.get("total", 0)
                    completed = progress.get("completed", 0)
                    failed = progress.get("failed", 0)
                    percentage = (completed / total * 100) if total > 0 else 0

                    progress_text = (
                        f"📊 **Progress:**\n"
                        f"  • Completed: {completed}/{total} ({percentage:.1f}%)\n"
                        f"  • Failed: {failed}\n\n"
                    )

                status_emoji = {"running": "🔄", "finished": "✅", "stopped": "⏹️", "exception": "❌"}.get(
                    job_state, "❓"
                )

                return [
                    {
                        "type": "text",
                        "text": f"{status_emoji} **Bulk Discovery Job Status**\n\n"
                        f"Job ID: **{job_id}**\n"
                        f"State: {job_state.upper()}\n"
                        f"Started: {started}\n"
                        f"Duration: {duration}\n\n"
                        f"{progress_text}"
                        f"💡 Use 'get_discovery_status' on individual hosts for detailed results.",
                    }
                ]
            else:
                error_msg = result.get("data", {}).get("detail", "Unknown error")
                return [{"type": "text", "text": f"❌ Failed to get bulk discovery status: {error_msg}"}]

        except Exception as e:
            logger.exception(f"Error getting bulk discovery status for job {job_id}")
            return [{"type": "text", "text": f"❌ Error getting bulk discovery status: {str(e)}"}]

    async def get_discovery_result(self, args: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get the current service discovery result (alias for get_discovery_status)"""
        return await self.get_discovery_status(args)

    async def wait_for_discovery(self, args: Dict[str, Any]) -> List[Dict[str, str]]:
        """Wait for service discovery completion on a host"""
        try:
            host_name = args.get("host_name")

            if not host_name:
                return [{"type": "text", "text": "❌ Error: host_name is required"}]

            result = self.client.get(f"objects/service_discovery_run/{host_name}/actions/wait-for-completion/invoke")

            if result.get("success"):
                return [
                    {
                        "type": "text",
                        "text": f"✅ **Discovery Completed**\n\n"
                        f"Host: **{host_name}**\n\n"
                        f"🔄 Service discovery has finished.\n"
                        f"Use 'get_discovery_status' to see the results.",
                    }
                ]
            else:
                error_msg = result.get("data", {}).get("detail", "Unknown error")
                return [{"type": "text", "text": f"❌ Failed to wait for discovery completion: {error_msg}"}]

        except Exception as e:
            logger.exception(f"Error waiting for discovery completion for {host_name}")
            return [{"type": "text", "text": f"❌ Error waiting for discovery completion: {str(e)}"}]

    async def get_discovery_background_job(self, args: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get the last service discovery background job status on a host"""
        try:
            host_name = args.get("host_name")

            if not host_name:
                return [{"type": "text", "text": "❌ Error: host_name is required"}]

            result = self.client.get(f"objects/service_discovery_run/{host_name}")

            if result.get("success"):
                data = result.get("data", {})
                extensions = data.get("extensions", {})

                # Extract background job information
                job_state = extensions.get("state", "unknown")
                started = extensions.get("started", "Unknown")
                finished = extensions.get("finished", "Not finished")
                duration = extensions.get("duration", "Unknown")

                status_emoji = {"running": "🔄", "finished": "✅", "stopped": "⏹️", "exception": "❌"}.get(
                    job_state, "❓"
                )

                return [
                    {
                        "type": "text",
                        "text": f"{status_emoji} **Discovery Background Job**\n\n"
                        f"Host: **{host_name}**\n"
                        f"State: {job_state.upper()}\n"
                        f"Started: {started}\n"
                        f"Finished: {finished}\n"
                        f"Duration: {duration}\n\n"
                        f"💡 Use 'get_discovery_status' to see discovery results.",
                    }
                ]
            else:
                error_msg = result.get("data", {}).get("detail", "Unknown error")
                return [{"type": "text", "text": f"❌ Failed to get discovery background job: {error_msg}"}]

        except Exception as e:
            logger.exception(f"Error getting discovery background job for {host_name}")
            return [{"type": "text", "text": f"❌ Error getting discovery background job: {str(e)}"}]
