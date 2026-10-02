"""
Configuration management handlers
"""

from typing import Any, Dict, List

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class ConfigurationHandler(BaseHandler):
    """Handle configuration management operations"""

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle configuration-related tool calls"""

        try:
            if tool_name == "vibemk_activate_changes":
                return await self._activate_changes(arguments)
            elif tool_name == "vibemk_get_pending_changes":
                return await self._get_pending_changes()
            elif tool_name == "vibemk_checkmk_rules_guide":
                return self._rules_guide()
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

    async def _activate_changes(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Activate pending configuration changes"""

        # Check if activation is disabled by configuration
        if self.client.config.never_activate_changes:
            return [
                {
                    "type": "text",
                    "text": (
                        "🚫 **Change Activation Disabled**\n\n"
                        "Configuration changes activation has been disabled by the `NEVER_ACTIVATE_CHANGES` setting.\n\n"
                        "**Reason:** This is typically used in development or testing environments to prevent "
                        "accidental activation of configuration changes.\n\n"
                        "**To enable activation:**\n"
                        "• Remove the `NEVER_ACTIVATE_CHANGES` environment variable, or\n"
                        "• Set `NEVER_ACTIVATE_CHANGES=false`\n\n"
                        "**Current configuration:** `NEVER_ACTIVATE_CHANGES=true`\n\n"
                        "💡 **Note:** You can still view pending changes using `get_pending_changes`."
                    ),
                }
            ]

        sites = arguments.get("sites", [])
        force = arguments.get("force_foreign_changes", False)

        # First, check pending changes to get current state
        pending_result = self.client.get("domain-types/activation_run/collections/pending_changes")

        if not pending_result.get("success"):
            return self.error_response("Cannot check pending changes", "Unable to verify current configuration state")

        pending_changes = pending_result["data"].get("value", [])
        if not pending_changes:
            return [
                {"type": "text", "text": "ℹ️ **No Pending Changes**\n\nThere are no configuration changes to activate."}
            ]

        # Prepare activation data
        data = {
            "redirect": False,
            "sites": sites if sites else [self.client.config.site],
            "force_foreign_changes": force,
        }

        # activate-changes is declared etag="input"; the ETag comes from the
        # pending_changes response fetched above, which is etag="output".
        # The wildcard was accepted but disabled the precondition check.
        headers = {"If-Match": self._extract_etag(pending_result)}

        try:
            result = self.client.post(
                "domain-types/activation_run/actions/activate-changes/invoke", data=data, headers=headers
            )
        except CheckMKError as error:
            return self.error_response("Activation failed", str(error))

        if result.get("success"):
            activation_id = result["data"].get("id", "unknown")
            return [
                {
                    "type": "text",
                    "text": (
                        f"✅ **Changes Activation Started Successfully**\n\n"
                        f"Activation ID: {activation_id}\n"
                        f"Sites: {', '.join(sites) if sites else self.client.config.site}\n"
                        f"Force foreign changes: {force}\n"
                        f"Changes to activate: {len(pending_changes)}\n\n"
                        f"⏳ Activation is now running...\n"
                        f"💡 Check the CheckMK GUI for progress details."
                    ),
                }
            ]
        else:
            return self.error_response("Activation failed", "Could not activate changes despite proper headers")

    async def _get_pending_changes(self) -> List[Dict[str, Any]]:
        """Get list of pending configuration changes"""
        result = self.client.get("domain-types/activation_run/collections/pending_changes")

        if not result.get("success"):
            status_code = result.get("status", "unknown")
            return self.error_response(
                f"Failed to retrieve pending changes (HTTP {status_code})", "Check CheckMK permissions and API access"
            )

        changes = result["data"].get("value", [])
        if not changes:
            return self.structured_response(
                (
                    "ℹ️ **No Pending Changes**\n\n"
                    "All configuration changes have been activated.\n"
                    "The CheckMK configuration is up to date."
                ),
                {"count": 0, "changes": []},
            )
        change_list = []
        entries = []
        change_summary = {"create": 0, "edit": 0, "delete": 0, "move": 0, "other": 0}

        for change in changes:
            # CheckMK sends each change as a flat object -- id, user_id,
            # action_name, text, time -- with no extensions and no separate
            # object type or name; "text" is its own description of the change.
            action = str(change.get("action_name") or "change")
            description = str(change.get("text") or action)
            user = str(change.get("user_id") or "unknown user")

            # Categorize changes
            if "create" in action.lower():
                change_summary["create"] += 1
                icon = "➕"
            elif "edit" in action.lower() or "update" in action.lower():
                change_summary["edit"] += 1
                icon = "📝"
            elif "delete" in action.lower():
                change_summary["delete"] += 1
                icon = "🗑️"
            elif "move" in action.lower():
                change_summary["move"] += 1
                icon = "📁"
            else:
                change_summary["other"] += 1
                icon = "⚙️"

            change_list.append(f"{icon} {description} (by {user})")
            entries.append({"change_id": str(change.get("id", "")), "user": user, "text": description})

        # Create summary
        summary_parts = []
        for action_type, count in change_summary.items():
            if count > 0:
                summary_parts.append(f"{action_type}: {count}")

        summary_text = ", ".join(summary_parts)

        return self.structured_response(
            (
                f"📋 **Pending Changes** ({len(changes)} total)\n\n"
                f"**Summary:** {summary_text}\n\n"
                f"**Details:**\n"
                + "\n".join(change_list[:15])
                + (f"\n\n... and {len(changes) - 15} more changes" if len(changes) > 15 else "")
                + "\n\n💡 Use 'activate_changes' to apply these changes"
            ),
            {"count": len(changes), "changes": entries},
        )

    def _rules_guide(self) -> List[Dict[str, Any]]:
        """Return comprehensive CheckMK rule management guide for LLM context."""
        guide = """# Checkmk Rule Management Guide

## Rule order (CRITICAL)

Checkmk evaluates rules by these principles:
1. **The first matching rule wins** — rules are searched top to bottom, and the first one that matches is applied.
2. **A subfolder rule ALWAYS beats a root folder rule** — a rule in `/muenchen/mue-0/` is evaluated before one in `/` (root), whatever position it holds.
3. **Within one folder**: position #0 (top) beats position #5.

### What follows from that
- ALWAYS create a new rule for a host in that host's own folder, not in root `~`.
- Before creating a rule, call `vibemk_get_ruleset` and check whether one already exists for this host.
- If one exists, prefer **updating** it (vibemk_update_rule) over adding another — otherwise two rules compete.
- After creating a rule, check the order and move it up with vibemk_move_rule if needed.

## value_raw — a Python literal, not JSON

Checkmk rule values are Python dicts containing tuples. JSON has no tuples, so always pass `value_raw` as a Python string:

```python
# CORRECT (value_raw as a string):
"{'levels': ('perc_used', (80.0, 90.0))}"
"{'levels_swap': ('perc_used', (30.0, 50.0)), 'levels_virtual': ('perc_used', (90.0, 95.0))}"

# WRONG (JSON / rule_config -> API 400):
{"levels": ["perc_used", [80.0, 90.0]]}  # lists instead of tuples -> error
```

## memory_linux parameter keys

For `checkgroup_parameters:memory_linux`:
- `levels_virtual` — total virtual memory (what Checkmk displays as "Total virtual memory")
- `levels_ram` — physical RAM
- `levels_swap` — swap usage
- `levels_committed` — committed memory

**NOT** `levels`: it does not exist in this ruleset, and sending it returns HTTP 400.

## Interface speed (checkgroup_parameters:interfaces)

For "expected speed" WARN messages:
- Ruleset: `checkgroup_parameters:interfaces`, NOT `checkgroup_parameters:if`
- Value: `{'speed': 1000000000}` — bits/s, not Mbit/s
- Typical values: 1 Gbit/s = 1_000_000_000, 10 Gbit/s = 10_000_000_000
- `vibemk_set_interface_params` with `expected_speed_mbit` converts for you.
- Only activate_changes is needed; no service discovery.

## Activation workflow

1. Create or change the rule (vibemk_create_rule / vibemk_update_rule / vibemk_set_*)
2. Activate the changes (vibemk_activate_changes) — the ETag is fetched for you
3. Wait for the next check cycle, normally one minute
4. Check the result (vibemk_get_service_status, or the Checkmk UI)

**INTERNAL:** vibeMK reads the ETag from `pending_changes` itself. There is no manual ETag handling to do.

## Process monitoring (inventory_processes_rules)

After creating a process rule:
1. Activate it (activate_changes)
2. **Run a service discovery** — the new "Process X" service appears only then
3. Without the discovery the rule exists but the service stays invisible

`vibemk_set_process_thresholds` does both the activation and the discovery.

## Common mistakes

| Symptom | Cause | Fix |
|---------|-------|-----|
| HTTP 400 | value_raw contains lists instead of tuples | pass value_raw as a Python literal string |
| The rule has no effect | a root rule beats the subfolder rule | create the rule in the host's folder |
| The rule has no effect (2) | wrong order | vibemk_move_rule + top_of_folder |
| The memory check shows stale values | the check has not run yet | wait one to two minutes after activating |
| The interface WARN persists | wrong ruleset | checkgroup_parameters:interfaces, not :if |
"""
        return [{"type": "text", "text": guide}]
