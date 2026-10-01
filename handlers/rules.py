"""
Rule management handlers for CheckMK monitoring rules
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class RulesHandler(BaseHandler):
    """Handle rule management operations"""

    _WRITE_TOOLS = frozenset({
        "vibemk_create_rule", "vibemk_update_rule",
        "vibemk_delete_rule", "vibemk_move_rule",
    })

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle rule-related tool calls"""

        try:
            if tool_name == "vibemk_get_rulesets":
                result = await self._get_rulesets(arguments)
            elif tool_name == "vibemk_get_ruleset":
                result = await self._get_ruleset(arguments)
            elif tool_name == "vibemk_create_rule":
                result = await self._create_rule(arguments)
            elif tool_name == "vibemk_update_rule":
                result = await self._update_rule(arguments)
            elif tool_name == "vibemk_delete_rule":
                result = await self._delete_rule(arguments)
            elif tool_name == "vibemk_move_rule":
                result = await self._move_rule(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

        if (tool_name in self._WRITE_TOOLS
                and arguments.get("activate_changes")
                and result
                and "❌" not in result[-1].get("text", "")):
            result[-1]["text"] += "\n" + self._run_activation()
        return result

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
        for ruleset in rulesets[:20]:  # Limit to first 20
            ruleset_name = ruleset.get("id", "Unknown")
            extensions = ruleset.get("extensions", {})
            title = extensions.get("title", ruleset_name)
            help_text = extensions.get("help", "No description")

            ruleset_list.append(f"📋 **{ruleset_name}**\n   Title: {title}\n   Help: {help_text[:100]}...")

        response_text = f"📋 **Available Rulesets** ({len(rulesets)} total):\n\n" + "\n\n".join(ruleset_list)
        if len(rulesets) > 20:
            response_text += f"\n\n... and {len(rulesets) - 20} more rulesets"

        return [{"type": "text", "text": response_text}]

    async def _get_ruleset(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get rules in a ruleset, optionally filtered by hostname."""
        ruleset_name = arguments.get("ruleset_name")
        hostname = arguments.get("hostname")
        limit = int(arguments.get("limit", 50))

        if not ruleset_name:
            return self.error_response("Missing parameter", "ruleset_name is required")

        params = {"ruleset_name": ruleset_name}
        result = self.client.get("domain-types/rule/collections/all", params=params)

        if not result.get("success"):
            return self.error_response(
                "Ruleset not found", f"Ruleset '{ruleset_name}' does not exist or has no rules"
            )

        all_rules = result["data"].get("value", [])

        # Filter by hostname if requested
        if hostname:
            rules = [
                r for r in all_rules
                if hostname in r.get("extensions", {}).get("conditions", {})
                                  .get("host_name", {}).get("match_on", [])
            ]
        else:
            rules = all_rules

        rule_list = []
        for i, rule in enumerate(rules[:limit]):
            rule_id = rule.get("id", f"Rule {i+1}")
            ext = rule.get("extensions", {})
            props = ext.get("properties", {})
            disabled = props.get("disabled", False)
            value_raw = ext.get("value_raw", "")
            folder = ext.get("folder", "/")
            conditions = ext.get("conditions", {})

            status = "🔒 Disabled" if disabled else "✅ Active"
            hosts = conditions.get("host_name", {}).get("match_on", [])
            cond_text = ", ".join(hosts) if hosts else "all hosts"

            rule_list.append(
                f"• [{status}] **ID: `{rule_id}`**\n"
                f"  Folder: {folder} | Hosts: {cond_text}\n"
                f"  Value: `{value_raw[:150]}{'…' if len(value_raw) > 150 else ''}`"
            )

        header = (
            f"📋 **{ruleset_name}** — {len(rules)}"
            + (f"/{len(all_rules)}" if hostname else "")
            + " Regeln"
            + (f" (hostname-Filter: {hostname})" if hostname else "")
        )
        body = "\n".join(rule_list) if rule_list else "Keine Regeln gefunden."
        if len(rules) > limit:
            body += f"\n\n…{len(rules) - limit} weitere (erhöhe limit)"

        return [{"type": "text", "text": f"{header}\n\n{body}"}]

    async def _validate_ruleset_value(self, ruleset_name: str, value: Any) -> str:
        """Validate and format value for specific ruleset"""
        # This method can be extended to handle specific ruleset requirements
        # For now, implement basic Python literal formatting

        if isinstance(value, dict):
            # For rulesets like host_label_rules: {'key': 'value'}
            return str(value).replace('"', "'")
        elif isinstance(value, list):
            if len(value) == 1:
                # Single item lists often need to be strings
                return f"'{value[0]}'"
            else:
                # Multi-item lists stay as Python list literals
                return str(value).replace('"', "'")
        elif isinstance(value, str):
            # String values need to be Python string literals
            return f"'{value}'"
        else:
            return str(value)

    async def _create_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a new monitoring rule"""
        ruleset_name = arguments.get("ruleset_name")
        rule_config = arguments.get("rule_config", {})
        value_raw_str = arguments.get("value_raw")  # direct Python literal string (preferred)
        conditions = arguments.get("conditions", {})
        comment = arguments.get("comment", "")
        folder = arguments.get("folder", "/")

        if not ruleset_name:
            return self.error_response("Missing parameter", "ruleset_name is required")

        if not rule_config and not value_raw_str:
            return self.error_response("Missing parameter", "rule_config or value_raw is required")

        if folder.startswith("/"):
            api_folder = "~" + folder[1:].replace("/", "~") if folder != "/" else "~"
        else:
            api_folder = "~" + folder.replace("/", "~")

        # Prefer direct value_raw string; fall back to auto-conversion (lossy: JSON has no tuples)
        if value_raw_str:
            value_raw = value_raw_str
        else:
            value_raw = await self._validate_ruleset_value(ruleset_name, rule_config)

        # Always include required empty arrays in conditions
        full_conditions = {
            "host_tags": [],
            "host_label_groups": [],
            "service_label_groups": [],
        }
        full_conditions.update(conditions)

        data = {
            "properties": {"disabled": False},
            "value_raw": value_raw,
            "conditions": full_conditions,
            "ruleset": ruleset_name,
            "folder": api_folder,
        }
        if comment:
            data["properties"]["comment"] = comment

        try:
            result = self.client.post("domain-types/rule/collections/all", data=data)
        except Exception as exc:
            detail = getattr(exc, "response_data", {})
            return self.error_response(
                "Rule creation failed",
                f"CheckMK API error: {exc}\nDetail: {detail}\nvalue_raw sent: {value_raw}",
            )

        if result.get("success"):
            rule_id = result["data"].get("id", "unknown")
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Rule Created Successfully**\n\n"
                        f"Ruleset: {ruleset_name}\n"
                        f"Rule ID: {rule_id}\n"
                        f"Folder: {folder}\n"
                        + (f"Comment: {comment}\n" if comment else "")
                        + f"\n⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            detail = result.get("data", {})
            return self.error_response(
                "Rule creation failed",
                f"Ruleset: {ruleset_name}\nDetail: {detail}\nvalue_raw sent: {value_raw}",
            )

    async def _update_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update an existing rule"""
        rule_id = arguments.get("rule_id")
        rule_config = arguments.get("rule_config")
        value_raw_str = arguments.get("value_raw")  # direct Python literal string (preferred)
        conditions = arguments.get("conditions")
        comment = arguments.get("comment")
        disabled = arguments.get("disabled")

        if not rule_id:
            return self.error_response("Missing parameter", "rule_id is required")

        data: Dict[str, Any] = {}
        sent_value_raw = None
        if value_raw_str:
            data["value_raw"] = value_raw_str
            sent_value_raw = value_raw_str
        elif rule_config:
            # Fallback: auto-convert (lossy — JSON has no tuples, use value_raw directly instead)
            sent_value_raw = await self._validate_ruleset_value("", rule_config)
            data["value_raw"] = sent_value_raw

        if conditions:
            full_conditions = {"host_tags": [], "host_label_groups": [], "service_label_groups": []}
            full_conditions.update(conditions)
            data["conditions"] = full_conditions

        properties: Dict[str, Any] = {}
        if comment is not None:
            properties["comment"] = comment
        if disabled is not None:
            properties["disabled"] = disabled
        if properties:
            data["properties"] = properties

        if not data:
            return self.error_response("No data to update", "At least one field must be provided")

        headers = {"If-Match": "*"}
        try:
            result = self.client.put(f"objects/rule/{rule_id}", data=data, headers=headers)
        except Exception as exc:
            detail = getattr(exc, "response_data", {})
            return self.error_response(
                "Rule update failed",
                f"CheckMK API error: {exc}\nDetail: {detail}\nvalue_raw sent: {sent_value_raw}",
            )

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
        else:
            detail = result.get("data", {})
            return self.error_response(
                "Rule update failed",
                f"Rule ID: {rule_id}\nDetail: {detail}\nvalue_raw sent: {sent_value_raw}",
            )

    async def _delete_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a rule by ID."""
        from api.exceptions import CheckMKError as _CMKError

        rule_id = arguments.get("rule_id")

        if not rule_id:
            return self.error_response(
                "Missing parameter",
                "rule_id is required — use vibemk_get_ruleset or vibemk_list_active_checks to find it",
            )

        try:
            self.client.delete(f"objects/rule/{rule_id}")
        except _CMKError as exc:
            detail = getattr(exc, "response_data", {}).get("detail", "")
            msg = str(exc) + (f"\nDetail: {detail}" if detail else "")
            return self.error_response("Regel löschen fehlgeschlagen", msg)

        return [{"type": "text", "text": f"✅ Regel `{rule_id}` gelöscht."}]

    async def _move_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Move a rule to a different position within its folder."""
        rule_id = arguments.get("rule_id")
        position = arguments.get("position", "top_of_folder")
        target_rule_id = arguments.get("target_rule_id")
        folder = arguments.get("folder", "~")

        if not rule_id:
            return self.error_response("Missing parameter", "rule_id is required")

        # Normalize legacy short names to the API enum values
        _ALIAS = {
            "top": "top_of_folder",
            "bottom": "bottom_of_folder",
            "before": "before_specific_rule",
            "after": "after_specific_rule",
        }
        position = _ALIAS.get(position, position)

        if position in ("before_specific_rule", "after_specific_rule") and not target_rule_id:
            return self.error_response(
                "Missing parameter",
                "target_rule_id is required for before_specific_rule / after_specific_rule",
            )

        if position in ("top_of_folder", "bottom_of_folder"):
            data: Dict[str, Any] = {"position": position, "folder": folder}
        else:
            data = {"position": position, "target_rule": target_rule_id}

        result = self.client.post(f"objects/rule/{rule_id}/actions/move/invoke", data=data)

        if result.get("success"):
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Rule Moved Successfully**\n\n"
                        f"Rule ID: {rule_id}\n"
                        f"New Position: {position}\n"
                        + (f"Target Rule: {target_rule_id}\n" if target_rule_id else "")
                        + (f"Folder: {folder}\n" if position in ("top_of_folder", "bottom_of_folder") else "")
                        + f"\n⚠️ **Remember to activate changes!**"
                    ),
                }
            ]
        else:
            detail = result.get("data", {})
            return self.error_response("Rule move failed", f"Rule '{rule_id}': {detail}")
