"""
Tests for the notification rule handler.

Endpoint paths and shapes were read from
cmk/gui/openapi/endpoints/notification_rules at tag v2.4.0p2. Note that
deletion is a POST action rather than a DELETE, and that none of these
endpoints declares an etag, so no If-Match is sent.
"""

import pytest

from handlers.notifications import NotificationHandler

COLLECTION = "domain-types/notification_rule/collections/all"


@pytest.fixture
def handler(mock_checkmk_client):
    return NotificationHandler(mock_checkmk_client)


def ok(data=None):
    return {"success": True, "status": 200, "headers": {}, "data": data if data is not None else {}}


RULE = {
    "id": "1",
    "extensions": {
        "rule_config": {
            "description": "Notify admins by email",
            "disabled": False,
            "notification_method": {"notify_plugin": {"option": "mail"}},
        }
    },
}


class TestListing:
    @pytest.mark.asyncio
    async def test_lists_rules_from_the_collection_endpoint(self, handler):
        handler.client.get.return_value = ok({"value": [RULE]})

        result = await handler.handle("vibemk_get_notification_rules", {})

        handler.client.get.assert_called_once_with(COLLECTION)
        assert "Notify admins by email" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_reports_an_empty_configuration(self, handler):
        handler.client.get.return_value = ok({"value": []})

        result = await handler.handle("vibemk_get_notification_rules", {})

        assert "No notification rules" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_shows_a_single_rule_by_id(self, handler):
        handler.client.get.return_value = ok(RULE)

        result = await handler.handle("vibemk_get_notification_rule", {"rule_id": "1"})

        handler.client.get.assert_called_once_with("objects/notification_rule/1")
        assert "Notify admins by email" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_show_requires_a_rule_id(self, handler):
        result = await handler.handle("vibemk_get_notification_rule", {})

        assert not handler.client.get.called
        assert "rule_id" in result[0]["text"]


class TestDeletion:
    @pytest.mark.asyncio
    async def test_delete_posts_to_the_delete_action(self, handler):
        # CheckMK models this as an action, not as an HTTP DELETE.
        handler.client.post.return_value = ok()

        await handler.handle("vibemk_delete_notification_rule", {"rule_id": "7"})

        handler.client.post.assert_called_once_with("objects/notification_rule/7/actions/delete/invoke")

    @pytest.mark.asyncio
    async def test_delete_requires_a_rule_id(self, handler):
        result = await handler.handle("vibemk_delete_notification_rule", {})

        assert not handler.client.post.called
        assert "rule_id" in result[0]["text"]


class TestCreateAndUpdate:
    @pytest.mark.asyncio
    async def test_create_posts_the_rule_config_to_the_collection(self, handler):
        handler.client.post.return_value = ok(RULE)
        config = {"properties": {"description": "New rule"}}

        await handler.handle("vibemk_create_notification_rule", {"rule_config": config})

        handler.client.post.assert_called_once_with(COLLECTION, data={"rule_config": config})

    @pytest.mark.asyncio
    async def test_update_puts_the_rule_config_to_the_object(self, handler):
        handler.client.put.return_value = ok(RULE)
        config = {"properties": {"description": "Changed"}}

        await handler.handle("vibemk_update_notification_rule", {"rule_id": "3", "rule_config": config})

        handler.client.put.assert_called_once_with("objects/notification_rule/3", data={"rule_config": config})

    @pytest.mark.asyncio
    async def test_create_requires_a_rule_config(self, handler):
        result = await handler.handle("vibemk_create_notification_rule", {})

        assert not handler.client.post.called
        assert "rule_config" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_update_requires_a_rule_id(self, handler):
        result = await handler.handle("vibemk_update_notification_rule", {"rule_config": {}})

        assert not handler.client.put.called
        assert "rule_id" in result[0]["text"]


class TestUnknownTool:
    @pytest.mark.asyncio
    async def test_reports_an_unknown_tool(self, handler):
        result = await handler.handle("vibemk_not_a_notification_tool", {})

        assert "not supported" in result[0]["text"].lower()
