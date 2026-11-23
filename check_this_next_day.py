#!/usr/bin/env python3
"""
Flag a "this <weekday>" / "next <weekday>" claim that doesn't match how
far that date actually is from the issue's send date.

    python3 check_this_next_day.py 2026-11-26

Built 2026-11-26 after the feature box for that issue called the Entry
of the Theotokos "This Friday, December 4" -- the issue sends Thursday
Nov 26, so the nearest actual Friday is the next day (Nov 27); December
4 is the Friday of the following week. Caught by Max reading the draft,
not by any existing check -- check_calendar.py verifies a date is a
real feast but not how the prose refers to it relative to send day.

Rule (deliberately simple, same narrow-by-design philosophy as
check_emoji_consistency.py): a weekday phrase paired with an explicit
date is checked against the gap in days from the issue date.
  - "this <weekday>" is only valid for a gap of 0-6 days.
  - "next <weekday>" is only valid for a gap of 7-13 days.
A gap outside both ranges (0-13 days) isn't flagged -- genuinely distant
dates ("in two months") don't use this phrasing in practice, and this
check isn't trying to validate every date reference in an issue, just
the specific this/next-weekday construction that caused the real
incident. English and Serbian (овог/следећег + genitive weekday) are
both covered since the bug appeared in both languages' copy.

Scans every drafts/<date>*.html variant that exists. Hard-fail (exit 1)
on any mismatch, same convention as check_links.py / check_title_date.py.
"""
import re
import sys
from datetime import date as _date
from pathlib import Path

from check_utils import CheckError, require_files

EN_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

# Serbian genitive month forms, as used in "4. децембра" style dates.
SR_MONTHS_GEN = {
    "јануара": 1, "фебруара": 2, "марта": 3, "априла": 4, "маја": 5, "јуна": 6,
    "јула": 7, "августа": 8, "септембра": 9, "октобра": 10, "новембра": 11,
    "децембра": 12,
}

# Serbian genitive weekday forms, as used after "овог"/"ове"/"следећег"/"следеће".
SR_WEEKDAYS_GEN = {
    "понедељка": 0, "уторка": 1, "среде": 2, "четвртка": 3,
    "петка": 4, "суботе": 5, "недеље": 6,
}

EN_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

# "this Friday, December 4" / "This Friday, December 4,"
EN_PATTERN = re.compile(
    r"\b(this|next)\s+(" + "|".join(EN_WEEKDAYS) + r")\b[,\s]{1,3}"
    r"(" + "|".join(EN_MONTHS) + r")\s+(\d{1,2})\b",
    re.IGNORECASE,
)

# "Овог петка, 4. децембра" / "Следећег петка, 4. дец" (abbreviated month not
# matched here -- the full genitive month name is what the real prose uses).
SR_PATTERN = re.compile(
    r"\b(овог|ове|следећег|следеће)\s+(" + "|".join(SR_WEEKDAYS_GEN) + r")\b[,\s]{1,3}"
    r"(\d{1,2})\.\s*(" + "|".join(SR_MONTHS_GEN) + r")\b",
    re.IGNORECASE,
)

SR_THIS_WORDS = {"овог", "ове"}


def find_mismatches(text, filename, issue_date):
    findings = []

    for m in EN_PATTERN.finditer(text):
        qualifier, weekday_word, month_word, day_str = m.groups()
        target = _date(issue_date.year, EN_MONTHS[month_word.lower()], int(day_str))
        if target < issue_date:
            target = _date(issue_date.year + 1, target.month, target.day)
        gap = (target - issue_date).days
        findings.extend(
            _check_gap(filename, text, m.start(), qualifier.lower(), gap, target, m.group(0))
        )

    for m in SR_PATTERN.finditer(text):
        qualifier_word, weekday_word, day_str, month_word = m.groups()
        qualifier = "this" if qualifier_word.lower() in SR_THIS_WORDS else "next"
        target = _date(issue_date.year, SR_MONTHS_GEN[month_word.lower()], int(day_str))
        if target < issue_date:
            target = _date(issue_date.year + 1, target.month, target.day)
        gap = (target - issue_date).days
        findings.extend(
            _check_gap(filename, text, m.start(), qualifier, gap, target, m.group(0))
        )

    return findings


def _check_gap(filename, text, pos, qualifier, gap, target, phrase):
    line_no = text.count("\n", 0, pos) + 1
    if qualifier == "this" and not (0 <= gap <= 6):
        return [
            f"{filename}:{line_no}: {phrase!r} says \"this\" but {target.isoformat()} "
            f"is {gap} day(s) after the issue date -- should be \"next\" (or isn't within "
            f"this issue's week at all)"
        ]
    if qualifier == "next" and not (7 <= gap <= 13):
        return [
            f"{filename}:{line_no}: {phrase!r} says \"next\" but {target.isoformat()} "
            f"is {gap} day(s) after the issue date -- should be \"this\" (or isn't a "
            f"following-week date at all)"
        ]
    return []


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <date>  e.g. {sys.argv[0]} 2026-11-26", file=sys.stderr)
        sys.exit(1)
    date_str = sys.argv[1]
    issue_date = _date(*(int(x) for x in date_str.split("-")))

    candidates = [
        Path(f"drafts/{date_str}.html"),
        Path(f"drafts/{date_str}.both.html"),
        Path(f"drafts/{date_str}.site.html"),
        Path(f"drafts/{date_str}.email.html"),
        Path(f"drafts/{date_str}.other.html"),
        Path(f"drafts/{date_str}.serbian.html"),
    ]
    existing = [p for p in candidates if p.exists()]
    try:
        require_files(*candidates[:1])  # at minimum drafts/<date>.html must exist
    except CheckError as e:
        print(f"check_this_next_day: {e}", file=sys.stderr)
        sys.exit(1)

    all_findings = []
    for path in existing:
        text = path.read_text(encoding="utf-8")
        all_findings.extend(find_mismatches(text, str(path), issue_date))

    if all_findings:
        print("check_this_next_day: MISMATCH")
        for f in all_findings:
            print(f"  {f}")
        sys.exit(1)

    print(f"check_this_next_day: OK ({len(existing)} file(s) checked, 0 mismatches)")


if __name__ == "__main__":
    main()
