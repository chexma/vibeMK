"""
Discovery must not remove services nobody asked it to remove.

CheckMK defaults every BulkDiscoveryOptions flag to False. Overriding four of
them with True means a call carrying nothing but hostnames removes vanished
services -- which is not what someone asking to discover services is asking
for.
"""

import pytest

from handlers.discovery import DiscoveryHandler


@pytest.fixture
def handler(mock_checkmk_client):
    return DiscoveryHandler(mock_checkmk_client)


def _sent_options(handler) -> dict:
    return handler.client.post.call_args.kwargs["data"]["options"]


class TestBulkDiscoveryDefaults:
    @pytest.mark.asyncio
    async def test_does_not_remove_vanished_services_by_default(self, handler):
        handler.client.post.return_value = {"success": True, "data": {"id": "job-1"}}

        await handler.start_bulk_discovery({"hostnames": ["web01"]})

        assert _sent_options(handler)["remove_vanished_services"] is False

    @pytest.mark.asyncio
    async def test_monitors_undecided_services_by_default(self, handler):
        """The additive option is the one that matches the request."""
        handler.client.post.return_value = {"success": True, "data": {"id": "job-1"}}

        await handler.start_bulk_discovery({"hostnames": ["web01"]})

        assert _sent_options(handler)["monitor_undecided_services"] is True

    @pytest.mark.asyncio
    async def test_removal_can_still_be_asked_for(self, handler):
        handler.client.post.return_value = {"success": True, "data": {"id": "job-1"}}

        await handler.start_bulk_discovery({"hostnames": ["web01"], "options": {"remove_vanished_services": True}})

        assert _sent_options(handler)["remove_vanished_services"] is True

    @pytest.mark.asyncio
    async def test_label_updates_are_not_forced_on(self, handler):
        handler.client.post.return_value = {"success": True, "data": {"id": "job-1"}}

        await handler.start_bulk_discovery({"hostnames": ["web01"]})

        options = _sent_options(handler)
        assert options["update_service_labels"] is False
        assert options["update_host_labels"] is False


class TestDiscoveryModes:
    """A mode nobody mapped must be refused, not silently emptied."""

    @pytest.mark.asyncio
    async def test_an_unknown_mode_is_refused(self, handler):
        """Four membership tests mean an unmapped mode asks CheckMK to do nothing.

        It then reports success, so the caller believes a discovery ran.
        """
        handler.client.post.return_value = {"success": True, "data": {"id": "job-1"}}

        result = await handler._fallback_to_bulk_discovery("web01", "tabula_rasa")

        assert "❌" in result[0]["text"]
        assert handler.client.post.call_count == 0

    @pytest.mark.asyncio
    async def test_a_known_mode_still_works(self, handler):
        handler.client.post.return_value = {"success": True, "data": {"id": "job-1"}}

        await handler._fallback_to_bulk_discovery("web01", "refresh")

        options = handler.client.post.call_args.kwargs["data"]["options"]
        assert options["monitor_undecided_services"] is True


class TestModeTableMatchesSchema:
    """The table and the advertised enum must not drift apart."""

    def test_every_advertised_mode_has_a_mapping(self):
        from handlers.discovery import _BULK_OPTIONS_BY_MODE
        from mcp.tools import get_all_tools

        tool = next(t for t in get_all_tools() if t["name"] == "vibemk_start_service_discovery")
        advertised = set(tool["inputSchema"]["properties"]["mode"]["enum"])

        unmapped = sorted(advertised - set(_BULK_OPTIONS_BY_MODE))
        assert unmapped == [], f"advertised but not mapped: {unmapped}"

    def test_every_mapping_is_advertised(self):
        from handlers.discovery import _BULK_OPTIONS_BY_MODE
        from mcp.tools import get_all_tools

        tool = next(t for t in get_all_tools() if t["name"] == "vibemk_start_service_discovery")
        advertised = set(tool["inputSchema"]["properties"]["mode"]["enum"])

        unadvertised = sorted(set(_BULK_OPTIONS_BY_MODE) - advertised)
        assert unadvertised == [], f"mapped but not advertised: {unadvertised}"
