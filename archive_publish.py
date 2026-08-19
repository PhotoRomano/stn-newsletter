#!/usr/bin/env python3
"""
Publish an approved bilingual master (drafts/<date>.both.html) to the public
archive at archive/<date>.html, and regenerate archive/index.html.

    python3 archive_publish.py drafts/2026-08-20.both.html

The archive page always shows both languages side by side (same content the
board already approved) -- there's no per-visitor language picker, so this
strips the two things that only make sense inside an actual sent email:
the DRAFT banner and the language-preference bar (its links depend on a
Beehiiv {{email}} merge tag that only resolves inside a real send).

This is the "publish" step until a real one-click button exists -- run it
by hand after Max approves an issue, then commit + push both changed files.
"""
import re
import sys
from datetime import date as _date
from pathlib import Path

from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).parent
ARCHIVE_DIR = ROOT / "archive"


def strip_draft_chrome(soup):
    # DRAFT banner div (the first <div> right after the hidden preview-text div)
    for div in soup.find_all("div"):
        if div.get("style") and "background:#1a1a1a" in div.get("style", ""):
            div.decompose()
            break
    # language-preference bar row -- walk up from the link itself to its
    # immediate containing <tr>, not find_all("tr") (which matches the outer
    # wrapper row first, since it also contains this link as a descendant,
    # and decomposing that nukes the whole table)
    link = soup.find("a", href=re.compile(r"stn-language-pref"))
    if link:
        tr = link.find_parent("tr")
        if tr:
            tr.decompose()
    # drop the now-orphaned HTML comment markers so the archive source stays tidy
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        if "Language preference" in c or "DRAFT BANNER" in c:
            c.extract()


def fix_title(soup, date_label_readable):
    if soup.title:
        soup.title.string = (
            f"The Messenger / Гласник — Week of {date_label_readable} "
            "· St. Nicholas Serbian Orthodox Church"
        )


def render_index(issues):
    rows = "\n".join(
        f'    <div class="issue"><a href="{fname}">{label}</a></div>'
        for fname, label in issues
    ) or '    <p style="color:#888; font-style:italic;">No issues published yet.</p>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Messenger — Newsletter Archive — St. Nicholas Serbian Orthodox Church</title>
<style>
  body {{ margin: 0; background: #ece7dd; font-family: Georgia, serif; color: #2b2b2b; }}
  .wrap {{ max-width: 660px; margin: 40px auto; padding: 0 20px; }}
  .hd {{ background: #02306e; color: #fff; padding: 28px 32px; border-radius: 6px 6px 0 0; text-align: center; }}
  .hd h1 {{ margin: 0 0 4px; font-size: 28px; font-family: 'El Messiri', Georgia, serif; }}
  .hd p {{ margin: 0; color: #a8c4e0; font-size: 14px; font-style: italic; }}
  .gold {{ height: 4px; background: #c9a227; }}
  .body {{ background: #fff; border: 1px solid #ddd4c4; border-top: none; padding: 28px 32px; }}
  a {{ color: #02306e; }}
  .issue {{ padding: 12px 0; border-bottom: 1px solid #f0e8d8; font-size: 16px; }}
  .issue:last-child {{ border-bottom: none; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hd">
    <h1>The Messenger &nbsp;/&nbsp; Гласник</h1>
    <p>St. Nicholas Serbian Orthodox Church &middot; Newsletter Archive</p>
  </div>
  <div class="gold"></div>
  <div class="body">
{rows}
  </div>
</div>
</body>
</html>
"""


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    master_path = Path(sys.argv[1])
    date_label = master_path.name.replace(".both.html", "")
    y, m, d = (int(x) for x in date_label.split("-"))
    date_label_readable = _date(y, m, d).strftime("%B %-d, %Y")

    soup = BeautifulSoup(master_path.read_text(encoding="utf-8"), "html.parser")
    strip_draft_chrome(soup)
    fix_title(soup, date_label_readable)

    ARCHIVE_DIR.mkdir(exist_ok=True)
    out_path = ARCHIVE_DIR / f"{date_label}.html"
    out_path.write_text(str(soup), encoding="utf-8")
    print(f"wrote {out_path}")

    # rebuild the index by scanning what's actually in archive/ -- newest first
    issues = []
    for f in sorted(ARCHIVE_DIR.glob("????-??-??.html"), reverse=True):
        fy, fm, fd = (int(x) for x in f.stem.split("-"))
        label = _date(fy, fm, fd).strftime("Week of %B %-d, %Y")
        issues.append((f.name, label))
    (ARCHIVE_DIR / "index.html").write_text(render_index(issues), encoding="utf-8")
    print(f"wrote {ARCHIVE_DIR / 'index.html'} ({len(issues)} issue(s))")


if __name__ == "__main__":
    main()
