#!/usr/bin/env python3
"""
Single source of truth for "is this week's issue actually fully staged."

    python3 check_publish_status.py 2026-10-08

Built 2026-10-08 after a "prepare the newsletter for publish" pass staged
three of four surfaces (GitHub Pages archive, parish CMS page, Beehiiv
draft) but silently skipped the fourth (the live Newsletter Archive
listing at stnicholasphilly.org/newsletter-archive) -- nothing in the
workflow forced a check across all of them together, so the gap only
surfaced because Max caught it by hand. This script is that check.

Pings each surface directly (no trusting local state or memory of what
was done) and reports LIVE / MISSING for:
  1. GitHub Pages archive      -- photoromano.github.io/stn-newsletter/archive/<date>.html
  2. Parish CMS page           -- stnicholasphilly.org/newsletter-<date>
  3. Newsletter Archive listing -- stnicholasphilly.org/newsletter-archive
                                    (checks the page actually LINKS to #2,
                                    not just that the listing page itself loads)
  4. Beehiiv draft              -- can't be checked via API (no reliable
                                    key/scope as of 2026-10-08 -- see README),
                                    always printed as a manual-check reminder.

Exit code is non-zero if any of the three URL-checkable surfaces are
missing, so this can gate a workflow the same way check_links.py does.
"""
import sys
import urllib.request

GITHUB_ARCHIVE = "https://photoromano.github.io/stn-newsletter/archive/{date}.html"
PARISH_PAGE = "https://stnicholasphilly.org/newsletter-{date}"
ARCHIVE_LISTING = "https://stnicholasphilly.org/newsletter-archive"


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return f"error: {e}", ""


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    date = sys.argv[1]

    problems = []

    print(f"Checking publish status for {date}...\n")

    status, _ = fetch(GITHUB_ARCHIVE.format(date=date))
    ok = status == 200
    print(f"  [{'LIVE' if ok else 'MISSING'}] GitHub Pages archive ({status})")
    if not ok:
        problems.append("GitHub Pages archive not live -- run archive_publish.py")

    status, _ = fetch(PARISH_PAGE.format(date=date))
    ok = status == 200
    print(f"  [{'LIVE' if ok else 'MISSING'}] Parish CMS page ({status})")
    if not ok:
        problems.append("Parish CMS page not live -- create it via Site Manager (README Step 4)")

    status, body = fetch(ARCHIVE_LISTING)
    link_present = f"/newsletter-{date}" in body
    ok = status == 200 and link_present
    label = "LIVE" if ok else ("MISSING" if status == 200 else "MISSING")
    detail = "" if ok else (" -- listing page loads but has no entry for this date" if status == 200 else f" ({status})")
    print(f"  [{label}] Newsletter Archive listing{detail}")
    if not ok:
        problems.append("Newsletter Archive listing has no entry for this date -- add it (README Step 6)")

    print(f"  [MANUAL CHECK] Beehiiv draft -- no reliable API check available; "
          f"confirm in app.beehiiv.com/posts that a Draft exists with "
          f"Subject/Preview Text/Audience set and the HTML Snippet block rendering correctly.")

    print()
    if problems:
        print(f"NOT READY -- {len(problems)} issue(s):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print("All URL-checkable surfaces are live. Confirm the Beehiiv draft manually, then it's Max's call to send.")


if __name__ == "__main__":
    main()
