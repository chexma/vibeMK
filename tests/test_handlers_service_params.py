"""
Listing process monitoring rules.

CheckMK hands a rule's value back as `value_raw`, a Python literal in a
string. The listing used to read it with eval(), which runs whatever the
string says -- and the string comes from the server, so anyone who can write
a rule, or anything between vibeMK and CheckMK, could run code in vibeMK.
It is data, and ast.literal_eval reads it as data.
"""

import ast
import pathlib

import pytest

from vibemk.handlers.service_params import ServiceParamsHandler


def rule(value_raw: str) -> dict:
    return {
        "id": "rule-1",
        "extensions": {
            "conditions": {"host_name": {"match_on": ["web01"]}},
            "value_raw": value_raw,
            "properties": {},
        },
    }


@pytest.fixture
def handler(mock_checkmk_client):
    return ServiceParamsHandler(mock_checkmk_client)


def answer_with(handler, *rules):
    handler.client.get.return_value = {"success": True, "data": {"value": list(rules)}}


class TestTheRuleValueIsReadAsData:
    @pytest.mark.asyncio
    async def test_a_value_that_is_code_is_not_run(self, handler, tmp_path):
        marker = tmp_path / "ran"
        answer_with(handler, rule(f"open({str(marker)!r}, 'w')"))

        result = await handler.handle("vibemk_list_process_rules", {})

        assert not marker.exists()
        # Shown raw instead, as any value that does not parse is
        assert "open(" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_a_process_rule_is_rendered(self, handler):
        answer_with(
            handler,
            rule(
                "{'descr': 'nginx', 'match': '~nginx', "
                "'default_params': {'levels': (1, 1, 10, 12), 'cpulevels': (80.0, 90.0)}}"
            ),
        )

        result = await handler.handle("vibemk_list_process_rules", {})

        text = result[0]["text"]
        assert "**Process nginx**" in text
        assert "`~nginx`" in text
        assert "min warn/crit: 1/1, max warn/crit: 10/12" in text
        assert "CPU warn/crit: 80.0%/90.0%" in text


def test_no_shipped_module_calls_eval_or_exec():
    """Every value CheckMK returns is data. Reading one should never run it."""
    root = pathlib.Path(__file__).resolve().parent.parent
    guilty = []
    sources = sorted((root / "src" / "vibemk").rglob("*.py"))
    assert sources, "no shipped source found"
    for path in sources:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                guilty.append(f"{path.relative_to(root)}:{node.lineno}: {node.func.id}()")

    assert guilty == [], f"eval/exec in shipped source: {guilty}"
