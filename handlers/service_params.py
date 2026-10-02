"""
Service parameter rules — process monitoring (inventory_processes_rules) and
interface parameter overrides (checkgroup_parameters:if).

Process thresholds: inventory_processes_rules + service discovery (refresh).
Interface params: checkgroup_parameters:if + activate (no discovery needed).
"""

from typing import Any, Dict, List, Optional

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class ServiceParamsHandler(BaseHandler):
    """Handle service parameter threshold rules"""

    _WRITE_TOOLS = frozenset(
        {
            "vibemk_set_process_thresholds",
            "vibemk_set_interface_params",
            "vibemk_set_memory_thresholds",
            "vibemk_delete_service_param_rule",
        }
    )

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            if tool_name == "vibemk_set_process_thresholds":
                result = await self._set_process_thresholds(arguments)
            elif tool_name == "vibemk_list_process_rules":
                result = await self._list_process_rules(arguments)
            elif tool_name == "vibemk_set_interface_params":
                result = await self._set_interface_params(arguments)
            elif tool_name == "vibemk_set_memory_thresholds":
                result = await self._set_memory_thresholds(arguments)
            elif tool_name == "vibemk_delete_service_param_rule":
                result = await self._delete_service_param_rule(arguments)
            else:
                return self.error_response("Unknown tool", f"Tool '{tool_name}' is not supported")

        except CheckMKError as e:
            return self.error_response("CheckMK API Error", str(e))
        except Exception as e:
            self.logger.exception(f"Error in {tool_name}")
            return self.error_response("Unexpected Error", str(e))

        if (
            tool_name in self._WRITE_TOOLS
            and arguments.get("activate_changes")
            and result
            and "❌" not in result[-1].get("text", "")
        ):
            result[-1]["text"] += "\n" + self._run_activation()
        return result

    def _resolve_folder(self, hostname: str, explicit_folder: Optional[str]) -> str:
        if explicit_folder:
            return explicit_folder
        try:
            result = self.client.get(f"objects/host_config/{hostname}")
            raw_folder = str(result["data"].get("extensions", {}).get("folder", "/"))
            return "~" + raw_folder.lstrip("/").replace("/", "~")
        except Exception:
            return "~"

    def _discover_services(self, hostname: str) -> str:
        """Trigger service discovery (refresh) to apply new process rules to autochecks."""
        try:
            self.client.post(
                f"objects/host/{hostname}/actions/discover_services/invoke",
                {"mode": "refresh"},
            )
            return f"✅ Service Discovery für '{hostname}' ausgeführt — neue Schwellwerte aktiv."
        except Exception as exc:
            return f"⚠️  Service Discovery fehlgeschlagen: {exc}"

    async def _set_process_thresholds(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        process_name = arguments.get("process_name", "")
        warn_max = arguments.get("warn_max")
        crit_max = arguments.get("crit_max")
        warn_min = int(arguments.get("warn_min", 1))
        crit_min = int(arguments.get("crit_min", 1))
        cpu_warn = arguments.get("cpu_warn_percent")
        cpu_crit = arguments.get("cpu_crit_percent")
        single_cpu_warn = arguments.get("single_cpu_warn_percent")
        single_cpu_crit = arguments.get("single_cpu_crit_percent")
        cpu_average_min = arguments.get("cpu_average_min")
        mem_warn_mb = arguments.get("mem_warn_mb")
        mem_crit_mb = arguments.get("mem_crit_mb")
        resident_warn_mb = arguments.get("resident_warn_mb")
        resident_crit_mb = arguments.get("resident_crit_mb")
        description = arguments.get("description", "")
        run_discovery = arguments.get("run_discovery", True)
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        if not hostname or not process_name:
            return self.error_response("Missing parameter", "hostname and process_name are required")
        if warn_max is None or crit_max is None:
            return self.error_response("Missing parameter", "warn_max and crit_max are required")

        # Strip "Process " prefix if user passes full service name
        proc = process_name.removeprefix("Process ")

        default_params: Dict[str, Any] = {
            "cpu_rescale_max": True,
            "levels": (warn_min, crit_min, int(warn_max), int(crit_max)),
        }
        if cpu_warn and cpu_crit:
            default_params["cpulevels"] = (float(cpu_warn), float(cpu_crit))
        if single_cpu_warn and single_cpu_crit:
            default_params["single_cpulevels"] = (float(single_cpu_warn), float(single_cpu_crit))
        if cpu_average_min:
            default_params["cpu_average"] = int(cpu_average_min)
        if mem_warn_mb and mem_crit_mb:
            default_params["virtual_levels"] = (int(mem_warn_mb) * 1024 * 1024, int(mem_crit_mb) * 1024 * 1024)
        if resident_warn_mb and resident_crit_mb:
            default_params["resident_levels"] = (
                int(resident_warn_mb) * 1024 * 1024,
                int(resident_crit_mb) * 1024 * 1024,
            )

        # inventory_processes_rules value format:
        # descr = service item name (shown as "Process <descr>")
        # match = process executable pattern (exact or ~regex prefix)
        # default_params = threshold dict
        value: Dict[str, Any] = {
            "descr": proc,
            "match": proc,
            "default_params": default_params,
        }

        props: Dict[str, Any] = {"disabled": False}
        if description:
            props["description"] = description
        else:
            props["description"] = f"Process {proc}: warn>={warn_max}, crit>={crit_max}"

        result = self.client.post(
            "domain-types/rule/collections/all",
            {
                "ruleset": "inventory_processes_rules",
                "folder": folder,
                "value_raw": repr(value),
                "conditions": {
                    "host_name": {"match_on": [hostname], "operator": "one_of"},
                    "host_tags": [],
                    "host_label_groups": [],
                    "service_label_groups": [],
                },
                "properties": props,
            },
        )

        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ Prozess-Schwellwerte für 'Process {proc}' auf '{hostname}' angelegt.\n"
                f"Minimum: warn<{warn_min}, crit<{crit_min}\n"
                f"Maximum: warn>={warn_max}, crit>={crit_max}\n"
                + (f"CPU gesamt: warn {cpu_warn}%, crit {cpu_crit}%\n" if cpu_warn else "")
                + (f"CPU pro Prozess: warn {single_cpu_warn}%, crit {single_cpu_crit}%\n" if single_cpu_warn else "")
                + (f"CPU-Mittelwert: {cpu_average_min} Minuten\n" if cpu_average_min else "")
                + (f"Virtueller Speicher: warn {mem_warn_mb} MB, crit {mem_crit_mb} MB\n" if mem_warn_mb else "")
                + (
                    f"Resident-Speicher: warn {resident_warn_mb} MB, crit {resident_crit_mb} MB\n"
                    if resident_warn_mb
                    else ""
                )
                + f"Rule-ID: {rule_id}\n"
            )
            if run_discovery:
                # Activation must happen first so the rule is visible during discovery
                msg += self._run_activation() + "\n"
                msg += self._discover_services(hostname)
            else:
                msg += "⚠️  Noch keine Service Discovery ausgeführt — Schwellwerte erst nach Discovery aktiv."
            return [{"type": "text", "text": msg}]
        return self.error_response("Regel anlegen fehlgeschlagen", str(result.get("data", {})))

    async def _list_process_rules(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname")
        process_name = arguments.get("process_name")

        result = self.client.get(
            "domain-types/rule/collections/all",
            params={"ruleset_name": "inventory_processes_rules"},
        )
        if not result.get("success"):
            return self.error_response("Abruf fehlgeschlagen", "inventory_processes_rules nicht erreichbar")

        lines = ["🔍 **Prozess-Monitoring-Regeln (inventory_processes_rules)**\n"]
        for rule in result["data"].get("value", []):
            ext = rule.get("extensions", {})
            cond = ext.get("conditions", {})
            hosts = cond.get("host_name", {}).get("match_on", [])
            vr = ext.get("value_raw", "")
            props = ext.get("properties", {})

            if hostname and hostname not in hosts:
                continue
            if process_name and process_name.lower() not in vr.lower():
                continue

            disabled = props.get("disabled", False)
            status = "🔴" if disabled else "🟢"
            hosts_str = ", ".join(hosts) if hosts else "alle Hosts"

            try:
                v = eval(vr)
                descr = v.get("descr", "?")
                match = v.get("match", "?")
                dp = v.get("default_params", {})
                levels = dp.get("levels", None)
                if levels:
                    details = f"min warn/crit: {levels[0]}/{levels[1]}, max warn/crit: {levels[2]}/{levels[3]}"
                else:
                    details = "(keine Schwellwerte)"
                cpu = dp.get("cpulevels", None)
                if cpu:
                    details += f", CPU warn/crit: {cpu[0]}%/{cpu[1]}%"
            except Exception:
                descr = "?"
                match = "?"
                details = vr[:120]

            lines.append(
                f"• {status} **Process {descr}** (match: `{match}`) → {hosts_str}\n"
                f"  ID: `{rule['id']}`\n"
                f"  {details}"
            )

        if len(lines) == 1:
            lines.append("Keine Prozess-Monitoring-Regeln gefunden.")
        return [{"type": "text", "text": "\n".join(lines)}]

    # Speed lookup: Mbit/s → bits/s
    _SPEED_MAP = {
        10: 10_000_000,
        100: 100_000_000,
        1000: 1_000_000_000,
        10000: 10_000_000_000,
    }

    async def _set_interface_params(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        interface_name = arguments.get("interface_name", "")
        expected_speed_mbit = arguments.get("expected_speed_mbit")
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        if not hostname or not interface_name:
            return self.error_response("Missing parameter", "hostname and interface_name are required")
        if expected_speed_mbit is None:
            return self.error_response("Missing parameter", "at least expected_speed_mbit is required")

        # Build service description: accept "vmbr1" or "Interface vmbr1"
        iface = interface_name.removeprefix("Interface ")
        service_desc = f"Interface {iface}"

        value: Dict[str, Any] = {}
        speed_mbit = int(expected_speed_mbit)
        # Map common speeds; fall back to direct conversion for others
        speed_bits = self._SPEED_MAP.get(speed_mbit, speed_mbit * 1_000_000)
        value["speed"] = speed_bits

        props: Dict[str, Any] = {"disabled": False}
        props["description"] = description or f"{service_desc} auf {hostname}: expected speed {speed_mbit} Mbit/s"

        result = self.client.post(
            "domain-types/rule/collections/all",
            {
                "ruleset": "checkgroup_parameters:interfaces",
                "folder": folder,
                "value_raw": repr(value),
                "conditions": {
                    "host_name": {"match_on": [hostname], "operator": "one_of"},
                    "service_description": {"match_on": [service_desc], "operator": "one_of"},
                    "host_tags": [],
                    "host_label_groups": [],
                    "service_label_groups": [],
                },
                "properties": props,
            },
        )

        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ Interface-Parameter für '{service_desc}' auf '{hostname}' gesetzt.\n"
                f"Erwartete Geschwindigkeit: {speed_mbit} Mbit/s ({speed_bits:,} bits/s)\n"
                f"Rule-ID: {rule_id}\n"
                f"ℹ️  Änderungen aktivieren damit die Regel greift."
            )
            return [{"type": "text", "text": msg}]
        return self.error_response("Regel anlegen fehlgeschlagen", str(result.get("data", {})))

    async def _set_memory_thresholds(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        ram_warn = arguments.get("ram_warn_percent")
        ram_crit = arguments.get("ram_crit_percent")
        swap_warn = arguments.get("swap_warn_percent")
        swap_crit = arguments.get("swap_crit_percent")
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        if not hostname:
            return self.error_response("Missing parameter", "hostname is required")
        if not any([ram_warn, swap_warn]):
            return self.error_response("Missing parameter", "at least ram_warn_percent or swap_warn_percent required")

        value: Dict[str, Any] = {}
        if ram_warn is not None and ram_crit is not None:
            # levels_virtual = Total virtual memory (RAM shown in "Total virtual memory" check output)
            value["levels_virtual"] = ("perc_used", (float(ram_warn), float(ram_crit)))
        if swap_warn is not None and swap_crit is not None:
            value["levels_swap"] = ("perc_used", (float(swap_warn), float(swap_crit)))

        props: Dict[str, Any] = {"disabled": False}
        parts = []
        if "levels_virtual" in value:
            parts.append(f"RAM warn={ram_warn}% crit={ram_crit}%")
        if "levels_swap" in value:
            parts.append(f"Swap warn={swap_warn}% crit={swap_crit}%")
        props["description"] = description or f"Memory {hostname}: {', '.join(parts)}"

        result = self.client.post(
            "domain-types/rule/collections/all",
            {
                "ruleset": "checkgroup_parameters:memory_linux",
                "folder": folder,
                "value_raw": repr(value),
                "conditions": {
                    "host_name": {"match_on": [hostname], "operator": "one_of"},
                    "host_tags": [],
                    "host_label_groups": [],
                    "service_label_groups": [],
                },
                "properties": props,
            },
        )

        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ Memory-Schwellwerte für '{hostname}' gesetzt.\n"
                + (f"RAM: warn>={ram_warn}%, crit>={ram_crit}%\n" if "levels_virtual" in value else "")
                + (f"Swap: warn>={swap_warn}%, crit>={swap_crit}%\n" if "levels_swap" in value else "")
                + f"Rule-ID: {rule_id}\n"
                + f"ℹ️  Regel steht ganz oben — höher priorisiert als ältere Regeln."
            )
            return [{"type": "text", "text": msg}]
        detail = result.get("data", {})
        return self.error_response("Regel anlegen fehlgeschlagen", f"{detail}\nvalue_raw: {repr(value)}")

    async def _delete_service_param_rule(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        rule_id = arguments.get("rule_id", "")
        if not rule_id:
            return self.error_response("Missing parameter", "rule_id is required")
        self.client.delete(f"objects/rule/{rule_id}")
        return [{"type": "text", "text": f"✅ Regel `{rule_id}` gelöscht."}]
