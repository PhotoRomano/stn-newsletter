#!/usr/bin/env python3
"""
Pull the Young Adults contact list from the sign-up Google Sheet, for
loading real recipients into an email draft instead of a manual placeholder.

    python3 young_adults_list.py

Source: the "Young Adults Sign-Ups" tab of the shared sign-up spreadsheet
(apps-script/signup-collector.gs writes to it; SHEET_ID below matches that
script's SHEET_ID constant -- keep them in sync if the sheet ever moves).

IMPORTANT -- this sheet is still the old "Teens" sign-up form under the
hood (see teens-signup.html's redirect to /young-adults-sign-up): its
columns are literally "Teen First/Last Name" and "Teen Age", never
relabeled after the group was renamed. Real entries include actual minors
(ages 13 and 15 seen in the data as of 2026-10-27), each with their own
personal email on file.

RESOLVED (Max, 2026-10-27): minors on this list SHOULD receive Young
Adults group emails -- a parent signing a child up for this list is
explicit consent for that child to get this specific communication.
That's a settled policy, not a per-send judgment call. See
check_minor_safety.py for the separate, narrower question this module
still gates: whether a minor's address should be VISIBLE to the rest of
a self-organizing group (To/Cc) vs. included some other way. Call
`partition_by_age` from that module to split adults/minors, and
`require_visible_list_safe` before populating a visible field -- it
raises unless acknowledge_minors=True, forcing that to stay a conscious
choice each time rather than a silent default in either direction.

Also flags obvious data-quality issues (duplicate contact across rows,
an empty name with only a phone number) rather than silently
deduplicating/guessing -- these need a human glance at the sheet itself.

Requires the mcp-gsheets MCP connection (same one used interactively) --
this script is meant to be read and adapted by Claude via the Sheets
tools, not run standalone with a service-account key (none is configured
for this spreadsheet). Its real job is to document the exact query/column
mapping/safety filter so re-deriving it from scratch isn't needed next
time -- see README's note on this script before re-querying by hand.

SHEET_ID = '1wAKlKyWzOQsbK4DU6BzvvGuWeBnnfdjWFtqM_ITE5jk'
RANGE    = "Young Adults Sign-Ups!A1:L"

Columns (0-indexed): 0 Timestamp, 1 Teen First Name, 2 Teen Last Name,
3 Teen Age, 4 Teen Contact, 5 (phone, unlabeled in the header row),
6 Parent First Name, 7 Parent Last Name, 8 Parent Email, 9 Parent Phone,
10 Interested in Leading, 11 Activity or Volunteer Idea.

Adult email precedence: Teen Contact if it looks like an email and the
age is >= 18; otherwise (age >= 18 but Teen Contact is blank/a phone
number) fall back to Parent Email, since several real rows show the
"adult" self-registering and filling in their own info under both the
Teen and Parent columns (e.g. age 26 with name==parent name).
"""

SHEET_ID = "1wAKlKyWzOQsbK4DU6BzvvGuWeBnnfdjWFtqM_ITE5jk"
TAB = "Young Adults Sign-Ups"
RANGE = f"{TAB}!A1:L"

MIN_ADULT_AGE = 18


def looks_like_email(s):
    return bool(s) and "@" in s and "." in s.split("@")[-1]


def parse_rows(values):
    """values: the raw 2D array from sheets_get_values (header row first).
    Returns (adults, minors, problems) -- call this after fetching RANGE
    via the mcp-gsheets tools; this module intentionally has no network
    code of its own (see docstring)."""
    header, *rows = values
    adults, minors, problems = [], [], []
    seen_emails = set()

    for i, row in enumerate(rows, start=2):  # sheet row number, for problem reports
        row = row + [""] * (12 - len(row))  # pad short rows
        timestamp, t_first, t_last, t_age, t_contact, _phone, \
            p_first, p_last, p_email, p_phone, leading, idea = row[:12]

        name = f"{t_first} {t_last}".strip()
        if not name:
            problems.append(f"row {i}: no name, only data: {row}")
            continue

        try:
            age = int(t_age)
        except ValueError:
            problems.append(f"row {i} ({name}): unparseable age {t_age!r} -- not classified, skipped")
            continue

        email = t_contact if looks_like_email(t_contact) else (p_email if looks_like_email(p_email) else "")
        if not email:
            problems.append(f"row {i} ({name}, age {age}): no usable email in Teen Contact or Parent Email")
            continue

        entry = {"name": name, "age": age, "email": email.strip().lower(), "row": i}

        if email.strip().lower() in seen_emails:
            problems.append(f"row {i} ({name}): duplicate email {email} already seen -- likely a repeat sign-up")
        seen_emails.add(email.strip().lower())

        (adults if age >= MIN_ADULT_AGE else minors).append(entry)

    return adults, minors, problems


def format_report(adults, minors, problems):
    lines = [f"Adults (age >= {MIN_ADULT_AGE}): {len(adults)}"]
    for a in adults:
        lines.append(f"  - {a['name']} ({a['age']}) <{a['email']}>")
    lines.append(f"\nMinors (age < {MIN_ADULT_AGE}): {len(minors)} -- parent-opted-in, OK to include "
                 f"(see RESOLVED note above) but run through check_minor_safety.require_visible_list_safe "
                 f"before putting any of them in a VISIBLE To/Cc")
    for m in minors:
        lines.append(f"  - {m['name']} ({m['age']}) <{m['email']}> -- row {m['row']}")
    if problems:
        lines.append(f"\nData-quality flags ({len(problems)}):")
        for p in problems:
            lines.append(f"  - {p}")
    all_entries = adults + minors
    lines.append(f"\nAll {len(all_entries)} email(s), comma-separated:")
    lines.append(", ".join(e["email"] for e in all_entries))
    return "\n".join(lines)
