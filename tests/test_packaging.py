"""
Guards for the distribution itself.

Everything else in this suite runs against the checkout, where `main.py` is
just a module and the handlers are just directories. None of that exercises
the two things a user who runs `pip install vibemk` actually touches: the
console script, and what ended up inside the wheel.

Both were broken without any test noticing -- the entry point resolved to a
coroutine that was never awaited, and the wheel shipped the local `build/`
artefact, the private `claude.md` notes and the `tmp/` planning files.
"""

import glob
import pathlib
import subprocess
import sys
import zipfile
from importlib.metadata import PackageNotFoundError, version

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

# The only top-level names this project is entitled to in site-packages.
EXPECTED_PACKAGES = frozenset(
    {
        "api",
        "checkmk_types",
        "config",
        "handlers",
        "utils",
        "vibemk_mcp",
    }
)


class TestTheConsoleScript:
    """`vibemk` has to start the server, not return a coroutine."""

    def test_the_entry_point_target_is_callable_synchronously(self):
        """The generated wrapper does `sys.exit(target())` and never awaits.

        An `async def` target therefore exits non-zero with a coroutine repr
        on stdout -- which, for a stdio MCP server, is malformed framing on
        the channel the client is parsing.
        """
        import inspect

        from vibemk_mcp.cli import cli

        assert not inspect.iscoroutinefunction(cli), "the console script target must not be a coroutine function"

    def test_the_checkout_shim_still_works(self):
        """`python main.py` is what every configuration example uses."""
        import main

        assert main.cli is not None
        assert main.parse_arguments(["--transport", "http"]).transport == "http"


class TestTheLicence:
    """The GPL is only a licence grant if its terms are actually present."""

    def test_the_licence_carries_the_operative_terms(self):
        """The file used to stop after the section 0 definitions.

        It ended with "END OF TERMS AND CONDITIONS" having granted nothing,
        which is also why GitHub classified the repository as "Other" rather
        than GPL-3.0.
        """
        text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")

        # The headings of the sections that do the actual work.
        for heading in (
            "1. Source Code.",
            "2. Basic Permissions.",
            "4. Conveying Verbatim Copies.",
            "5. Conveying Modified Source Versions.",
            "11. Patents.",
            "15. Disclaimer of Warranty.",
            "16. Limitation of Liability.",
        ):
            assert heading in text, f"LICENSE is missing section: {heading}"

    def test_the_licence_ends_after_the_terms(self):
        text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")

        assert text.index("END OF TERMS AND CONDITIONS") > text.index("15. Disclaimer of Warranty.")


@pytest.fixture(scope="session")
def wheel(tmp_path_factory):
    """Build the wheel once; hand back its paths and its entry points.

    Reading the entry point out of the built artefact rather than out of
    pyproject.toml is both the stronger check -- it is what setuptools
    actually produced -- and the portable one: tomllib only exists from
    Python 3.11, and this project supports 3.10.
    """
    pytest.importorskip("build", reason="python-build is needed to inspect the distribution")

    outdir = tmp_path_factory.mktemp("dist")
    completed = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(outdir), str(PROJECT_ROOT)],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.fail(f"wheel build failed:\n{completed.stdout}\n{completed.stderr}")

    wheels = glob.glob(str(outdir / "*.whl"))
    assert wheels, "the build produced no wheel"

    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
        declared = [name for name in names if name.endswith("entry_points.txt")]
        entry_points = archive.read(declared[0]).decode() if declared else ""

    return {"names": names, "entry_points": entry_points}


@pytest.fixture(scope="session")
def built_wheel(wheel):
    """Just the paths, for the tests that only care what is in the archive."""
    return wheel["names"]


class TestTheShippedEntryPoint:
    """What `pip install` wires the `vibemk` command to."""

    def test_the_wheel_declares_the_console_script(self, wheel):
        assert "vibemk = vibemk_mcp.cli:cli" in wheel["entry_points"], wheel["entry_points"]

    def test_the_target_module_is_actually_in_the_wheel(self, wheel):
        """The original target, `main:cli`, never shipped.

        `main.py` is a loose top-level module and packages.find only collects
        packages, so `vibemk` died with ModuleNotFoundError before it could
        even reach the coroutine problem. Declaring an entry point is not the
        same as shipping what it points at.
        """
        target = wheel["entry_points"].split("vibemk = ")[1].split("\n")[0].strip()
        module_path = target.split(":")[0].replace(".", "/") + ".py"

        assert module_path in wheel["names"], f"{module_path} is declared but not packaged"


class TestTheWheel:
    """What a `pip install` puts on someone else's machine."""

    def test_it_claims_only_the_packages_it_owns(self, built_wheel):
        """`include = ["*"]` handed this project every directory in the tree.

        Four of those names -- api, config, handlers, utils -- are generic
        enough to collide with unrelated distributions in the same
        environment, and three more were never packages at all.
        """
        tops = {name.split("/")[0] for name in built_wheel}
        tops = {top for top in tops if not top.endswith(".dist-info")}

        assert tops == set(EXPECTED_PACKAGES), f"unexpected top-level entries: {sorted(tops - EXPECTED_PACKAGES)}"

    def test_it_does_not_ship_the_private_development_notes(self, built_wheel):
        """`claude.md` is gitignored as private; package-data shipped it anyway."""
        leaked = [name for name in built_wheel if name.endswith("claude.md")]

        assert leaked == [], f"private notes in the wheel: {leaked}"

    def test_it_does_not_ship_the_local_build_artefact(self, built_wheel):
        """A stale `build/lib/...` tree was being packaged recursively."""
        nested = [name for name in built_wheel if name.startswith("build/")]

        assert nested == [], f"local build artefact in the wheel: {nested[:5]}"

    def test_it_does_not_ship_scratch_directories(self, built_wheel):
        """tmp/plan.md and tmp/current_state.md are working notes, not product."""
        scratch = [name for name in built_wheel if name.startswith(("tmp/", "examples/", "scripts/"))]

        assert scratch == [], f"scratch files in the wheel: {scratch}"

    def test_it_marks_itself_as_typed(self, built_wheel):
        """The project is mypy-strict; consumers should get the annotations.

        Without a py.typed marker PEP 561 tells type checkers to ignore every
        annotation in the package.
        """
        markers = [name for name in built_wheel if name.endswith("py.typed")]

        assert markers, "no py.typed marker in the wheel"


class TestTheDistributionMetadata:
    def test_the_installed_version_matches_what_the_server_advertises(self):
        """Guards the pyproject -> config.version wiring.

        This used to look up "vibemk-mcp", which is not the name the project
        publishes, so it skipped on every run including a correctly installed
        one -- a green test that never executed.
        """
        from config import MCPConfig

        try:
            installed = version("vibemk")
        except PackageNotFoundError:
            pytest.skip("package is not installed; nothing to compare the handshake against")

        assert MCPConfig().version == installed
