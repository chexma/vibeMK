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

    def test_pyproject_points_the_script_at_that_target(self):
        """The declaration and the function cannot drift apart silently."""
        import tomllib

        with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
            pyproject = tomllib.load(handle)

        assert pyproject["project"]["scripts"]["vibemk"] == "vibemk_mcp.cli:cli"

    def test_the_entry_point_lives_inside_a_shipped_package(self):
        """A top-level `main.py` is never in the wheel, so `main:cli` could
        not resolve at all -- `vibemk` died with ModuleNotFoundError before it
        ever reached the coroutine problem."""
        import tomllib

        with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
            pyproject = tomllib.load(handle)

        module = pyproject["project"]["scripts"]["vibemk"].split(":")[0]

        assert module.split(".")[0] in EXPECTED_PACKAGES, f"{module} is not inside a packaged module"

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
def built_wheel(tmp_path_factory):
    """Build the wheel once and hand back the paths it contains."""
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
        return archive.namelist()


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
