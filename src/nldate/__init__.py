"""Deterministic natural-language date parsing.

The grammar, after normalizing case, whitespace and commas, is roughly::

    expr    := offsets ("before" | "after" | "from") expr
             | offsets "ago"
             | "in" offsets
             | base
    offsets := offset (("and" | ",") offset)*
    offset  := number unit
    base    := today | tomorrow | yesterday | now
             | [the] day after tomorrow | [the] day before yesterday
             | ISO date | YYYY/M/D date | month-name date | (next | last) weekday
"""

import calendar
import re
import sys
from collections.abc import Sequence
from datetime import date, timedelta

__all__ = ["parse"]

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "mon": 0,
    "tue": 1,
    "tues": 1,
    "wed": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

_SMALL_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

# Unit name -> (days, months) contributed by one unit.
_UNITS = {
    "day": (1, 0),
    "week": (7, 0),
    "fortnight": (14, 0),
    "month": (0, 1),
    "year": (0, 12),
}

_RELATIVE_DAYS = {
    "today": 0,
    "now": 0,
    "tomorrow": 1,
    "yesterday": -1,
    "the day after tomorrow": 2,
    "day after tomorrow": 2,
    "the day before yesterday": -2,
    "day before yesterday": -2,
}

_ORDINAL = r"(?P<day>\d{1,2})(?P<suffix>st|nd|rd|th)?"
_YEAR = r"(?:,? (?P<year>\d{4}))?"
_MONTH_FIRST = re.compile(rf"(?P<month>[a-z]+)\.? {_ORDINAL}{_YEAR}")
_DAY_FIRST = re.compile(rf"(?:the )?{_ORDINAL} (?:of )?(?P<month>[a-z]+)\.?{_YEAR}")
_ISO = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})")
_SLASHED = re.compile(r"(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})")
_WEEKDAY = re.compile(r"(?P<direction>next|last) (?P<weekday>[a-z]+)")
_RELATION = re.compile(r" (before|after|from) ")
_OFFSET_SEPARATOR = re.compile(r", and |, | and ")


def parse(s: str, today: date | None = None) -> date:
    """Convert a natural-language date expression into a date.

    ``today`` is the reference date for relative expressions and defaults to
    ``date.today()``. Raises ``ValueError`` if the input is empty, cannot be
    understood, or describes an impossible date.
    """
    if today is None:
        today = date.today()
    text = _normalize(s)
    if not text:
        raise ValueError("empty date expression")
    try:
        return _parse_expr(text, today)
    except OverflowError as exc:
        raise ValueError(f"date out of range: {s!r}") from exc


def _normalize(s: str) -> str:
    text = " ".join(s.lower().split())
    return re.sub(r" ?, ?", ", ", text)


def _parse_expr(text: str, today: date) -> date:
    # "<offsets> before/after/from <expr>". Try each connector position so
    # nested expressions such as "2 days after 3 days before today" work.
    for match in _RELATION.finditer(text):
        offsets = _parse_offsets(text[: match.start()])
        if offsets is None:
            continue
        base = _parse_expr(text[match.end() :], today)
        sign = -1 if match.group(1) == "before" else 1
        return _shift(base, offsets, sign)

    if text.endswith(" ago"):
        offsets = _parse_offsets(text[: -len(" ago")])
        if offsets is not None:
            return _shift(today, offsets, -1)

    if text.startswith("in "):
        offsets = _parse_offsets(text[len("in ") :])
        if offsets is not None:
            return _shift(today, offsets, 1)

    return _parse_base(text, today)


def _parse_offsets(text: str) -> tuple[int, int] | None:
    """Parse "1 year and 2 months" into (days, months), or None if invalid."""
    total_days = 0
    total_months = 0
    for part in _OFFSET_SEPARATOR.split(text):
        words = part.split(" ")
        if len(words) < 2:
            return None
        unit = words[-1].removesuffix("s")
        if unit not in _UNITS:
            return None
        amount = _parse_number(" ".join(words[:-1]))
        if amount is None:
            return None
        days, months = _UNITS[unit]
        total_days += amount * days
        total_months += amount * months
    return total_days, total_months


def _parse_number(text: str) -> int | None:
    if text.isascii() and text.isdigit():
        return int(text)
    if text in ("a", "an"):
        return 1
    if text in _SMALL_NUMBERS:
        return _SMALL_NUMBERS[text]
    if text in _TENS:
        return _TENS[text]
    tens, sep, ones = text.replace("-", " ").partition(" ")
    if (
        sep
        and tens in _TENS
        and ones in _SMALL_NUMBERS
        and 0 < _SMALL_NUMBERS[ones] < 10
    ):
        return _TENS[tens] + _SMALL_NUMBERS[ones]
    return None


def _shift(base: date, offsets: tuple[int, int], sign: int) -> date:
    """Apply months/years first (clamping the day), then days/weeks."""
    days, months = offsets
    return _add_months(base, sign * months) + timedelta(days=sign * days)


def _add_months(base: date, months: int) -> date:
    index = base.year * 12 + (base.month - 1) + months
    year, month = divmod(index, 12)
    if not 1 <= year <= 9999:
        raise OverflowError("year out of range")
    last_day = calendar.monthrange(year, month + 1)[1]
    return date(year, month + 1, min(base.day, last_day))


def _parse_base(text: str, today: date) -> date:
    if text in _RELATIVE_DAYS:
        return today + timedelta(days=_RELATIVE_DAYS[text])

    if match := _ISO.fullmatch(text) or _SLASHED.fullmatch(text):
        return date(int(match["year"]), int(match["month"]), int(match["day"]))

    for pattern in (_MONTH_FIRST, _DAY_FIRST):
        match = pattern.fullmatch(text)
        if match and match["month"] in _MONTHS:
            return _month_name_date(match, today)

    if (match := _WEEKDAY.fullmatch(text)) and match["weekday"] in _WEEKDAYS:
        target = _WEEKDAYS[match["weekday"]]
        if match["direction"] == "next":
            delta = (target - today.weekday() - 1) % 7 + 1
        else:
            delta = -((today.weekday() - target - 1) % 7 + 1)
        return today + timedelta(days=delta)

    raise ValueError(f"unrecognized date expression: {text!r}")


def _month_name_date(match: re.Match[str], today: date) -> date:
    day = int(match["day"])
    suffix = match["suffix"]
    if suffix is not None and suffix != _ordinal_suffix(day):
        raise ValueError(f"wrong ordinal suffix: {day}{suffix}")
    year = int(match["year"]) if match["year"] else today.year
    return date(year, _MONTHS[match["month"]], day)


def _ordinal_suffix(day: int) -> str:
    if 10 <= day % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point: print the parsed date in ISO format."""
    args = sys.argv[1:] if argv is None else list(argv)
    try:
        print(parse(" ".join(args)).isoformat())
    except ValueError as exc:
        print(f"nldate: {exc}", file=sys.stderr)
        return 1
    return 0
