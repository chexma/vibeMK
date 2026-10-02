"""
Structured output for service status, problems, downtimes and metrics

The response shapes below are the ones CheckMK 2.5 returned on the local Raw
and Ultimate instances. Every successful answer of a tool with an output
schema has to carry structured content that validates against it: the SDK
refuses the result otherwise, which breaks the tool for every client.
"""

import datetime
from typing import Any, Dict, List

import jsonschema
import pytest

from vibemk.handlers.downtimes import DowntimeHandler
from vibemk.handlers.metrics import MetricsHandler, series_summary
from vibemk.handlers.monitoring import MonitoringHandler
from vibemk.handlers.services import ServiceHandler
from vibemk.server.dispatch import is_error, structured_of
from vibemk.server.schemas import OUTPUT_SCHEMAS


def assert_valid(tool: str, content: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The answer succeeded and its structured content matches the tool's schema."""
    assert not is_error(content), content[0].get("text")
    data = structured_of(content)
    assert data is not None, f"{tool} answered without structured content"
    jsonschema.validate(data, OUTPUT_SCHEMAS[tool])
    return data


def _iso(offset: datetime.timedelta) -> str:
    return (datetime.datetime.now(datetime.timezone.utc) + offset).isoformat(timespec="seconds")


class TestServiceStatus:
    @pytest.mark.asyncio
    async def test_a_critical_service_is_a_finding_not_a_failed_call(self, mock_checkmk_client):
        """The status line used to start with ❌ for CRITICAL -- the dispatcher's error marker."""
        mock_checkmk_client.get.return_value = {
            "success": True,
            "data": {
                "value": [
                    {
                        "extensions": {
                            "host_name": "defender",
                            "description": "Check_MK",
                            "state": 2,
                            "state_type": 1,
                            "plugin_output": "[agent] Communication failed",
                            "last_check": 1790982890,
                            "last_state_change": 1790900000,
                        }
                    }
                ]
            },
        }

        content = await ServiceHandler(mock_checkmk_client).handle(
            "vibemk_get_service_status", {"host_name": "defender", "service_description": "Check_MK"}
        )

        data = assert_valid("vibemk_get_service_status", content)
        assert data["state"] == "CRITICAL"
        assert data["state_code"] == 2
        assert data["is_hard_state"] is True
        assert data["plugin_output"] == "[agent] Communication failed"

    @pytest.mark.asyncio
    async def test_the_show_service_fallback_carries_structured_content_too(self, mock_checkmk_client):
        """show_service has no plugin_output, but its answer still has to fit the schema."""
        mock_checkmk_client.get.side_effect = [
            {"success": True, "data": {"value": []}},
            {
                "success": True,
                "data": {
                    "extensions": {
                        "host_name": "web01",
                        "description": "CPU load",
                        "state": 1,
                        "state_type": 0,
                        "last_check": 1790983377,
                    }
                },
            },
        ]

        content = await ServiceHandler(mock_checkmk_client).handle(
            "vibemk_get_service_status", {"host_name": "web01", "service_description": "CPU load"}
        )

        data = assert_valid("vibemk_get_service_status", content)
        assert data["state"] == "WARNING"
        assert data["is_hard_state"] is False
        assert data["plugin_output"] == ""
        assert data["last_state_change"] is None


class TestCurrentProblems:
    @pytest.mark.asyncio
    async def test_problems_say_whether_someone_already_handles_them(self, mock_checkmk_client):
        mock_checkmk_client.get.side_effect = [
            {
                "success": True,
                "data": {
                    "value": [
                        {
                            "extensions": {
                                "name": "defender",
                                "state": 1,
                                "acknowledged": 1,
                                "scheduled_downtime_depth": 0,
                            }
                        }
                    ]
                },
            },
            {
                "success": True,
                "data": {
                    "value": [
                        {
                            "extensions": {
                                "host_name": "defender",
                                "description": "Check_MK",
                                "state": 2,
                                "plugin_output": "timeout",
                                "last_state_change": 1790900000,
                                "acknowledged": 0,
                                "scheduled_downtime_depth": 1,
                            }
                        },
                        {"extensions": {"host_name": "defender", "description": "Uptime", "state": 0}},
                    ]
                },
            },
        ]

        content = await MonitoringHandler(mock_checkmk_client).handle("vibemk_get_current_problems", {})

        data = assert_valid("vibemk_get_current_problems", content)
        assert data["total"] == 2
        assert data["host_problems"] == [
            {"host_name": "defender", "state": "DOWN", "state_code": 1, "acknowledged": True, "in_downtime": False}
        ]
        assert data["service_problems"][0]["in_downtime"] is True
        text = content[0]["text"]
        assert "defender - DOWN (acknowledged)" in text, "clients that pass only text must see it as well"
        assert "CRITICAL (in downtime)" in text

    @pytest.mark.asyncio
    async def test_no_problems_still_carries_structured_content(self, mock_checkmk_client):
        mock_checkmk_client.get.return_value = {"success": True, "data": {"value": []}}

        content = await MonitoringHandler(mock_checkmk_client).handle("vibemk_get_current_problems", {})

        assert assert_valid("vibemk_get_current_problems", content) == {
            "total": 0,
            "host_problems": [],
            "service_problems": [],
        }


def _downtimes() -> Dict[str, Any]:
    """One host downtime running now and one service downtime starting tomorrow, as 2.5 lists them."""
    hour, day = datetime.timedelta(hours=1), datetime.timedelta(days=1)
    return {
        "success": True,
        "data": {
            "value": [
                {
                    "id": "8",
                    "extensions": {
                        "site_id": "cmk",
                        "host_name": "vibemk-test",
                        "author": "cmkadmin",
                        "start_time": _iso(-hour),
                        "end_time": _iso(hour),
                        "recurring": False,
                        "comment": "patching",
                        "mode": {"type": "fixed"},
                        "is_service": False,
                    },
                },
                {
                    "id": "9",
                    "extensions": {
                        "site_id": "cmk",
                        "host_name": "vibemk-test",
                        "author": "cmkadmin",
                        "start_time": _iso(day),
                        "end_time": _iso(day + hour),
                        "recurring": False,
                        "comment": "tomorrow",
                        "mode": {"type": "fixed"},
                        "is_service": True,
                        "service_description": "Uptime",
                    },
                },
            ]
        },
    }


class TestDowntimes:
    @pytest.mark.asyncio
    async def test_active_only_leaves_out_downtimes_that_have_not_started(self, mock_checkmk_client):
        """The filter read an is_pending field 2.5 does not send, so it never filtered anything."""
        mock_checkmk_client.get.return_value = _downtimes()

        content = await DowntimeHandler(mock_checkmk_client).handle("vibemk_list_downtimes", {})

        data = assert_valid("vibemk_list_downtimes", content)
        assert [d["downtime_id"] for d in data["downtimes"]] == ["8"]

    @pytest.mark.asyncio
    async def test_every_downtime_is_listed_with_its_kind_and_whether_it_runs(self, mock_checkmk_client):
        mock_checkmk_client.get.return_value = _downtimes()

        content = await DowntimeHandler(mock_checkmk_client).handle("vibemk_list_downtimes", {"active_only": False})

        host, service = assert_valid("vibemk_list_downtimes", content)["downtimes"]
        assert (host["is_service"], host["service_description"], host["active"]) == (False, None, True)
        assert (service["is_service"], service["service_description"], service["active"]) == (True, "Uptime", False)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("handler_class", "tool"),
        [(MonitoringHandler, "vibemk_get_downtimes"), (DowntimeHandler, "vibemk_get_active_downtimes")],
    )
    async def test_the_other_downtime_lists_fit_the_same_schema(self, mock_checkmk_client, handler_class, tool):
        mock_checkmk_client.get.return_value = _downtimes()

        content = await handler_class(mock_checkmk_client).handle(tool, {})

        assert_valid(tool, content)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("handler_class", "tool"),
        [
            (MonitoringHandler, "vibemk_get_downtimes"),
            (DowntimeHandler, "vibemk_list_downtimes"),
            (DowntimeHandler, "vibemk_get_active_downtimes"),
        ],
    )
    async def test_no_downtimes_still_carries_structured_content(self, mock_checkmk_client, handler_class, tool):
        mock_checkmk_client.get.return_value = {"success": True, "data": {"value": []}}

        content = await handler_class(mock_checkmk_client).handle(tool, {})

        assert assert_valid(tool, content) == {"total": 0, "downtimes": []}


class TestMetrics:
    @pytest.mark.asyncio
    async def test_listing_reads_the_metrics_column_it_asks_for(self, mock_checkmk_client):
        """Without columns the collection omits `metrics`, so every listing used to be empty."""
        mock_checkmk_client.get.return_value = {
            "success": True,
            "data": {
                "value": [{"extensions": {"host_name": "vibemk-test", "description": "Uptime", "metrics": ["uptime"]}}]
            },
        }

        content = await MetricsHandler(mock_checkmk_client).handle(
            "vibemk_get_service_metrics", {"host_name": "vibemk-test", "service_description": "Uptime"}
        )

        assert assert_valid("vibemk_get_service_metrics", content)["available_metrics"] == ["uptime"]
        assert "metrics" in mock_checkmk_client.get.call_args.kwargs["params"]["columns"]

    @pytest.mark.asyncio
    async def test_list_available_metrics_fits_its_schema(self, mock_checkmk_client):
        mock_checkmk_client.get.return_value = {
            "success": True,
            "data": {"value": [{"extensions": {"name": "vibemk-test", "metrics": ["rta", "pl"]}}]},
        }

        content = await MetricsHandler(mock_checkmk_client).handle(
            "vibemk_list_available_metrics", {"host_name": "vibemk-test"}
        )

        assert assert_valid("vibemk_list_available_metrics", content)["available_metrics"] == ["rta", "pl"]

    @pytest.mark.asyncio
    async def test_a_host_metric_is_requested_under_the_host_pseudo_service(self, mock_checkmk_client):
        """The endpoint requires service_description; without _HOST_ every host metric answered 400."""
        mock_checkmk_client.post.return_value = {
            "success": True,
            "data": {
                "time_range": {"start": "2026-10-02T20:23:00+00:00", "end": "2026-10-02T21:24:00+00:00"},
                "step": 60,
                "metrics": [{"title": "Round trip average", "data_points": [0.0001, 0.0003, None]}],
            },
        }

        content = await MetricsHandler(mock_checkmk_client).handle(
            "vibemk_get_host_metrics", {"host_name": "vibemk-test", "metric_name": "rta"}
        )

        data = assert_valid("vibemk_get_host_metrics", content)
        assert mock_checkmk_client.post.call_args.kwargs["data"]["service_description"] == "_HOST_"
        assert data["step"] == 60
        assert data["series"][0]["latest"] == 0.0003

    @pytest.mark.asyncio
    async def test_a_window_without_values_is_reported_not_crashed_on(self, mock_checkmk_client):
        """All-None points made the average "N/A", which the :.2f format then raised on."""
        mock_checkmk_client.post.return_value = {
            "success": True,
            "data": {"step": 60, "metrics": [{"title": "Uptime", "data_points": [None, None]}]},
        }

        content = await MetricsHandler(mock_checkmk_client).handle(
            "vibemk_get_service_metrics",
            {"host_name": "vibemk-test", "service_description": "Uptime", "metric_name": "uptime"},
        )

        data = assert_valid("vibemk_get_service_metrics", content)
        assert data["series"][0] == {
            "title": "Uptime",
            "points": 2,
            "latest": None,
            "min": None,
            "max": None,
            "avg": None,
        }
        assert "N/A (no values in this window)" in content[0]["text"]


def test_the_latest_value_is_the_last_one_carrying_a_value():
    """CheckMK's newest bucket is usually still empty -- "Latest Value: None" was the result."""
    summary = series_summary({"title": "Uptime", "data_points": [48597.9, 48655.1, None]})

    assert summary["latest"] == 48655.1
    assert (summary["min"], summary["max"], summary["points"]) == (48597.9, 48655.1, 3)
