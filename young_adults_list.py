#!/usr/bin/env python3
"""
Pull the Young Adults contact list from the sign-up Google Sheet, for
loading real recipients into an email draft instead of a manual placeholder.

    python3 young_adults_list.py

Source: the "Young Adults Sign-Ups" tab of the shared sign-up spreadsheet
(apps-script/signup-collector.gs writes to it; SHEET_ID below matches that
script's SHEET_ID constant -- keep them in sync if the sheet ever moves).

IMPORTANT -- this sheet used to be the old "Teens" sign-up form under the
hood (see teens-signup.html's redirect to /young-adults-sign-up); its
column headers ("Teen First/Last Name" etc.) were relabeled to "Member
.../Parent-Guardian ..." on 2026-10-27 (live sheet row 1 updated via the
Sheets API, apps-script/signup-collector.gs's `headers` config updated to
match for any future fresh-sheet creation) -- see that script's comment
for why `row()`'s p['Teen ...'] lookups were deliberately left alone (they
match the live HTML form's field names, a separate thing from the sheet's
display headers). Real entries include actual minors (ages 13 and 15 seen
in the data as of 2026-10-27), each with their own personal email on file.

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

import datetime

SHEET_ID = "1wAKlKyWzOQsbK4DU6BzvvGuWeBnnfdjWFtqM_ITE5jk"
TAB = "Young Adults Sign-Ups"
RANGE = f"{TAB}!A1:L"

MIN_ADULT_AGE = 18

# Explicit, auditable one-character-typo fixes for common domains -- NOT a
# fuzzy/guessed correction. Added 2026-10-27 after a real repeat submission
# had "jlotrean6@yahoo.com" the first time and "jlotrean6@yahoo.con" the
# second -- same person, same local-part, a dropped keystroke on the TLD.
# Extend this list only when a specific real typo like that shows up; don't
# turn it into general fuzzy email correction.
DOMAIN_TYPO_FIXES = {
    "yahoo.con": "yahoo.com", "gmail.con": "gmail.com", "hotmail.con": "hotmail.com",
    "yahoo.comm": "yahoo.com", "gmail.comm": "gmail.com", "hotmail.comm": "hotmail.com",
    "icloud.con": "icloud.com", "outlook.con": "outlook.com",
}


def looks_like_email(s):
    return bool(s) and "@" in s and "." in s.split("@")[-1]


def parse_sheet_timestamp(s):
    """Sheet timestamps are un-zero-padded M/D/YYYY H:MM:SS text (e.g.
    '9/20/2026 15:45:20') -- NOT lexically sortable (plain string sort
    puts '9/20/2026' after '10/8/2026' because '9' > '1'). Parse to a
    real datetime so chronological order is actually chronological.
    Returns datetime.min for anything unparseable, so bad timestamps sort
    first rather than crashing the whole dedupe pass."""
    try:
        return datetime.datetime.strptime(s.strip(), "%m/%d/%Y %H:%M:%S")
    except ValueError:
        return datetime.datetime.min


def fix_known_domain_typo(email):
    local, _, domain = email.rpartition("@")
    fixed = DOMAIN_TYPO_FIXES.get(domain)
    return f"{local}@{fixed}" if fixed else email


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

        email = email.strip().lower()
        fixed = fix_known_domain_typo(email)
        if fixed != email:
            problems.append(f"row {i} ({name}): auto-corrected known domain typo {email!r} -> {fixed!r}")
            email = fixed

        entry = {
            "name": name, "age": age, "email": email, "row": i,
            "timestamp": timestamp, "leading": leading, "idea": idea,
        }

        if email in seen_emails:
            problems.append(f"row {i} ({name}): duplicate email {email} already seen -- likely a repeat sign-up")
        seen_emails.add(email)

        (adults if age >= MIN_ADULT_AGE else minors).append(entry)

    return adults, minors, problems


def dedupe_by_person(entries):
    """Collapse multiple rows for the same person (matched by normalized
    name) into one entry, after fix_known_domain_typo has already run in
    parse_rows. If a name's rows DISAGREE on email even after typo-fixing,
    don't guess -- keep every distinct (name, email) pair and flag it, so
    a real ambiguity surfaces instead of silently picking one.

    Returns (deduped_entries, notes)."""
    by_name = {}
    for e in entries:
        by_name.setdefault(e["name"].lower(), []).append(e)

    out, notes = [], []
    for name_key, group in by_name.items():
        distinct_emails = {e["email"] for e in group}
        if len(distinct_emails) == 1:
            # Same person, same (post-typo-fix) email across 1+ rows --
            # keep the most recently submitted row's data, but carry
            # forward any non-empty "leading"/"idea" text an earlier row
            # had that the latest row left blank (people often fill more
            # in on a later submission, but not always everything).
            group.sort(key=lambda e: parse_sheet_timestamp(e["timestamp"]))
            best = dict(group[-1])
            for e in group[:-1]:
                if not best.get("leading") and e.get("leading"):
                    best["leading"] = e["leading"]
                if not best.get("idea") and e.get("idea"):
                    best["idea"] = e["idea"]
            if len(group) > 1:
                notes.append(f"{best['name']}: merged {len(group)} repeat sign-up rows "
                             f"(rows {[e['row'] for e in group]}) into one")
            out.append(best)
        else:
            notes.append(f"{group[0]['name']}: {len(distinct_emails)} DIFFERENT emails across rows "
                         f"{[e['row'] for e in group]} ({sorted(distinct_emails)}) -- not merged, "
                         f"needs a human decision (could be two different people sharing a name, "
                         f"or a real address change)")
            out.extend(group)
    return out, notes


def format_report(adults, minors, problems):
    adults, dedupe_notes_a = dedupe_by_person(adults)
    minors, dedupe_notes_m = dedupe_by_person(minors)

    lines = [f"Adults (age >= {MIN_ADULT_AGE}): {len(adults)}"]
    for a in adults:
        lines.append(f"  - {a['name']} ({a['age']}) <{a['email']}>")
    lines.append(f"\nMinors (age < {MIN_ADULT_AGE}): {len(minors)} -- parent-opted-in, OK to include "
                 f"(see RESOLVED note above) but run through check_minor_safety.require_visible_list_safe "
                 f"before putting any of them in a VISIBLE To/Cc")
    for m in minors:
        lines.append(f"  - {m['name']} ({m['age']}) <{m['email']}> -- row {m['row']}")
    dedupe_notes = dedupe_notes_a + dedupe_notes_m
    if dedupe_notes:
        lines.append(f"\nDeduplication ({len(dedupe_notes)}):")
        for n in dedupe_notes:
            lines.append(f"  - {n}")
    if problems:
        lines.append(f"\nData-quality flags ({len(problems)}):")
        for p in problems:
            lines.append(f"  - {p}")
    all_entries = adults + minors
    lines.append(f"\nAll {len(all_entries)} email(s), comma-separated:")
    lines.append(", ".join(e["email"] for e in all_entries))
    return "\n".join(lines)
