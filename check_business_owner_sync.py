#!/usr/bin/env python3
"""
Catch a drift between what the Parishioner Businesses section of the
newsletter says (an owner's name, since the 2026-10-28 "hire {name} for
{service}" CTA rewrite) and what the live businesses D1 table actually has
in `contact_name` -- before it's just something Max happens to notice.

Built right after exactly that gap was found by hand: `contact_name` was
null for Tica's Souvlaki and just "Chad" (no last name) for Modern Home
Investments, while the newsletter needed each owner's real full name
(Jon Lotrean, Čedo Plevac). Nothing had been checking the two stayed in
sync.

    python3 check_business_owner_sync.py            # live D1 query via wrangler
    python3 check_business_owner_sync.py --offline   # use the newest backups/*.json instead

Source of truth for "what the newsletter currently shows": business_owner_map.json
in this directory (slug -> owner full name). Update that file by hand whenever
the Parishioner Businesses listing in drafts/<date>.both.html changes --
this script only diffs it against the DB, it doesn't read the draft HTML
itself (owner names there aren't tagged with their slug, so there's nothing
reliable to parse out automatically).

Checks, per ACTIVE business row in the DB:
  1. Map has no entry for this slug -- newsletter may be missing this
     business, or the map just hasn't been updated yet.
  2. DB contact_name is empty -- newsletter has a real name (from the map)
     that was confirmed by Max but never written back to the DB.
  3. DB contact_name doesn't match the map's name -- one of the two is
     stale.
  4. DB contact_name has no space (looks like a first name only, e.g.
     "Chad") -- flagged as a weaker warning even if it happens to match
     the map, since the map itself might just be carrying the same gap.
  5. Map has a slug with no matching ACTIVE row in the DB at all -- stale
     map entry (business removed/deactivated) or a typo'd slug.

Exits non-zero if anything is found, so it can gate the weekly "Draft"
step the same way check_calendar.py / check_board_resolutions.py do.
"""
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
MAP_PATH = ROOT / "business_owner_map.json"
WORKER_DIR = ROOT.parent / "classifieds" / "worker"
BACKUPS_DIR = ROOT.parent / "classifieds" / "backups"

SELECT_COLUMNS = "id,slug,name,contact_name,contact_email,website_url,status"


def normalize(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().casefold()


def load_map():
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def load_live_rows():
    result = subprocess.run(
        [
            "wrangler", "d1", "execute", "stnicholas-classifieds", "--remote",
            "--command", f"SELECT {SELECT_COLUMNS} FROM businesses ORDER BY sort_order;",
        ],
        cwd=WORKER_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"wrangler query failed:\n{result.stderr}")
    # wrangler prints progress/warning lines before the JSON array -- same
    # convention backup_businesses.sh relies on (sed -n '/^\[/,$p').
    stdout = result.stdout
    start = stdout.index("[")
    payload = json.loads(stdout[start:])
    return payload[0]["results"]


def load_offline_rows():
    backups = sorted(BACKUPS_DIR.glob("businesses_*.json"))
    if not backups:
        raise RuntimeError(f"no backup files found in {BACKUPS_DIR}")
    latest = backups[-1]
    print(f"(offline mode -- using {latest.name}, may be stale)")
    data = json.loads(latest.read_text(encoding="utf-8"))
    return data[0]["results"]


def main():
    offline = "--offline" in sys.argv[1:]
    owner_map = load_map()
    rows = load_offline_rows() if offline else load_live_rows()

    active_slugs = set()
    problems = []

    for row in rows:
        if row.get("status") != "active":
            continue
        slug = row["slug"]
        active_slugs.add(slug)
        name = row["name"]
        db_contact = row.get("contact_name")

        if slug not in owner_map:
            problems.append(
                f"'{name}' (slug={slug}) has no entry in business_owner_map.json -- "
                f"may be missing from the newsletter, or the map just needs updating"
            )
            continue

        mapped_name = owner_map[slug]

        if not db_contact:
            problems.append(
                f"'{name}' (slug={slug}): DB contact_name is empty, but the newsletter "
                f"shows '{mapped_name}' -- backfill the DB via the admin API"
            )
        elif normalize(db_contact) != normalize(mapped_name):
            problems.append(
                f"'{name}' (slug={slug}): mismatch -- DB contact_name='{db_contact}' "
                f"but newsletter shows '{mapped_name}'"
            )
        elif " " not in db_contact.strip():
            problems.append(
                f"'{name}' (slug={slug}): DB contact_name='{db_contact}' looks like a "
                f"first name only (no space) -- verify it's the full name"
            )

    for slug, mapped_name in owner_map.items():
        if slug not in active_slugs:
            problems.append(
                f"business_owner_map.json has slug='{slug}' -> '{mapped_name}' but no "
                f"matching ACTIVE business row in the DB -- stale entry or typo'd slug"
            )

    if problems:
        print(f"FAILED -- {len(problems)} issue(s):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print(f"OK -- business_owner_map.json matches the live DB for all {len(active_slugs)} active businesses")


if __name__ == "__main__":
    main()
