"""
Structural guards for the MCP tool registry.

The catalogue in mcp/tools.py and the dispatch table in mcp/registry.py are
maintained by hand in two different files. These tests keep them in agreement:
a tool the client can see must be callable, and a handler that exists must be
reachable.
"""

import ast
import inspect
import itertools
import pathlib
import re
import tokenize
from typing import Dict
from unittest.mock import MagicMock

import pytest

from vibemk.server.registry import ToolRegistry
from vibemk.server.tools import get_all_tools

HANDLERS_DIR = pathlib.Path(__file__).resolve().parent.parent / "src" / "vibemk" / "handlers"


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
        "handlers, mcp and utils"
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
        module = f"vibemk.handlers.{path.stem}"
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


def test_every_registered_tool_is_dispatched_by_its_handler(registry):
    """A handler can be wired for a tool and still not act on it.

    The registry maps a name to a handler instance; whether that handler's
    own `handle()` has a branch for the name is a separate question. When a
    handler is replaced wholesale and loses a branch, the tool stays
    advertised and stays routed, and answers "Unknown tool" at runtime --
    which no registry-level check can see.
    """
    missing = {}
    for name in sorted(registry.tool_names()):
        handler = registry.handler_for(name)
        module = pathlib.Path(inspect.getfile(type(handler)))
        if f'"{name}"' not in module.read_text():
            missing[name] = module.name

    assert missing == {}, f"routed to a handler that never mentions them: {missing}"


class TestEveryToolIsClassified:
    """Annotations are a safety signal, so they may not be guessed.

    A host decides from `readOnlyHint` and `destructiveHint` whether a call
    needs a confirmation prompt. A tool that nobody classified falls back to
    "destructive", which is the safe reading but also a lie about a harmless
    one -- so the catalogue and the classification have to stay in step.
    """

    def test_each_tool_is_in_exactly_one_bucket(self):
        from vibemk.server.annotations import DESTRUCTIVE, READ_ONLY, SAFE_WRITES

        declared = {tool["name"] for tool in get_all_tools()}
        buckets = (READ_ONLY, SAFE_WRITES, DESTRUCTIVE)

        unclassified = sorted(name for name in declared if not any(name in b for b in buckets))
        assert unclassified == [], f"no behaviour declared for: {unclassified}"

        twice = sorted(name for name in declared if sum(name in b for b in buckets) > 1)
        assert twice == [], f"classified more than once: {twice}"

    def test_no_classification_names_a_tool_that_is_gone(self):
        from vibemk.server.annotations import DESTRUCTIVE, READ_ONLY, SAFE_WRITES

        declared = {tool["name"] for tool in get_all_tools()}
        stale = sorted((READ_ONLY | SAFE_WRITES | DESTRUCTIVE) - declared)

        assert stale == [], f"classified but no longer declared: {stale}"

    def test_a_read_only_tool_never_claims_to_be_destructive(self):
        from vibemk.server.annotations import annotations_for

        for tool in get_all_tools():
            hints = annotations_for(tool["name"])
            if hints.get("readOnlyHint"):
                assert not hints.get("destructiveHint"), tool["name"]

    def test_every_tool_carries_a_title_and_annotations(self):
        for tool in get_all_tools():
            assert tool.get("title"), f"{tool['name']} has no title"
            assert tool.get("annotations"), f"{tool['name']} has no annotations"


class TestStructuredOutput:
    """A declared output schema has to have something behind it.

    The specification lets a client validate structuredContent against the
    schema a tool declares, so a schema with no handler filling it is worse
    than none at all.
    """

    def test_every_output_schema_belongs_to_a_declared_tool(self):
        from vibemk.server.schemas import OUTPUT_SCHEMAS

        declared = {tool["name"] for tool in get_all_tools()}
        orphans = sorted(set(OUTPUT_SCHEMAS) - declared)

        assert orphans == [], f"output schema for a tool that does not exist: {orphans}"

    def test_a_tool_with_an_output_schema_only_reads(self):
        """Structured output is for results a model works with, not for writes."""
        from vibemk.server.annotations import READ_ONLY
        from vibemk.server.schemas import OUTPUT_SCHEMAS

        writes = sorted(name for name in OUTPUT_SCHEMAS if name not in READ_ONLY)
        assert writes == [], f"output schema on a tool that writes: {writes}"

    def test_each_output_schema_is_a_valid_json_schema(self):
        import jsonschema

        from vibemk.server.schemas import OUTPUT_SCHEMAS

        for schema in OUTPUT_SCHEMAS.values():
            jsonschema.Draft202012Validator.check_schema(schema)


class TestASchemaIsAlwaysHonoured:
    """A declared output schema binds every successful answer, not the happy one.

    The SDK refuses a result that has an output schema and no structured
    content -- "has an output schema but did not return structured content" --
    so an empty list or a fallback path that answers in prose alone breaks the
    tool for every client. This was found by running against an instance with
    no hosts, which is exactly the path nobody exercises.
    """

    @pytest.mark.asyncio
    async def test_an_empty_host_list_still_carries_structured_content(self, mock_checkmk_client):
        from vibemk.handlers.hosts import HostHandler
        from vibemk.server.dispatch import is_error, structured_of

        mock_checkmk_client.get.return_value = {"success": True, "data": {"value": []}}

        content = await HostHandler(mock_checkmk_client).handle("vibemk_get_checkmk_hosts", {})

        assert not is_error(content), "an empty result is not a failure"
        assert structured_of(content) == {"total": 0, "hosts": []}

    @pytest.mark.asyncio
    async def test_no_pending_changes_still_carries_structured_content(self, mock_checkmk_client):
        from vibemk.handlers.configuration import ConfigurationHandler
        from vibemk.server.dispatch import is_error, structured_of

        mock_checkmk_client.get.return_value = {"success": True, "data": {"value": []}}

        content = await ConfigurationHandler(mock_checkmk_client).handle("vibemk_get_pending_changes", {})

        assert not is_error(content)
        assert structured_of(content) == {"count": 0, "changes": []}

    @pytest.mark.asyncio
    async def test_a_state_the_mapping_does_not_know_is_reported_as_unknown(self, mock_checkmk_client):
        """The prose may say UNKNOWN(7); the structured value may not."""
        from vibemk.handlers.hosts import HostHandler
        from vibemk.server.dispatch import structured_of

        mock_checkmk_client.get.return_value = {
            "success": True,
            "data": {"value": [{"id": "web01", "extensions": {"state": 7}}]},
        }

        content = await HostHandler(mock_checkmk_client).handle("vibemk_get_checkmk_hosts", {})

        assert structured_of(content)["hosts"][0]["state"] == "UNKNOWN"

    def test_structured_payloads_satisfy_their_schema(self):
        """Spot-check the shapes the handlers build against what they declare."""
        import jsonschema

        from vibemk.server.schemas import HOST_LIST, HOST_STATUS, PENDING_CHANGES

        jsonschema.validate({"total": 0, "hosts": []}, HOST_LIST)
        jsonschema.validate({"count": 0, "changes": []}, PENDING_CHANGES)
        jsonschema.validate(
            {"host_name": "web01", "state": "UNKNOWN", "state_code": -1, "is_hard_state": False},
            HOST_STATUS,
        )


class TestTheCatalogueIsInEnglish:
    """CLAUDE.md requires English for user-facing text.

    The catalogue is where that matters most: unlike an error message, which
    a user sees only when something goes wrong, every description here is
    read by every client and model that connects. Thirty-one of them were in
    German, next to a hundred and thirty-two German field descriptions, so
    one tool offered "🏓 ICMP/PING-Check für einen Host anlegen" and the next
    "🖥️ List hosts".

    An umlaut or an eszett is the cheap, near-certain signal: no English
    string in this project has one. It is not enough on its own, though:
    "Neues Thema" and "Warn-Schwelle in Millisekunden (z.B. 500)" have
    neither, and short field descriptions like these outlived the first
    sweep. So a handful of common German words that are not English words
    count as well.
    """

    GERMAN_LETTERS = "äöüÄÖÜß"
    GERMAN_WORDS = re.compile(
        r"\b(oder|und|wenn|nicht|keine?|alle|heute|verwenden|aktivieren|aktualisieren|ignorieren"
        r"|quittier\w*|Quittier\w*|Neue[rsn]?|Pflicht|gesetzt|Beschreibung|weitere|gefunden"
        r"|Erwartete[rn]?|Krit|Ziel)\b|Schwelle|z\.B\."
    )

    def _offenders(self, text: str) -> str:
        found = {c for c in text if c in self.GERMAN_LETTERS}
        found |= {m.group(0) for m in self.GERMAN_WORDS.finditer(text)}
        return ", ".join(sorted(found))

    def test_no_tool_description_is_german(self):
        guilty = {
            tool["name"]: self._offenders(tool.get("description", ""))
            for tool in get_all_tools()
            if self._offenders(tool.get("description", ""))
        }

        assert guilty == {}, f"German in tool descriptions: {guilty}"

    def test_no_tool_title_is_german(self):
        guilty = [tool["name"] for tool in get_all_tools() if self._offenders(tool.get("title", ""))]

        assert guilty == [], f"German in tool titles: {guilty}"

    def test_no_input_schema_field_is_german(self):
        """The field descriptions are what a model reads to fill in arguments."""
        guilty = []
        for tool in get_all_tools():
            properties = tool.get("inputSchema", {}).get("properties") or {}
            for field, spec in properties.items():
                if isinstance(spec, dict) and self._offenders(str(spec.get("description", ""))):
                    guilty.append(f"{tool['name']}.{field}")

        assert guilty == [], f"German in input schema descriptions: {guilty}"

    def test_no_handler_response_is_german(self):
        """What a tool answers is user-facing too, and is not in the catalogue.

        Docstrings and comments are left out: they are read by developers,
        and the language policy for them is enforced in review.
        """
        guilty = []
        # Absolute: a path relative to the working directory found nothing
        # once the handlers moved, and an empty loop passes.
        sources = sorted(HANDLERS_DIR.glob("*.py"))
        assert sources, f"no handler sources under {HANDLERS_DIR}"
        for path in sources:
            with path.open("rb") as source:
                tokens = [t for t in tokenize.tokenize(source.readline) if t.type not in self._INSIGNIFICANT]
            for previous, token in itertools.pairwise(tokens):
                if token.type not in self._STRING_TOKENS:
                    continue
                # A string that opens a statement is a docstring
                if token.type == tokenize.STRING and previous.type in self._STATEMENT_START:
                    continue
                offenders = self._offenders(token.string)
                if offenders:
                    guilty.append(f"{path}:{token.start[0]}: {offenders}")

        assert guilty == [], "German in handler responses:\n" + "\n".join(guilty)

    _STRING_TOKENS = {tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING)}
    _INSIGNIFICANT = {tokenize.COMMENT, tokenize.NL}
    _STATEMENT_START = {tokenize.ENCODING, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT}

    def test_no_description_names_a_real_host(self):
        """Four descriptions used production host names as their examples.

        They shipped in a public repository, in the catalogue every client
        downloads. Examples belong in the reserved example.com space.
        """
        import re

        real_host = re.compile(r"\b[a-z0-9-]+\.(?!example\.(com|org|net)\b)[a-z]{2,}\.[a-z]{2,}\b")
        guilty = {}
        for tool in get_all_tools():
            texts = [tool.get("description", "")]
            properties = tool.get("inputSchema", {}).get("properties") or {}
            texts += [str(spec.get("description", "")) for spec in properties.values() if isinstance(spec, dict)]
            found = {m.group(0) for text in texts for m in real_host.finditer(text)}
            if found:
                guilty[tool["name"]] = sorted(found)

        assert guilty == {}, f"non-example host names in the catalogue: {guilty}"
