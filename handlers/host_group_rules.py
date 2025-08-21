"""
Specialized handler for host group and contact group rules
"""

from typing import Dict, Any, List
from handlers.base import BaseHandler
from api.exceptions import CheckMKError


class HostGroupRulesHandler(BaseHandler):
    """Handle host grouping and contact assignment rules"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle host group rule tool calls"""

        try:
            if tool_name == "vibemk_find_host_grouping_rulesets":
                return await self._find_host_grouping_rulesets(arguments)
            elif tool_name == "vibemk_create_host_contactgroup_rule":
                return await self._create_host_contactgroup_rule(arguments)
            elif tool_name == "vibemk_create_host_hostgroup_rule":
                return await self._create_host_hostgroup_rule(arguments)
            elif tool_name == "vibemk_get_example_rule_structures":
                return await self._get_example_rule_structures(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _find_host_grouping_rulesets(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find all rulesets related to host grouping and contact assignment"""

        # Search for relevant rulesets
        search_terms = ["contact", "group", "host", "notification", "assignment"]

        results = []
        results.append("🔍 **Host Grouping and Contact Assignment Rulesets**\\n")

        all_rulesets = {}

        for search_term in search_terms:
            try:
                result = self.client.get("domain-types/ruleset/collections/all", params={"search": search_term})

                if result.get("success"):
                    rulesets = result["data"].get("value", [])

                    for ruleset in rulesets:
                        if isinstance(ruleset, dict):
                            ruleset_id = ruleset.get("id", "Unknown")
                            title = ruleset.get("title", "No title")

                            # Filter for host-related grouping rules
                            if any(
                                keyword in ruleset_id.lower()
                                for keyword in ["host", "contact", "group", "notification"]
                            ):
                                all_rulesets[ruleset_id] = {
                                    "title": title,
                                    "id": ruleset_id,
                                    "search_term": search_term,
                                }
            except Exception as e:
                results.append(f"Search for '{search_term}' failed: {e}")

        # Categorize found rulesets
        contact_rules = {}
        host_group_rules = {}
        notification_rules = {}
        other_rules = {}

        for ruleset_id, info in all_rulesets.items():
            if "contact" in ruleset_id.lower():
                contact_rules[ruleset_id] = info
            elif "hostgroup" in ruleset_id.lower() or "host_group" in ruleset_id.lower():
                host_group_rules[ruleset_id] = info
            elif "notification" in ruleset_id.lower():
                notification_rules[ruleset_id] = info
            else:
                other_rules[ruleset_id] = info

        # Format results
        if contact_rules:
            results.append("\\n📞 **Contact Group Assignment Rules:**")
            for ruleset_id, info in contact_rules.items():
                results.append(f"   • **{ruleset_id}**: {info['title']}")

        if host_group_rules:
            results.append("\\n🏠 **Host Group Assignment Rules:**")
            for ruleset_id, info in host_group_rules.items():
                results.append(f"   • **{ruleset_id}**: {info['title']}")

        if notification_rules:
            results.append("\\n📨 **Notification Rules:**")
            for ruleset_id, info in notification_rules.items():
                results.append(f"   • **{ruleset_id}**: {info['title']}")

        if other_rules:
            results.append("\\n🔧 **Other Related Rules:**")
            for ruleset_id, info in other_rules.items():
                results.append(f"   • **{ruleset_id}**: {info['title']}")

        results.append(f"\\n📊 **Summary:** Found {len(all_rulesets)} relevant rulesets")

        return [{"type": "text", "text": "\\n".join(results)}]

    async def _create_host_contactgroup_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a rule to assign contact groups to hosts using the corrected format"""
        contact_groups = arguments.get("contact_groups", [])
        host_conditions = arguments.get("host_conditions", {})
        comment = arguments.get("comment", "Host contact group assignment")
        folder = arguments.get("folder", "/")

        if not contact_groups:
            return self.error_response("Missing parameter", "contact_groups list is required")

        # Use the working ruleset name we discovered
        working_ruleset = "host_contactgroups"

        # Convert folder path: "/" -> "~", "/hosts/linux" -> "~hosts~linux"
        if folder.startswith("/"):
            api_folder = "~" + folder[1:].replace("/", "~") if folder != "/" else "~"
        else:
            api_folder = "~" + folder.replace("/", "~")

        # Format contact groups as single string if only one, otherwise as Python list string
        if isinstance(contact_groups, list):
            if len(contact_groups) == 1:
                # Single contact group -> use as string
                value_raw = f"'{contact_groups[0]}'"
            else:
                # Multiple contact groups -> use Python list format
                formatted_groups = "', '".join(contact_groups)
                value_raw = f"['{formatted_groups}']"
        else:
            # Already a string
            value_raw = f"'{contact_groups}'"

        # Build rule data structure using the corrected format we discovered
        rule_data = {
            "properties": {"disabled": False},
            "value_raw": value_raw,
            "conditions": host_conditions if host_conditions else {},
            "ruleset": working_ruleset,
            "folder": api_folder,
        }

        # Add comment to properties if provided
        if comment:
            rule_data["properties"]["comment"] = comment

        try:
            result = self.client.post("domain-types/rule/collections/all", data=rule_data)

            if result.get("success"):
                rule_id = result["data"].get("id", "unknown")
                return [
                    {
                        "type": "text",
                        "text": (
                            f"✅ **Host Contact Group Rule Created Successfully**\\n\\n"
                            f"Ruleset: {working_ruleset}\\n"
                            f"Rule ID: {rule_id}\\n"
                            f"Contact Groups: {contact_groups}\\n"
                            f"Folder: {folder}\\n"
                            f"Comment: {comment}\\n\\n"
                            f"📝 **Conditions:** {host_conditions if host_conditions else 'None (applies to all hosts)'}\\n\\n"
                            f"⚠️ **Remember to activate changes!**"
                        ),
                    }
                ]
            else:
                error_data = result.get("data", {})
                return [
                    {
                        "type": "text",
                        "text": (
                            f"❌ **Rule Creation Failed**\\n\\n"
                            f"Ruleset: {working_ruleset}\\n"
                            f"Error: {error_data.get('title', 'Unknown error')}\\n"
                            f"Details: {error_data.get('detail', '')}\\n\\n"
                            f"**Debug - Rule Data:** {rule_data}"
                        ),
                    }
                ]
        except Exception as e:
            return self.error_response("Rule creation failed", f"Could not create contact group rule: {str(e)}")

    async def _create_host_hostgroup_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a rule to assign hosts to host groups"""
        host_groups = arguments.get("host_groups", [])
        host_conditions = arguments.get("host_conditions", {})
        comment = arguments.get("comment", "Host group assignment")
        folder = arguments.get("folder", "/")

        if not host_groups:
            return self.error_response("Missing parameter", "host_groups list is required")

        # Find the correct ruleset for host group assignment
        hostgroup_ruleset_candidates = ["host_groups", "hostgroups", "host_group_assignment", "host_grouping"]

        working_ruleset = None

        for candidate in hostgroup_ruleset_candidates:
            try:
                result = self.client.get(f"objects/ruleset/{candidate}")
                if result.get("success"):
                    working_ruleset = candidate
                    break
            except Exception:
                continue

        if not working_ruleset:
            return [
                {
                    "type": "text",
                    "text": (
                        f"❌ **Host Group Ruleset Not Found**\\n\\n"
                        f"Could not find a working ruleset for host group assignment.\\n\\n"
                        f"**Tried rulesets:**\\n"
                        + "\\n".join([f"• {rs}" for rs in hostgroup_ruleset_candidates])
                        + "\\n\\n"
                        f"**Recommendation:**\\n"
                        f"1. Use 'find_host_grouping_rulesets' to find available rulesets\\n"
                        f"2. Check existing host group rules in CheckMK GUI"
                    ),
                }
            ]

        # Build rule data structure for host groups according to CMDBsyncer working implementation
        rule_data = {
            "ruleset": working_ruleset,
            "folder": folder,
            "properties": {"disabled": False, "description": "Host group assignment via vibeMK", "comment": comment},
            "value_raw": host_groups,
        }

        # Add host conditions if provided (flat structure, not under extensions)
        if host_conditions:
            rule_data["conditions"] = host_conditions

        try:
            result = self.client.post("domain-types/rule/collections/all", data=rule_data)

            if result.get("success"):
                return [
                    {
                        "type": "text",
                        "text": (
                            f"✅ **Host Group Assignment Rule Created**\\n\\n"
                            f"Ruleset: {working_ruleset}\\n"
                            f"Host Groups: {', '.join(host_groups)}\\n"
                            f"Folder: {folder}\\n"
                            f"Comment: {comment}\\n\\n"
                            f"📝 **Conditions:** {host_conditions if host_conditions else 'None (applies to all hosts)'}\\n\\n"
                            f"⚠️ **Remember to activate changes!**"
                        ),
                    }
                ]
            else:
                error_data = result.get("data", {})
                return [
                    {
                        "type": "text",
                        "text": (
                            f"❌ **Rule Creation Failed**\\n\\n"
                            f"Ruleset: {working_ruleset}\\n"
                            f"Error: {error_data.get('title', 'Unknown error')}\\n"
                            f"Details: {error_data.get('detail', '')}\\n\\n"
                            f"**Rule Data:** {rule_data}"
                        ),
                    }
                ]
        except Exception as e:
            return self.error_response("Rule creation failed", f"Could not create host group rule: {str(e)}")

    async def _get_example_rule_structures(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Show example rule structures for host grouping"""

        examples = []

        examples.append("📚 **Example Rule Structures for Host Grouping**\\n")

        examples.append("\\n🔧 **1. Host Contact Group Assignment (Swagger Format)**")
        examples.append("```json")
        examples.append("{")
        examples.append('  "extensions": {')
        examples.append('    "ruleset": "host_contactgroups",')
        examples.append('    "folder": "/",')
        examples.append('    "properties": {')
        examples.append('      "comment": "Critical hosts to admin teams"')
        examples.append("    },")
        examples.append('    "value_raw": ["admins", "network-team"],')
        examples.append('    "conditions": {')
        examples.append('      "host_tags": [')
        examples.append("        {")
        examples.append('          "key": "criticality",')
        examples.append('          "operator": "is",')
        examples.append('          "value": "critical"')
        examples.append("        }")
        examples.append("      ]")
        examples.append("    }")
        examples.append("  }")
        examples.append("}")
        examples.append("```")

        examples.append("\\n🏠 **2. Host Group Assignment (Swagger Format)**")
        examples.append("```json")
        examples.append("{")
        examples.append('  "extensions": {')
        examples.append('    "ruleset": "host_groups",')
        examples.append('    "folder": "/",')
        examples.append('    "properties": {')
        examples.append('      "comment": "Database servers to appropriate groups"')
        examples.append("    },")
        examples.append('    "value_raw": ["database-servers", "production"],')
        examples.append('    "conditions": {')
        examples.append('      "host_name": {')
        examples.append('        "match_on": ["db.*"],')
        examples.append('        "operator": "match_regex"')
        examples.append("      }")
        examples.append("    }")
        examples.append("  }")
        examples.append("}")
        examples.append("```")

        examples.append("\\n🔍 **3. Advanced Host Conditions (Swagger Format)**")
        examples.append("```json")
        examples.append("{")
        examples.append('  "extensions": {')
        examples.append('    "ruleset": "host_contactgroups",')
        examples.append('    "folder": "/",')
        examples.append('    "value_raw": ["web-admins"],')
        examples.append('    "conditions": {')
        examples.append('      "host_name": {')
        examples.append('        "match_on": ["web[0-9]+"],')
        examples.append('        "operator": "match_regex"')
        examples.append("      },")
        examples.append('      "host_tags": [')
        examples.append("        {")
        examples.append('          "key": "environment",')
        examples.append('          "operator": "is",')
        examples.append('          "value": "production"')
        examples.append("        },")
        examples.append("        {")
        examples.append('          "key": "location",')
        examples.append('          "operator": "is",')
        examples.append('          "value": "datacenter-1"')
        examples.append("        }")
        examples.append("      ],")
        examples.append('      "host_label_groups": [')
        examples.append("        {")
        examples.append('          "label_group": [')
        examples.append("            {")
        examples.append('              "operator": "and",')
        examples.append('              "label": "application:wordpress"')
        examples.append("            }")
        examples.append("          ]")
        examples.append("        }")
        examples.append("      ]")
        examples.append("    }")
        examples.append("  }")
        examples.append("}")
        examples.append("```")

        examples.append("\\n💡 **4. Simple All-Hosts Rule (Swagger Format)**")
        examples.append("```json")
        examples.append("{")
        examples.append('  "extensions": {')
        examples.append('    "ruleset": "host_contactgroups",')
        examples.append('    "folder": "/",')
        examples.append('    "properties": {')
        examples.append('      "comment": "Default contact group for all hosts"')
        examples.append("    },")
        examples.append('    "value_raw": ["monitoring-team"]')
        examples.append("  }")
        examples.append("}")
        examples.append("```")

        examples.append("\\n🎯 **Usage Tips (Updated for Swagger Format):**")
        examples.append("• All rule data must be under `extensions` object")
        examples.append("• Use `conditions` with proper operator format (match_on, operator)")
        examples.append("• `value_raw` contains the actual rule values (contact groups, host groups)")
        examples.append("• Empty conditions = rule applies to all hosts")
        examples.append("• Multiple groups can be assigned in one rule")
        examples.append("• Use `folder_index` for rule positioning (0 = top)")
        examples.append("• Remember to activate changes after creating rules")

        return [{"type": "text", "text": "\\n".join(examples)}]
