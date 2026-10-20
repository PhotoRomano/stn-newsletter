#!/usr/bin/env python3
"""
Pre-send QA gate: catch a wrong link target or a leftover placeholder
before Max ever opens the Beehiiv draft, instead of relying on him to
eyeball it and catch it after the fact (which is what happened with the
2026-09-10 issue -- the "Read This Week's Issue" links pointed at the
GitHub Pages archive instead of the live parish site, twice, before it
got noticed).

    python3 check_links.py drafts/2026-09-10.email.html

Checks, in order:
  1. Every <a href> is an http(s)/mailto/tel/# link (catches a stray
     relative path or a typo'd scheme).
  2. `.email.html` specifically must NOT contain any link to
     photoromano.github.io -- per README Step 5, the emailed brief links
     to the live parish site (stnicholasphilly.org/newsletter-<date>),
     never the GitHub Pages archive. This is the exact bug this script
     exists to catch.
  3. No leftover placeholder text anywhere in the file: [BOARD:],
     [TODO, [PLACEHOLDER, [МЕСТО (the Serbian placeholder marker used in
     drafts/2026-09-17.both.html).
  3b. A literal unresolved `{{email}}` merge tag, but ONLY checked for
     `.site.html` and `archive/*.html` -- those are the two outputs
     build_site_html.py / archive_publish.py are specifically supposed
     to strip it from. `.both.html` (the master) and the raw build.py
     output (`.html`/`.serbian.html`/`.other.html`) legitimately carry
     `{{email}}` in their language-preference-bar boilerplate until one
     of those two scripts processes them -- flagging it there is a false
     positive, not a bug.
  4. Every http(s) link actually resolves (HTTP 200, 15s timeout).
     Skipped with --no-fetch for a fast offline pass.
  5. If the file's CSS uses the 'El Messiri' font-family anywhere, it must
     also load it via a Google Fonts <link> -- otherwise every heading
     silently falls back to Georgia with no visible error (the exact bug
     Max caught 2026-10-20, which had been shipping unnoticed for weeks
     on every standalone GitHub Pages page: drafts/*.both.html, build.py's
     per-language output, and archive/index.html). Skipped for
     `.site.html` -- that file is a content fragment pasted into the
     parish CMS, which already supplies the font site-wide; it never has
     its own <head> by design.

Exits non-zero if anything fails, so it can gate the workflow instead of
just being advisory.
"""
import re
import sys
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

PLACEHOLDER_PATTERNS = [
    r"\[BOARD:",
    r"\[TODO",
    r"\[PLACEHOLDER",
    r"\[МЕСТО",
]

GITHUB_PAGES_HOST = "photoromano.github.io"
# github.io in an <img src> (banner, icons) is fine -- those assets
# genuinely live there. Only flag it in an <a href>, where it means a
# reader gets sent to the wrong place instead of stnicholasphilly.org.


def fetch_status(url, timeout=15):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        if e.code == 405:  # some servers reject HEAD -- retry GET
            req2 = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            try:
                with urllib.request.urlopen(req2, timeout=timeout) as resp:
                    return resp.status
            except Exception as e2:
                return f"error: {e2}"
        return f"error: {e}"
    except Exception as e:
        return f"error: {e}"


def main():
    args = sys.argv[1:]
    do_fetch = "--no-fetch" not in args
    args = [a for a in args if a != "--no-fetch"]
    if len(args) != 1:
        print(__doc__)
        sys.exit(1)
    path = Path(args[0])
    text = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(text, "html.parser")
    is_email_file = path.name.endswith(".email.html")

    problems = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#"):
            continue
        if href.startswith(("mailto:", "tel:")):
            continue
        if not href.startswith(("http://", "https://")):
            problems.append(f"non-http(s) link: {href!r}")
            continue
        if is_email_file and GITHUB_PAGES_HOST in href:
            problems.append(f"email brief links to GitHub Pages archive instead of the live site: {href}")

    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, text):
            problems.append(f"leftover placeholder text matching {pat!r}")

    checks_email_tag_stripped = path.name.endswith(".site.html") or "archive" in path.parts
    if checks_email_tag_stripped and "{{email}}" in text:
        problems.append("unresolved {{email}} merge tag found -- should have been stripped by now")

    is_site_fragment = path.name.endswith(".site.html")
    uses_el_messiri = re.search(r"font-family:\s*['\"]?El Messiri", text) is not None
    has_el_messiri_link = "fonts.googleapis.com" in text and "El+Messiri" in text
    if uses_el_messiri and not is_site_fragment and not has_el_messiri_link:
        problems.append(
            "uses 'El Messiri' in font-family but has no Google Fonts <link> for it "
            "-- will silently fall back to Georgia (the 2026-10-20 font bug)"
        )

    if do_fetch:
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith(("http://", "https://")) or href in seen:
                continue
            seen.add(href)
            status = fetch_status(href)
            if status != 200:
                problems.append(f"link did not return 200 ({status}): {href}")

    if problems:
        print(f"FAILED -- {len(problems)} issue(s) in {path}:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print(f"OK -- {path} passed all checks" + ("" if do_fetch else " (link-fetch skipped)"))


if __name__ == "__main__":
    main()
