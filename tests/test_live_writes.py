"""
Write round-trips against a real CheckMK instance.

The unit tests mock the HTTP client, so they cannot tell whether CheckMK accepts
what a write tool sends. On 2.5 most of the active check creators did not: the
rulesets moved to form specs, whose stored shape -- ("fixed", (warn, crit))
levels, password tuples, cascading choices -- the REST API does not migrate
from the old one. Every tool worked with its required arguments and failed as
soon as an option was set. Each test here therefore creates with the options
filled in, reads the object back, deletes it and checks it is gone.

It is skipped unless LIVE_WRITE_TEST=true and is kept out of CI: it changes the
configuration of the instance it runs against. Point it at a test site only.

    LIVE_WRITE_TEST=true TEST_HOST_NAME=vibemk-test \\
    CHECKMK_SERVER_URL=http://localhost:8055 CHECKMK_SITE=cmk \\
    CHECKMK_USERNAME=cmkadmin CHECKMK_PASSWORD=cmkadmin \\
    python -m pytest tests/test_live_writes.py -v

Everything a test creates is deleted again, but nothing is activated: the
create/delete pairs remain as pending changes on the site.

The Event Console test needs open events from application "vibemk-probe" on
TEST_HOST_NAME; it skips without them. To create some, add an EC rule that
matches that application and write a syslog line into the site's event pipe:

    echo "<10>Oct  3 01:45:01 vibemk-test vibemk-probe: test" > ~/tmp/run/mkeventd/events
"""

import asyncio
import os
import re
import time
from typing import Any, Dict, Iterator, List, Tuple

import pytest

from vibemk.api import CheckMKClient
from vibemk.config import CheckMKConfig
from vibemk.server.dispatch import is_error
from vibemk.server.registry import ToolRegistry

pytestmark = pytest.mark.skipif(
    os.environ.get("LIVE_WRITE_TEST") != "true",
    reason="Live write test requires LIVE_WRITE_TEST=true and a CheckMK test site",
)

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
PROBE = "vibemk-live"


@pytest.fixture(scope="module")
def registry() -> ToolRegistry:
    return ToolRegistry.from_client(CheckMKClient(CheckMKConfig.from_env()))


@pytest.fixture(scope="module")
def host() -> str:
    name = os.environ.get("TEST_HOST_NAME")
    if not name:
        pytest.skip("TEST_HOST_NAME names the host the rules are written for")
    return name


def call(registry: ToolRegistry, name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """Run one tool; return whether it failed and its text."""
    handler = registry.handler_for(name)
    assert handler is not None, f"{name} is declared but not wired"
    content = asyncio.run(handler.handle(name, arguments))
    return is_error(content), "\n".join(part.get("text", "") for part in content if part.get("type") == "text")


def ok(registry: ToolRegistry, name: str, arguments: Dict[str, Any]) -> str:
    failed, text = call(registry, name, arguments)
    assert not failed, f"{name} failed:\n{text}"
    return text


def rule_ids(text: str) -> List[str]:
    return list(dict.fromkeys(UUID.findall(text)))


# Every active check creator, with its options filled in: the defects were in
# the options, so a call with the required arguments alone proves little.
ACTIVE_CHECKS = {
    "http_url": (
        "vibemk_create_http_check",
        {
            "name": f"{PROBE}-http",
            "uri": "/health",
            "port": 8080,
            "ssl": True,
            "expect_string": "ok",
            "expect_regex": "o.",
            "expect_response": "HTTP/1.1 200",
            "method": "POST",
            "onredirect": "follow",
            "timeout": 10,
            "response_time_warn": 1,
            "response_time_crit": 2,
            "extended_perfdata": True,
            "auth_user": "probe",
            "auth_password": "probe-secret",
            "address_family": "ipv4",
        },
    ),
    "http_cert": (
        "vibemk_create_http_check",
        {"name": f"{PROBE}-cert", "cert_mode": True, "cert_days_warn": 30, "cert_days_crit": 14},
    ),
    "tcp": (
        "vibemk_create_tcp_check",
        {
            "port": 443,
            "name": f"{PROBE}-tcp",
            "ssl": True,
            "cert_days_warn": 30,
            "cert_days_crit": 14,
            "expect": "SSH-2.0",
            "refuse_state": "crit",
            "mismatch_state": "warn",
            "timeout": 10,
            "response_time_warn": 1,
            "response_time_crit": 2,
        },
    ),
    "icmp": (
        "vibemk_create_icmp_check",
        {
            "name": f"{PROBE}-icmp",
            "packets": 3,
            "timeout": 10,
            "explicit_address": "127.0.0.1",
            "rta_warn_ms": 200,
            "rta_crit_ms": 500,
            "loss_warn_percent": 20,
            "loss_crit_percent": 50,
            "min_pings": 1,
        },
    ),
    "custom": (
        "vibemk_create_custom_check",
        {"service_description": f"{PROBE}-custom", "command_line": "echo ok", "command_name": "vibemk_live"},
    ),
    "dns": (
        "vibemk_create_dns_check",
        {
            "lookup_hostname": "localhost",
            "dns_server": "127.0.0.1",
            "expected_addresses": "127.0.0.1",
            "expect_all_addresses": True,
            "response_time_warn": 1,
            "response_time_crit": 2,
        },
    ),
    "smtp": (
        "vibemk_create_smtp_check",
        {"name": f"{PROBE}-smtp", "port": 587, "starttls": True, "cert_days_warn": 30, "cert_days_crit": 14},
    ),
    "ftp": ("vibemk_create_ftp_check", {"port": 21, "timeout": 10, "refuse_state": "crit"}),
    "ldap": (
        "vibemk_create_ldap_check",
        {
            "name": f"{PROBE}-ldap",
            "base_dn": "dc=example,dc=com",
            "bind_dn": "cn=probe",
            "password": "probe-secret",
            "port": 636,
            "attribute": "(objectclass=*)",
            "response_time_warn_ms": 500,
            "response_time_crit_ms": 800,
        },
    ),
    "smb": (
        "vibemk_create_smb_check",
        {
            "share": "data",
            "smb_host": "fileserver",
            "warn_percent": 80,
            "crit_percent": 90,
            "username": "probe",
            "password": "probe-secret",
            "workgroup": "WG",
        },
    ),
    "mkevents": (
        "vibemk_create_mkevents_check",
        {"ignore_acknowledged": False, "show_last_log": "details", "remote_ec_host": "127.0.0.1"},
    ),
    "inventory": (
        "vibemk_create_inventory_check",
        {"sw_changes_state": 1, "sw_missing_state": 1, "hw_changes_state": 1, "fail_status": 2},
    ),
}


@pytest.mark.parametrize("case", sorted(ACTIVE_CHECKS))
def test_an_active_check_is_created_listed_and_deleted(registry: ToolRegistry, host: str, case: str) -> None:
    tool, options = ACTIVE_CHECKS[case]
    created = ok(registry, tool, {"hostname": host, **options})
    (rule_id,) = rule_ids(created)
    try:
        assert rule_id in ok(registry, "vibemk_list_active_checks", {"hostname": host})
    finally:
        ok(registry, "vibemk_delete_active_check", {"rule_id": rule_id})
    assert rule_id not in ok(registry, "vibemk_list_active_checks", {"hostname": host})


SERVICE_PARAMS = {
    "memory": (
        "vibemk_set_memory_thresholds",
        {"ram_warn_percent": 90, "ram_crit_percent": 95, "swap_warn_percent": 30, "swap_crit_percent": 50},
    ),
    "interface": ("vibemk_set_interface_params", {"interface_name": "eth0", "expected_speed_mbit": 1000}),
    "process": (
        "vibemk_set_process_thresholds",
        {
            "process_name": f"{PROBE}-process",
            "warn_max": 10,
            "crit_max": 12,
            "warn_min": 1,
            "crit_min": 1,
            "cpu_warn_percent": 80,
            "cpu_crit_percent": 95,
            "single_cpu_warn_percent": 50,
            "single_cpu_crit_percent": 70,
            "cpu_average_min": 5,
            "mem_warn_mb": 1000,
            "mem_crit_mb": 2000,
            "resident_warn_mb": 500,
            "resident_crit_mb": 800,
            "run_discovery": False,
        },
    ),
}


@pytest.mark.parametrize("case", sorted(SERVICE_PARAMS))
def test_a_service_parameter_rule_is_created_and_deleted(registry: ToolRegistry, host: str, case: str) -> None:
    tool, options = SERVICE_PARAMS[case]
    ids = rule_ids(ok(registry, tool, {"hostname": host, **options}))
    assert ids, "the answer names no rule ID to delete"
    try:
        if case == "process":
            listed = ok(registry, "vibemk_list_process_rules", {"hostname": host})
            assert all(rule_id in listed for rule_id in ids)
    finally:
        for rule_id in ids:
            ok(registry, "vibemk_delete_service_param_rule", {"rule_id": rule_id})
    assert not set(ids) & set(rule_ids(ok(registry, "vibemk_list_process_rules", {"hostname": host})))


def test_event_console_events_are_acknowledged_changed_and_deleted(registry: ToolRegistry, host: str) -> None:
    listed = ok(registry, "vibemk_get_events", {"host": host, "application": "vibemk-probe"})
    event_ids = [int(found) for found in re.findall(r"^• \*\*(\d+)\*\*", listed, re.M)]
    if len(event_ids) < 2:
        pytest.skip("needs two open vibemk-probe events on TEST_HOST_NAME, see the module docstring")
    first, second = event_ids[:2]

    ok(registry, "vibemk_acknowledge_event", {"event_id": first, "comment": "vibeMK live test"})
    ok(registry, "vibemk_change_event_state", {"event_id": second, "new_state": "warning"})
    assert f"**{first}** [" in ok(registry, "vibemk_get_events", {"phase": "ack", "host": host})
    assert f"**{second}** [warning]" in ok(registry, "vibemk_get_events", {"phase": "open", "host": host})

    ok(registry, "vibemk_delete_events", {"event_ids": [first]})
    ok(registry, "vibemk_delete_events", {"host": host, "phase": "open"})
    remaining = ok(registry, "vibemk_get_events", {"host": host}) + ok(
        registry, "vibemk_get_events", {"host": host, "phase": "ack"}
    )
    assert f"**{first}**" not in remaining
    assert f"**{second}**" not in remaining


def test_the_agent_bakery_bakes_or_says_why_it_cannot(registry: ToolRegistry, host: str) -> None:
    commercial = ".community" not in ok(registry, "vibemk_get_checkmk_version", {})
    failed, text = call(registry, "vibemk_bake_agents", {})
    if not commercial:
        assert failed
        assert "no agent bakery" in text, "Raw answers 404; the tool has to say what that means"
        return

    assert not failed, text
    for _ in range(60):
        status = ok(registry, "vibemk_baking_status", {})
        if "State: running" not in status:
            break
        time.sleep(2)
    assert "State: finished" in status
    url = ok(registry, "vibemk_download_agent_by_host", {"host_name": host})
    assert "/domain-types/agent/actions/download_by_host/invoke?" in url


@pytest.fixture
def bulk_hosts(registry: ToolRegistry) -> Iterator[List[str]]:
    names = [f"{PROBE}-bulk-1", f"{PROBE}-bulk-2"]
    yield names
    for name in names:
        call(registry, "vibemk_delete_host", {"host_name": name})


def test_hosts_are_created_updated_and_discovered_in_bulk(registry: ToolRegistry, bulk_hosts: List[str]) -> None:
    entries = [{"host_name": name, "folder": "/", "attributes": {"ipaddress": "127.0.0.1"}} for name in bulk_hosts]
    ok(registry, "vibemk_bulk_create_hosts", {"entries": entries})

    updates = [{"host_name": name, "update_attributes": {"alias": f"{name}-alias"}} for name in bulk_hosts]
    ok(registry, "vibemk_bulk_update_hosts", {"entries": updates})
    assert f"{bulk_hosts[0]}-alias" in ok(registry, "vibemk_get_host_config", {"host_name": bulk_hosts[0]})

    started = ok(registry, "vibemk_start_bulk_discovery", {"hostnames": bulk_hosts, "do_full_scan": False})
    (job_id,) = re.findall(r"Job ID: \*\*(\S+)\*\*", started)
    for _ in range(60):
        status = ok(registry, "vibemk_get_bulk_discovery_status", {"job_id": job_id})
        if "State: RUNNING" not in status:
            break
        time.sleep(2)
    assert "State: FINISHED" in status
    # Whether discovery succeeds depends on an agent answering on 127.0.0.1,
    # which a test site need not have. The job has to have run for every host
    # and said how each went -- the status used to read UNKNOWN regardless.
    assert f"Hosts: {len(bulk_hosts)} total" in status
    assert all(f"{name}: discovery" in status for name in bulk_hosts)


def test_service_groups_are_created_updated_and_deleted_in_bulk(registry: ToolRegistry) -> None:
    names = [f"{PROBE.replace('-', '_')}_sg1", f"{PROBE.replace('-', '_')}_sg2"]
    ok(
        registry,
        "vibemk_bulk_create_service_groups",
        {"entries": [{"name": name, "alias": f"{name} alias"} for name in names]},
    )
    try:
        ok(
            registry,
            "vibemk_bulk_update_service_groups",
            {"entries": [{"name": names[0], "attributes": {"alias": "renamed"}}]},
        )
        assert "**Alias:** renamed" in ok(registry, "vibemk_get_service_group", {"name": names[0]})
    finally:
        ok(registry, "vibemk_bulk_delete_service_groups", {"entries": names})
    assert call(registry, "vibemk_get_service_group", {"name": names[0]})[0], "the group is still there"
