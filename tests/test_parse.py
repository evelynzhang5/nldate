from datetime import date

import pytest

from nldate import parse

TODAY = date(2026, 11, 4)  # Wednesday


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("today", date(2026, 11, 4)),
        ("tomorrow", date(2026, 11, 5)),
        ("yesterday", date(2026, 11, 3)),
        ("in 3 days", date(2026, 11, 7)),
        ("2 weeks ago", date(2026, 10, 21)),
        ("next Tuesday", date(2026, 11, 10)),
        ("2025-12-01", date(2025, 12, 1)),
        ("2025/12/04", date(2025, 12, 4)),
        ("December 1st, 2025", date(2025, 12, 1)),
        ("5 days before December 1st, 2025", date(2025, 11, 26)),
        ("two weeks from tomorrow", date(2026, 11, 19)),
        ("1 year and 2 months after yesterday", date(2028, 1, 3)),
    ],
)
def test_parse_dates(text: str, expected: date) -> None:
    assert parse(text, today=TODAY) == expected


@pytest.mark.parametrize("text", ["", "   ", "not a date"])
def test_invalid_input(text: str) -> None:
    with pytest.raises(ValueError):
        parse(text, today=TODAY)
