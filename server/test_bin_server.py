import pytest

import datetime

from bin_server import (
    relative_date,
    DateInPastError,
)


class TestRelativeDate:

    @pytest.mark.parametrize(
        "now, then, exp",
        [
            # Same day
            (
                datetime.date(2000, 1, 1),
                datetime.date(2000, 1, 1),
                "today",
            ),
            # Tomorrow (different weeks)
            (
                datetime.date(2000, 1, 2),  # Sun
                datetime.date(2000, 1, 3),  # Mon
                "tomorrow",
            ),
            # Tomorrow (same week)
            (
                datetime.date(2000, 1, 3),  # Mon
                datetime.date(2000, 1, 4),  # Tue
                "tomorrow",
            ),
            # Weekday names
            (
                datetime.date(2000, 1, 1),  # Sat
                datetime.date(2000, 1, 3),  # Mon
                "monday",
            ),
            (
                datetime.date(2000, 1, 1),  # Sat
                datetime.date(2000, 1, 4),  # Tue
                "tuesday",
            ),
            (
                datetime.date(2000, 1, 1),  # Sat
                datetime.date(2000, 1, 5),  # Wed
                "wednesday",
            ),
            (
                datetime.date(2000, 1, 1),  # Sat
                datetime.date(2000, 1, 6),  # Thu
                "thursday",
            ),
            (
                datetime.date(2000, 1, 1),  # Sat
                datetime.date(2000, 1, 7),  # Fri
                "friday",
            ),
            (
                datetime.date(2000, 1, 2),  # Sun
                datetime.date(2000, 1, 8),  # Sat
                "saturday",
            ),
            (
                datetime.date(2000, 1, 3),  # Mon
                datetime.date(2000, 1, 9),  # Sun
                "sunday",
            ),
            # Next week
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 1, 12),  # Wed
                "next week",
            ),
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 1, 13),  # Thu
                "next week",
            ),
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 1, 14),  # Fri
                "next week",
            ),
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 1, 15),  # Sat
                "next week",
            ),
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 1, 16),  # Sun
                "next week",
            ),
            # Two weeks time (NB: by calendar week)
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 1, 17),  # Mon
                "week after next",
            ),
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 1, 23),  # Sun
                "week after next",
            ),
            # Three weeks time (NB: by calendar week)
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 1, 24),  # Mon
                "three weeks",
            ),
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 1, 30),  # Sun
                "three weeks",
            ),
            # Four weeks time (NB: by calendar week)
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 1, 31),  # Mon
                "four weeks",
            ),
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 2, 6),  # Sun
                "four weeks",
            ),
            # Beyond that: a long time!
            (
                datetime.date(2000, 1, 5),  # Wed
                datetime.date(2000, 2, 7),  # Mon
                "very long time",
            ),
        ],
    )
    def test_valid(self, now: datetime.date, then: datetime.date, exp: str) -> None:
        assert relative_date(now, then) == exp

    def test_in_past(self) -> None:
        with pytest.raises(DateInPastError):
            relative_date(datetime.date(2000, 1, 1), datetime.date(1999, 1, 1))
