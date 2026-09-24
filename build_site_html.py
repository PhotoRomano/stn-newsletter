#!/usr/bin/env python3
"""
Assemble the parish-website (OWS Site Manager CMS) version of an issue:
drafts/<date>.site.html, built from the English and Serbian variants
build.py already generated.

    python3 build_site_html.py drafts/2026-09-10.both.html

Run this AFTER build.py has produced drafts/<date>.html and
drafts/<date>.serbian.html -- it doesn't read the master directly, just
derives the date label from its filename for consistency with
archive_publish.py's calling convention.

The live CMS page shows English and Serbian together with a client-side
EN/СР toggle, so this wraps both languages' <table class="email-body">
content together in a `stn-nl-wrap` / `stn-en` / `stn-sr` shell (the
pattern reverse-engineered from the hand-built 2026-08-20/08-27 site.html
files in the old ~/Projects/stn-newsletter clone). It also strips the
"Read this issue in" language-preference bar from each side first --
same reason archive_publish.py strips it from the GitHub Pages archive:
its links depend on a Beehiiv {{email}} merge tag that only resolves
inside a real email send, and would otherwise render as literal
"{{email}}" text on the static site.

Paste the output directly into the CMS's HTML Code section (see
README.md Step 4) -- it's a plain <textarea>, so clipboard paste works
cleanly.
"""
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
DRAFTS_DIR = ROOT / "drafts"

WRAP_STYLE = """<style>
.stn-nl-wrap { background:#eef1f6; padding:16px 8px; }
</style>
"""


def extract_email_body(path):
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    table = soup.find("table", class_="email-body")
    if table is None:
        raise SystemExit(f"no <table class=\"email-body\"> found in {path}")

    # strip the "Read this issue in" language-pref row -- {{email}} merge
    # tags render as literal text outside a real Beehiiv send
    link = table.find("a", href=re.compile(r"stn-language-pref"))
    if link:
        tr = link.find_parent("tr")
        if tr:
            tr.decompose()

    return str(table)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    master_path = Path(sys.argv[1])
    date_label = master_path.name.replace(".both.html", "")

    en_path = DRAFTS_DIR / f"{date_label}.html"
    sr_path = DRAFTS_DIR / f"{date_label}.serbian.html"
    for p in (en_path, sr_path):
        if not p.exists():
            raise SystemExit(f"{p} doesn't exist yet -- run build.py first")

    en_table = extract_email_body(en_path)
    sr_table = extract_email_body(sr_path)

    site_html = (
        WRAP_STYLE
        + '<div class="stn-nl-wrap">\n<center>\n'
        + f'<div class="stn-en">\n{en_table}\n</div>\n'
        + f'<div class="stn-sr">\n{sr_table}\n</div>\n'
        + "</center>\n</div>\n"
    )

    out_path = DRAFTS_DIR / f"{date_label}.site.html"
    out_path.write_text(site_html, encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
