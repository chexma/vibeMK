"""
What the write tools send, in the shape CheckMK 2.5 accepts

Every expectation below is a request body that the local 2.5 instances
accepted, after the shape the handlers used to send had been refused with a 400.
The live round-trips in test_live_writes.py prove it against a server; these
keep it from regressing in CI, which has none.

The common cause for the active checks: rulesets moved to form specs store
levels as ("fixed", (warn, crit)) in the spec's base unit, passwords as
("cmk_postprocessed", "explicit_password", (id, secret)) and cascading choices
as (name, value). Their migrations only run when a stored rule is loaded, so
the REST API refuses the old shapes ("Unable to transform value").
"""

import ast
from typing import Any, Dict

import pytest

from vibemk.handlers.active_checks import ActiveChecksHandler
from vibemk.handlers.agents import AgentHandler
from vibemk.handlers.discovery import DiscoveryHandler
from vibemk.handlers.event_console import EventConsoleHandler
from vibemk.handlers.service_groups import ServiceGroupHandler
from vibemk.server.dispatch import is_error

SECRET = ("cmk_postprocessed", "explicit_password", ("", "s3cret"))


@pytest.fixture
def checks(mock_checkmk_client):
    handler = ActiveChecksHandler(mock_checkmk_client)
    handler.client.post.return_value = {"success": True, "status": 200, "data": {"id": "rule-1"}}
    handler.client.get.return_value = {"success": True, "data": {"extensions": {"folder": "/"}}}
    return handler


async def value_sent(handler: ActiveChecksHandler, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    content = await handler.handle(tool, {"hostname": "web01", **arguments})
    assert not is_error(content), content[0]["text"]
    value: Dict[str, Any] = ast.literal_eval(handler.client.post.call_args.args[1]["value_raw"])
    return value


class TestActiveCheckValues:
    @pytest.mark.asyncio
    async def test_http_levels_password_regex_and_address_family(self, checks):
        value = await value_sent(
            checks,
            "vibemk_create_http_check",
            {
                "response_time_warn": 1,
                "response_time_crit": 2,
                "auth_user": "probe",
                "auth_password": "s3cret",
                "expect_regex": "o.",
                "address_family": "ipv4",
            },
        )

        url = value["mode"][1]
        assert url["response_time"] == ("fixed", (1.0, 2.0))
        assert url["auth"] == {"user": "probe", "password": SECRET}
        assert url["expect_regex"] == {
            "regex": "o.",
            "case_insensitive": False,
            "crit_if_found": False,
            "multiline": False,
        }
        assert value["host"]["address_family"] == "ipv4_enforced"

    @pytest.mark.asyncio
    async def test_http_certificate_days_are_seconds(self, checks):
        value = await value_sent(
            checks, "vibemk_create_http_check", {"cert_mode": True, "cert_days_warn": 30, "cert_days_crit": 14}
        )

        assert value["mode"] == ("cert", {"cert_days": ("fixed", (30 * 86400.0, 14 * 86400.0))})

    @pytest.mark.asyncio
    async def test_tcp_levels_and_certificate_days(self, checks):
        value = await value_sent(
            checks,
            "vibemk_create_tcp_check",
            {"port": 443, "cert_days_warn": 30, "cert_days_crit": 14, "response_time_warn": 1, "response_time_crit": 2},
        )

        assert value["cert_days"] == ("fixed", (30 * 86400.0, 14 * 86400.0))
        assert value["response_time"] == ("fixed", (1.0, 2.0))

    @pytest.mark.asyncio
    async def test_icmp_timeout_is_an_integer(self, checks):
        """A legacy valuespec: 20.0 was refused as "wrong type float, must be int"."""
        assert (await value_sent(checks, "vibemk_create_icmp_check", {}))["timeout"] == 20
        assert isinstance((await value_sent(checks, "vibemk_create_icmp_check", {"timeout": 10}))["timeout"], int)

    @pytest.mark.asyncio
    async def test_smtp_certificate_days_are_seconds(self, checks):
        value = await value_sent(
            checks, "vibemk_create_smtp_check", {"starttls": True, "cert_days_warn": 30, "cert_days_crit": 14}
        )

        assert value["cert_days"] == ("fixed", (30 * 86400.0, 14 * 86400.0))

    @pytest.mark.asyncio
    async def test_ftp_sends_no_passive_key(self, checks):
        """check_ftp has no passive mode; the key was refused as undefined."""
        assert "passive" not in await value_sent(checks, "vibemk_create_ftp_check", {})

    @pytest.mark.asyncio
    async def test_ldap_response_time_is_seconds_and_authentication_a_dictionary(self, checks):
        value = await value_sent(
            checks,
            "vibemk_create_ldap_check",
            {
                "base_dn": "dc=example,dc=com",
                "bind_dn": "cn=probe",
                "password": "s3cret",
                "response_time_warn_ms": 500,
                "response_time_crit_ms": 800,
            },
        )

        assert value["response_time"] == ("fixed", (0.5, 0.8))
        assert value["authentication"] == {"bind_dn": "cn=probe", "password": SECRET}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("smb_host", "expected"),
        [("use_parent_host", ("use_parent_host", "")), ("fileserver", ("define_host", "fileserver"))],
    )
    async def test_smb_host_is_a_cascading_choice(self, checks, smb_host, expected):
        value = await value_sent(
            checks,
            "vibemk_create_smb_check",
            {"share": "data", "smb_host": smb_host, "username": "probe", "password": "s3cret"},
        )

        assert value["host"] == expected
        assert value["levels"] == ("fixed", (85.0, 95.0))
        assert value["auth"] == {"user": "probe", "password": SECRET}

    @pytest.mark.asyncio
    async def test_mkevents_ignore_acknowledged_is_present_or_absent(self, checks):
        """A FixedValue(True): False was refused, the key has to be left out."""
        assert "ignore_acknowledged" not in await value_sent(
            checks, "vibemk_create_mkevents_check", {"ignore_acknowledged": False}
        )
        assert (await value_sent(checks, "vibemk_create_mkevents_check", {}))["ignore_acknowledged"] is True

    @pytest.mark.asyncio
    async def test_mkevents_remote_and_last_log_use_the_rulesets_values(self, checks):
        value = await value_sent(
            checks, "vibemk_create_mkevents_check", {"remote_ec_host": "10.0.0.1", "show_last_log": "none"}
        )

        assert value["remote"] == ("10.0.0.1", 6558)
        assert value["show_last_log"] == "no"


class TestEventConsole:
    @pytest.fixture
    def handler(self, mock_checkmk_client):
        mock_checkmk_client.post.return_value = {"success": True, "status": 204, "data": {}}
        return EventConsoleHandler(mock_checkmk_client)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("tool", "arguments"),
        [
            ("vibemk_acknowledge_event", {"event_id": 7}),
            ("vibemk_change_event_state", {"event_id": 7, "new_state": "warning"}),
        ],
    )
    async def test_writes_name_the_site_the_event_lives_on(self, handler, tool, arguments):
        """An event ID is unique per site only; CheckMK refused the body without site_id."""
        await handler.handle(tool, arguments)

        assert handler.client.post.call_args.args[1]["site_id"] == "test_site"

    @pytest.mark.asyncio
    async def test_deleting_by_id_is_one_by_id_call_per_event(self, handler):
        await handler.handle("vibemk_delete_events", {"event_ids": [7, 8], "site_id": "remote"})

        bodies = [call.args[1] for call in handler.client.post.call_args_list]
        assert bodies == [
            {"filter_type": "by_id", "site_id": "remote", "event_id": 7},
            {"filter_type": "by_id", "site_id": "remote", "event_id": 8},
        ]

    @pytest.mark.asyncio
    async def test_deleting_by_filter_names_the_filter_type(self, handler):
        await handler.handle("vibemk_delete_events", {"host": "web01"})

        assert handler.client.post.call_args.args[1] == {
            "filter_type": "params",
            "filters": {"phase": "open", "host": "web01"},
        }


class TestAgentBakery:
    @pytest.mark.asyncio
    async def test_the_download_url_is_the_action_checkmk_serves(self, mock_checkmk_client):
        """objects/agent/download_by_host read 'download_by_host' as an agent hash and answered 404."""
        content = await AgentHandler(mock_checkmk_client).handle(
            "vibemk_download_agent_by_host", {"host_name": "web01", "os_type": "windows_msi"}
        )

        assert (
            "/domain-types/agent/actions/download_by_host/invoke?os_type=windows_msi&host_name=web01&agent_type=host_name"
            in content[0]["text"]
        )

    @pytest.mark.asyncio
    async def test_the_baking_status_is_read_from_the_job(self, mock_checkmk_client):
        mock_checkmk_client.get.return_value = {
            "success": True,
            "data": {
                "resultType": "object",
                "result": {
                    "value": {
                        "state": "finished",
                        "started": 1790984580.75,
                        "duration": 1.73,
                        "loginfo": {"JobProgressUpdate": [], "JobResult": ["Baking successful"], "JobException": []},
                    }
                },
            },
        }

        text = (await AgentHandler(mock_checkmk_client).handle("vibemk_baking_status", {}))[0]["text"]

        assert "State: finished" in text
        assert "Result: Baking successful" in text

    @pytest.mark.asyncio
    async def test_a_raw_site_is_told_it_has_no_bakery(self, mock_checkmk_client):
        from vibemk.api.exceptions import CheckMKNotFoundError

        mock_checkmk_client.post.side_effect = CheckMKNotFoundError("Resource not found", 404)

        content = await AgentHandler(mock_checkmk_client).handle("vibemk_bake_agents", {})

        assert is_error(content)
        assert "no agent bakery" in content[0]["text"]


@pytest.mark.asyncio
async def test_bulk_discovery_status_is_read_from_the_background_job(mock_checkmk_client):
    """The state sits under extensions.status; the tool reported UNKNOWN for every job."""
    mock_checkmk_client.get.return_value = {
        "success": True,
        "data": {
            "extensions": {
                "site_id": "cmk",
                "active": False,
                "status": {
                    "state": "finished",
                    "log_info": {
                        "JobProgressUpdate": [
                            "Acquired lock",
                            "[1/1] web01: discovery successful",
                            "Hosts: 1 total (1 succeeded, 0 skipped, 0 failed)",
                        ],
                        "JobResult": ["Bulk discovery finished"],
                        "JobException": [],
                    },
                },
            }
        },
    }

    text = (await DiscoveryHandler(mock_checkmk_client).get_bulk_discovery_status({"job_id": "bulk_discovery-1"}))[0][
        "text"
    ]

    assert "State: FINISHED" in text
    assert "Hosts: 1 total (1 succeeded" in text
    assert "Acquired lock" not in text


@pytest.mark.asyncio
async def test_a_service_groups_alias_is_its_title(mock_checkmk_client):
    """CheckMK returns the alias as the title and leaves extensions empty."""
    mock_checkmk_client.get.return_value = {
        "success": True,
        "data": {"domainType": "service_group_config", "id": "web", "title": "Web services", "extensions": {}},
    }

    text = (await ServiceGroupHandler(mock_checkmk_client).handle("vibemk_get_service_group", {"name": "web"}))[0][
        "text"
    ]

    assert "**Alias:** Web services" in text
