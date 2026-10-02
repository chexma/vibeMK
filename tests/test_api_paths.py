"""
Tests for api/paths.py

A value from a tool argument must fill exactly one segment of the API path,
whatever characters it contains.
"""

import re
from pathlib import Path

import pytest

from vibemk.api.paths import UnsafePathError, check_endpoint, path_segment

HANDLERS = Path(__file__).resolve().parent.parent / "src" / "vibemk" / "handlers"


class TestPathSegment:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("myhost", "myhost"),
            ("web-01.example.com", "web-01.example.com"),
            ("~linux~web", "~linux~web"),
            ("checkgroup_parameters:cpu_load", "checkgroup_parameters%3Acpu_load"),
            ("x/../../objects/user_config/admin", "x%2F..%2F..%2Fobjects%2Fuser_config%2Fadmin"),
            ("x?effective_attributes=true", "x%3Feffective_attributes%3Dtrue"),
            ("x#frag", "x%23frag"),
            ("my host", "my%20host"),
            (42, "42"),
        ],
    )
    def test_value_stays_in_one_segment(self, value, expected):
        assert path_segment(value) == expected

    @pytest.mark.parametrize("value", ["", ".", ".."])
    def test_navigation_and_empty_values_are_refused(self, value):
        with pytest.raises(UnsafePathError):
            path_segment(value)


class TestCheckEndpoint:
    @pytest.mark.parametrize(
        "endpoint",
        [
            "version",
            "objects/host_config/myhost",
            "objects/folder_config/~linux~web/collections/hosts",
            "objects/host_config/x%2F..%2Fy",
        ],
    )
    def test_ordinary_endpoints_pass(self, endpoint):
        check_endpoint(endpoint)

    @pytest.mark.parametrize(
        "endpoint",
        [
            "objects/host_config/../user_config/admin",
            "objects/host_config/%2e%2e/user_config/admin",
            "objects/host_config/./x",
            "objects/host_config/x?y=1",
            "objects/host_config/x#y",
        ],
    )
    def test_navigation_query_and_fragment_are_refused(self, endpoint):
        with pytest.raises(UnsafePathError):
            check_endpoint(endpoint)

    def test_client_refuses_before_sending(self, mock_config):
        from vibemk.api.client import CheckMKClient

        client = CheckMKClient(mock_config, skip_url_detection=True)
        with pytest.raises(UnsafePathError):
            client.request("objects/host_config/../user_config/admin")


class TestHandlersEncodeTheirPathValues:
    """Structural guard: a new endpoint that interpolates a raw value fails here."""

    # Values encoded on the line before, by hand, for a reason stated there.
    PRE_ENCODED = {"encoded_service"}

    def test_no_raw_interpolation_in_object_paths(self):
        offenders = []
        for source in sorted(HANDLERS.glob("*.py")):
            for number, line in enumerate(source.read_text().splitlines(), start=1):
                for literal in re.findall(r'f"objects/[^"]*"', line):
                    for field in re.findall(r"\{([^}]*)\}", literal):
                        if field.startswith("path_segment(") or field in self.PRE_ENCODED:
                            continue
                        offenders.append(f"{source.name}:{number}: {{{field}}}")
        assert not offenders, "Wrap path values in path_segment():\n" + "\n".join(offenders)
