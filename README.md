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
directly, matching the callout content in `<date>.both.html`.

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
this becomes both the "Read This Week's Issue" link target in the
Beehiiv brief and the source content for the parish-website CMS page
(next step).

### 4. Post to the parish website (OWS Site Manager CMS)

The live site shows English and Serbian together with a client-side
EN/СР toggle, so the CMS section needs both languages wrapped together,
not either generated file as-is:
```html
<style>
.stn-nl-wrap { background:#eef1f6; padding:16px 8px; }
</style>
<div class="stn-nl-wrap">
<center>
<div class="stn-en">[inner <table class="email-body">…</table> from <date>.html]</div>
<div class="stn-sr">[same, from <date>.serbian.html]</div>
</center>
</div>
```
Also strip the "Read this issue in" language-pref bar from each side
first — it contains `{{email}}` Beehiiv merge tags that render as
literal text on a static page (`archive_publish.py` already strips this
for the GitHub Pages archive; do the same here). Save the result as
`drafts/<date>.site.html` for the record.

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
- `*.html`, `*-sr.html` at the repo root — standalone sign-up/subscribe
  pages linked from newsletter CTAs (Church School, Serbian School,
  Teens/Young Adults, general mailing list).
