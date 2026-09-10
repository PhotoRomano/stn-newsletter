#!/usr/bin/env python3
"""
Cross-check "This Week at the Altar" against the parish's own live
calendar data before finalizing a draft.

    python3 check_calendar.py 2026-09-10

Fetches stnicholasphilly.org/calendar.html, pulls its `FEASTS` JS array
(the site's own list of Great Feasts and parish fundraising events), and
prints any entries that fall within the target week -- plus the standing
weekly baseline (Sunday Divine Liturgy, Saturday/eve Great Vespers).

IMPORTANT -- this is a checklist, not an auto-populator. FEASTS only
covers ~20 major dates a year (feasts with fundraising lunches, SerbFest,
etc.) -- it does NOT include every weekday feast's actual vespers/liturgy
times (e.g. the Sept 10/11 2026 Beheading of St. John the Baptist isn't
in FEASTS at all, despite needing its own Thu-eve/Fri-liturgy listing).
Getting service times right still needs a human with the Church
calendar -- this script's job is narrower: catch a special event
(a lunch, SerbFest, a major feast) that the site itself knows about but
the draft forgot to mention.
"""
import json
import re
import sys
import urllib.request
from datetime import date as _date, timedelta

CALENDAR_URL = "https://stnicholasphilly.org/calendar.html"


def fetch_feasts():
    html = urllib.request.urlopen(CALENDAR_URL, timeout=15).read().decode("utf-8")
    m = re.search(r"var FEASTS = (\[.*?\]);", html, re.S)
    if not m:
        raise SystemExit("couldn't find FEASTS array in calendar.html -- page structure may have changed")
    # the array is JS, not strict JSON (unquoted keys, single quotes, &quot;/&amp; entities) -- normalize it
    raw = m.group(1)
    raw = raw.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    raw = re.sub(r"\\u([0-9a-fA-F]{4})", lambda mm: chr(int(mm.group(1), 16)), raw)
    raw = re.sub(r"(\w+):", r'"\1":', raw)  # unquoted keys -> quoted
    raw = re.sub(r"'([^']*)'", lambda mm: json.dumps(mm.group(1)), raw)  # single-quoted strings -> JSON strings
    return json.loads(raw)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    y, m, d = (int(x) for x in sys.argv[1].split("-"))
    send_date = _date(y, m, d)
    week_start = send_date - timedelta(days=1)
    week_end = send_date + timedelta(days=9)

    print(f"Checking calendar.html for events between {week_start} and {week_end}...\n")
    feasts = fetch_feasts()

    hits = []
    for it in feasts:
        d1 = _date(*(int(x) for x in it["d"].split("-")))
        d2 = _date(*(int(x) for x in it["d2"].split("-"))) if it.get("d2") else d1
        if d1 <= week_end and d2 >= week_start:
            hits.append((d1, it))

    if hits:
        print("Found on the site's own calendar this week -- confirm the draft reflects these:")
        for d1, it in sorted(hits):
            tag = " [fundraiser/social]" if it.get("s") else ""
            print(f"  {d1} — {it['l']}{tag}")
    else:
        print("No FEASTS entries in this window (routine week).")

    print(
        "\nStanding baseline (not in FEASTS, from the site's service-times "
        "card): Sundays — Divine Liturgy 10:00 AM. Saturdays & eves of "
        "feasts — Great Vespers, time varies by week. Verify any weekday "
        "feast's actual vespers/liturgy times by hand — FEASTS doesn't "
        "carry them."
    )


if __name__ == "__main__":
    main()
