"""
Rule management handlers for CheckMK monitoring rules
"""

from typing import Dict, Any, List
from handlers.base import BaseHandler
from api.exceptions import CheckMKError


class RulesHandler(BaseHandler):
    """Handle rule management operations"""
    
    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle rule-related tool calls"""
        
        try:
            if tool_name == "vibemk_get_rulesets":
                return await self._get_rulesets(arguments)
            elif tool_name == "vibemk_get_ruleset":
                return await self._get_ruleset(arguments)
            elif tool_name == "vibemk_create_rule":
                return await self._create_rule(arguments)
            elif tool_name == "vibemk_update_rule":
                return await self._update_rule(arguments)
            elif tool_name == "vibemk_delete_rule":
                return await self._delete_rule(arguments)
            elif tool_name == "vibemk_move_rule":
                return await self._move_rule(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")
                
        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
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
            return [{
                "type": "text", 
                "text": "📋 **No Rulesets Found**\n\nNo rulesets are available or match the search criteria."
            }]
        
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
        for i, rule in enumerate(rules[:10]):  # Show first 10 rules
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
                condition_summary.append(f"Hosts: {host_match.get('match_on', [])} ({host_match.get('operator', 'unknown')})")
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
        
        return [{
            "type": "text",
            "text": (
                f"📋 **Ruleset: {ruleset_name}**\n\n"
                f"Rules ({len(rules)} total):\n\n" + 
                ("\n\n".join(rule_list) if rule_list else "No rules configured in this ruleset") +
                (f"\n\n... and {len(rules) - 10} more rules" if len(rules) > 10 else "")
            )
        }]
    
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
        conditions = arguments.get("conditions", {})
        comment = arguments.get("comment", "")
        folder = arguments.get("folder", "/")
        position = arguments.get("position", "top")
        
        if not ruleset_name:
            return self.error_response("Missing parameter", "ruleset_name is required")
        
        if not rule_config:
            return self.error_response("Missing parameter", "rule_config is required")
        
        # Build rule data structure according to CheckMK 2.3 OpenAPI specification
        # Convert folder path: "/" -> "~", "/hosts/linux" -> "~hosts~linux" 
        if folder.startswith("/"):
            api_folder = "~" + folder[1:].replace("/", "~") if folder != "/" else "~"
        else:
            api_folder = "~" + folder.replace("/", "~")
            
        # Use the validation method to format the value correctly
        value_raw = await self._validate_ruleset_value(ruleset_name, rule_config)
            
        data = {
            "properties": {
                "disabled": False
            },
            "value_raw": value_raw,
            "conditions": conditions if conditions else {},
            "ruleset": ruleset_name,
            "folder": api_folder
        }
        
        # Add comment to properties if provided
        if comment:
            data["properties"]["comment"] = comment
        
        result = self.client.post("domain-types/rule/collections/all", data=data)
        
        if result.get("success"):
            rule_id = result["data"].get("id", "unknown")
            return [{
                "type": "text",
                "text": (
                    f"✅ **Rule Created Successfully**\n\n"
                    f"Ruleset: {ruleset_name}\n"
                    f"Rule ID: {rule_id}\n"
                    f"Folder: {folder}\n"
                    f"Comment: {comment}\n\n"
                    f"⚠️ **Remember to activate changes!**"
                )
            }]
        else:
            return self.error_response("Rule creation failed", f"Could not create rule in ruleset '{ruleset_name}'")
    
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
        
        # Use ETag for optimistic locking
        headers = {"If-Match": "*"}
        result = self.client.put(f"objects/rule/{rule_id}", data=data, headers=headers)
        
        if result.get("success"):
            return [{
                "type": "text",
                "text": (
                    f"✅ **Rule Updated Successfully**\n\n"
                    f"Rule ID: {rule_id}\n"
                    f"Updated fields: {', '.join(data.keys())}\n\n"
                    f"⚠️ **Remember to activate changes!**"
                )
            }]
        else:
            return self.error_response("Rule update failed", f"Could not update rule '{rule_id}'")
    
    async def _delete_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete a rule"""
        rule_id = arguments.get("rule_id")
        
        if not rule_id:
            return self.error_response("Missing parameter", "rule_id is required")
        
        result = self.client.delete(f"objects/rule/{rule_id}")
        
        if result.get("success"):
            return [{
                "type": "text",
                "text": (
                    f"✅ **Rule Deleted Successfully**\n\n"
                    f"Rule ID: {rule_id}\n\n"
                    f"📝 **Next Steps:**\n"
                    f"1️⃣ Use 'get_pending_changes' to review the deletion\n"
                    f"2️⃣ Use 'activate_changes' to apply the configuration\n\n"
                    f"💡 **Important:** The rule is only marked for deletion until you activate changes!"
                )
            }]
        else:
            return self.error_response("Rule deletion failed", f"Could not delete rule '{rule_id}'")
    
    async def _move_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Move a rule to different position"""
        rule_id = arguments.get("rule_id")
        position = arguments.get("position", "top")  # top, bottom, before, after
        target_rule_id = arguments.get("target_rule_id")  # for before/after
        
        if not rule_id:
            return self.error_response("Missing parameter", "rule_id is required")
        
        if position in ["before", "after"] and not target_rule_id:
            return self.error_response("Missing parameter", "target_rule_id is required for before/after positioning")
        
        # Build move data
        data = {"position": position}
        if target_rule_id:
            data["target_rule"] = target_rule_id
        
        result = self.client.post(f"objects/rule/{rule_id}/actions/move/invoke", data=data)
        
        if result.get("success"):
            return [{
                "type": "text",
                "text": (
                    f"✅ **Rule Moved Successfully**\n\n"
                    f"Rule ID: {rule_id}\n"
                    f"New Position: {position}\n" +
                    (f"Target Rule: {target_rule_id}\n" if target_rule_id else "") +
                    f"\n⚠️ **Remember to activate changes!**"
                )
            }]
        else:
            return self.error_response("Rule move failed", f"Could not move rule '{rule_id}'")