"""
The time handling behind scheduling a downtime.

`downtimes.py` is the largest handler in the project and was the least
covered. Most of it is formatting, but the part that decides *when* a
downtime starts and ends is arithmetic, and getting it wrong does not
produce an error -- it produces a maintenance window at the wrong hour,
which nobody notices until the alerts arrive.

These cover the duration grammar the README advertises ("2h", "1h30m"), the
timestamp conversions used to decide whether a downtime is running, and the
timezone handling, which was wrong: natural-language times were read as
local and then labelled UTC.
"""

import datetime
import time
from unittest.mock import MagicMock

import pytest

from handlers.downtimes import DowntimeHandler


@pytest.fixture
def handler():
    return DowntimeHandler(MagicMock())


@pytest.fixture
def away_from_utc(monkeypatch):
    """Run the body in a timezone that is not UTC.

    CI runners are UTC, where local and UTC agree and a test that compares
    them passes whatever the code does -- the buggy version passed this
    file's conversion test on a UTC machine. Asia/Kolkata is +5:30 all year:
    no DST to reason about, and the half hour catches arithmetic that only
    handles whole-hour offsets.
    """
    if not hasattr(time, "tzset"):
        pytest.skip("the timezone cannot be changed at runtime on this platform")

    monkeypatch.setenv("TZ", "Asia/Kolkata")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


class TestTheDurationGrammar:
    """What the README promises: "2h", "1h30m"."""

    @pytest.mark.parametrize(
        ("text", "minutes"),
        [
            ("30m", 30),
            ("2h", 120),
            ("1d", 1440),
            ("1h30m", 90),
            ("2d4h", 3120),
            ("1d2h30m", 1590),
        ],
    )
    def test_it_reads_the_documented_forms(self, handler, text, minutes):
        assert handler._parse_time_delta(text) == minutes

    def test_a_leading_plus_is_a_direction_not_a_digit(self, handler):
        """start_time uses "+1h" to mean "an hour from now"."""
        assert handler._parse_time_delta("+1h") == handler._parse_time_delta("1h")

    def test_a_bare_number_is_minutes(self, handler):
        assert handler._parse_time_delta("45") == 45

    def test_the_components_are_case_insensitive(self, handler):
        assert handler._parse_time_delta("2H30M") == 150

    def test_an_unparseable_duration_falls_back_to_an_hour(self, handler):
        """Rather than raising, which would lose the whole request.

        Note that this makes a typo silent: "90s" is not a supported unit,
        so it becomes 60 minutes rather than an error.
        """
        assert handler._parse_time_delta("later") == 60
        assert handler._parse_time_delta("90s") == 60


class TestReadingTimestampsBackFromCheckmk:
    """CheckMK returns start/end times as either ISO strings or Unix numbers."""

    def test_an_iso_string_with_z_is_understood(self, handler):
        assert handler._format_timestamp("2026-03-01T22:00:00Z") == "2026-03-01 22:00"

    def test_a_unix_number_is_understood(self, handler):
        stamp = datetime.datetime(2026, 3, 1, 22, 0).timestamp()

        assert handler._format_timestamp(stamp) == "2026-03-01 22:00"

    @pytest.mark.parametrize("value", [None, 0, "", "not a time", {}])
    def test_anything_unreadable_says_so_rather_than_guessing(self, handler, value):
        assert handler._format_timestamp(value) == "Unknown"

    def test_unix_conversion_round_trips_an_iso_string(self, handler):
        text = "2026-03-01T22:00:00+00:00"
        expected = datetime.datetime.fromisoformat(text).timestamp()

        assert handler._timestamp_to_unix(text) == expected

    @pytest.mark.parametrize("value", [None, "", "not a time", {}])
    def test_unix_conversion_of_rubbish_is_zero_not_an_exception(self, handler, value):
        """Zero sorts before every real downtime, so it reads as "not active"."""
        assert handler._timestamp_to_unix(value) == 0.0


class TestDecidingWhetherADowntimeIsRunning:
    """`_is_downtime_active` answers the question the status tools report."""

    @staticmethod
    def _downtime(start, end):
        return {"extensions": {"start_time": start, "end_time": end}}

    def test_a_window_containing_now_is_active(self, handler):
        assert handler._is_downtime_active(self._downtime(100, 200), 150) is True

    def test_the_boundaries_are_inclusive(self, handler):
        assert handler._is_downtime_active(self._downtime(100, 200), 100) is True
        assert handler._is_downtime_active(self._downtime(100, 200), 200) is True

    def test_a_window_that_has_passed_is_not_active(self, handler):
        assert handler._is_downtime_active(self._downtime(100, 200), 201) is False

    def test_a_window_that_has_not_started_is_not_active(self, handler):
        assert handler._is_downtime_active(self._downtime(100, 200), 99) is False

    def test_iso_strings_are_compared_the_same_as_numbers(self, handler):
        start = "2026-03-01T22:00:00+00:00"
        end = "2026-03-01T23:00:00+00:00"
        inside = datetime.datetime.fromisoformat("2026-03-01T22:30:00+00:00").timestamp()

        assert handler._is_downtime_active(self._downtime(start, end), inside) is True

    def test_an_unreadable_window_is_not_reported_as_active(self, handler):
        """Claiming a downtime is running when it cannot be read would
        suppress alerts that should fire."""
        assert handler._is_downtime_active(self._downtime("nonsense", "also nonsense"), 150) is False

    def test_a_downtime_without_extensions_is_not_active(self, handler):
        assert handler._is_downtime_active({}, 150) is False


class TestTheScheduleIsExpressedInUTC:
    """The API is sent `...Z`, so everything handed to it must be UTC.

    This was the defect: the relative and default paths used utcnow(), but
    natural-language times came from datetime.now() -- local -- and were then
    stamped with the same Z. In Europe/Berlin "22:00 tomorrow", the example in
    the project's own README, produced 22:00Z, which is midnight local. The
    maintenance window opened two hours after the operator meant it to.
    """

    @staticmethod
    def _as_utc(stamp: str) -> datetime.datetime:
        return datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)

    def test_a_parsed_wall_clock_time_carries_an_offset(self, handler):
        """The assertion that holds in every timezone, UTC included.

        The defect was a *naive* datetime being labelled Z. Comparing local
        against UTC cannot catch that on a UTC machine -- but a missing
        tzinfo is missing everywhere, so this is the guard that still works
        on a CI runner.
        """
        parsed = handler._parse_natural_time("22:00 tomorrow")

        assert parsed is not None
        assert parsed.tzinfo is not None, "a wall-clock time was parsed without an offset"

    def test_a_wall_clock_time_is_converted_from_local_to_utc(self, handler, away_from_utc):
        times = handler._parse_downtime_times("22:00 tomorrow", None, 120)

        # 22:00 tomorrow on the operator's wall clock, expressed in UTC.
        local = (
            (datetime.datetime.now() + datetime.timedelta(days=1))
            .replace(hour=22, minute=0, second=0, microsecond=0)
            .astimezone()
        )
        expected = local.astimezone(datetime.timezone.utc)

        assert self._as_utc(times["start_time"]) == expected

    def test_now_means_now(self, handler):
        times = handler._parse_downtime_times("now", None, 60)

        drift = abs((self._as_utc(times["start_time"]) - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
        assert drift < 5, f"start drifted {drift}s from the actual moment"

    def test_a_relative_start_is_measured_from_now(self, handler):
        times = handler._parse_downtime_times("+2h", None, 60)

        expected = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)
        drift = abs((self._as_utc(times["start_time"]) - expected).total_seconds())
        assert drift < 5

    def test_the_duration_decides_the_end_when_none_is_given(self, handler):
        times = handler._parse_downtime_times("now", None, 90)

        span = self._as_utc(times["end_time"]) - self._as_utc(times["start_time"])
        assert span == datetime.timedelta(minutes=90)

    def test_a_relative_end_is_measured_from_the_start(self, handler):
        times = handler._parse_downtime_times("now", "+45m", 120)

        span = self._as_utc(times["end_time"]) - self._as_utc(times["start_time"])
        assert span == datetime.timedelta(minutes=45)

    def test_an_end_before_the_start_is_pushed_past_it(self, handler):
        """CheckMK would reject the window, and the operator would lose the
        request; extending by the duration keeps it usable."""
        times = handler._parse_downtime_times("22:00 today", "21:00 today", 60)

        assert self._as_utc(times["end_time"]) > self._as_utc(times["start_time"])

    def test_the_format_is_the_one_the_api_accepts(self, handler):
        times = handler._parse_downtime_times("now", None, 60)

        for value in times.values():
            datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
