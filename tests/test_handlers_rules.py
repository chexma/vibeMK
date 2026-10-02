"""
Tests for rule creation and positioning.

Both tools that take a `position` were wrong about it. `vibemk_move_rule`
sent "top", "bottom", "before" and "after" and put the target rule under
`target_rule`; CheckMK's own OpenAPI document discriminates on `position`
with exactly four values — `top_of_folder`, `bottom_of_folder`,
`after_specific_rule`, `before_specific_rule` — expects the target under
`rule_id`, and requires `folder` for the two folder positions. Every move
this server ever sent was rejected.

`vibemk_create_rule` advertised `position` in its schema and never read it,
so a caller asking for a position was told the rule was created and never
told it went somewhere else. The create endpoint takes no position at all —
only `folder`, `ruleset`, `value_raw`, `properties` and `conditions` — so
honouring the parameter means creating and then moving.
"""

import ast
from typing import Any, Dict, List, Optional

import pytest

from handlers.rules import RulesHandler

RULE_ID = "f8b74720-a454-4242-99c4-62994ef0f2bf"
TARGET_ID = "0e3b1a44-9a2e-4c17-8f5d-2b6c1d0e7a93"


def ok(data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"success": True, "status": 200, "headers": {"ETag": '"abc"'}, "data": data or {}}


def failed() -> Dict[str, Any]:
    return {"success": False, "status": 400, "headers": {}, "data": {}}


def rule_object(folder: str = "~servers~linux") -> Dict[str, Any]:
    return ok({"id": RULE_ID, "extensions": {"folder": folder, "ruleset": "checkgroup_parameters:filesystem"}})


@pytest.fixture
def handler(mock_checkmk_client: Any) -> RulesHandler:
    return RulesHandler(mock_checkmk_client)


def move_payload(client: Any) -> Dict[str, Any]:
    """The body of the one move call, or fail loudly."""
    calls = [c for c in client.post.call_args_list if "actions/move/invoke" in c.args[0]]
    assert len(calls) == 1, f"expected exactly one move call, saw {len(calls)}"
    return dict(calls[0].kwargs["data"])


def text(result: List[Dict[str, Any]]) -> str:
    return "\n".join(part.get("text", "") for part in result)


class TestMoveSpeaksTheApisVocabulary:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("given", "expected"),
        [
            ("top", "top_of_folder"),
            ("bottom", "bottom_of_folder"),
            ("top_of_folder", "top_of_folder"),
            ("bottom_of_folder", "bottom_of_folder"),
        ],
    )
    async def test_a_folder_position_is_translated(
        self, handler: RulesHandler, mock_checkmk_client: Any, given: str, expected: str
    ) -> None:
        mock_checkmk_client.get.return_value = rule_object()
        mock_checkmk_client.post.return_value = ok()

        await handler.handle("vibemk_move_rule", {"rule_id": RULE_ID, "position": given})

        assert move_payload(mock_checkmk_client)["position"] == expected

    @pytest.mark.asyncio
    async def test_a_folder_position_carries_the_rules_own_folder(
        self, handler: RulesHandler, mock_checkmk_client: Any
    ) -> None:
        # CheckMK rejects top_of_folder without a folder, and the caller of a
        # move has no reason to know where the rule already lives.
        mock_checkmk_client.get.return_value = rule_object("~servers~linux")
        mock_checkmk_client.post.return_value = ok()

        await handler.handle("vibemk_move_rule", {"rule_id": RULE_ID, "position": "top"})

        assert move_payload(mock_checkmk_client)["folder"] == "~servers~linux"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("given", "expected"),
        [("before", "before_specific_rule"), ("after", "after_specific_rule")],
    )
    async def test_a_relative_position_names_its_target_rule_id(
        self, handler: RulesHandler, mock_checkmk_client: Any, given: str, expected: str
    ) -> None:
        mock_checkmk_client.get.return_value = rule_object()
        mock_checkmk_client.post.return_value = ok()

        await handler.handle("vibemk_move_rule", {"rule_id": RULE_ID, "position": given, "target_rule_id": TARGET_ID})

        payload = move_payload(mock_checkmk_client)
        assert payload == {"position": expected, "rule_id": TARGET_ID}, "the API names the target rule_id"

    @pytest.mark.asyncio
    async def test_an_unknown_position_never_reaches_checkmk(
        self, handler: RulesHandler, mock_checkmk_client: Any
    ) -> None:
        mock_checkmk_client.get.return_value = rule_object()

        result = await handler.handle("vibemk_move_rule", {"rule_id": RULE_ID, "position": "sideways"})

        assert not mock_checkmk_client.post.called
        assert "sideways" in text(result)
        assert "top_of_folder" in text(result), "the answer should name the values that do work"

    @pytest.mark.asyncio
    async def test_a_relative_position_without_a_target_is_refused(
        self, handler: RulesHandler, mock_checkmk_client: Any
    ) -> None:
        mock_checkmk_client.get.return_value = rule_object()

        result = await handler.handle("vibemk_move_rule", {"rule_id": RULE_ID, "position": "after"})

        assert not mock_checkmk_client.post.called
        assert "target_rule_id" in text(result)


class TestCreateHonoursThePositionItAdvertises:
    @pytest.fixture
    def created(self, mock_checkmk_client: Any) -> Any:
        """A successful create, followed by whatever the handler does next."""
        mock_checkmk_client.get.return_value = rule_object()
        mock_checkmk_client.post.return_value = ok({"id": RULE_ID})
        return mock_checkmk_client

    @pytest.mark.asyncio
    async def test_a_requested_position_is_applied(self, handler: RulesHandler, created: Any) -> None:
        await handler.handle(
            "vibemk_create_rule",
            {
                "ruleset_name": "checkgroup_parameters:filesystem",
                "rule_config": {"levels": (80.0, 90.0)},
                "folder": "/servers/linux",
                "position": "bottom",
            },
        )

        assert move_payload(created)["position"] == "bottom_of_folder"

    @pytest.mark.asyncio
    async def test_no_position_means_no_move(self, handler: RulesHandler, created: Any) -> None:
        # The create endpoint takes no position, so asking for none must not
        # cost a second write.
        await handler.handle(
            "vibemk_create_rule",
            {"ruleset_name": "checkgroup_parameters:filesystem", "rule_config": {"levels": (80.0, 90.0)}},
        )

        moves = [c for c in created.post.call_args_list if "actions/move/invoke" in c.args[0]]
        assert moves == []

    @pytest.mark.asyncio
    async def test_a_failed_move_is_reported_with_the_rule_id(
        self, handler: RulesHandler, mock_checkmk_client: Any
    ) -> None:
        # The rule exists either way. Reporting plain success would leave a
        # caller believing a position it did not get.
        mock_checkmk_client.get.return_value = rule_object()
        mock_checkmk_client.post.side_effect = lambda endpoint, **_: (
            failed() if "move" in endpoint else ok({"id": RULE_ID})
        )

        result = await handler.handle(
            "vibemk_create_rule",
            {
                "ruleset_name": "checkgroup_parameters:filesystem",
                "rule_config": {"levels": (80.0, 90.0)},
                "position": "bottom",
            },
        )

        answer = text(result)
        assert RULE_ID in answer, "the caller needs the id of the rule that was created"
        assert "position" in answer.lower()


class TestRuleValuesSurviveTheirOwnQuotes:
    """CheckMK expects value_raw as a Python literal, and this built one by
    hand: str(value) with every double quote rewritten to a single one, and
    strings wrapped in f"'{value}'".

    Both break on their own content. A dict holding `'He said "no"'` became
    `{'k': 'He said 'no''}`, which is not parseable, and an apostrophe in a
    plain string did the same. repr() is the operation being approximated
    here, and it gets the quoting right.

    Asserted through rule creation, which is where value_raw actually goes
    over the wire.
    """

    @pytest.fixture
    def created(self, mock_checkmk_client: Any) -> Any:
        mock_checkmk_client.get.return_value = rule_object()
        mock_checkmk_client.post.return_value = ok({"id": RULE_ID})
        return mock_checkmk_client

    async def value_raw(self, handler: RulesHandler, client: Any, config: Any) -> str:
        await handler.handle(
            "vibemk_create_rule",
            {"ruleset_name": "checkgroup_parameters:filesystem", "rule_config": config},
        )
        call = next(c for c in client.post.call_args_list if c.args[0] == "domain-types/rule/collections/all")
        return str(call.kwargs["data"]["value_raw"])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "config",
        [
            {"levels": [80.0, 90.0]},
            {"comment": 'He said "no"'},
            {"path": "it's here"},
            {"mixed": ['say "what"', "plain"]},
            {"apostrophe": "o'clock"},
        ],
    )
    async def test_the_literal_parses_back_to_what_went_in(
        self, handler: RulesHandler, created: Any, config: Any
    ) -> None:
        rendered = await self.value_raw(handler, created, config)

        assert ast.literal_eval(rendered) == config
