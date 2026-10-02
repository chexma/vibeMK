"""
Every action a workflow runs is pinned to a full commit SHA

A tag such as @v7 is a pointer its owner can move. Whoever controls the
action's repository -- or has stolen access to it -- can point the tag at new
code, and the next run executes it with this repository's token. A commit SHA
cannot be moved. The version stays readable in a trailing comment, which is
also what Dependabot reads and rewrites when it updates the pin.
"""

import pathlib
import re

WORKFLOWS = pathlib.Path(__file__).resolve().parent.parent / ".github" / "workflows"

USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>\S+)(?P<rest>.*)$")
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"^\s+#\s*v\d+(\.\d+)*\s*$")


def _uses_lines():
    for workflow in sorted(WORKFLOWS.glob("*.y*ml")):
        for number, line in enumerate(workflow.read_text().splitlines(), start=1):
            match = USES.match(line)
            if match:
                yield f"{workflow.name}:{number}", match.group("ref"), match.group("rest")


def test_there_are_workflows_to_check():
    assert list(_uses_lines()), "no `uses:` found -- the guard below would pass vacuously"


def test_every_action_is_pinned_to_a_commit_sha():
    unpinned = [
        f"{where}: {ref}"
        for where, ref, _ in _uses_lines()
        # Local actions (./path) and container images are not fetched by tag.
        if not ref.startswith(("./", "docker://")) and not PINNED.match(ref)
    ]
    assert not unpinned, "Pin to a full commit SHA, with the version in a comment:\n" + "\n".join(unpinned)


def test_every_pin_names_its_version():
    unnamed = [
        f"{where}: {ref}" for where, ref, rest in _uses_lines() if PINNED.match(ref) and not VERSION_COMMENT.match(rest)
    ]
    assert not unnamed, "Add the version as a trailing comment, e.g. `# v7.0.1`:\n" + "\n".join(unnamed)
