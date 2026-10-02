"""
Deleting one downtime must delete one downtime.

An id identifies exactly one downtime, and CheckMK can delete it that way.
Resolving the id into a host-and-comment query turns "delete this downtime"
into "delete everything that looks like it": a comment is optional when
creating a downtime, so one without a comment dropped the comment filter and
took every downtime on the host with it, and `op: "~"` is a substring match,
so deleting "Patch" also deleted "Patching".
"""

from unittest.mock import AsyncMock, patch

import pytest

from handlers.downtimes import DowntimeHandler


@pytest.fixture
def handler(mock_checkmk_client):
    return DowntimeHandler(mock_checkmk_client)


class TestDeleteByIdentifier:
    @pytest.mark.asyncio
    async def test_an_id_deletes_by_id(self, handler):
        handler.client.post.return_value = {"success": True, "data": {}}

        await handler._delete_downtime({"downtime_id": "123"})

        sent = handler.client.post.call_args.kwargs["data"]
        assert sent["delete_type"] == "by_id"
        assert sent["downtime_id"] == "123"

    @pytest.mark.asyncio
    async def test_an_id_never_builds_a_query(self, handler):
        """A query is how one deletion becomes several."""
        handler.client.post.return_value = {"success": True, "data": {}}

        await handler._delete_downtime({"downtime_id": "123"})

        sent = handler.client.post.call_args.kwargs["data"]
        assert "query" not in sent, "an id must not be widened into a query"

    @pytest.mark.asyncio
    async def test_an_id_does_not_need_to_list_every_downtime_first(self, handler):
        """Resolving the id into host and comment is what caused the widening."""
        handler.client.post.return_value = {"success": True, "data": {}}

        await handler._delete_downtime({"downtime_id": "123"})

        assert handler.client.get.call_count == 0

    @pytest.mark.asyncio
    async def test_missing_host_and_id_is_refused(self, handler):
        result = await handler._delete_downtime({})

        assert "❌" in result[0]["text"]
        assert handler.client.post.call_count == 0


class TestRecurIsSent:
    """recur was advertised but never read: a weekly downtime came out as a single one."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("tool", ["vibemk_schedule_host_downtime", "vibemk_schedule_service_downtime"])
    async def test_recur_reaches_checkmk(self, handler, tool):
        handler.client.get.return_value = {"success": True, "data": {"value": []}}
        handler.client.post.return_value = {"success": True, "data": {}}
        arguments = {"host_name": "web01", "duration": "30m", "comment": "patch window", "recur": "week"}
        if tool == "vibemk_schedule_service_downtime":
            arguments["service_descriptions"] = ["CPU load"]

        with patch("asyncio.sleep", new=AsyncMock()):
            await handler.handle(tool, arguments)

        sent = next(c.kwargs["data"] for c in handler.client.post.call_args_list if "downtime/collections" in c.args[0])
        assert sent["recur"] == "week"

    @pytest.mark.asyncio
    async def test_no_recur_sends_no_field(self, handler):
        handler.client.get.return_value = {"success": True, "data": {"value": []}}
        handler.client.post.return_value = {"success": True, "data": {}}

        with patch("asyncio.sleep", new=AsyncMock()):
            await handler.handle("vibemk_schedule_host_downtime", {"host_name": "web01", "duration": "30m"})

        sent = next(c.kwargs["data"] for c in handler.client.post.call_args_list if "downtime/collections" in c.args[0])
        assert "recur" not in sent
