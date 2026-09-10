# stn-newsletter

"The Messenger" — weekly parish newsletter for St. Nicholas Serbian Orthodox
Church (Elkins Park, PA), sent every **Thursday**, covering the upcoming week
(Sunday–Saturday). Three separate deliveries come out of one weekly draft:
a bilingual page on GitHub Pages (this repo), a bilingual page on the parish
website (`stnicholasphilly.org`, a separate CMS), and a short brief email via
Beehiiv that links out to the full issue. Full pipeline below — six phases,
roughly Sunday draft through Thursday send.

## Weekly workflow

### 1. Draft

Edit **`drafts/<date>.both.html`** — the bilingual (English + Serbian
side-by-side) master. This is the ONE file the board reviews each week
(linked from `index.html` as "Current Draft"). Weekly content lives in
two-column rows, each with a `<td class="bl-col bl-en">` / `<td
class="bl-col bl-sr">` pair — edit both languages together so nothing
drifts out of sync between them. `<date>` is the Thursday send date, not
the week-start Sunday.

Pull liturgical data from `stnicholasphilly.org/calendar.html` (its JS
`FEASTS` array) and apply Julian-calendar context (13 days behind
Gregorian) for service listings.

Before moving on, check:
- Run `python3 check_calendar.py <date>` — cross-checks the draft against
  the site's own live `calendar.html` FEASTS data and prints anything
  falling in this issue's week that the draft might have missed (a
  fundraising lunch, a Great Feast, SerbFest). It's a checklist, not an
  auto-populator — FEASTS is too sparse to give real liturgical service
  times (it doesn't even cover every weekday feast), so it won't catch
  everything, but it catches the "forgot this was happening" class of
  miss for free.
- Prayer-request names and Serbian phrasing confirmed with Max
- SerbFest / school-enrollment / event dates are correct
- No `[BOARD:]` placeholder text left anywhere, in any language — an
  internal note-to-self ("hours TBD, confirm before send") is not
  acceptable copy for ~215 subscribers. If a real fact (hours, a band
  name, a price) isn't available yet, either get it from Max or replace
  the placeholder with safe generic wording that points to an existing
  link/flyer instead of inventing a number — never fabricate the missing
  detail yourself.
- The amber "NEEDS BOARD INPUT" callout box at the top of the master (if
  present) still accurately lists every open question — `archive_publish.py`
  strips this box automatically before anything goes public, so it's safe
  to leave visible in the draft for board review.

Also hand-write **`drafts/<date>.email.html`** — the short Beehiiv brief.
This is NOT the full newsletter: one highlight callout (usually whatever's
most time-sensitive that week) plus a short "This Week" paragraph linking
out to the full issue. There's no generator for this one — write it
directly, matching the callout content in `<date>.both.html`. **Link out
to `stnicholasphilly.org/newsletter-<date>`** (the live parish site, not
the GitHub Pages archive) — that page doesn't exist yet at this point in
the workflow (it's built in Step 4), but write the link now anyway so
it's correct once that page goes live; just don't rely on it resolving
before then.

Then run the generator to produce the other three full-issue variants:
```
python3 build.py drafts/<date>.both.html
```
This (re)writes `<date>.html` (English), `<date>.serbian.html`
(Serbian), and `<date>.other.html` (English + a "translation not
available yet" banner, for subscribers with no language preference set).

**Never hand-edit** `<date>.html` / `<date>.serbian.html` /
`<date>.other.html` directly — the next `build.py` run overwrites them.
If something in an output file looks wrong, fix the corresponding
section in `<date>.both.html` and rebuild.

Commit and push. This repo deploys straight from `main` via GitHub
Pages — an unpushed commit is invisible on the live preview even though
it's "done" locally.

### 2. Board review

The draft becomes available at
`https://photoromano.github.io/stn-newsletter/drafts/<date>.both.html`.
Send this link to the board. Resolve anything they flag (including every
item in the "NEEDS BOARD INPUT" box) directly in `<date>.both.html`, then
re-run `build.py` and re-push. Don't move to archive publish until every
placeholder and open question is actually resolved, not just noted.

### 3. Publish archive

Run after board approval:
```
python3 archive_publish.py drafts/<date>.both.html
```
Strips the DRAFT banner, the "NEEDS BOARD INPUT" box, and the
email-only language-preference bar; rebuilds `archive/index.html`.
Commit and push. Live at
`https://photoromano.github.io/stn-newsletter/archive/<date>.html` —
this feeds the parish-website CMS page (next step) and serves as a
permanent public mirror/backlink target. **It is not what the Beehiiv
brief links to** — that goes to the live parish site itself (see Step 5)
so readers land on `stnicholasphilly.org`, not an unbranded GitHub Pages
URL.

### 4. Post to the parish website (OWS Site Manager CMS)

The live site shows English and Serbian together with a client-side
EN/СР toggle, so the CMS section needs both languages wrapped together,
not either generated file as-is. Build this with:
```
python3 build_site_html.py drafts/<date>.both.html
```
This wraps the `.html`/`.serbian.html` files' `<table class="email-body">`
content in a `stn-nl-wrap`/`stn-en`/`stn-sr` shell and strips the "Read
this issue in" language-pref bar from each side (it contains `{{email}}`
Beehiiv merge tags that render as literal text on a static page —
`archive_publish.py` strips the same thing for the GitHub Pages archive).
Writes `drafts/<date>.site.html`, which is what actually gets pasted into
the CMS below.

Then in Site Manager (`stnicholasphilly.org/admin`, login may need a
2FA code emailed to the admin address if the session expired):
1. **Pages** → the newsletter page (reused weekly, currently page id
   **129** — rename its title/slug each week, don't create a new page)
2. **Page Properties** → update Title (`The Messenger — Week of
   [Month D, YYYY]`) and Page Name/slug (`newsletter-<date>`) → Save
3. **Edit Page** → the page's one **HTML Code** section (currently
   section id **316**) → pencil icon to open it → select all, paste in
   `<date>.site.html`'s content → Save changes. This field is a plain
   `<textarea>`, so clipboard paste (copy the file, `Cmd+V`) works
   cleanly every time — no special handling needed here, unlike Beehiiv
   (see gotchas below).

Verify afterward: fetch the live URL
(`stnicholasphilly.org/newsletter-<date>`) and confirm it contains this
week's real content and no literal `{{email}}` text anywhere.

### 5. Load the Beehiiv draft

First, tag the brief's outbound links so Beehiiv's click data can
actually attribute traffic to the newsletter instead of lumping it in
with direct/social visits:
```
python3 add_utm_tags.py drafts/<date>.email.html <date>
```
Idempotent (safe to re-run) — adds `utm_source=newsletter&utm_medium=
email&utm_campaign=<date>` to any link that doesn't already carry a
`utm_source` (so it won't double-tag something like the Instagram flyer
link's own share-tracking param). Only run this on `.email.html` — the
full-issue variants and `.site.html` aren't sent as email, so
email-attribution tags don't belong on their links.

Then run the QA gate before pasting anything into Beehiiv:
```
python3 check_links.py drafts/<date>.email.html
```
Catches, automatically, the exact class of bug that slipped through
twice on 2026-09-10 (the emailed brief's "Read This Week's Issue" links
pointing at the GitHub Pages archive instead of the live parish site)
plus leftover `[BOARD:]`/`[TODO`/`[PLACEHOLDER` text and any dead link
(non-200). Exits non-zero on failure, so don't proceed to Beehiiv until
it passes. Add `--no-fetch` for a fast offline pass (skips the live
link-fetch step) — useful mid-edit, but always run the full version
(with fetch) at least once before loading the Beehiiv draft. Also worth
running against `<date>.both.html`, `<date>.site.html`, and
`archive/<date>.html` at their respective steps — the placeholder and
`{{email}}`-leak checks apply there too.

Beehiiv's "New Post" only offers **Blank draft post** or **Template
post** — there is no separate "Custom HTML post type" to pick at
creation time (older instructions describing that are stale).
1. Posts → **Start writing → Blank draft post**
2. Set **Title** and **Subtitle** (subtitle doubles as preview text) in
   the header fields directly
3. In the body, on an empty block, type `/html` and choose **HTML
   Snippet** (listed under "Premium" in the slash menu) — this is the
   block type that actually renders full HTML (banner image, colored
   callout boxes, etc.); the standard block editor cannot reproduce the
   real design and will look plain/broken if used instead
4. Copy `<date>.email.html`'s exact contents to the clipboard and paste
   once into that block (see gotchas below for why clipboard beats
   typing here)
5. Use the block's own **Preview** toggle to confirm it renders
   correctly — banner image loads, both language sections present,
   buttons styled — before moving on
6. **Audience** tab → confirm "All free subscribers"
7. Leave as **Draft** — do not send

### 6. Thursday: send

Max reviews the Beehiiv draft (Preview, then the full Review step) and
sends it himself. This is a deliberate two-gate process — board approves
the content, Max approves the actual send — and the final click is
always his.

## Platform gotchas (learned the hard way — check here before re-learning them)

- **Beehiiv's block editor: `Cmd+A` isn't reliably scoped to the block
  you're focused in.** It usually only selects that block's own text,
  but at least once it silently replaced the entire post body instead.
  To clear a block, use its drag-handle (⋮⋮ icon, appears on hover at
  the block's left edge) → **Delete** from the context menu — that
  method has never failed. Keyboard-based multi-block selection (click,
  Home, shift+click elsewhere, shift+End, Backspace) works sometimes but
  not consistently.
- **Beehiiv: don't paste over a block that already has other content.**
  Once, pasting into a partially-typed HTML Snippet block silently
  converted it into a plain-text paragraph (which then displayed the
  literal HTML source instead of rendering it). Delete the block
  entirely and insert a fresh, empty one, then paste into that.
- **Beehiiv: paste large HTML via the clipboard, not by typing it.**
  Simulated keystrokes for anything over a couple hundred characters are
  unreliable — key-dispatch can time out partway through and silently
  drop the last few characters, and the whole browser tab can stall on
  script-injection calls for a minute or more while it processes a huge
  paste. `pbcopy` the file, then `Cmd+V` once into an empty block.
- **Verify with each platform's own Preview before saving/sending** —
  Beehiiv's Preview toggle on the HTML Snippet block, the CMS's Live
  Preview panel above the HTML Code field. A source view that "looks
  right" doesn't guarantee it rendered right.
- **Editing `<date>.email.html` after Step 5 is already done does NOT
  update the live Beehiiv draft.** Beehiiv only has whatever was pasted
  in at load time — fixing the source file (a bad link, a typo) and
  committing it is necessary but not sufficient. You have to go back
  into the draft and redo the paste: delete the HTML Snippet block
  entirely, insert a fresh one, `pbcopy` the corrected file, `Cmd+V`
  once, then re-check Preview. This bit us for real once — a bad link
  target got fixed in the repo but the already-loaded draft kept
  serving the old version until it was manually re-synced. If you touch
  `<date>.email.html` post-Step-5 for any reason, treat the Beehiiv
  re-sync as part of that same fix, not optional follow-up.

## Why one master file

Before this generator existed, all four variants were hand-maintained
independently. That drifted: real content (a caption, a full sentence, a
whole paragraph) ended up present in some variants and silently missing
in others, and a broken image path only got fixed in one of the four
files. `build.py` derives en/sr/other mechanically from the one master,
so there's exactly one place to edit and one thing for the board to
review.

## What the generator does and doesn't touch

- **Extracted from the master** (changes every week): everything between
  "This Week at the Altar" and "Need a Priest" — the two-column
  `bl-en`/`bl-sr` content rows. The "Giving" section is a documented
  exception — its heading and buttons are shared bilingual-merged strings
  by design (`" &nbsp;/&nbsp; "` as the split point), not a bug, so the
  bilingual layout doesn't double up its call-to-action buttons.
- **Fixed per-language boilerplate** (rarely changes): masthead, quick
  links, language-preference bar, footer, and the "Share This Issue"
  block. These live directly in `build.py`'s `SHELL` dict, one entry per
  language — edit there if the boilerplate wording itself needs to
  change, not in a draft file.

## Files

- `index.html` — unlisted landing page linking the current draft, shared
  only with board members.
- `drafts/` — one dated set of files per issue:
  - `<date>.both.html` — bilingual master, hand-edited (see Step 1)
  - `<date>.html` / `<date>.serbian.html` / `<date>.other.html` —
    generated by `build.py`, never hand-edit
  - `<date>.email.html` — Beehiiv brief, hand-edited, no generator
  - `<date>.site.html` — parish-website CMS content (EN+SR wrapped),
    assembled per Step 4, kept for the record
- `archive/` — published, public issues plus `index.html`; generated by
  `archive_publish.py` from the approved master.
- `build.py` — generates the four `drafts/<date>.*` variants from the
  master. Requires `beautifulsoup4`.
- `archive_publish.py` — publishes an approved master to `archive/`,
  stripping the draft-only banner, board-input callout, and
  Beehiiv-only language-pref bar.
- `build_site_html.py` — assembles `drafts/<date>.site.html` (the
  parish-website CMS content) from the already-generated `.html` /
  `.serbian.html` files. Run after `build.py`. Requires `beautifulsoup4`.
- `check_calendar.py` — cross-checks a draft's week against the site's
  live `calendar.html` FEASTS data; prints anything the draft might have
  missed. Checklist only, not an auto-populator (see Step 1).
- `add_utm_tags.py` — tags `<date>.email.html`'s outbound links for
  click attribution before loading into Beehiiv (see Step 5).
- `check_links.py` — pre-send QA gate: wrong-link-target detection
  (GitHub archive vs. live site), leftover placeholder text, unresolved
  `{{email}}` leaks, and dead links. Run before loading the Beehiiv
  draft (see Step 5); exits non-zero on failure.
- `*.html`, `*-sr.html` at the repo root — standalone sign-up/subscribe
  pages linked from newsletter CTAs (Church School, Serbian School,
  Teens/Young Adults, general mailing list).
