# nldate

Parse common English date expressions into `datetime.date` values, using
deterministic pattern matching (no LLMs, no network calls, no dependencies).

```python
from datetime import date
from nldate import parse

parse("next Tuesday", today=date(2026, 11, 4))  # 2026-11-10
parse("1 year and 2 months after yesterday", today=date(2026, 11, 4))  # 2028-01-03
parse("December 1st, 2025")  # 2025-12-01
```

`parse(s, today=None)` resolves relative expressions against `today`, which
defaults to `date.today()`. It raises `ValueError` for empty, invalid or
unrecognized input, and for dates outside the range `date` supports.

There is also a small CLI: `nldate two weeks from tomorrow` prints an ISO date.

## Supported expressions

Input is case-insensitive, and extra whitespace is ignored.

| Kind | Examples |
| --- | --- |
| Relative days | `today`, `now`, `tomorrow`, `yesterday` |
| ISO dates | `2025-12-01` |
| Month-name dates | `December 1st, 2025`, `Dec 1 2025`, `Sept. 22nd`, `the 3rd of March 2027`, `11th November 2026` |
| Weekdays | `next Tuesday`, `last fri` |
| Offsets from today | `in 3 days`, `in a year`, `2 weeks ago` |
| Offsets from a date | `5 days before December 1st, 2025`, `3 days after 2025-12-30`, `two weeks from tomorrow` |
| Combined offsets | `1 year and 2 months after yesterday`, `1 year, 2 months and 3 days ago` |
| Nested offsets | `2 days after 3 days before tomorrow` |

Units are `day`, `week`, `fortnight`, `month` and `year` (singular or plural).
Amounts are digits, `a`/`an`, or written numbers from `zero` to `ninety-nine`
(`twenty-one` or `twenty one`).

## Design choices

- **Calendar arithmetic for months and years.** Adding a month moves to the
  same day of the next month. If that day doesn't exist, the result is
  clamped to the last day of the month: `1 month after January 31st, 2025` is
  2025-02-28, and `1 year after February 29th, 2024` is 2025-02-28.
- **Order in combined offsets.** All year and month parts are added together
  first (with clamping), then week and day parts. So
  `1 month and 1 day after January 31st, 2025` is Feb 28 + 1 day = 2025-03-01.
  This makes the result independent of the order the parts are written in.
- **`next`/`last` weekdays are strictly future/past.** `next Wednesday` on a
  Wednesday is 7 days later, not today; `last Wednesday` is 7 days earlier.
  `next Thursday` on a Wednesday is the following day. A bare weekday such as
  `Tuesday` is ambiguous and raises `ValueError`.
- **Month-name dates without a year** use the year of `today`, even if that
  date has already passed.
- **Validation is strict.** Impossible dates (`February 30th`), wrong ordinal
  suffixes (`December 2st`), and unknown units (`3 hours ago`) raise
  `ValueError` instead of being guessed at.

## Development

```sh
uv run pytest
uv run mypy src/
uv run ruff check
uv run ruff format --check
```
