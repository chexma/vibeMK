"""
Creating active check rules.

`active_checks.py` is the second-largest handler and was at 5% coverage. It
builds eleven kinds of rule, and every one of them hands CheckMK a
`value_raw` that has to be a *Python literal* rather than JSON -- the format
documented in CLAUDE.md after it caused a run of HTTP 400s. That is the
thing worth asserting mechanically: `ast.literal_eval` either accepts what
the handler produced or it does not, for every check type, without a server.

The rest covers the three helpers all eleven share, since a mistake there is
a mistake in all of them at once: which folder the rule lands in, which host
it is conditioned on, and what the request body looks like.
"""

import ast

import pytest

from vibemk.handlers.active_checks import ActiveChecksHandler


@pytest.fixture
def handler(mock_checkmk_client):
    handler = ActiveChecksHandler(mock_checkmk_client)
    handler.client.post.return_value = {"success": True, "status": 200, "data": {"id": "rule-1"}}
    handler.client.get.return_value = {"success": True, "data": {"extensions": {"folder": "/servers/web"}}}
    return handler


def sent_rule(handler):
    """The rule body the handler posted."""
    args, kwargs = handler.client.post.call_args
    return kwargs.get("data", args[1] if len(args) > 1 else {})


# tool name -> (minimal arguments, the ruleset CheckMK expects)
CHECKS = [
    ("vibemk_create_http_check", {"hostname": "web01", "uri": "/health"}, "active_checks:http"),
    ("vibemk_create_tcp_check", {"hostname": "web01", "port": 443}, "active_checks:tcp"),
    ("vibemk_create_icmp_check", {"hostname": "web01"}, "active_checks:icmp"),
    ("vibemk_create_dns_check", {"hostname": "web01", "hostname_to_query": "example.org"}, "active_checks:dns"),
    ("vibemk_create_smtp_check", {"hostname": "mail01"}, "active_checks:smtp"),
    ("vibemk_create_ftp_check", {"hostname": "ftp01"}, "active_checks:ftp"),
    ("vibemk_create_ldap_check", {"hostname": "dc01", "base_dn": "dc=example,dc=org"}, "active_checks:ldap"),
    ("vibemk_create_smb_check", {"hostname": "fs01", "share": "public"}, "active_checks:disk_smb"),
    ("vibemk_create_mkevents_check", {"hostname": "log01"}, "active_checks:mkevents"),
    ("vibemk_create_inventory_check", {"hostname": "web01"}, "active_checks:cmk_inv"),
    (
        "vibemk_create_custom_check",
        {"hostname": "web01", "command_line": "/bin/true", "service_description": "Custom"},
        "custom_checks",
    ),
]


class TestEveryCheckProducesAPythonLiteral:
    """CheckMK parses value_raw with Python's own literal syntax.

    JSON looks close enough to pass review and is rejected at the API: `true`
    is not a Python literal, and neither is `null`. literal_eval settles it
    without a server.
    """

    @pytest.mark.parametrize(("tool", "arguments", "ruleset"), CHECKS, ids=[c[0] for c in CHECKS])
    @pytest.mark.asyncio
    async def test_the_value_parses_as_a_python_literal(self, handler, tool, arguments, ruleset):
        await handler.handle(tool, arguments)

        raw = sent_rule(handler)["value_raw"]
        ast.literal_eval(raw)  # raises if the handler emitted JSON or a fragment

    @pytest.mark.parametrize(("tool", "arguments", "ruleset"), CHECKS, ids=[c[0] for c in CHECKS])
    @pytest.mark.asyncio
    async def test_it_targets_the_ruleset_checkmk_serves(self, handler, tool, arguments, ruleset):
        await handler.handle(tool, arguments)

        assert sent_rule(handler)["ruleset"] == ruleset

    @pytest.mark.parametrize(("tool", "arguments", "ruleset"), CHECKS, ids=[c[0] for c in CHECKS])
    @pytest.mark.asyncio
    async def test_the_rule_is_conditioned_on_the_host_it_was_asked_for(self, handler, tool, arguments, ruleset):
        """A rule without a host condition applies to every host in the folder."""
        await handler.handle(tool, arguments)

        conditions = sent_rule(handler)["conditions"]
        assert conditions["host_name"]["match_on"] == [arguments["hostname"]]
        assert conditions["host_name"]["operator"] == "one_of"

    @pytest.mark.parametrize(("tool", "arguments", "ruleset"), CHECKS, ids=[c[0] for c in CHECKS])
    @pytest.mark.asyncio
    async def test_no_check_is_created_disabled(self, handler, tool, arguments, ruleset):
        await handler.handle(tool, arguments)

        assert sent_rule(handler)["properties"]["disabled"] is False


class TestRequiredParameters:
    """A missing parameter must be an error, not a rule with a hole in it."""

    @pytest.mark.asyncio
    async def test_tcp_needs_a_port(self, handler):
        result = await handler.handle("vibemk_create_tcp_check", {"hostname": "web01"})

        assert result[0]["text"].startswith("❌")
        handler.client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_icmp_needs_a_hostname(self, handler):
        result = await handler.handle("vibemk_create_icmp_check", {})

        assert result[0]["text"].startswith("❌")
        handler.client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_an_unknown_tool_is_reported_not_silently_ignored(self, handler):
        result = await handler.handle("vibemk_create_quantum_check", {"hostname": "web01"})

        assert result[0]["text"].startswith("❌")
        handler.client.post.assert_not_called()


class TestWhichFolderTheRuleLandsIn:
    """A rule in the wrong folder silently applies to the wrong hosts."""

    def test_an_explicit_folder_wins(self, handler):
        assert handler._resolve_folder("web01", "~custom") == "~custom"
        handler.client.get.assert_not_called()

    def test_otherwise_it_follows_the_host(self, handler):
        """CheckMK addresses folders with tildes, the API reports them with
        slashes, so the lookup has to convert."""
        assert handler._resolve_folder("web01", None) == "~servers~web"

    def test_a_host_in_the_root_folder_resolves_to_the_root(self, handler):
        handler.client.get.return_value = {"success": True, "data": {"extensions": {"folder": "/"}}}

        assert handler._resolve_folder("web01", None) == "~"

    def test_a_failed_lookup_falls_back_to_the_root_rather_than_raising(self, handler):
        handler.client.get.side_effect = Exception("host not found")

        assert handler._resolve_folder("ghost", None) == "~"


class TestTheRequestBody:
    def test_a_description_is_sent_when_given(self, handler):
        handler._post_rule("active_checks:icmp", "{}", "web01", "~", "why this exists")

        assert sent_rule(handler)["properties"]["description"] == "why this exists"

    def test_no_empty_description_is_sent(self, handler):
        """CheckMK stores what it is given; an empty string is not nothing."""
        handler._post_rule("active_checks:icmp", "{}", "web01", "~", "")

        assert "description" not in sent_rule(handler)["properties"]

    def test_rules_go_to_the_collection_endpoint(self, handler):
        handler._post_rule("active_checks:icmp", "{}", "web01", "~")

        assert handler.client.post.call_args[0][0] == "domain-types/rule/collections/all"

    def test_the_host_condition_carries_the_empty_groups_checkmk_expects(self, handler):
        condition = handler._host_condition("web01")

        assert condition["host_tags"] == []
        assert condition["host_label_groups"] == []
        assert condition["service_label_groups"] == []


class TestListingAndDeleting:
    @pytest.mark.asyncio
    async def test_listing_asks_for_every_active_check_ruleset(self, handler):
        handler.client.get.return_value = {"success": True, "data": {"value": []}}

        await handler.handle("vibemk_list_active_checks", {})

        asked = {call.kwargs["params"]["ruleset_name"] for call in handler.client.get.call_args_list}

        assert asked == set(ActiveChecksHandler._ALL_RULESETS)

    @pytest.mark.asyncio
    async def test_deleting_needs_a_rule_id(self, handler):
        result = await handler.handle("vibemk_delete_active_check", {})

        assert result[0]["text"].startswith("❌")
        handler.client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_deleting_addresses_the_rule_by_id(self, handler):
        handler.client.delete.return_value = {"success": True, "status": 204, "data": {}}

        await handler.handle("vibemk_delete_active_check", {"rule_id": "rule-42"})

        assert "rule-42" in handler.client.delete.call_args[0][0]
