from datetime import date

import pytest

from nldate import main, parse

TODAY = date(2026, 11, 4)  # Wednesday


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Capitalization and whitespace
        ("  ToDay  ", date(2026, 11, 4)),
        ("NEXT   tuesday", date(2026, 11, 10)),
        ("December 1st ,  2025", date(2025, 12, 1)),
        # Strictly future/past weekdays
        ("next Wednesday", date(2026, 11, 11)),
        ("last Wednesday", date(2026, 10, 28)),
        ("last Tuesday", date(2026, 11, 3)),
        ("next Thursday", date(2026, 11, 5)),
        ("next fri", date(2026, 11, 6)),
        # Month-name formats
        ("Dec 1 2025", date(2025, 12, 1)),
        ("Sept. 22nd, 2024", date(2024, 9, 22)),
        ("the 3rd of March 2027", date(2027, 3, 3)),
        ("11th November 2026", date(2026, 11, 11)),
        ("March 3", date(2026, 3, 3)),
        ("February 29th, 2024", date(2024, 2, 29)),
        # Offsets
        ("in 1 month", date(2026, 12, 4)),
        ("in a year", date(2027, 11, 4)),
        ("a week ago", date(2026, 10, 28)),
        ("3 years ago", date(2023, 11, 4)),
        ("in 2 weeks and 3 days", date(2026, 11, 21)),
        ("1 year, 2 months and 3 days ago", date(2025, 9, 1)),
        ("10 days from now", date(2026, 11, 14)),
        ("twenty-one days from today", date(2026, 11, 25)),
        ("thirty one days before today", date(2026, 10, 4)),
        ("a fortnight after next Monday", date(2026, 11, 23)),
        ("3 days after 2025-12-30", date(2026, 1, 2)),
        # Slashed year/month/day dates
        ("2025/1/5", date(2025, 1, 5)),
        ("  2024/02/29 ", date(2024, 2, 29)),
        ("5 days before 2025/12/04", date(2025, 11, 29)),
        ("1 month after 2025/01/31", date(2025, 2, 28)),
        # Day after tomorrow / day before yesterday
        ("day after tomorrow", date(2026, 11, 6)),
        ("day before yesterday", date(2026, 11, 2)),
        ("  The   Day After  TOMORROW ", date(2026, 11, 6)),
        ("two weeks from the day after tomorrow", date(2026, 11, 20)),
        ("3 days before the day before yesterday", date(2026, 10, 30)),
        # Nested offsets
        ("2 days after 3 days before tomorrow", date(2026, 11, 4)),
        # Month clamping
        ("1 month after January 31st, 2025", date(2025, 2, 28)),
        ("1 month after January 31st, 2024", date(2024, 2, 29)),
        ("1 year after February 29th, 2024", date(2025, 2, 28)),
        ("1 month before March 31st, 2026", date(2026, 2, 28)),
        # Months/years apply before days/weeks
        ("1 month and 1 day after January 31st, 2025", date(2025, 3, 1)),
        ("0 days ago", date(2026, 11, 4)),
    ],
)
def test_edge_cases(text: str, expected: date) -> None:
    assert parse(text, today=TODAY) == expected


@pytest.mark.parametrize(
    "text",
    [
        "\t\n",
        "next",
        "tuesday",
        "next blursday",
        "in days",
        "3 days",
        "3 hours ago",
        "3 days before",
        "before tomorrow",
        "2025-13-01",
        "2025-1-1",
        "2025/02/30",
        "2025/13/01",
        "2025/00/10",
        "2025/12/0",
        "2025/12-04",
        "2025//12/04",
        "12/04/2025",
        "2025/123/4",
        "3 days after 2025/02/29",
        "February 30th, 2025",
        "December 2st, 2025",
        "Smarch 3rd, 2025",
        "twenty-zero days ago",
        "in 3 days ago",
        "10000 years from today",
        "3000 years ago",
    ],
)
def test_more_invalid_input(text: str) -> None:
    with pytest.raises(ValueError):
        parse(text, today=TODAY)


@pytest.mark.parametrize(
    ("text", "today", "expected"),
    [
        # Month boundaries
        ("the day after tomorrow", date(2026, 11, 29), date(2026, 12, 1)),
        ("the day before yesterday", date(2026, 12, 1), date(2026, 11, 29)),
        ("the day after tomorrow", date(2024, 2, 28), date(2024, 3, 1)),
        ("the day after tomorrow", date(2025, 2, 27), date(2025, 3, 1)),
        ("day before yesterday", date(2024, 3, 1), date(2024, 2, 28)),
        # Year boundaries
        ("the day after tomorrow", date(2026, 12, 30), date(2027, 1, 1)),
        ("the day after tomorrow", date(2026, 12, 31), date(2027, 1, 2)),
        ("the day before yesterday", date(2027, 1, 1), date(2026, 12, 30)),
        ("day before yesterday", date(2027, 1, 2), date(2026, 12, 31)),
        # As a reference date across a boundary
        ("1 month after the day after tomorrow", date(2026, 1, 29), date(2026, 2, 28)),
        ("2 days after the day before yesterday", date(2027, 1, 1), date(2027, 1, 1)),
    ],
)
def test_day_after_tomorrow_boundaries(text: str, today: date, expected: date) -> None:
    assert parse(text, today=today) == expected


@pytest.mark.parametrize(
    "text",
    [
        "the day after",
        "the day before",
        "the day after today",
        "the day after next tuesday",
        "the the day after tomorrow",
        "day after",
    ],
)
def test_day_after_tomorrow_invalid(text: str) -> None:
    with pytest.raises(ValueError):
        parse(text, today=TODAY)


def test_defaults_to_real_today() -> None:
    assert parse("today") == date.today()


def test_main(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["2025-12-01"]) == 0
    assert capsys.readouterr().out == "2025-12-01\n"
    assert main(["nonsense"]) == 1
    assert "unrecognized" in capsys.readouterr().err
