#!/usr/bin/env python3
"""
Flag emoji that don't match the activity/section they're captioning.

    python3 check_emoji_consistency.py 2026-11-19

Built 2026-11-19 after the "Ping Pong Stays" weekly feature ran with the
volleyball emoji (🏐) instead of table tennis (🏓) for three straight
issues (2026-11-05/12/19) before anyone noticed -- 21 occurrences across
sent archives and drafts, caught only because Max happened to look at
the picture. check_links.py verifies hrefs resolve and check_calendar.py
verifies dates against the live site, but nothing verified that an
emoji actually matches the text/keyword it's sitting next to. This is
that missing check -- narrow by design: it only knows about a small set
of CONFUSABLE_EMOJI pairs (keyword -> correct emoji, plus commonly
mixed-up wrong ones), seeded from the real incident plus the other
round-ball-sport emoji that are visually/semantically easy to confuse
the same way. It does not try to validate every emoji in an issue
against its surrounding text -- that would need real image/caption
understanding, not a keyword match.

Scans every drafts/<date>*.html variant that exists. Hard-fail (exit 1)
on any mismatch, same convention as check_links.py / check_title_date.py.
"""
import re
import sys
from pathlib import Path

from check_utils import CheckError, require_files

# keyword (case-insensitive substring) -> (correct emoji, {wrong emoji seen in the wild})
CONFUSABLE_EMOJI = {
    "ping pong": ("🏓", {"🏐", "🏀", "⚽", "🎾"}),
    "table tennis": ("🏓", {"🏐", "🏀", "⚽", "🎾"}),
    "стони тенис": ("🏓", {"🏐", "🏀", "⚽", "🎾"}),
    "volleyball": ("🏐", {"🏓", "🏀", "⚽", "🎾"}),
    "basketball": ("🏀", {"🏓", "🏐", "⚽", "🎾"}),
    "soccer": ("⚽", {"🏓", "🏐", "🏀", "🎾"}),
    "tennis": ("🎾", {"🏓", "🏐", "🏀", "⚽"}),
}

WINDOW = 80  # chars of context scanned around each keyword hit for an emoji


def find_mismatches(text, filename):
    findings = []
    lower = text.lower()
    for keyword, (correct, wrong_set) in CONFUSABLE_EMOJI.items():
        start = 0
        while True:
            idx = lower.find(keyword, start)
            if idx == -1:
                break
            start = idx + len(keyword)
            window = text[max(0, idx - WINDOW):idx + len(keyword) + WINDOW]
            found_wrong = [e for e in wrong_set if e in window]
            if found_wrong and correct not in window:
                line_no = text.count("\n", 0, idx) + 1
                findings.append(
                    f"{filename}:{line_no}: near \"{keyword}\" found {found_wrong} "
                    f"but expected {correct!r}"
                )
    return findings


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <date>  e.g. {sys.argv[0]} 2026-11-19", file=sys.stderr)
        sys.exit(1)
    date = sys.argv[1]

    candidates = [
        Path(f"drafts/{date}.html"),
        Path(f"drafts/{date}.both.html"),
        Path(f"drafts/{date}.site.html"),
        Path(f"drafts/{date}.email.html"),
        Path(f"drafts/{date}.other.html"),
        Path(f"drafts/{date}.serbian.html"),
    ]
    existing = [p for p in candidates if p.exists()]
    try:
        require_files(*candidates[:1])  # at minimum drafts/<date>.html must exist
    except CheckError as e:
        print(f"check_emoji_consistency: {e}", file=sys.stderr)
        sys.exit(1)

    all_findings = []
    for path in existing:
        text = path.read_text(encoding="utf-8")
        all_findings.extend(find_mismatches(text, str(path)))

    if all_findings:
        print("check_emoji_consistency: MISMATCH")
        for f in all_findings:
            print(f"  {f}")
        sys.exit(1)

    print(f"check_emoji_consistency: OK ({len(existing)} file(s) checked, 0 mismatches)")


if __name__ == "__main__":
    main()
