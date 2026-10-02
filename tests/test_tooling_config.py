"""
Guards for the project's own tool configuration.

A configuration file that is present but ignored is worse than none: it
reads as a decision that was made, so nobody checks whether it took effect.
This project had that twice over -- a `pytest.ini` carrying the section
header `[tool:pytest]`, which only setup.cfg understands, which meant every
option in it was dropped; and because that file existed, it also shadowed
the `[tool.pytest.ini_options]` table in pyproject.toml, so neither had any
effect. The suite ran in asyncio strict mode while both files asked for
auto, with `--strict-markers` never applied and six declared markers never
registered.

These tests assert that the configuration pytest is actually running under
is the one the repository declares.
"""

import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Files pytest would prefer over pyproject.toml if any of them existed.
# Listed in pytest's own precedence order.
SHADOWING_FILES = ("pytest.ini", ".pytest.ini", "tox.ini", "setup.cfg")


class TestThePytestConfigurationIsTheOneWeDeclared:
    def test_the_active_config_file_is_pyproject(self, request):
        """Not merely that pyproject has a pytest table -- that it is in use."""
        inipath = request.config.inipath

        assert inipath is not None, "pytest found no configuration file at all"
        assert inipath.name == "pyproject.toml", f"pytest is configured by {inipath.name}, not pyproject.toml"

    def test_nothing_in_the_repository_shadows_it(self):
        """pytest.ini, tox.ini and setup.cfg all outrank pyproject.toml.

        Adding one of them back silently demotes the pyproject table, which
        is exactly how the previous configuration became inert.
        """
        present = [name for name in SHADOWING_FILES if (PROJECT_ROOT / name).exists()]

        assert present == [], f"these take precedence over pyproject.toml: {present}"

    def test_async_tests_run_in_auto_mode(self, request):
        """Under strict mode an unmarked async test is skipped, not failed.

        That is the quiet-green failure mode this suite keeps running into,
        so the setting is worth asserting rather than assuming.
        """
        assert request.config.getini("asyncio_mode") == "auto"

    def test_unknown_markers_are_an_error(self, request):
        """--strict-markers turns a typo in a marker name into a failure."""
        assert request.config.getoption("strict_markers") is True
