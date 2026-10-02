"""
Structural guards for the MCP tool registry.

The catalogue in mcp/tools.py and the dispatch table in mcp/registry.py are
maintained by hand in two different files. These tests keep them in agreement:
a tool the client can see must be callable, and a handler that exists must be
reachable.
"""

import ast
import pathlib
from typing import Dict
from unittest.mock import MagicMock

import pytest

from mcp.registry import ToolRegistry
from mcp.tools import get_all_tools

HANDLERS_DIR = pathlib.Path(__file__).resolve().parent.parent / "handlers"


@pytest.fixture
def registry():
    """A registry over a client that is never actually called."""
    return ToolRegistry.from_client(MagicMock())


def test_registry_exposes_every_wired_name(registry):
    assert "vibemk_get_checkmk_hosts" in registry.tool_names()


def test_registry_returns_none_for_an_unknown_tool(registry):
    assert registry.handler_for("vibemk_not_a_tool") is None


def test_registry_returns_a_handler_with_a_handle_method(registry):
    handler = registry.handler_for("vibemk_get_checkmk_hosts")

    assert hasattr(handler, "handle")


def test_no_tool_is_declared_twice():
    names = [tool["name"] for tool in get_all_tools()]

    duplicates = sorted({name for name in names if names.count(name) > 1})
    assert duplicates == [], f"declared more than once: {duplicates}"


def test_every_declared_tool_has_a_handler(registry):
    declared = {tool["name"] for tool in get_all_tools()}

    unroutable = sorted(name for name in declared if registry.handler_for(name) is None)
    assert unroutable == [], f"advertised to the client but not callable: {unroutable}"


def test_every_handler_is_declared_as_a_tool(registry):
    declared = {tool["name"] for tool in get_all_tools()}

    unreachable = sorted(name for name in registry.tool_names() if name not in declared)
    assert unreachable == [], f"wired to a handler but never advertised: {unreachable}"


def test_every_vibemk_string_literal_in_a_handler_is_a_declared_tool():
    """Catches orphan dispatch branches the registry-level guards cannot see.

    ToolRegistry only ever sees tool names that were actually wired in
    mcp/registry.py, so a handler's own `if tool_name == "vibemk_x": ...`
    dispatch branch for a name nobody registers is invisible to it — the
    branch is simply dead code that no request can ever reach. This walks
    every handlers/*.py module with ast and collects every string constant
    that starts with "vibemk_" (dict keys and comparison literals alike, not
    substrings inside longer help text, since ast.Constant.value is the whole
    literal), then checks each one against the declared catalogue directly.
    """
    declared = {tool["name"] for tool in get_all_tools()}

    orphans: Dict[str, str] = {}
    for path in sorted(HANDLERS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if not node.value.startswith("vibemk_"):
                continue
            if node.value not in declared:
                orphans.setdefault(node.value, path.name)

    assert orphans == {}, f"referenced in a handler but never declared as a tool: {orphans}"


def test_every_tool_has_a_usable_schema():
    for tool in get_all_tools():
        name = tool["name"]
        assert tool.get("description"), f"{name} has no description"

        schema = tool.get("inputSchema")
        assert schema, f"{name} has no inputSchema"
        assert schema.get("type") == "object", f"{name} schema is not an object"

        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            assert required in properties, f"{name} requires '{required}' but never defines it"


def test_every_tool_name_keeps_the_vibemk_prefix():
    """The vibemk_ prefix is the compatibility surface for every existing client.

    Nothing else in the suite pins this: a tool renamed together with its
    registry key would otherwise pass every other structural guard here.
    """
    unprefixed = sorted(tool["name"] for tool in get_all_tools() if not tool["name"].startswith("vibemk_"))
    assert unprefixed == [], f"missing the vibemk_ prefix: {unprefixed}"


def test_repository_root_is_not_a_python_package():
    """The checkout directory must not be importable as a package.

    An __init__.py at the repository root makes pytest treat the checkout
    directory itself as the root package, which only works while that
    directory's name happens to be a valid Python identifier. Renaming the
    repository to anything containing a hyphen then breaks collection of the
    whole suite with "attempted relative import with no known parent package".
    """
    root = pathlib.Path(__file__).resolve().parent.parent

    assert not (root / "__init__.py").exists(), (
        "__init__.py at the repository root couples the test suite to the "
        "checkout directory's name; the importable packages are api, config, "
        "handlers, mcp, utils and checkmk_types"
    )


def test_every_dispatch_branch_belongs_to_the_handler_that_holds_it(registry):
    """Catches a branch that is live code in the wrong module.

    The guard above proves a handler's `vibemk_x` branch names a *declared*
    tool. It cannot see whether the registry routes that tool back to this
    handler. When it routes somewhere else, the branch is unreachable in a
    way that reads as working code: `handlers/monitoring.py` carried a full
    `_delete_downtime` implementation against an endpoint CheckMK does not
    serve, and no request ever reached it because the registry sends
    vibemk_delete_downtime to DowntimeHandler.

    Two handlers implementing one tool is the real defect — whichever loses
    the routing rots silently, and a reader fixing a bug may well fix the
    copy that never runs.
    """
    misrouted: Dict[str, str] = {}
    for path in sorted(HANDLERS_DIR.glob("*.py")):
        module = f"handlers.{path.stem}"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if not node.value.startswith("vibemk_"):
                continue
            handler = registry.handler_for(node.value)
            if handler is None:
                continue  # undeclared or unwired: the guard above owns that case
            routed_to = type(handler).__module__
            if routed_to != module:
                misrouted[node.value] = f"branch in {path.name}, routed to {routed_to}"

    assert misrouted == {}, f"dispatch branches that can never run: {misrouted}"
