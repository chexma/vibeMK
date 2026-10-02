"""
Tests that CheckMK's own explanation reaches the caller.

The client parses the error body and hands it to the exception, but every
handler renders the exception with str(e) — and that was only
"HTTP 400: Bad Request". CheckMK had said which field was wrong; the model
never saw it, so it could only retry the same call or give up.

There is a second, related fact worth pinning down: the client *raises* on
every HTTP error and never returns a result with success=False. Handlers are
full of `if not result.get("success")` branches written on the opposite
assumption. They are unreachable, and a test that mocks success=False to
exercise one is testing something that cannot happen.
"""

import inspect

from vibemk.api.client import CheckMKClient
from vibemk.api.exceptions import CheckMKAPIError, CheckMKError


class TestTheExplanationSurvivesToTheMessage:
    def test_the_detail_is_part_of_the_string(self) -> None:
        error = CheckMKAPIError(
            "HTTP 400: Bad Request",
            400,
            {"title": "Bad Request", "detail": "These fields have problems: ipaddress"},
        )

        assert "ipaddress" in str(error)

    def test_the_original_message_is_kept(self) -> None:
        error = CheckMKAPIError("HTTP 400: Bad Request", 400, {"detail": "nope"})

        assert "HTTP 400" in str(error)

    def test_a_title_is_used_when_there_is_no_detail(self) -> None:
        error = CheckMKAPIError("HTTP 409: Conflict", 409, {"title": "The host is already known"})

        assert "already known" in str(error)

    def test_a_detail_that_merely_repeats_the_message_is_not_doubled(self) -> None:
        error = CheckMKAPIError("HTTP 404: Not Found", 404, {"title": "Not Found"})

        assert str(error).count("Not Found") == 1

    def test_an_error_without_a_body_reads_as_before(self) -> None:
        assert str(CheckMKError("Connection refused")) == "Connection refused"

    def test_a_non_dict_body_does_not_crash_the_message(self) -> None:
        error = CheckMKAPIError("HTTP 502: Bad Gateway", 502, {"raw": "<html>gateway</html>"})

        assert "502" in str(error)


class TestTheClientRaisesRatherThanReporting:
    def test_every_successful_result_is_marked_successful(self) -> None:
        # The invariant the handlers' `if not result.get("success")` branches
        # were written against: there is no other value. Asserting it here
        # keeps the next reader from adding a branch that cannot run.
        source = inspect.getsource(CheckMKClient)

        assert source.count('"success"') == 1, "a second success value would make the branches meaningful again"
        assert '"success": True' in source
