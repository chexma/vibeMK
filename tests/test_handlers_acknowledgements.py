"""
Acknowledgements are a comment type, not a guess about comment text.

CheckMK types every comment: the Livestatus entry_type column is 1 for a user
comment, 2 for downtime, 3 for flapping and 4 for an acknowledgement. The ids
this listing returns are what remove_acknowledgement deletes by, so a listing
that includes an ordinary comment is a listing that can delete one.
"""

import pytest

from vibemk.handlers.acknowledgements import AcknowledgementHandler


def _comment(comment_id: str, text: str, persistent: bool = False) -> dict:
    return {
        "id": comment_id,
        "extensions": {"host_name": "web01", "comment": text, "persistent": persistent, "author": "ops"},
    }


@pytest.fixture
def handler(mock_checkmk_client):
    return AcknowledgementHandler(mock_checkmk_client)


class TestListAcknowledgements:
    @pytest.mark.asyncio
    async def test_asks_checkmk_for_the_acknowledgement_entry_type(self, handler):
        handler.client.get.return_value = {"success": True, "data": {"value": []}}

        await handler.list_acknowledgements({})

        params = handler.client.get.call_args.kwargs.get("params") or {}
        assert params.get("query") == {"op": "=", "left": "entry_type", "right": "4"}

    @pytest.mark.asyncio
    async def test_does_not_invent_acknowledgements_from_comment_text(self, handler):
        """CheckMK returned no acknowledgements, so the listing reports none.

        'packaging' contains 'ack'; under the old substring rule it qualified.
        """
        handler.client.get.return_value = {"success": True, "data": {"value": []}}

        result = await handler.list_acknowledgements({})

        assert "No active acknowledgements" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_lists_what_checkmk_returns(self, handler):
        handler.client.get.return_value = {
            "success": True,
            "data": {"value": [_comment("42", "disk replaced, waiting for RMA")]},
        }

        result = await handler.list_acknowledgements({})

        assert "web01" in result[0]["text"]
        assert "disk replaced" in result[0]["text"]
