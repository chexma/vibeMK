"""
Tests for the stdio transport.

The streams are injected, so the loop is exercised without a subprocess.
"""

import asyncio
import io
import json

from mcp.transport import StdioTransport


def responder(response=None):
    async def handle(request):
        if response is None:
            return {"jsonrpc": "2.0", "id": request.get("id"), "result": {"echo": request.get("method")}}
        return response

    return handle


def run_with(lines, handle):
    stdin = io.StringIO("".join(line + "\n" for line in lines))
    stdout = io.StringIO()

    asyncio.run(StdioTransport(handle, stdin=stdin, stdout=stdout).run())
    return [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]


def test_a_request_produces_one_response_line():
    written = run_with(['{"jsonrpc":"2.0","id":1,"method":"tools/list"}'], responder())

    assert written == [{"jsonrpc": "2.0", "id": 1, "result": {"echo": "tools/list"}}]


def test_a_malformed_line_is_skipped_and_the_loop_continues():
    written = run_with(["not json at all", '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'], responder())

    assert [r["id"] for r in written] == [2]


def test_a_blank_line_is_skipped():
    written = run_with(["", '{"jsonrpc":"2.0","id":3,"method":"tools/list"}'], responder())

    assert [r["id"] for r in written] == [3]


def test_a_notification_writes_nothing():
    async def handle(_request):
        return None

    assert run_with(['{"jsonrpc":"2.0","method":"notifications/initialized"}'], handle) == []


def test_the_loop_ends_at_end_of_input():
    # Completing at all is the assertion: a loop that does not stop hangs here.
    assert run_with([], responder()) == []


def test_non_ascii_content_survives_the_round_trip():
    written = run_with(
        ['{"jsonrpc":"2.0","id":4,"method":"tools/list"}'],
        responder({"jsonrpc": "2.0", "id": 4, "result": {"text": "Grüße 🚀"}}),
    )

    assert written[0]["result"]["text"] == "Grüße 🚀"
