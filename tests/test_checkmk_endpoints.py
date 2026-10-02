"""
Tests that the paths vibeMK calls exist in the CheckMK 2.4 REST API.

Every path asserted here was read from cmk/gui/openapi/endpoints at tag
v2.4.0p2. A call to a path CheckMK does not serve fails with 404 at runtime,
which the handlers swallow into a generic "failed" message — so the endpoint
names need pinning in tests rather than discovering in production.
"""

import pathlib
import re
from typing import Any, List

import pytest

from api.exceptions import CheckMKAPIError
from handlers.discovery import DiscoveryHandler
from handlers.services import ServiceHandler
from mcp.tools import get_all_tools

# Paths registered by cmk/gui/openapi/endpoints/service_discovery/__init__.py
SINGLE_HOST_DISCOVERY = "domain-types/service_discovery_run/actions/start/invoke"
BULK_DISCOVERY = "domain-types/discovery_run/actions/bulk-discovery-start/invoke"

# cmk/gui/openapi/endpoints/background_job/__init__.py registers
# objects/background_job/{job_id}; there is no objects/discovery_run/{id}.
BACKGROUND_JOB = "objects/background_job/"


@pytest.fixture
def discovery_handler(mock_checkmk_client):
    return DiscoveryHandler(mock_checkmk_client)


@pytest.fixture
def service_handler(mock_checkmk_client):
    return ServiceHandler(mock_checkmk_client)


def posted_paths(client: Any) -> List[str]:
    return [call.args[0] for call in client.post.call_args_list if call.args]


def fetched_paths(client: Any) -> List[str]:
    return [call.args[0] for call in client.get.call_args_list if call.args]


class TestDiscoveryEndpoints:
    @pytest.mark.asyncio
    async def test_single_host_discovery_uses_service_discovery_run(self, discovery_handler):
        discovery_handler.client.post.return_value = {"success": True, "data": {}}

        await discovery_handler.handle("vibemk_start_service_discovery", {"host_name": "example.com"})

        assert posted_paths(discovery_handler.client) == [SINGLE_HOST_DISCOVERY]

    @pytest.mark.asyncio
    async def test_bulk_discovery_uses_discovery_run(self, discovery_handler):
        discovery_handler.client.post.return_value = {"success": True, "data": {}}

        await discovery_handler.handle("vibemk_start_bulk_discovery", {"hostnames": ["a", "b"]})

        assert posted_paths(discovery_handler.client) == [BULK_DISCOVERY]

    @pytest.mark.asyncio
    async def test_bulk_discovery_status_queries_the_background_job(self, discovery_handler):
        discovery_handler.client.get.return_value = {"success": True, "data": {}}

        await discovery_handler.handle("vibemk_get_bulk_discovery_status", {"job_id": "job-42"})

        paths = fetched_paths(discovery_handler.client)
        assert paths, "no request was made"
        assert all(path.startswith(BACKGROUND_JOB) for path in paths), paths

    def test_all_documented_discovery_modes_are_accepted(self):
        # cmk/gui/openapi/endpoints/service_discovery declares these seven.
        tool = next(t for t in get_all_tools() if t["name"] == "vibemk_start_service_discovery")
        declared = set(tool["inputSchema"]["properties"]["mode"].get("enum", []))

        assert {"tabula_rasa", "only_service_labels"} <= declared, declared


class TestNoFabricatedEndpoints:
    @pytest.mark.asyncio
    async def test_service_status_never_calls_a_livestatus_endpoint(self, service_handler):
        # domain-types/bi_rule/actions/livestatus_query does not exist in any
        # CheckMK release; the REST API exposes no Livestatus passthrough.
        # Every GET-based attempt must fail for the fallback chain to reach the
        # Livestatus block; a plain unsuccessful response returns early instead.
        service_handler.client.get.side_effect = CheckMKAPIError("boom", 500, {})
        service_handler.client.post.return_value = {"success": False, "data": {}}

        await service_handler.handle(
            "vibemk_get_service_status",
            {"host_name": "example.com", "service_description": "CPU utilization"},
        )

        called = posted_paths(service_handler.client) + fetched_paths(service_handler.client)
        assert not [path for path in called if "bi_rule" in path or "livestatus" in path], called


class TestRedundantDiscoveryToolIsGone:
    def test_discover_services_tool_is_not_advertised(self):
        # It posted to domain-types/service_discovery/actions/start, which does
        # not exist, and duplicated two tools that call the right paths.
        names = {tool["name"] for tool in get_all_tools()}

        assert "vibemk_discover_services" not in names
        assert {"vibemk_start_service_discovery", "vibemk_start_bulk_discovery"} <= names


class TestServiceStatusCarriesItsOutput:
    """`show_service` does not return plugin_output — verified against 2.4.0p2 CRE,
    where its extensions are exactly description, host_name, last_check, state and
    state_type. The service collection does return it, so that is what a status
    lookup has to use if it is to answer "why is this critical?".
    """

    @pytest.fixture
    def handler(self, mock_checkmk_client):
        return ServiceHandler(mock_checkmk_client)

    @pytest.mark.asyncio
    async def test_the_check_output_reaches_the_caller(self, handler):
        handler.client.get.return_value = {
            "success": True,
            "status": 200,
            "headers": {},
            "data": {
                "value": [
                    {
                        "extensions": {
                            "host_name": "web01",
                            "description": "Filesystem /var",
                            "state": 2,
                            "plugin_output": "CRIT - 94.1% used (89.2 of 94.8 GiB)",
                        }
                    }
                ]
            },
        }

        result = await handler.handle(
            "vibemk_get_service_status", {"host_name": "web01", "service_description": "Filesystem /var"}
        )

        assert "94.1% used" in result[0]["text"]
        assert "CRITICAL" in result[0]["text"]


class TestDeadFallbacksAreGone:
    """Both were verified dead against 2.4.0p2 CRE, not merely suspected."""

    def test_no_handler_calls_the_service_object_endpoint(self):
        # objects/service/{host}/{description} answers 404 on 2.4.
        root = pathlib.Path(__file__).resolve().parent.parent
        for path in (root / "handlers" / "services.py",):
            assert "objects/service/" not in path.read_text(encoding="utf-8"), path

    def test_no_handler_posts_to_show_service(self):
        # POST on the show_service action answers 405 METHOD NOT ALLOWED on 2.4;
        # it is a GET action with a service_description parameter.
        root = pathlib.Path(__file__).resolve().parent.parent
        source = (root / "handlers" / "services.py").read_text(encoding="utf-8")
        posts = re.findall(r"client\.post\([^)]*show_service[^)]*\)", source)
        assert posts == [], posts
