"""
Requests a handler makes side by side.

Some tools have to ask CheckMK the same question once per ruleset. The client
blocks in urllib, so those requests run on threads -- in the order the caller
gave, and never more at once than the limit allows: the Ultimate test
instance has two CPUs, and a production site has better things to do.
"""

import threading
import time
from typing import Any, Dict, List

import pytest

from vibemk.handlers.active_checks import ActiveChecksHandler
from vibemk.handlers.base import BaseHandler


class Handler(BaseHandler):
    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []


@pytest.fixture
def handler(mock_checkmk_client):
    return Handler(mock_checkmk_client)


class TestMappingConcurrently:
    def test_results_come_back_in_the_order_of_the_items(self, handler):
        def slower_for_earlier(n: int) -> int:
            time.sleep((5 - n) * 0.01)
            return n * 10

        assert handler._map_concurrently(slower_for_earlier, range(5)) == [0, 10, 20, 30, 40]

    def test_the_requests_overlap(self, handler):
        """Four calls that each wait for all four can only finish together."""
        barrier = threading.Barrier(4, timeout=2)

        def wait_for_the_others(n: int) -> int:
            barrier.wait()
            return n

        assert handler._map_concurrently(wait_for_the_others, range(4), max_concurrent=4) == [0, 1, 2, 3]

    def test_no_more_run_at_once_than_the_limit(self, handler):
        lock = threading.Lock()
        running = 0
        peak = 0

        def track(_: int) -> None:
            nonlocal running, peak
            with lock:
                running += 1
                peak = max(peak, running)
            time.sleep(0.02)
            with lock:
                running -= 1

        handler._map_concurrently(track, range(12), max_concurrent=3)

        assert peak == 3

    def test_a_failing_request_raises_as_it_would_have_in_a_loop(self, handler):
        def fail_on_two(n: int) -> int:
            if n == 2:
                raise RuntimeError("boom")
            return n

        with pytest.raises(RuntimeError, match="boom"):
            handler._map_concurrently(fail_on_two, range(4))

    def test_nothing_to_do_returns_nothing(self, handler):
        assert handler._map_concurrently(lambda n: n, []) == []


class TestActiveChecksAskTheirRulesetsSideBySide:
    @pytest.fixture
    def active_checks(self, mock_checkmk_client):
        handler = ActiveChecksHandler(mock_checkmk_client)

        def rules_of(_endpoint: str, params: Dict[str, str]) -> Dict[str, Any]:
            ruleset = params["ruleset_name"]
            # The first ruleset answers last, so a listing assembled in
            # completion order would put it at the end.
            time.sleep(0.03 if ruleset == ActiveChecksHandler._ALL_RULESETS[0] else 0)
            rule = {
                "id": f"rule-{ruleset}",
                "extensions": {
                    "conditions": {"host_name": {"match_on": ["web01"]}},
                    "value_raw": "{}",
                    "properties": {},
                },
            }
            return {"success": True, "data": {"value": [rule]}}

        handler.client.get.side_effect = rules_of
        return handler

    @pytest.mark.asyncio
    async def test_the_listing_keeps_the_ruleset_order(self, active_checks):
        result = await active_checks.handle("vibemk_list_active_checks", {})

        text = result[0]["text"]
        positions = [text.index(f"rule-{ruleset}") for ruleset in ActiveChecksHandler._ALL_RULESETS]
        assert positions == sorted(positions)

    @pytest.mark.asyncio
    async def test_deleting_by_host_finds_matches_in_ruleset_order(self, active_checks):
        result = await active_checks.handle("vibemk_delete_active_check", {"hostname": "web01"})

        text = result[0]["text"]
        positions = [text.index(f"rule-{ruleset}") for ruleset in ActiveChecksHandler._ALL_RULESETS]
        assert positions == sorted(positions)
