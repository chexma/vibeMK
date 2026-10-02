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
            return [
                {
                    "type": "text",
                    "text": (
                        "ℹ️ **No Pending Changes**\n\n"
                        "All configuration changes have been activated.\n"
                        "The CheckMK configuration is up to date."
                    ),
                }
            ]

        change_list = []
        change_summary = {"create": 0, "edit": 0, "delete": 0, "move": 0, "other": 0}

        for change in changes:
            extensions = change.get("extensions", {})
            action = extensions.get("action_name", "Unknown")
            obj_type = extensions.get("object_type", "Unknown")
            obj_name = extensions.get("object_name", "Unknown")
            user = extensions.get("user_id", "unknown")

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

            change_list.append(f"{icon} {action}: {obj_type} '{obj_name}' (by {user})")

        # Create summary
        summary_parts = []
        for action_type, count in change_summary.items():
            if count > 0:
                summary_parts.append(f"{action_type}: {count}")

        summary_text = ", ".join(summary_parts)

        return [
            {
                "type": "text",
                "text": (
                    f"📋 **Pending Changes** ({len(changes)} total)\n\n"
                    f"**Summary:** {summary_text}\n\n"
                    f"**Details:**\n"
                    + "\n".join(change_list[:15])
                    + (f"\n\n... and {len(changes) - 15} more changes" if len(changes) > 15 else "")
                    + "\n\n⚠️ **Use 'activate_changes' to apply these changes.**"
                ),
            }
        ]

    def _rules_guide(self) -> List[Dict[str, Any]]:
        """Return comprehensive CheckMK rule management guide for LLM context."""
        guide = """# CheckMK Rule Management Guide

## Regelreihenfolge (KRITISCH)

CheckMK wertet Regeln nach diesen Prinzipien aus:
1. **Erste passende Regel gewinnt** — Regeln werden von oben nach unten durchsucht, sobald eine Regel matched, wird sie angewendet.
2. **Subfolder-Regeln gewinnen IMMER gegen Root-Folder-Regeln** — eine Regel in `/muenchen/mue-0/` wird vor einer Regel in `/` (Root) ausgewertet, egal welche Position sie hat.
3. **Innerhalb eines Ordners**: Position #0 (top) gewinnt gegen Position #5.

### Konsequenzen
- Neue Regeln für einen Host IMMER im Ordner des Hosts anlegen (nicht in Root `~`).
- Bevor eine neue Regel angelegt wird: `vibemk_get_ruleset` aufrufen und prüfen ob bereits eine Regel für diesen Host existiert.
- Wenn eine Regel existiert: lieber **updaten** (vibemk_update_rule) als eine neue anlegen — sonst entstehen zwei konkurrierende Regeln.
- Nach Anlegen einer neuen Regel: Reihenfolge prüfen, ggf. mit vibemk_move_rule nach oben verschieben.

## value_raw — Python-Literal (kein JSON!)

CheckMK-Regelwerte sind Python-Dicts mit Tuples. JSON kennt keine Tuples → immer `value_raw` als Python-String verwenden:

```python
# RICHTIG (value_raw als String):
"{'levels': ('perc_used', (80.0, 90.0))}"
"{'levels_swap': ('perc_used', (30.0, 50.0)), 'levels_virtual': ('perc_used', (90.0, 95.0))}"

# FALSCH (JSON / rule_config → API 400):
{"levels": ["perc_used", [80.0, 90.0]]}  # Listen statt Tuples → Fehler
```

## Memory-Linux Parameter-Keys

Für `checkgroup_parameters:memory_linux`:
- `levels_virtual` — Total virtual memory (das was CheckMK als "Total virtual memory" anzeigt)
- `levels_ram` — Physischer RAM
- `levels_swap` — Swap-Auslastung
- `levels_committed` — Committed memory

**NICHT** `levels` (existiert nicht in diesem Ruleset → HTTP 400).

## Interface Speed (checkgroup_parameters:interfaces)

Für "expected speed" WARN-Meldungen:
- Ruleset: `checkgroup_parameters:interfaces` (NICHT `checkgroup_parameters:if`)
- Wert: `{'speed': 1000000000}` (bits/s, nicht Mbit/s)
- Typische Werte: 1 GBit/s = 1_000_000_000, 10 GBit/s = 10_000_000_000
- `vibemk_set_interface_params` mit `expected_speed_mbit` macht die Konvertierung automatisch.
- Nur activate_changes nötig, keine Service Discovery.

## Aktivierung — Workflow

1. Regel anlegen/ändern (vibemk_create_rule / vibemk_update_rule / vibemk_set_*)
2. Änderungen aktivieren (vibemk_activate_changes) — ETag wird automatisch geholt
3. Warten bis der nächste Check-Zyklus läuft (normalerweise 1 Minute)
4. Ergebnis prüfen (vibemk_get_service_status oder Check-MK-UI)

**INTERN:** vibemk holt den ETag automatisch von `pending_changes` — manuelles ETag-Management nicht nötig.

## Prozess-Monitoring (inventory_processes_rules)

Nach Anlegen einer Prozess-Regel:
1. Regel aktivieren (activate_changes)
2. **Service Discovery ausführen** — erst dann erscheint der neue "Process X"-Service
3. Ohne Discovery: Regel existiert, Service aber nicht sichtbar

`vibemk_set_process_thresholds` macht Aktivierung + Discovery automatisch.

## Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| HTTP 400 | value_raw enthält Listen statt Tuples | value_raw als Python-Literal-String |
| Regel greift nicht | Root-Regel vs. Subfolder-Regel | Regel in Host-Ordner anlegen |
| Regel greift nicht (2) | Falsche Reihenfolge | vibemk_move_rule + top_of_folder |
| Memory-Check zeigt alte Werte | Check noch nicht gelaufen | 1-2 Minuten warten nach Aktivierung |
| Interface WARN bleibt | Falsches Ruleset | checkgroup_parameters:interfaces (nicht :if) |
"""
        return [{"type": "text", "text": guide}]
