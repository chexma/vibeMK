"""
Rule management handlers for CheckMK monitoring rules
"""

from typing import Any, ClassVar, Dict, List, Optional, Tuple

from vibemk.api.exceptions import CheckMKError
from vibemk.api.paths import path_segment
from vibemk.handlers.base import BaseHandler

RULESET_DISPLAY_LIMIT = 20
RULE_DISPLAY_LIMIT = 10


class RulesHandler(BaseHandler):
    """Handle rule management operations"""

    # CheckMK's move endpoint discriminates on `position` and admits exactly
    # these four values — see the discriminator on MoveRuleTo in the API's own
    # OpenAPI document. The short forms on the left are what this server's tool
    # schema has always advertised, so they keep working and are translated.
    # The two folder positions additionally require `folder`, and the two
    # relative ones name their target under `rule_id`, not `target_rule`.
    _FOLDER_POSITIONS: ClassVar[Dict[str, str]] = {
        "top": "top_of_folder",
        "bottom": "bottom_of_folder",
        "top_of_folder": "top_of_folder",
        "bottom_of_folder": "bottom_of_folder",
    }
    _RELATIVE_POSITIONS: ClassVar[Dict[str, str]] = {
        "before": "before_specific_rule",
        "after": "after_specific_rule",
        "before_specific_rule": "before_specific_rule",
        "after_specific_rule": "after_specific_rule",
    }

    @classmethod
    def _move_body(
        cls, position: str, folder: Optional[str], target_rule_id: Optional[str]
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Translate a requested position into the move endpoint's body.

        Returns (body, error). On failure the body is empty and error says why.
        """
        if position in cls._FOLDER_POSITIONS:
            if not folder:
                return {}, "the folder the rule lives in could not be determined"
            return {"position": cls._FOLDER_POSITIONS[position], "folder": folder}, None

        if position in cls._RELATIVE_POSITIONS:
            if not target_rule_id:
                return {}, "target_rule_id is required for 'before' and 'after'"
            return {"position": cls._RELATIVE_POSITIONS[position], "rule_id": target_rule_id}, None

        accepted = sorted(set(cls._FOLDER_POSITIONS) | set(cls._RELATIVE_POSITIONS))
        return {}, f"'{position}' is not a position CheckMK accepts. Use one of: {', '.join(accepted)}"

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle rule-related tool calls"""

        try:
            if tool_name == "vibemk_get_rulesets":
                return await self._get_rulesets(arguments)
            if tool_name == "vibemk_get_ruleset":
                return await self._get_ruleset(arguments)
            if tool_name == "vibemk_create_rule":
                return await self._create_rule(arguments)
            if tool_name == "vibemk_update_rule":
                return await self._update_rule(arguments)
            if tool_name == "vibemk_delete_rule":
                return await self._delete_rule(arguments)
            if tool_name == "vibemk_move_rule":
                return await self._move_rule(arguments)
            return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception("Error in %s", tool_name)
            return self.error_response("Unexpected Error", str(e))

    async def _get_rulesets(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of available rulesets"""
        search = arguments.get("search", "")

        params = {}
        if search:
            params["search"] = search

        result = self.client.get("domain-types/ruleset/collections/all", params=params)

        if not result.get("success"):
            return self.error_response("Failed to retrieve rulesets")

        rulesets = result["data"].get("value", [])
        if not rulesets:
            return [
                {
                    "type": "text",
                    "text": "📋 **No Rulesets Found**\n\nNo rulesets are available or match the search criteria.",
                }
            ]

        ruleset_list = []
        for ruleset in rulesets[:RULESET_DISPLAY_LIMIT]:  # Limit to first 20
            ruleset_name = ruleset.get("id", "Unknown")
            extensions = ruleset.get("extensions", {})
            title = extensions.get("title", ruleset_name)
            help_text = extensions.get("help", "No description")

            ruleset_list.append(f"📋 **{ruleset_name}**\n   Title: {title}\n   Help: {help_text[:100]}...")

        response_text = f"📋 **Available Rulesets** ({len(rulesets)} total):\n\n" + "\n\n".join(ruleset_list)
        if len(rulesets) > RULESET_DISPLAY_LIMIT:
            response_text += f"\n\n... and {len(rulesets) - RULESET_DISPLAY_LIMIT} more rulesets"

        return [{"type": "text", "text": response_text}]

    async def _get_ruleset(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get specific ruleset configuration and rules"""
        ruleset_name = arguments.get("ruleset_name")

        if not ruleset_name:
            return self.error_response("Missing parameter", "ruleset_name is required")

        # Use the correct endpoint to get actual rules with ruleset_name parameter
        params = {"ruleset_name": ruleset_name}
        result = self.client.get("domain-types/rule/collections/all", params=params)

        if not result.get("success"):
            return self.error_response("Ruleset not found", f"Ruleset '{ruleset_name}' does not exist or has no rules")

        rules = result["data"].get("value", [])

        rule_list = []
        for i, rule in enumerate(rules[:RULE_DISPLAY_LIMIT]):  # Show first 10 rules
            rule_id = rule.get("id", f"Rule {i+1}")
            extensions = rule.get("extensions", {})
            properties = extensions.get("properties", {})
            comment = properties.get("comment", "No comment")
            disabled = properties.get("disabled", False)
            value_raw = extensions.get("value_raw", "No value")
            folder = extensions.get("folder", "/")
            conditions = extensions.get("conditions", {})

            status = "🔒 Disabled" if disabled else "✅ Active"

            # Format conditions summary
            condition_summary = []
            if conditions.get("host_name"):
                host_match = conditions["host_name"]
                condition_summary.append(
                    f"Hosts: {host_match.get('match_on', [])} ({host_match.get('operator', 'unknown')})"
                )
            if conditions.get("host_tags") and len(conditions["host_tags"]) > 0:
                tag_count = len(conditions["host_tags"])
                condition_summary.append(f"Tags: {tag_count} conditions")
            if conditions.get("host_label_groups") and len(conditions["host_label_groups"]) > 0:
                label_count = len(conditions["host_label_groups"])
                condition_summary.append(f"Labels: {label_count} conditions")

            conditions_text = ", ".join(condition_summary) if condition_summary else "All hosts"

            rule_list.append(
                f"🔧 **Rule {i+1}** (ID: {rule_id})\n"
                f"   Status: {status}\n"
                f"   Value: {value_raw}\n"
                f"   Folder: {folder}\n"
                f"   Conditions: {conditions_text}\n"
                f"   Comment: {comment}"
            )

        return [
            {
                "type": "text",
                "text": (
                    f"📋 **Ruleset: {ruleset_name}**\n\n"
                    f"Rules ({len(rules)} total):\n\n"
                    + ("\n\n".join(rule_list) if rule_list else "No rules configured in this ruleset")
                    + (
                        f"\n\n... and {len(rules) - RULE_DISPLAY_LIMIT} more rules"
                        if len(rules) > RULE_DISPLAY_LIMIT
                        else ""
                    )
                ),
            }
        ]

    async def _validate_ruleset_value(self, _ruleset_name: str, value: Any) -> str:
        """Render a rule value as the Python literal CheckMK stores in value_raw.

        This used to build the literal by hand -- str(value) with every double
        quote rewritten to a single one, and strings wrapped in f"'{value}'".
        Both break on their own content: a comment reading He said "no" came
        out as 'He said 'no'', which does not parse, and an apostrophe in a
        plain string did the same. repr() is exactly the operation those lines
        were approximating.
        """
        # A one-item list is flattened to the bare value: long-standing
        # behaviour for rulesets that expect a single string rather than a
        # list of one. Kept deliberately, now quoted correctly.
        if isinstance(value, list) and len(value) == 1:
            return repr(value[0])

        return repr(value)

    async def _create_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new monitoring rule"""
        ruleset_name = arguments.get("ruleset_name")
        rule_config = arguments.get("rule_config", {})
        conditions = arguments.get("conditions", {})
        comment = arguments.get("comment", "")
        folder = arguments.get("folder", "/")

        if not ruleset_name:
            return self.error_response("Missing parameter", "ruleset_name is required")

        if not rule_config:
            return self.error_response("Missing parameter", "rule_config is required")

        # Convert folder path: "/" -> "~", "/hosts/linux" -> "~hosts~linux".
        # A path that already uses tilde notation is passed through: prefixing
        # it again turned "~" into "~~", which CheckMK rejects.
        if folder.startswith("~"):
            api_folder = folder
        elif folder.startswith("/"):
            api_folder = "~" + folder[1:].replace("/", "~") if folder != "/" else "~"
        else:
            api_folder = "~" + folder.replace("/", "~")

        # Use the validation method to format the value correctly
        value_raw = await self._validate_ruleset_value(ruleset_name, rule_config)

        data = {
            "properties": {"disabled": False},
            "value_raw": value_raw,
            "conditions": conditions if conditions else {},
            "ruleset": ruleset_name,
            "folder": api_folder,
        }

        # Add comment to properties if provided
        if comment:
            data["properties"]["comment"] = comment

        result = self.client.post("domain-types/rule/collections/all", data=data)

        if result.get("success"):
            rule_id = result["data"].get("id", "unknown")
            placement = self._place_new_rule(rule_id, arguments.get("position"), api_folder, arguments)
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Rule Created Successfully**\n\n"
                        f"Ruleset: {ruleset_name}\n"
                        f"Rule ID: {rule_id}\n"
                        f"Folder: {folder}\n"
                        f"Comment: {comment}\n"
                        f"{placement}\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        return self.error_response("Rule creation failed", f"Could not create rule in ruleset '{ruleset_name}'")

    def _place_new_rule(self, rule_id: str, position: Optional[str], api_folder: str, arguments: Dict[str, Any]) -> str:
        """Move a freshly created rule into the requested position.

        The create endpoint takes no position — its body is only `folder`,
        `ruleset`, `value_raw`, `properties` and `conditions` — so a `position`
        argument can only be honoured by moving afterwards. Asking for none
        costs no second write.

        Returns a line for the answer. A failed move is reported rather than
        swallowed: the rule exists either way, and a caller told nothing would
        believe it got a position it did not get.
        """
        if not position:
            return ""

        body, problem = self._move_body(position, api_folder, arguments.get("target_rule_id"))
        if problem is not None:
            return f"\n⚠️ **Created, but not positioned:** {problem}\n"

        moved = self.client.post(
            f"objects/rule/{path_segment(rule_id)}/actions/move/invoke",
            data=body,
            headers=self._if_match_header(f"objects/rule/{path_segment(rule_id)}"),
        )
        if moved.get("success"):
            return f"Position: {body['position']}\n"
        return f"\n⚠️ **Created, but the requested position '{position}' could not be applied.**\n"

    async def _update_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update an existing rule"""
        rule_id = arguments.get("rule_id")
        rule_config = arguments.get("rule_config")
        conditions = arguments.get("conditions")
        comment = arguments.get("comment")
        disabled = arguments.get("disabled")

        if not rule_id:
            return self.error_response("Missing parameter", "rule_id is required")

        # Build update data
        data = {}
        if rule_config:
            data["value_raw"] = rule_config
        if conditions:
            data["conditions"] = conditions

        properties = {}
        if comment is not None:
            properties["comment"] = comment
        if disabled is not None:
            properties["disabled"] = disabled
        if properties:
            data["properties"] = properties

        if not data:
            return self.error_response("No data to update", "At least one field must be provided")

        headers = self._if_match_header(f"objects/rule/{path_segment(rule_id)}")
        result = self.client.put(f"objects/rule/{path_segment(rule_id)}", data=data, headers=headers)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Rule Updated Successfully**\n\n"
                        f"Rule ID: {rule_id}\n"
                        f"Updated fields: {', '.join(data.keys())}\n\n"
                        f"⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        return self.error_response("Rule update failed", f"Could not update rule '{rule_id}'")

    async def _delete_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a rule"""
        rule_id = arguments.get("rule_id")

        if not rule_id:
            return self.error_response("Missing parameter", "rule_id is required")

        result = self.client.delete(f"objects/rule/{path_segment(rule_id)}")

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Rule Deleted Successfully**\n\n"
                        f"Rule ID: {rule_id}\n\n"
                        f"📝 **Next Steps:**\n"
                        f"1️⃣ Use 'get_pending_changes' to review the deletion\n"
                        f"2️⃣ Use 'activate_changes' to apply the configuration\n\n"
                        f"💡 **Important:** The rule is only marked for deletion until you activate changes!"
                    ),
                }
            ]
        return self.error_response("Rule deletion failed", f"Could not delete rule '{rule_id}'")

    async def _move_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Move a rule to different position"""
        rule_id = arguments.get("rule_id")
        position = arguments.get("position", "top")
        target_rule_id = arguments.get("target_rule_id")

        if not rule_id:
            return self.error_response("Missing parameter", "rule_id is required")

        # One read serves two purposes: the ETag CheckMK demands on a move, and
        # the rule's current folder, which the folder positions require and the
        # caller has no reason to know.
        endpoint = f"objects/rule/{path_segment(rule_id)}"
        try:
            current = self.client.get(endpoint)
        except CheckMKError as error:
            self.logger.debug("Could not read rule %s before moving it: %s", rule_id, error)
            current = {}

        folder = current.get("data", {}).get("extensions", {}).get("folder")
        data, problem = self._move_body(position, folder, target_rule_id)
        if problem is not None:
            return self.error_response("Invalid position", problem)

        headers = {"If-Match": self._extract_etag(current)} if current else {"If-Match": "*"}
        result = self.client.post(f"{endpoint}/actions/move/invoke", data=data, headers=headers)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Rule Moved Successfully**\n\n"
                        f"Rule ID: {rule_id}\n"
                        f"New Position: {data['position']}\n"
                        + (f"Target Rule: {target_rule_id}\n" if target_rule_id else "")
                        + "\n⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        return self.error_response("Rule move failed", f"Could not move rule '{rule_id}'")
