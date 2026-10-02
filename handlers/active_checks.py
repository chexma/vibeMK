"""
Active check management — creates CheckMK active check rules
(HTTP, TCP, ICMP, custom Nagios plugin) for specific hosts.
Active checks are implemented as rules on active_checks:* rulesets.
"""

from typing import Any, Dict, List, Optional

from api.exceptions import CheckMKError
from handlers.base import BaseHandler


class ActiveChecksHandler(BaseHandler):
    """Handle active check rule creation"""

    _WRITE_TOOLS = frozenset(
        {
            "vibemk_create_http_check",
            "vibemk_create_tcp_check",
            "vibemk_create_icmp_check",
            "vibemk_create_custom_check",
            "vibemk_create_dns_check",
            "vibemk_create_smtp_check",
            "vibemk_create_ftp_check",
            "vibemk_create_ldap_check",
            "vibemk_create_smb_check",
            "vibemk_create_mkevents_check",
            "vibemk_create_inventory_check",
            "vibemk_delete_active_check",
        }
    )

    _ALL_RULESETS = [
        "active_checks:http",
        "active_checks:tcp",
        "active_checks:icmp",
        "active_checks:dns",
        "active_checks:smtp",
        "active_checks:ftp",
        "active_checks:ldap",
        "active_checks:disk_smb",
        "active_checks:mkevents",
        "active_checks:cmk_inv",
        "custom_checks",
    ]

    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            if tool_name == "vibemk_create_http_check":
                result = await self._create_http_check(arguments)
            elif tool_name == "vibemk_create_tcp_check":
                result = await self._create_tcp_check(arguments)
            elif tool_name == "vibemk_create_icmp_check":
                result = await self._create_icmp_check(arguments)
            elif tool_name == "vibemk_create_custom_check":
                result = await self._create_custom_check(arguments)
            elif tool_name == "vibemk_create_dns_check":
                result = await self._create_dns_check(arguments)
            elif tool_name == "vibemk_create_smtp_check":
                result = await self._create_smtp_check(arguments)
            elif tool_name == "vibemk_create_ftp_check":
                result = await self._create_ftp_check(arguments)
            elif tool_name == "vibemk_create_ldap_check":
                result = await self._create_ldap_check(arguments)
            elif tool_name == "vibemk_create_smb_check":
                result = await self._create_smb_check(arguments)
            elif tool_name == "vibemk_create_mkevents_check":
                result = await self._create_mkevents_check(arguments)
            elif tool_name == "vibemk_create_inventory_check":
                result = await self._create_inventory_check(arguments)
            elif tool_name == "vibemk_list_active_checks":
                result = await self._list_active_checks(arguments)
            elif tool_name == "vibemk_delete_active_check":
                result = await self._delete_active_check(arguments)
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

    def _host_condition(self, hostname: str) -> Dict[str, Any]:
        return {
            "host_name": {"match_on": [hostname], "operator": "one_of"},
            "host_tags": [],
            "host_label_groups": [],
            "service_label_groups": [],
        }

    def _resolve_folder(self, hostname: str, explicit_folder: Optional[str]) -> str:
        """Return explicit_folder if given, otherwise look up the host's own folder."""
        if explicit_folder:
            return explicit_folder
        try:
            result = self.client.get(f"objects/host_config/{hostname}")
            raw_folder = str(result["data"].get("extensions", {}).get("folder", "/"))
            return "~" + raw_folder.lstrip("/").replace("/", "~")
        except Exception:
            return "~"

    def _post_rule(
        self, ruleset: str, value_raw: str, hostname: str, folder: str, description: str = ""
    ) -> Dict[str, Any]:
        props: Dict[str, Any] = {"disabled": False}
        if description:
            props["description"] = description
        return self.client.post(
            "domain-types/rule/collections/all",
            {
                "ruleset": ruleset,
                "folder": folder,
                "value_raw": value_raw,
                "conditions": self._host_condition(hostname),
                "properties": props,
            },
        )

    async def _create_http_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        name = arguments.get("name", "HTTP")
        uri = arguments.get("uri", "/")
        port = arguments.get("port")
        use_ssl = arguments.get("ssl", False)
        virt_host = arguments.get("virt_host")
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        # Content checks
        expect_string = arguments.get("expect_string")
        expect_regex = arguments.get("expect_regex")
        expect_response = arguments.get("expect_response")  # list of HTTP status strings

        # Timing
        timeout = arguments.get("timeout")
        warn_seconds = arguments.get("response_time_warn")
        crit_seconds = arguments.get("response_time_crit")

        # Request options
        method = arguments.get("method")  # GET, POST, HEAD, …
        no_body = arguments.get("no_body", False)
        onredirect = arguments.get("onredirect")  # ok, warning, critical, follow, sticky, stickyport
        extended_perfdata = arguments.get("extended_perfdata", False)

        # Auth
        auth_user = arguments.get("auth_user")
        auth_password = arguments.get("auth_password")

        # Host addressing
        direct_address = arguments.get("direct_address")
        proxy_address = arguments.get("proxy_address")
        proxy_port = arguments.get("proxy_port")
        address_family = arguments.get("address_family")  # ipv4 / ipv6

        # Certificate mode (alternative to URL mode)
        cert_mode = arguments.get("cert_mode", False)
        cert_days_warn = arguments.get("cert_days_warn", 14)
        cert_days_crit = arguments.get("cert_days_crit", 7)

        if not hostname:
            return self.error_response("Missing parameter", "hostname is required")

        # --- host block ---
        host_cfg: Dict[str, Any] = {}
        if port:
            host_cfg["port"] = int(port)
        if address_family:
            host_cfg["address_family"] = address_family
        if proxy_address:
            host_cfg["address"] = ("proxy", {"address": proxy_address, "port": int(proxy_port or 80)})
        elif direct_address:
            host_cfg["address"] = ("direct", direct_address)
        if virt_host or not direct_address:
            host_cfg["virthost"] = virt_host or hostname

        # --- mode block ---
        if cert_mode:
            mode = ("cert", {"cert_days": (int(cert_days_warn), int(cert_days_crit))})
        else:
            url_params: Dict[str, Any] = {}
            if uri and uri != "/" or uri:
                url_params["uri"] = uri
            if use_ssl:
                url_params["ssl"] = "auto"
            if expect_string:
                url_params["expect_string"] = expect_string
            if expect_regex:
                url_params["expect_regex"] = expect_regex
            if expect_response:
                url_params["expect_response"] = (
                    expect_response if isinstance(expect_response, list) else [expect_response]
                )
            if timeout:
                url_params["timeout"] = int(timeout)
            if warn_seconds and crit_seconds:
                url_params["response_time"] = (float(warn_seconds), float(crit_seconds))
            if method:
                url_params["method"] = method.upper()
            if no_body:
                url_params["no_body"] = True
            if onredirect:
                url_params["onredirect"] = onredirect
            if extended_perfdata:
                url_params["extended_perfdata"] = True
            if auth_user and auth_password:
                url_params["auth"] = (auth_user, ("password", auth_password))
            mode = ("url", url_params)

        value = {"name": name, "host": host_cfg, "mode": mode}
        value_raw = repr(value)

        result = self._post_rule("active_checks:http", value_raw, hostname, folder, description)
        if result.get("success"):
            rule_id = result["data"].get("id", "")
            details = []
            if not cert_mode:
                details.append(f"URI: {uri}, SSL: {use_ssl}, Port: {port or 'standard'}")
                if expect_string:
                    details.append(f"Expect string: {expect_string}")
                if expect_regex:
                    details.append(f"Expect regex: {expect_regex}")
                if expect_response:
                    details.append(f"Expect response: {expect_response}")
                if method:
                    details.append(f"Method: {method}")
            else:
                details.append(f"Modus: Zertifikat-Check (warn {cert_days_warn}d, crit {cert_days_crit}d)")
            if description:
                details.append(f"Beschreibung: {description}")
            details.append(f"Rule-ID: {rule_id}")
            return [
                {"type": "text", "text": f"✅ HTTP-Check '{name}' für '{hostname}' angelegt.\n" + "\n".join(details)}
            ]
        return self.error_response("HTTP-Check fehlgeschlagen", str(result.get("data", {})))

    async def _create_tcp_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        port = arguments.get("port")
        name = arguments.get("name")
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))
        use_ssl = arguments.get("ssl", False)
        cert_warn = arguments.get("cert_days_warn")
        cert_crit = arguments.get("cert_days_crit")
        expect = arguments.get("expect")  # string or list of strings to expect in response
        refuse_state = arguments.get("refuse_state")  # ok / warn / crit
        mismatch_state = arguments.get("mismatch_state")  # ok / warn / crit
        timeout = arguments.get("timeout")
        warn_s = arguments.get("response_time_warn")
        crit_s = arguments.get("response_time_crit")

        if not hostname or not port:
            return self.error_response("Missing parameter", "hostname and port are required")

        value: Dict[str, Any] = {"port": int(port)}
        if name:
            value["svc_description"] = name
        if use_ssl:
            value["ssl"] = True
        if cert_warn and cert_crit:
            value["cert_days"] = (int(cert_warn), int(cert_crit))
        if expect:
            value["expect"] = expect if isinstance(expect, list) else [expect]
        if refuse_state:
            value["refuse_state"] = refuse_state
        if mismatch_state:
            value["mismatch_state"] = mismatch_state
        if timeout:
            value["timeout"] = int(timeout)
        if warn_s and crit_s:
            value["response_time"] = (float(warn_s), float(crit_s))

        result = self._post_rule("active_checks:tcp", repr(value), hostname, folder, description)
        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ TCP-Check Port {port} für '{hostname}' angelegt.\n"
                f"Service: {name or f'TCP Port {port}'}, SSL: {use_ssl}\n"
                + (f"Expect: {expect}\n" if expect else "")
                + (f"Beschreibung: {description}\n" if description else "")
                + f"Rule-ID: {rule_id}"
            )
            return [{"type": "text", "text": msg}]
        return self.error_response("TCP-Check fehlgeschlagen", str(result.get("data", {})))

    async def _create_icmp_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        name = arguments.get("name", "PING")
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))
        packets = arguments.get("packets", 5)
        timeout = arguments.get("timeout", 20.0)
        explicit_address = arguments.get("explicit_address")  # ping a different IP
        rta_warn = arguments.get("rta_warn_ms")  # round-trip warn ms
        rta_crit = arguments.get("rta_crit_ms")  # round-trip crit ms
        loss_warn = arguments.get("loss_warn_percent")  # packet loss warn %
        loss_crit = arguments.get("loss_crit_percent")  # packet loss crit %
        min_pings = arguments.get("min_pings")

        if not hostname:
            return self.error_response("Missing parameter", "hostname is required")

        value: Dict[str, Any] = {
            "description": name,
            "packets": int(packets),
            "timeout": float(timeout),
        }
        if explicit_address:
            value["address"] = ("explicit", explicit_address)
        if rta_warn and rta_crit:
            value["rta"] = (float(rta_warn), float(rta_crit))
        if loss_warn and loss_crit:
            value["loss"] = (float(loss_warn), float(loss_crit))
        if min_pings:
            value["min_pings"] = int(min_pings)

        result = self._post_rule("active_checks:icmp", repr(value), hostname, folder, description)
        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ ICMP/PING-Check '{name}' für '{hostname}' angelegt.\n"
                f"Pakete: {packets}, Timeout: {timeout}s\n"
                + (f"Ziel-IP: {explicit_address}\n" if explicit_address else "")
                + (f"RTA: warn {rta_warn}ms / crit {rta_crit}ms\n" if rta_warn else "")
                + (f"Loss: warn {loss_warn}% / crit {loss_crit}%\n" if loss_warn else "")
                + (f"Beschreibung: {description}\n" if description else "")
                + f"Rule-ID: {rule_id}"
            )
            return [{"type": "text", "text": msg}]
        return self.error_response("ICMP-Check fehlgeschlagen", str(result.get("data", {})))

    async def _create_custom_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        service_description = arguments.get("service_description", "")
        command_line = arguments.get("command_line", "")
        command_name = arguments.get("command_name")
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        if not hostname or not service_description or not command_line:
            return self.error_response(
                "Missing parameter",
                "hostname, service_description and command_line are required",
            )

        value: Dict[str, Any] = {
            "service_description": service_description,
            "command_line": command_line,
        }
        if command_name:
            value["command_name"] = command_name

        result = self._post_rule("custom_checks", repr(value), hostname, folder)
        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ Custom-Check '{service_description}' für '{hostname}' angelegt.\n"
                f"Kommando: {command_line}\nRule-ID: {rule_id}"
            )
            return [{"type": "text", "text": msg}]
        return self.error_response("Custom-Check fehlgeschlagen", str(result.get("data", {})))

    async def _create_dns_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        lookup_hostname = arguments.get("lookup_hostname", hostname)
        dns_server = arguments.get("dns_server")
        expected_addresses = arguments.get("expected_addresses")  # list of IPs
        expect_all = arguments.get("expect_all_addresses", False)
        warn = float(arguments.get("response_time_warn", 0.2))
        crit = float(arguments.get("response_time_crit", 0.3))
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        if not hostname:
            return self.error_response("Missing parameter", "hostname is required")

        value: Dict[str, Any] = {
            "hostname": lookup_hostname,
            "server": dns_server,
            "response_time": (warn, crit),
        }
        if expected_addresses:
            addr_list = expected_addresses if isinstance(expected_addresses, list) else [expected_addresses]
            value["expected_addresses_list"] = addr_list
            value["expect_all_addresses"] = expect_all

        result = self._post_rule("active_checks:dns", repr(value), hostname, folder, description)
        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ DNS-Check für '{hostname}' angelegt.\n"
                f"Lookup: {lookup_hostname}, DNS-Server: {dns_server or 'Standard'}\n"
                + (f"Erwartete IPs: {expected_addresses} (alle: {expect_all})\n" if expected_addresses else "")
                + (f"Beschreibung: {description}\n" if description else "")
                + f"Rule-ID: {rule_id}"
            )
            return [{"type": "text", "text": msg}]
        return self.error_response("DNS-Check fehlgeschlagen", str(result.get("data", {})))

    async def _create_smtp_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        name = arguments.get("name", "SMTP")
        port = arguments.get("port")
        starttls = arguments.get("starttls", False)
        cert_warn = arguments.get("cert_days_warn", 14)
        cert_crit = arguments.get("cert_days_crit", 7)
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        if not hostname:
            return self.error_response("Missing parameter", "hostname is required")

        value: Dict[str, Any] = {"name": name}
        if starttls:
            value["starttls"] = True
        if starttls or arguments.get("check_cert"):
            value["cert_days"] = (int(cert_warn), int(cert_crit))

        result = self._post_rule("active_checks:smtp", repr(value), hostname, folder, description)
        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ SMTP-Check '{name}' für '{hostname}' angelegt.\n"
                f"Port: {port or 'Standard'}, STARTTLS: {starttls}\n"
                + (f"Beschreibung: {description}\n" if description else "")
                + f"Rule-ID: {rule_id}"
            )
            return [{"type": "text", "text": msg}]
        return self.error_response("SMTP-Check fehlgeschlagen", str(result.get("data", {})))

    async def _create_ftp_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        port = int(arguments.get("port", 21))
        timeout = arguments.get("timeout")
        passive = arguments.get("passive")
        refuse_state = arguments.get("refuse_state", "crit")
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        if not hostname:
            return self.error_response("Missing parameter", "hostname is required")

        value: Dict[str, Any] = {"port": port, "refuse_state": refuse_state}
        if timeout is not None:
            value["timeout"] = int(timeout)
        if passive is not None:
            value["passive"] = passive

        result = self._post_rule("active_checks:ftp", repr(value), hostname, folder, description)
        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ FTP-Check Port {port} für '{hostname}' angelegt.\n"
                + (f"Beschreibung: {description}\n" if description else "")
                + f"Rule-ID: {rule_id}"
            )
            return [{"type": "text", "text": msg}]
        return self.error_response("FTP-Check fehlgeschlagen", str(result.get("data", {})))

    async def _create_ldap_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        name = arguments.get("name", "LDAP")
        base_dn = arguments.get("base_dn", "")
        bind_dn = arguments.get("bind_dn")
        password = arguments.get("password")
        port = arguments.get("port")
        warn_ms = float(arguments.get("response_time_warn_ms", 500.0))
        crit_ms = float(arguments.get("response_time_crit_ms", 800.0))
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        if not hostname or not base_dn:
            return self.error_response("Missing parameter", "hostname and base_dn are required")

        attribute = arguments.get("attribute")  # LDAP filter/attribute string

        value: Dict[str, Any] = {
            "name": name,
            "base_dn": base_dn,
            "response_time": (warn_ms, crit_ms),
        }
        if bind_dn and password:
            value["authentication"] = (bind_dn, ("password", password))
        if port:
            value["port"] = int(port)
        if attribute:
            value["attribute"] = attribute

        result = self._post_rule("active_checks:ldap", repr(value), hostname, folder, description)
        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ LDAP-Check '{name}' für '{hostname}' angelegt.\n"
                f"Base-DN: {base_dn}\n"
                + (f"Beschreibung: {description}\n" if description else "")
                + f"Rule-ID: {rule_id}"
            )
            return [{"type": "text", "text": msg}]
        return self.error_response("LDAP-Check fehlgeschlagen", str(result.get("data", {})))

    async def _create_smb_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        share = arguments.get("share", "")
        smb_host = arguments.get("smb_host", "use_parent_host")
        warn_pct = float(arguments.get("warn_percent", 85.0))
        crit_pct = float(arguments.get("crit_percent", 95.0))
        username = arguments.get("username")
        password = arguments.get("password")
        workgroup = arguments.get("workgroup")
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        if not hostname or not share:
            return self.error_response("Missing parameter", "hostname and share are required")

        value: Dict[str, Any] = {
            "share": share,
            "host": smb_host,
            "levels": (warn_pct, crit_pct),
        }
        if username and password:
            value["auth"] = (username, ("password", password))
        if workgroup:
            value["workgroup"] = workgroup

        result = self._post_rule("active_checks:disk_smb", repr(value), hostname, folder, description)
        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ SMB-Check Share '{share}' für '{hostname}' angelegt.\n"
                f"Warn: {warn_pct}%, Krit: {crit_pct}%\n"
                + (f"Beschreibung: {description}\n" if description else "")
                + f"Rule-ID: {rule_id}"
            )
            return [{"type": "text", "text": msg}]
        return self.error_response("SMB-Check fehlgeschlagen", str(result.get("data", {})))

    async def _create_mkevents_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        ignore_acknowledged = arguments.get("ignore_acknowledged", True)
        show_last_log = arguments.get("show_last_log", "summary")
        remote = arguments.get("remote_ec_host")
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        if not hostname:
            return self.error_response("Missing parameter", "hostname is required")

        value: Dict[str, Any] = {
            "hostspec": ["$HOSTNAME$", "$HOSTADDRESS$", "$HOSTALIAS$"],
            "ignore_acknowledged": ignore_acknowledged,
            "remote": ("socket", remote) if remote else None,
            "show_last_log": show_last_log,
        }

        result = self._post_rule("active_checks:mkevents", repr(value), hostname, folder, description)
        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ Event-Console-Check für '{hostname}' angelegt.\n"
                + (f"Beschreibung: {description}\n" if description else "")
                + f"Rule-ID: {rule_id}"
            )
            return [{"type": "text", "text": msg}]
        return self.error_response("mkevents-Check fehlgeschlagen", str(result.get("data", {})))

    async def _create_inventory_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname", "")
        sw_changes = int(arguments.get("sw_changes_state", 0))
        sw_missing = int(arguments.get("sw_missing_state", 0))
        hw_changes = int(arguments.get("hw_changes_state", 0))
        fail_status = int(arguments.get("fail_status", 0))
        status_data = arguments.get("status_data_inventory", True)
        description = arguments.get("description", "")
        folder = self._resolve_folder(hostname, arguments.get("folder"))

        if not hostname:
            return self.error_response("Missing parameter", "hostname is required")

        value: Dict[str, Any] = {
            "sw_changes": sw_changes,
            "sw_missing": sw_missing,
            "hw_changes": hw_changes,
            "fail_status": fail_status,
            "status_data_inventory": status_data,
        }

        result = self._post_rule("active_checks:cmk_inv", repr(value), hostname, folder, description)
        if result.get("success"):
            rule_id = result["data"].get("id", "")
            msg = (
                f"✅ HW/SW-Inventory-Check für '{hostname}' angelegt.\n"
                + (f"Beschreibung: {description}\n" if description else "")
                + f"Rule-ID: {rule_id}"
            )
            return [{"type": "text", "text": msg}]
        return self.error_response("Inventory-Check fehlgeschlagen", str(result.get("data", {})))

    async def _list_active_checks(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = arguments.get("hostname")
        check_type = arguments.get("check_type")

        rulesets = (
            [f"active_checks:{check_type}"]
            if check_type and check_type != "custom"
            else ["custom_checks"] if check_type == "custom" else self._ALL_RULESETS
        )

        lines = ["🔍 **Active Checks**\n"]
        for ruleset in rulesets:
            result = self.client.get("domain-types/rule/collections/all", params={"ruleset_name": ruleset})
            if not result.get("success"):
                continue
            rules = result["data"].get("value", [])
            for rule in rules:
                rule_id = rule.get("id", "")
                ext = rule.get("extensions", {})
                cond = ext.get("conditions", {})
                hosts_in_rule = cond.get("host_name", {}).get("match_on", [])
                if hostname and hostname not in hosts_in_rule:
                    continue
                val_raw = ext.get("value_raw", "")
                props = ext.get("properties", {})
                disabled = props.get("disabled", False)
                status = "🔴 disabled" if disabled else "🟢 active"
                hosts_display = ", ".join(hosts_in_rule) if hosts_in_rule else "all hosts"
                lines.append(
                    f"• [{status}] **{ruleset}** — {hosts_display}\n"
                    f"  ID: {rule_id}\n"
                    f"  Value: `{val_raw[:120]}{'...' if len(val_raw) > 120 else ''}`"
                )

        if len(lines) == 1:
            lines.append("Keine Active-Check-Regeln gefunden.")
        return [{"type": "text", "text": "\n".join(lines)}]

    async def _delete_active_check(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        rule_id = arguments.get("rule_id")
        hostname = arguments.get("hostname")
        service_name = arguments.get("service_name")

        # If hostname given but no rule_id: find matching rules first
        if not rule_id and hostname:
            check_type = arguments.get("check_type")
            rulesets = (
                [f"active_checks:{check_type}"]
                if check_type and check_type != "custom"
                else ["custom_checks"] if check_type == "custom" else self._ALL_RULESETS
            )
            matches = []
            for rs in rulesets:
                res = self.client.get("domain-types/rule/collections/all", params={"ruleset_name": rs})
                if not res.get("success"):
                    continue
                for rule in res["data"].get("value", []):
                    ext = rule.get("extensions", {})
                    hosts = ext.get("conditions", {}).get("host_name", {}).get("match_on", [])
                    if hostname not in hosts:
                        continue
                    if service_name:
                        vr = ext.get("value_raw", "")
                        if service_name.lower() not in vr.lower():
                            continue
                    matches.append((rule.get("id"), rs, ext.get("value_raw", "")))

            if not matches:
                return self.error_response(
                    "Keine Regel gefunden",
                    f"Keine Active-Check-Regel für '{hostname}'"
                    + (f" mit Service '{service_name}'" if service_name else "")
                    + " gefunden.",
                )
            if len(matches) > 1:
                lines = [f"Mehrere Regeln für '{hostname}' gefunden — bitte rule_id angeben:\n"]
                for rid, rs, vr in matches:
                    lines.append(f"• {rs}: {rid}\n  Value: `{vr[:100]}`")
                return [{"type": "text", "text": "\n".join(lines)}]

            rule_id = matches[0][0]

        if not rule_id:
            return self.error_response(
                "Missing parameter",
                "rule_id oder hostname angeben",
            )

        self.client.delete(f"objects/rule/{rule_id}")
        return [{"type": "text", "text": f"✅ Active-Check-Regel '{rule_id}' gelöscht."}]
