"""
Tests for optimistic locking against the CheckMK REST API.

CheckMK accepts `If-Match: *` (Werkzeug's ETags.contains() is true for the
star tag), so sending the wildcard never fails — it just switches the
concurrency check off. Two writers then silently overwrite each other, which
is exactly what the ETag exists to prevent. These tests pin that the handlers
send the object's real ETag.

Which endpoints require If-Match was read from the `etag="input"` / `"both"`
declarations in cmk/gui/openapi/endpoints at tag v2.4.0p2.
"""

from typing import Any, Optional

import pytest

from api.exceptions import CheckMKNotFoundError
from handlers.configuration import ConfigurationHandler
from handlers.folders import FolderHandler
from handlers.groups import GroupsHandler
from handlers.passwords import PasswordsHandler
from handlers.rules import RulesHandler
from handlers.tags import TagsHandler
from handlers.timeperiods import TimePeriodsHandler
from handlers.users import UserHandler

ETAG = '"a1b2c3d4"'


def response(etag=ETAG, data=None):
    """A successful client response carrying an ETag response header."""
    return {
        "success": True,
        "status": 200,
        "headers": {"ETag": etag} if etag else {},
        "data": data if data is not None else {"extensions": {}},
    }


def if_match_of(mock_call: Any) -> Optional[str]:
    return (mock_call.kwargs.get("headers") or {}).get("If-Match")


class TestIfMatchHeaderHelper:
    @pytest.fixture
    def handler(self, mock_checkmk_client):
        return TagsHandler(mock_checkmk_client)

    def test_reads_the_etag_from_the_response_header(self, handler):
        handler.client.get.return_value = response()

        assert handler._if_match_header("objects/host_tag_group/x") == {"If-Match": ETAG}

    def test_falls_back_to_the_etag_in_meta_data(self, handler):
        handler.client.get.return_value = response(
            etag=None, data={"extensions": {"meta_data": {"etag": '"from-body"'}}}
        )

        assert handler._if_match_header("objects/host_tag_group/x") == {"If-Match": '"from-body"'}

    def test_falls_back_to_the_wildcard_when_no_etag_is_present(self, handler):
        handler.client.get.return_value = response(etag=None)

        assert handler._if_match_header("objects/host_tag_group/x") == {"If-Match": "*"}

    def test_falls_back_to_the_wildcard_when_the_lookup_fails(self, handler):
        # A failed lookup must not block the write; it degrades to no locking.
        handler.client.get.side_effect = CheckMKNotFoundError("gone", 404, {})

        assert handler._if_match_header("objects/host_tag_group/x") == {"If-Match": "*"}


class TestUpdatesSendTheRealEtag:
    """PUT on these object types is declared etag="both" in CheckMK 2.4."""

    @pytest.mark.asyncio
    async def test_update_time_period(self, mock_checkmk_client):
        handler = TimePeriodsHandler(mock_checkmk_client)
        mock_checkmk_client.get.return_value = response()
        mock_checkmk_client.put.return_value = response()

        await handler.handle(
            "vibemk_update_timeperiod", {"name": "workhours", "alias": "Work", "active_time_ranges": []}
        )

        assert if_match_of(mock_checkmk_client.put.call_args) == ETAG

    @pytest.mark.asyncio
    async def test_update_host_group(self, mock_checkmk_client):
        handler = GroupsHandler(mock_checkmk_client)
        mock_checkmk_client.get.return_value = response()
        mock_checkmk_client.put.return_value = response()

        await handler.handle("vibemk_update_host_group", {"name": "linux", "alias": "Linux servers"})

        assert if_match_of(mock_checkmk_client.put.call_args) == ETAG

    @pytest.mark.asyncio
    async def test_update_password(self, mock_checkmk_client):
        handler = PasswordsHandler(mock_checkmk_client)
        mock_checkmk_client.get.return_value = response()
        mock_checkmk_client.put.return_value = response()

        await handler.handle("vibemk_update_password", {"ident": "svc", "title": "Service account"})

        assert if_match_of(mock_checkmk_client.put.call_args) == ETAG

    @pytest.mark.asyncio
    async def test_update_host_tag_group(self, mock_checkmk_client):
        handler = TagsHandler(mock_checkmk_client)
        mock_checkmk_client.get.return_value = response()
        mock_checkmk_client.put.return_value = response()

        await handler.handle("vibemk_update_host_tag", {"tag_id": "criticality", "title": "Criticality"})

        assert if_match_of(mock_checkmk_client.put.call_args) == ETAG

    @pytest.mark.asyncio
    async def test_update_user(self, mock_checkmk_client):
        handler = UserHandler(mock_checkmk_client)
        mock_checkmk_client.get.return_value = response()
        mock_checkmk_client.put.return_value = response()

        await handler.handle("vibemk_update_user", {"username": "alice", "fullname": "Alice"})

        assert if_match_of(mock_checkmk_client.put.call_args) == ETAG

    @pytest.mark.asyncio
    async def test_update_rule(self, mock_checkmk_client):
        handler = RulesHandler(mock_checkmk_client)
        mock_checkmk_client.get.return_value = response()
        mock_checkmk_client.put.return_value = response()

        await handler.handle("vibemk_update_rule", {"rule_id": "abc123", "rule_config": "{}"})

        assert if_match_of(mock_checkmk_client.put.call_args) == ETAG


class TestPreviouslyMissingIfMatch:
    """These call sites sent no If-Match at all, though 2.4 requires one."""

    @pytest.mark.asyncio
    async def test_update_folder(self, mock_checkmk_client):
        handler = FolderHandler(mock_checkmk_client)
        mock_checkmk_client.get.return_value = response()
        mock_checkmk_client.put.return_value = response()

        await handler.handle("vibemk_update_folder", {"folder": "/servers", "title": "Servers"})

        assert if_match_of(mock_checkmk_client.put.call_args) == ETAG

    @pytest.mark.asyncio
    async def test_delete_time_period(self, mock_checkmk_client):
        # The only DELETE among vibeMK's call sites that CheckMK declares
        # etag="input"; every other delete works without a precondition.
        handler = TimePeriodsHandler(mock_checkmk_client)
        mock_checkmk_client.get.return_value = response()
        mock_checkmk_client.delete.return_value = response()

        await handler.handle("vibemk_delete_timeperiod", {"name": "workhours"})

        assert if_match_of(mock_checkmk_client.delete.call_args) == ETAG


class TestActivation:
    @pytest.mark.asyncio
    async def test_activation_uses_the_pending_changes_etag(self, mock_checkmk_client):
        # POST activate-changes is etag="input"; GET pending_changes is
        # etag="output" and is already fetched to decide whether to activate.
        handler = ConfigurationHandler(mock_checkmk_client)
        mock_checkmk_client.get.return_value = response(data={"value": [{"id": "change-1"}]})
        mock_checkmk_client.post.return_value = response(data={"id": "activation-1"})

        await handler.handle("vibemk_activate_changes", {})

        assert mock_checkmk_client.post.called, "activation must go through the client, not raw urllib"
        assert if_match_of(mock_checkmk_client.post.call_args) == ETAG
