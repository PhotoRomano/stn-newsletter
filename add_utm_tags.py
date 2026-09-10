#!/usr/bin/env python3
"""
Tag outbound links in the Beehiiv email brief with UTM parameters, so
Beehiiv's click data (and GA on stnicholasphilly.org) can actually
attribute traffic to the newsletter instead of lumping it in with
direct/social visits.

    python3 add_utm_tags.py drafts/2026-09-10.email.html 2026-09-10

Adds `utm_source=newsletter&utm_medium=email&utm_campaign=<date>` to
every http(s) link that doesn't already carry a utm_source (idempotent
-- safe to re-run). Skips `mailto:`, `tel:`, and same-page `#` links.
Only ever touches the `.email.html` brief -- the full-issue variants and
the CMS `.site.html` aren't sent as email, so email-attribution tags
don't belong on their links.
"""
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from bs4 import BeautifulSoup


def tag_url(url, date_label):
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return url
    query = parse_qsl(parts.query, keep_blank_values=True)
    if any(k == "utm_source" for k, _ in query):
        return url  # already tagged, leave as-is
    query += [
        ("utm_source", "newsletter"),
        ("utm_medium", "email"),
        ("utm_campaign", date_label),
    ]
    return urlunsplit(parts._replace(query=urlencode(query)))


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    path = Path(sys.argv[1])
    date_label = sys.argv[2]

    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    tagged = 0
    for a in soup.find_all("a", href=True):
        new_href = tag_url(a["href"], date_label)
        if new_href != a["href"]:
            a["href"] = new_href
            tagged += 1

    path.write_text(str(soup), encoding="utf-8")
    print(f"tagged {tagged} link(s) in {path}")


if __name__ == "__main__":
    main()
