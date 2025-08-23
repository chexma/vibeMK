"""
Rulesets management handlers for CheckMK ruleset discovery and display
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class RulesetsHandler(BaseHandler):
    """Handle ruleset search and display operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle ruleset-related tool calls"""

        try:
            if tool_name == "vibemk_search_rulesets":
                return await self._search_rulesets(arguments)
            elif tool_name == "vibemk_show_ruleset":
                return await self._show_ruleset(arguments)
            elif tool_name == "vibemk_list_rulesets":
                return await self._list_rulesets(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _search_rulesets(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for rulesets with optional filters"""
        fulltext = arguments.get("fulltext", "")
        folder = arguments.get("folder", "")
        deprecated = arguments.get("deprecated", False)
        used = arguments.get("used", True)
        name = arguments.get("name", "")

        # Build query parameters based on API documentation
        params = {}

        if fulltext:
            params["fulltext"] = fulltext
        if folder:
            params["folder"] = folder
        if deprecated is not None:
            params["deprecated"] = str(deprecated).lower()
        if used is not None:
            params["used"] = str(used).lower()
        if name:
            params["name"] = name

        self.logger.debug(f"Searching rulesets with params: {params}")

        try:
            result = self.client.get("domain-types/ruleset/collections/all", params=params)
            rulesets = result["data"].get("value", [])

            if not rulesets:
                search_criteria = []
                if fulltext:
                    search_criteria.append(f"text '{fulltext}'")
                if folder:
                    search_criteria.append(f"folder '{folder}'")
                if name:
                    search_criteria.append(f"name '{name}'")

                criteria_text = " and ".join(search_criteria) if search_criteria else "your criteria"

                return [
                    {
                        "type": "text",
                        "text": (
                            f"🔍 **No Rulesets Found**\n\n"
                            f"No rulesets match {criteria_text}.\n\n"
                            f"💡 **Tips:**\n"
                            f"• Try broader search terms\n"
                            f"• Check if deprecated rulesets should be included\n"
                            f"• Verify folder path is correct"
                        ),
                    }
                ]

            return [
                {
                    "type": "text",
                    "text": self._format_rulesets_search_response(rulesets, params),
                }
            ]

        except CheckMKError as e:
            http_status = getattr(e, "status_code", 0)
            error_data = getattr(e, "error_data", {})

            if http_status == 400:
                return self.error_response(
                    "Search Parameter Error", f"Invalid search parameters: {error_data.get('detail', str(e))}"
                )
            elif http_status == 403:
                return self.error_response(
                    "Permission Denied",
                    "Access denied. You may not have 'wato.rulesets' permission for ruleset management.",
                )
            elif http_status == 406:
                return self.error_response(
                    "Accept Header Error", "API cannot satisfy the requested content type. Check Accept headers."
                )
            else:
                return self.error_response("Ruleset Search Failed", str(e))

    async def _show_ruleset(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Show detailed information about a specific ruleset"""
        ruleset_name = arguments.get("ruleset_name")

        if not ruleset_name:
            return self.error_response("Missing parameter", "ruleset_name is required")

        self.logger.debug(f"Showing ruleset: {ruleset_name}")

        try:
            result = self.client.get(f"objects/ruleset/{ruleset_name}")
            ruleset_data = result["data"]

            return [
                {
                    "type": "text",
                    "text": self._format_ruleset_details(ruleset_name, ruleset_data),
                }
            ]

        except CheckMKError as e:
            http_status = getattr(e, "status_code", 0)
            error_data = getattr(e, "error_data", {})

            if http_status == 403:
                return self.error_response(
                    "Permission Denied",
                    "Access denied. You may not have 'wato.rulesets' permission for ruleset management.",
                )
            elif http_status == 404:
                return self.error_response(
                    "Ruleset Not Found", f"Ruleset '{ruleset_name}' not found. Check the ruleset name and try again."
                )
            elif http_status == 406:
                return self.error_response(
                    "Accept Header Error", "API cannot satisfy the requested content type. Check Accept headers."
                )
            else:
                return self.error_response("Failed to retrieve ruleset", str(e))

    async def _list_rulesets(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all available rulesets with basic information"""
        limit = arguments.get("limit", 50)
        show_deprecated = arguments.get("show_deprecated", False)

        params = {"used": "true", "deprecated": str(show_deprecated).lower()}

        try:
            result = self.client.get("domain-types/ruleset/collections/all", params=params)
            rulesets = result["data"].get("value", [])

            # Limit results for performance
            if limit and len(rulesets) > limit:
                rulesets = rulesets[:limit]
                truncated = True
            else:
                truncated = False

            return [
                {
                    "type": "text",
                    "text": self._format_rulesets_list(rulesets, limit, truncated, show_deprecated),
                }
            ]

        except CheckMKError as e:
            http_status = getattr(e, "status_code", 0)

            if http_status == 403:
                return self.error_response(
                    "Permission Denied", "Access denied. You may not have 'wato.rulesets' permission."
                )
            else:
                return self.error_response("Failed to list rulesets", str(e))

    def _format_rulesets_search_response(self, rulesets: List[Dict], search_params: Dict) -> str:
        """Format search results for display"""
        response = f"🔍 **Ruleset Search Results**\n\n"

        # Show search criteria
        if search_params:
            response += "**Search Criteria:**\n"
            for key, value in search_params.items():
                response += f"• {key}: {value}\n"
            response += "\n"

        response += f"**Found {len(rulesets)} rulesets**\n\n"

        for i, ruleset in enumerate(rulesets[:20], 1):  # Show first 20 results
            extensions = ruleset.get("extensions", {})
            ruleset_id = ruleset.get("id", "Unknown")
            title = extensions.get("title", "No title")
            help_text = extensions.get("help", "")
            deprecated = extensions.get("deprecated", False)
            number_of_rules = extensions.get("number_of_rules", 0)

            # Truncate help text
            if help_text and len(help_text) > 100:
                help_text = help_text[:100] + "..."

            status_icon = "⚠️" if deprecated else "✅"

            response += f"**{i}. {status_icon} {ruleset_id}**\n"
            response += f"   📋 Title: {title}\n"
            response += f"   📊 Rules: {number_of_rules}\n"

            if help_text:
                response += f"   💡 {help_text}\n"
            if deprecated:
                response += f"   ⚠️ Deprecated ruleset\n"

            response += "\n"

        if len(rulesets) > 20:
            response += f"... and {len(rulesets) - 20} more rulesets\n\n"

        response += "💡 **Use `vibemk_show_ruleset` with ruleset name for detailed information**"

        return response

    def _format_ruleset_details(self, ruleset_name: str, ruleset_data: Dict) -> str:
        """Format detailed ruleset information"""
        extensions = ruleset_data.get("extensions", {})

        title = extensions.get("title", "No title")
        help_text = extensions.get("help", "No help available")
        deprecated = extensions.get("deprecated", False)
        number_of_rules = extensions.get("number_of_rules", 0)
        ruleset_type = extensions.get("type", "Unknown")
        match_type = extensions.get("match_type", "Unknown")

        # Format the response
        response = f"📋 **Ruleset Details: {ruleset_name}**\n\n"

        if deprecated:
            response += "⚠️ **DEPRECATED RULESET**\n\n"

        response += f"**Title:** {title}\n"
        response += f"**Type:** {ruleset_type}\n"
        response += f"**Match Type:** {match_type}\n"
        response += f"**Number of Rules:** {number_of_rules}\n\n"

        response += f"**Description:**\n{help_text}\n\n"

        # Show available operations
        response += "**Available Operations:**\n"
        response += f"• Use `vibemk_get_ruleset` to see actual rules in this ruleset\n"
        response += f"• Use `vibemk_create_rule` to add new rules to this ruleset\n"
        response += f"• Use `vibemk_search_rulesets` to find related rulesets\n"

        if deprecated:
            response += "\n⚠️ **Note:** This is a deprecated ruleset. Consider using newer alternatives."

        return response

    def _format_rulesets_list(self, rulesets: List[Dict], limit: int, truncated: bool, show_deprecated: bool) -> str:
        """Format rulesets list for display"""
        response = f"📋 **Available Rulesets**\n\n"

        if show_deprecated:
            response += "**Including deprecated rulesets**\n\n"

        response += f"**Showing {len(rulesets)} rulesets" + (f" (limited to {limit})" if truncated else "") + "**\n\n"

        # Group by category if possible
        categorized = {}
        uncategorized = []

        for ruleset in rulesets:
            extensions = ruleset.get("extensions", {})
            ruleset_id = ruleset.get("id", "Unknown")
            title = extensions.get("title", "No title")
            deprecated = extensions.get("deprecated", False)

            # Try to categorize by ruleset prefix
            if "_" in ruleset_id:
                category = ruleset_id.split("_")[0]
            else:
                category = "general"

            if category not in categorized:
                categorized[category] = []

            categorized[category].append({"id": ruleset_id, "title": title, "deprecated": deprecated})

        # Display categorized rulesets
        for category, rules in sorted(categorized.items()):
            if len(rules) > 1:  # Only show categories with multiple rules
                response += f"**{category.upper()}:**\n"
                for rule in rules[:5]:  # Limit per category
                    status_icon = "⚠️" if rule["deprecated"] else "✅"
                    response += f"  {status_icon} `{rule['id']}` - {rule['title']}\n"
                if len(rules) > 5:
                    response += f"  ... and {len(rules) - 5} more {category} rulesets\n"
                response += "\n"

        if truncated:
            response += f"\n⚠️ **Note:** Results limited to {limit}. Use search filters for more specific results.\n"

        response += "\n💡 **Usage:**\n"
        response += "• `vibemk_show_ruleset` - Get detailed information about a specific ruleset\n"
        response += "• `vibemk_search_rulesets` - Search rulesets with filters\n"
        response += "• `vibemk_get_ruleset` - View rules within a ruleset\n"

        return response
