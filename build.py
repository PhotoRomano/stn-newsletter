#!/usr/bin/env python3
"""
Generate the English, Serbian, and Other-fallback newsletter drafts from the
single bilingual master file, which is the ONE draft the board reviews each
week (photoromano.github.io/stn-newsletter -> index.html "Current Draft").

    python3 build.py drafts/2026-08-20.both.html

Regenerates <date>.html, <date>.serbian.html, and <date>.other.html next to
the master. Never hand-edit those three files — the next build overwrites
them. Edit the .both.html master, then re-run this script.

Content model: every weekly-varying section in the master is a two-column
row with `<td class="bl-col bl-en">`/`<td class="bl-col bl-sr">` children.
For a single-language build we keep only the matching column and widen it
to 100%. The "Giving" section is a documented exception (see SEPARATOR
below) — it uses shared bilingual-merged headings/buttons by design, not a
bug, so buttons don't double up in the two-column layout.

Boilerplate (masthead, quick links, language-preference bar, footer, share
block) is NOT extracted from the master — each language's wording for that
boilerplate is fixed and rarely changes, so it lives directly in this
script's SHELL templates below, authored once per language.
"""
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString

ROOT = Path(__file__).parent
BANNER_URL = "https://photoromano.github.io/stn-newsletter/st_nicholas_banner.png"
SEPARATOR = " \xa0/\xa0 "  # the literal "&nbsp;/&nbsp;" text bs4 exposes for Giving's merged strings

CONTENT_START_MARKER = "This Week at the Altar"
CONTENT_END_MARKER = "Beehiiv Poll placeholder"
GIVING_MARKER = "Giving —"


def load_master(path):
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def top_level_children_with_comments(table):
    """Yield (comment_text_or_None, tag) for each top-level <tr>, using every
    HTML comment seen since the previous <tr> as that row's section label
    (joined) -- some rows are preceded by more than one comment."""
    labels = []
    for child in table.children:
        if isinstance(child, Comment):
            labels.append(child.strip())
        elif isinstance(child, NavigableString):
            continue
        elif child.name == "tr":
            yield (" | ".join(labels) or None), child
            labels = []


def keep_only_lang(tag, lang):
    """Remove every bl-col element for the other language; widen the survivor to 100%."""
    other = "bl-sr" if lang == "en" else "bl-en"
    keep = "bl-en" if lang == "en" else "bl-sr"
    for el in tag.find_all(class_=other):
        el.decompose()
    for el in tag.find_all(class_=keep):
        if "width" in el.attrs:
            el["width"] = "100%"
        if el.get("style"):
            el["style"] = re.sub(r"width:\s*50%", "width:100%", el["style"])
    # unwrap the now-single-cell inner two-column table so it doesn't force a stray width
    for inner_table in tag.find_all("table"):
        trs = inner_table.find_all("tr", recursive=False)
        if len(trs) == 1:
            tds = trs[0].find_all("td", recursive=False)
            if len(tds) == 1 and "bl-col" in (tds[0].get("class") or []):
                inner_table.replace_with(*tds[0].contents)


def render_giving(tr, lang):
    """Special-cased: Giving's heading and buttons are shared bilingual-merged
    strings by design (one row of buttons, not two per language) -- split on
    the literal separator instead of the generic bl-col strip."""
    tr = BeautifulSoup(str(tr), "html.parser")
    keep_only_lang(tr, lang)  # handles the bl-en/bl-sr intro paragraph
    for el in tr.find_all(string=lambda s: SEPARATOR in s):
        en_text, sr_text = el.split(SEPARATOR, 1)
        el.replace_with(en_text if lang == "en" else sr_text)
    return str(tr)


def extract_sections(soup, lang):
    table = soup.find("table", class_="email-body")
    out = []
    in_zone = False
    for label, tr in top_level_children_with_comments(table):
        if label and CONTENT_START_MARKER in label:
            in_zone = True
        if label and CONTENT_END_MARKER in label:
            break
        if not in_zone:
            continue
        if label and GIVING_MARKER in label:
            out.append(render_giving(tr, lang))
            continue
        tr_copy = BeautifulSoup(str(tr), "html.parser")
        keep_only_lang(tr_copy, lang)
        out.append(str(tr_copy))
    return "\n\n".join(out)


SHELL = {
    "en": dict(
        html_lang="en",
        title_tpl="The Messenger — Week of {date_label} · St. Nicholas Serbian Orthodox Church · DRAFT",
        preview_key="preview_en",
        draft_banner='&#9998;&nbsp; DRAFT — For board review only. Not yet sent. &nbsp;&middot;&nbsp; '
                     '<a href="mailto:photoromano@gmail.com" style="color:#ffd700;">Send edits to Max</a>',
        langbar_lead="Read this issue in:",
        langbar_links=[("Both", "Both"), ("English", "English"), ("Serbian", "Srpski"), ("Other", "Other")],
        masthead_alt="St. Nicholas Serbian Orthodox Church — Elkins Park, PA",
        issue_title="The Messenger",
        issue_sub="Week of {date_label} &nbsp;&middot;&nbsp; Добро дошли · Welcome",
        ql_labels=[("Calendar", "https://stnicholasphilly.org/calendar.html"),
                   ("Donate", "https://stnicholasphilly.org/donate"),
                   ("Instagram", "https://www.instagram.com/stnicholasphilly"),
                   ("Contact", "mailto:hello@stnicholasphilly.org")],
        share_heading="Know a Family Who&rsquo;d Love This?",
        share_body="Forward this email, or share our mailing list with them directly.",
        share_buttons=[("Share the Sign-Up Link", "https://photoromano.github.io/stn-newsletter/subscribe.html")],
        footer_links=[("Calendar", "https://stnicholasphilly.org/calendar.html"),
                      ("Facebook", "https://www.facebook.com/stnicholasphilly"),
                      ("YouTube", "https://www.youtube.com/@stnicholasphilly"),
                      ("Instagram", "https://www.instagram.com/stnicholasphilly")],
        footer_note="You&rsquo;re receiving this because you&rsquo;re part of the St. Nicholas Serbian "
                    "Orthodox family in Elkins Park, PA.",
        footer_prefs="Update preferences",
        footer_unsub="Unsubscribe",
        other_banner=None,
    ),
    "sr": dict(
        html_lang="sr",
        title_tpl="Гласник — Недеља, {date_label_sr} · Црква Светог Николе Српске православне цркве · НАЦРТ",
        preview_key="preview_sr",
        draft_banner='&#9998;&nbsp; НАЦРТ — Само за преглед одбора. Још није послато. &nbsp;&middot;&nbsp; '
                     '<a href="mailto:photoromano@gmail.com" style="color:#ffd700;">Пошаљите измене Максу</a>',
        langbar_lead="Прочитајте ово издање на:",
        langbar_links=[("Both", "Оба језика"), ("English", "Енглески"), ("Serbian", "Српски"), ("Other", "Остало")],
        masthead_alt="Српска православна црква Светог Николе — Elkins Park, PA",
        issue_title="Гласник",
        issue_sub="Недеља, {date_label_sr}. &nbsp;&middot;&nbsp; Добро дошли",
        ql_labels=[("Календар", "https://stnicholasphilly.org/calendar.html"),
                   ("Донирајте", "https://stnicholasphilly.org/donate"),
                   ("Инстаграм", "https://www.instagram.com/stnicholasphilly"),
                   ("Контакт", "mailto:hello@stnicholasphilly.org")],
        share_heading="Знате породицу која би ово волела?",
        share_body="Проследите овај имејл, или поделите нашу листу за пријаву директно с њима.",
        share_buttons=[("Поделите линк за пријаву", "https://photoromano.github.io/stn-newsletter/subscribe-sr.html")],
        footer_links=[("Календар", "https://stnicholasphilly.org/calendar.html"),
                      ("Фејсбук", "https://www.facebook.com/stnicholasphilly"),
                      ("Јутјуб", "https://www.youtube.com/@stnicholasphilly"),
                      ("Инстаграм", "https://www.instagram.com/stnicholasphilly")],
        footer_note="Ово писмо примате јер сте део српске православне породице Светог Николе у Елкинс "
                    "Парку, Пенсилванија.",
        footer_prefs="Ажурирајте подешавања",
        footer_unsub="Одјавите се",
        other_banner=None,
    ),
}
SHELL["other"] = dict(SHELL["en"])
SHELL["other"] = {**SHELL["en"], "other_banner": (
    "A translation for your preferred language isn&rsquo;t available yet — showing English. "
    "Reply to this email if you&rsquo;d like to help translate for your community."
)}

STYLE_SINGLE = """
  /* ── Mobile responsive overrides ─────────────────── */
  @media only screen and (max-width: 620px) {
    .email-body { width: 100% !important; }
    .pad  { padding-left: 16px !important; padding-right: 16px !important; }
    .ql-table { display: block !important; }
    .ql-row   { display: block !important; font-size: 0; }
    .ql-cell  { display: inline-block !important; width: 50% !important;
                box-sizing: border-box !important; vertical-align: top !important;
                font-size: 13px !important; padding: 13px 8px !important; }
    .ql-cell.r2 { border-top: 1px solid #c8d5e8 !important; }
    .ql-cell.left { border-left: none !important; }
    .svc-date { width: auto !important; white-space: normal !important; font-size: 13px !important; }
    .pad h2 { font-size: 17px !important; }
    .give-cell { display: block !important; width: 100% !important;
                 padding: 0 0 10px 0 !important; box-sizing: border-box !important; }
    .give-cell a { padding-top: 14px !important; padding-bottom: 14px !important;
                   font-size: 15px !important; }
    .issue-title { font-size: 22px !important; }
    .footer-links a { display: inline-block !important; padding: 4px 0 !important; }
  }

  /* ── Wide-browser treatment (a full browser window, not Outlook/Gmail's
       reading pane, which stays under 620px anyway) ── */
  @media only screen and (min-width: 820px) {
    .shell        { padding: 40px 8px !important; }
    .email-body   { width: 680px !important; max-width: 680px !important; }
    .pad          { padding-left: 46px !important; padding-right: 46px !important; }
    .masthead-img { max-width: 620px !important; }
    .pad > p, .pad td p { font-size: 16.5px !important; line-height: 1.8 !important; }
    .pad h2       { font-size: 22px !important; }
    .issue-title  { font-size: 30px !important; }
  }
"""


def render_langbar(cfg):
    links = "\n    ".join(
        f'<a href="https://stn-language-pref.photoromano.workers.dev/set?email={{{{email}}}}&pref={pref}" '
        f'style="font-size:11.5px; color:#02306e; text-decoration:underline;">{label}</a>\n'
        '    <span style="font-size:11.5px; color:#c8d5e8;">&nbsp;&middot;&nbsp;</span>'
        for pref, label in cfg["langbar_links"]
    )
    links = re.sub(r"\n\s*<span[^>]*>&nbsp;&middot;&nbsp;</span>\s*$", "", links)
    return (
        '  <tr><td style="padding:7px 16px; text-align:center; background:#f0f4fb; '
        'border-bottom:1px solid #c8d5e8; font-family:Arial,sans-serif;">\n'
        f'    <span style="font-size:11.5px; color:#5a6b85;">{cfg["langbar_lead"]}</span>\n    {links}\n'
        "  </td></tr>\n"
    )


def render_ql(cfg):
    icons = ["&#128197;", "&#128591;", "&#128247;", "&#9993;"]
    cells = []
    for i, ((label, href), icon) in enumerate(zip(cfg["ql_labels"], icons)):
        cls = "ql-cell" + (" left" if i == 0 else "") + (" r2" if i >= 2 else "") + (" left" if i == 2 else "")
        border = "" if i == 0 else " border-left:1px solid #c8d5e8;"
        cells.append(
            f'<td class="{cls}" style="padding:11px; text-align:center; font-size:13px; width:25%;{border}">'
            f'<a href="{href}" style="color:#02306e; text-decoration:none;">{icon} {label}</a></td>'
        )
    return (
        '  <tr><td style="padding:12px 16px;">\n'
        '    <table class="ql-table" role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="background:#f0f4fb; border:1px solid #c8d5e8; border-radius:3px;">\n'
        '      <tr class="ql-row">' + "".join(cells) + "</tr>\n"
        "    </table>\n  </td></tr>\n"
    )


def render_share(cfg):
    buttons = "\n".join(
        f'        <a href="{href}" style="display:inline-block; background:#c9a227; color:#3a2e00; '
        f'text-decoration:none; padding:10px 22px; font-size:14px; font-weight:bold; border-radius:2px; '
        f'margin:0 4px 8px;">{label}</a>'
        for label, href in cfg["share_buttons"]
    )
    return f"""  <!-- ══ Share This Issue ══ -->
  <tr><td class="pad" style="padding:0 32px 24px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8f4e8; border:1px solid #e0d4a0; border-left:4px solid #c9a227;">
      <tr><td style="padding:18px 16px; text-align:center;">
        <p style="font-size:15px; line-height:1.65; color:#333; margin:0 0 10px;">
          <strong style="color:#02306e;">&#128228; {cfg["share_heading"]}</strong><br>
          {cfg["share_body"]}
        </p>
{buttons}
      </td></tr>
    </table>
  </td></tr>
"""


FOOTER_ICONS = ["&#128197;", "&#128248;", "&#9654;&#65039;", "&#128247;"]


def render_footer(cfg):
    links = "\n      &nbsp;&middot;&nbsp;\n      ".join(
        f'<a href="{href}" style="color:#a8c4e0; text-decoration:none;">{icon} {label}</a>'
        for (label, href), icon in zip(cfg["footer_links"], FOOTER_ICONS)
    )
    return f"""  <!-- ══ Footer ══ -->
  <tr><td style="height:3px; background:#c31f27;"></td></tr>
  <tr><td style="background:#02306e; padding:22px 20px; text-align:center;">
    <div class="footer-links" style="color:#a8c4e0; font-size:14px; margin-bottom:10px;">
      {links}
    </div>
    <div style="color:#c9a227; font-size:13px; margin-bottom:14px;">&#9993; hello@stnicholasphilly.org</div>
    <div style="color:#7090b8; font-size:11.5px; line-height:1.65;">
      {cfg["footer_note"]}<br>
      506 Stahr Road, Elkins Park, PA 19027<br>
      <a href="#" style="color:#a8c4e0;">{cfg["footer_prefs"]}</a> &nbsp;&middot;&nbsp; <a href="#" style="color:#a8c4e0;">{cfg["footer_unsub"]}</a>
    </div>
  </td></tr>
  <tr><td style="height:4px; background:#c9a227;"></td></tr>
"""


def build_variant(lang, week, sections_html):
    cfg = SHELL[lang]
    title = cfg["title_tpl"].format(**week)
    issue_sub = cfg["issue_sub"].format(**week)
    other_banner_html = ""
    if cfg["other_banner"]:
        other_banner_html = (
            '  <tr><td style="padding:6px 16px; text-align:center; background:#fff8e1; '
            'border-bottom:1px solid #c8d5e8; font-family:Arial,sans-serif; font-size:11.5px; color:#7a6a2e;">'
            f'{cfg["other_banner"]}</td></tr>\n'
        )
    return f"""<!DOCTYPE html>
<html lang="{cfg['html_lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{STYLE_SINGLE}</style>
</head>
<body style="margin:0; padding:0; background:#eef1f6; font-family:Georgia,'Times New Roman',serif; color:#2b2b2b;">

<!-- preview text (hidden) -->
<div style="display:none; max-height:0; overflow:hidden; opacity:0;">{week[cfg['preview_key']]}</div>

<!-- DRAFT BANNER -->
<div style="background:#1a1a1a; color:#ffd700; text-align:center; padding:9px 16px; font-family:Arial,sans-serif; font-size:12.5px; letter-spacing:.5px;">
  {cfg["draft_banner"]}
</div>

<center>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef1f6;">
<tr><td class="shell" align="center" style="padding:16px 8px;">

<table class="email-body" role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px; max-width:600px; background:#ffffff; border:1px solid #c8d5e8;">

{render_langbar(cfg)}
{other_banner_html}  <!-- ══ Masthead ══ -->
  <tr><td style="background:#ffffff; padding:14px 16px 10px; text-align:center;">
    <img class="masthead-img" src="{BANNER_URL}" width="560" alt="{cfg['masthead_alt']}"
         style="display:block; margin:0 auto; width:100%; max-width:560px; height:auto;">
  </td></tr>

  <!-- flag stripe: red · navy header · gold rule -->
  <tr><td style="height:3px; background:#c31f27;"></td></tr>
  <tr><td style="background:#02306e; padding:14px 20px; text-align:center;">
    <span class="issue-title" style="color:#ffffff; font-family:'El Messiri',Georgia,serif; font-size:26px; font-weight:700; letter-spacing:1px;">{cfg['issue_title']}</span><br>
    <span style="color:#a8c4e0; font-size:13px; font-style:italic; letter-spacing:.3px;">{issue_sub}</span>
  </td></tr>
  <tr><td style="height:4px; background:#c9a227;"></td></tr>

{render_ql(cfg)}
{sections_html}

{render_share(cfg)}
{render_footer(cfg)}
</table>
</td></tr>
</table>
</center>
</body>
</html>
"""


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    master_path = Path(sys.argv[1])
    date_label = master_path.name.replace(".both.html", "")
    soup = load_master(master_path)

    # week metadata: pull straight from the master so it never drifts from the source of truth
    preview_div = soup.find("div", style=re.compile("display:none"))
    preview_en, preview_sr = preview_div.decode_contents().split(" / ", 1)
    from datetime import date as _date
    y, m, d = (int(x) for x in date_label.split("-"))
    date_label_readable = _date(y, m, d).strftime("%B %-d, %Y")
    # Serbian date wording (day. month_genitive year.) -- Aug is fixed for now; extend if the
    # generator is ever used outside August.
    sr_months_gen = {8: "август"}
    date_label_sr = f"{d}. {sr_months_gen.get(m, m)} {y}"
    week = {
        "date_label": date_label_readable,
        "date_label_sr": date_label_sr,
        "preview_en": preview_en.strip(),
        "preview_sr": preview_sr.strip(),
    }

    for lang, suffix in [("en", ".html"), ("sr", ".serbian.html"), ("other", ".other.html")]:
        content_lang = "sr" if lang == "sr" else "en"
        sections_html = extract_sections(soup, content_lang)
        out = build_variant(lang, week, sections_html)
        out_path = master_path.parent / f"{date_label}{suffix}"
        out_path.write_text(out, encoding="utf-8")
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
