"""
Read-only smoke test against a real CheckMK instance.

The rest of the suite mocks the HTTP client, which means it cannot tell whether
CheckMK actually serves a path the code calls. Three endpoints turned out to be
dead — `objects/service/{host}/{description}` answers 404, POSTing to the
show_service action answers 405, and `domain-types/bi_rule/actions/livestatus_query`
has never existed — and none of them was caught by a test. They were found by an
LLM driving the server against live data.

This test closes that gap for the read-only surface: it calls each listed tool
once and fails on the signatures of a wrong endpoint.

It is skipped unless LIVE_SMOKE_TEST=true and is deliberately kept out of CI:
it needs credentials for a real instance, and CI has none.

    LIVE_SMOKE_TEST=true python -m pytest tests/test_live_smoke.py -v

Every tool listed here was checked to make no POST, PUT or DELETE call. The
list is explicit rather than derived from tool names, because a heuristic that
misjudges one tool writes to somebody's production monitoring.
"""

import asyncio
import os
import re
from typing import Any, Dict, Optional

import pytest

from api import CheckMKClient
from config import CheckMKConfig
from mcp.registry import ToolRegistry

pytestmark = pytest.mark.skipif(
    os.environ.get("LIVE_SMOKE_TEST") != "true",
    reason="Live smoke test requires LIVE_SMOKE_TEST=true and a reachable CheckMK",
)

# Phrases that mean the endpoint behind a tool is wrong. They are matched only
# against a handler's *error envelope*, never against its payload: a check
# output legitimately says things like "file not found", and matching that
# would flag a perfectly working tool. Handlers mark errors with a leading ❌.
BROKEN_ENDPOINT_SIGNS = (
    "not found",
    "method not allowed",
    "http 404",
    "http 405",
    "retrieval failed",
    "unexpected response format",
)

# These tools exist to probe endpoints and report which answer. "not found" is
# their output, not their failure, so the check above cannot apply to them.
# They are still called, to catch an outright crash.
ENDPOINT_PROBES = (
    "vibemk_debug_url_detection",
    "vibemk_debug_api_endpoints",
    "vibemk_debug_permissions",
    "vibemk_debug_checkmk_connection",
)

# Tools taking no arguments. Verified free of POST/PUT/DELETE.
NO_ARGUMENT_TOOLS = (
    "vibemk_get_checkmk_version",
    "vibemk_get_checkmk_hosts",
    "vibemk_get_current_problems",
    "vibemk_get_folders",
    "vibemk_get_host_groups",
    "vibemk_get_service_groups",
    "vibemk_list_service_groups",
    "vibemk_get_host_tags",
    "vibemk_get_timeperiods",
    "vibemk_get_users",
    "vibemk_get_contact_groups",
    "vibemk_list_user_roles",
    "vibemk_get_passwords",
    "vibemk_get_pending_changes",
    "vibemk_get_notification_rules",
    "vibemk_get_downtimes",
    "vibemk_list_downtimes",
    "vibemk_get_active_downtimes",
    "vibemk_get_comments",
    "vibemk_debug_checkmk_connection",
    "vibemk_debug_url_detection",
    "vibemk_debug_api_endpoints",
    "vibemk_debug_permissions",
    "vibemk_get_example_rule_structures",
    "vibemk_find_host_grouping_rulesets",
)

# Tools needing a host that exists on the instance.
HOST_TOOLS = (
    "vibemk_get_host_status",
    "vibemk_get_host_details",
    "vibemk_get_host_config",
    "vibemk_get_host_effective_attributes",
    "vibemk_get_checkmk_services",
    "vibemk_validate_host_config",
    "vibemk_check_host_downtime_status",
)

# Tools needing a host and one of its services.
SERVICE_TOOLS = ("vibemk_get_service_status",)


@pytest.fixture(scope="module")
def registry() -> ToolRegistry:
    return ToolRegistry.from_client(CheckMKClient(CheckMKConfig.from_env()))


async def call(registry: ToolRegistry, name: str, arguments: Dict[str, Any]) -> str:
    handler = registry.handler_for(name)
    assert handler is not None, f"{name} is declared but not wired"
    content = await handler.handle(name, arguments)
    return "\n".join(part.get("text", "") for part in content)


def looks_broken(tool: str, answer: str) -> Optional[str]:
    """Return the sign of a wrong endpoint, or None.

    Only the error envelope is inspected. A handler that succeeded returns
    monitoring data, and monitoring data is full of words like "not found".
    """
    if tool in ENDPOINT_PROBES:
        return None
    if not answer.lstrip().startswith("❌"):
        return None
    lowered = answer.lower()
    for sign in BROKEN_ENDPOINT_SIGNS:
        if sign in lowered:
            return sign
    return None


@pytest.fixture(scope="module")
def a_host(registry: ToolRegistry) -> str:
    """A host name taken from the instance itself."""
    answer = asyncio.run(call(registry, "vibemk_get_checkmk_hosts", {}))
    # Lines read "🖥️ hostname (UP)". A CheckMK host name need not be an FQDN,
    # so a dot is not required here.
    hosts = re.findall(r"^\S+ ([A-Za-z0-9][A-Za-z0-9._-]*) \(", answer, re.M)
    if not hosts:
        pytest.skip(f"no host could be read from the instance: {answer[:200]}")
    return str(hosts[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", NO_ARGUMENT_TOOLS)
async def test_tool_without_arguments_reaches_a_real_endpoint(registry: ToolRegistry, tool: str) -> None:
    answer = await call(registry, tool, {})

    sign = looks_broken(tool, answer)
    assert sign is None, f"{tool} looks like a dead endpoint ({sign}): {answer[:300]}"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", HOST_TOOLS)
async def test_host_tool_reaches_a_real_endpoint(registry: ToolRegistry, tool: str, a_host: str) -> None:
    answer = await call(registry, tool, {"host_name": a_host})

    sign = looks_broken(tool, answer)
    assert sign is None, f"{tool} looks like a dead endpoint ({sign}): {answer[:300]}"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", SERVICE_TOOLS)
async def test_service_tool_reaches_a_real_endpoint(registry: ToolRegistry, tool: str, a_host: str) -> None:
    # Every CheckMK host carries this one, so no discovery round trip is needed.
    answer = await call(registry, tool, {"host_name": a_host, "service_description": "Check_MK"})

    sign = looks_broken(tool, answer)
    assert sign is None, f"{tool} looks like a dead endpoint ({sign}): {answer[:300]}"


@pytest.mark.asyncio
async def test_problems_carry_their_check_output(registry: ToolRegistry) -> None:
    """The regression that started this file.

    Asked what is wrong, the server used to answer with names and states only,
    leaving a caller no way to learn why — which is what sent an agent around
    the server and into the API directly.
    """
    answer = await call(registry, "vibemk_get_current_problems", {})

    if "No current problems" in answer:
        pytest.skip("nothing is failing on this instance right now")
    assert "since " in answer, f"problems carry no timestamp: {answer[:300]}"
    lines = [line for line in answer.splitlines() if line.startswith("    ") and not line.strip().startswith("since")]
    assert lines, f"problems carry no check output: {answer[:300]}"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", NO_ARGUMENT_TOOLS)
async def test_tool_does_not_crash_the_checkmk_server(registry: ToolRegistry, tool: str) -> None:
    """A 500 means the path exists and CheckMK broke serving it.

    That is not this project's defect, but it does mean the tool is unusable on
    that instance, and it is worth knowing rather than discovering through an
    agent. CheckMK writes a crash report and returns its id; the assertion
    message carries it so it can be looked up or filed.
    """
    answer = await call(registry, tool, {})

    if not answer.lstrip().startswith("❌"):
        return
    assert "500" not in answer, f"{tool}: CheckMK returned a server error — {answer[:300]}"
