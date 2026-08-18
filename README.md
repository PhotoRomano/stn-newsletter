# stn-newsletter

"The Messenger" — weekly parish newsletter for St. Nicholas Serbian Orthodox
Church (Elkins Park, PA). Published as static HTML on GitHub Pages at
`photoromano.github.io/stn-newsletter`; each issue's content goes out via
Beehiiv, in one of four language variants a subscriber can pick between
(the language-preference bar at the top of every issue).

## Weekly workflow

1. Edit **`drafts/<date>.both.html`** — the bilingual (English + Serbian
   side-by-side) master. This is the ONE file the board reviews each week
   (linked from `index.html` as "Current Draft"). Weekly content lives in
   two-column rows, each with a `<td class="bl-col bl-en">` / `<td
   class="bl-col bl-sr">` pair — edit both languages together so nothing
   drifts out of sync between them.
2. Run the generator to produce the other three send variants:
   ```
   python3 build.py drafts/<date>.both.html
   ```
   This (re)writes `<date>.html` (English), `<date>.serbian.html`
   (Serbian), and `<date>.other.html` (English + a "translation not
   available yet" banner, for subscribers with no language preference set).
3. **Never hand-edit** `<date>.html` / `<date>.serbian.html` /
   `<date>.other.html` directly — the next `build.py` run overwrites them.
   If something in an output file looks wrong, fix the corresponding
   section in `<date>.both.html` and rebuild.
4. Commit and push all four files. This repo deploys straight from
   `main` via GitHub Pages — an unpushed commit is invisible on the live
   preview even though it's "done" locally.

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
- `drafts/` — one dated set of files per issue.
- `build.py` — the generator (see above). Requires `beautifulsoup4`.
- `*.html`, `*-sr.html` at the repo root — standalone sign-up/subscribe
  pages linked from newsletter CTAs (Church School, Serbian School,
  Teens/Young Adults, general mailing list).
