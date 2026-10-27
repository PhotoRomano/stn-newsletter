#!/usr/bin/env python3
"""
Catch a cancelled/resolved item from a past issue silently reappearing in
the current draft, before it gets re-announced to ~215 subscribers.

    python3 check_board_resolutions.py 2026-10-29

Why this exists: on 2026-10-29, drafting that issue by copying forward from
2026-10-22 resurrected the Nov 7 "Krajina Evening" dinner (performance by
Boris Batula) -- it had appeared in the 2026-10-15 issue as "still needed
for the Oct 29 issue" (time/place/ticket price pending), but was in fact
confirmed CANCELLED and deliberately removed from the 2026-10-22 issue in
commit 1b43944 ("remove cancelled Krajina Evening dinner"). The absence
looked like an oversight relative to the Oct 15 note, so it got added back
without checking *why* it had disappeared. Max had to correct this live,
and said he'd flagged the same mistake before.

What this does: scans the full git history of this repo for commits whose
message contains a resolution/cancellation keyword ("cancel", "remove",
"drop", "pull", "scrap", "kill", "no longer happening", ...) together with
a quoted phrase -- e.g. `... the Nov 7 "Krajina Evening" dinner is
cancelled ...`. Each such quoted phrase becomes a thing to watch for. If
any of those phrases shows up again in the CURRENT draft (both.html or
email.html, visible text only, excluding the NEEDS BOARD INPUT box itself
since that box legitimately discusses resolution history), it's flagged.

Deliberately conservative (quoted-phrase matching only, not every removed
line) to keep false positives low -- like check_calendar.py, this is a
checklist to prompt a human glance, not an exhaustive or authoritative
gate. It will miss cancellations whose commit message never quoted the
item's name. A flag here means "go read the commit and confirm this isn't
the same mistake" -- it is not proof the item is still dead; a board could
always revive something later, and the warning is just a prompt to check.

Advisory only -- never fails the build (matches check_calendar.py, not
check_email_consistency.py). Run as part of prepare_publish.py's chain,
or standalone any time while drafting.
"""
import re
import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).parent

RESOLUTION_KEYWORDS = re.compile(
    r"\b(cancel(?:led|ed|ling|s)?|remov(?:e|ed|es|ing)|dropp?(?:ed|ing)?|"
    r"pull(?:ed|ing)?|scrapp?(?:ed|ing)?|kill(?:ed|ing)?|"
    r"no longer (?:happening|on|planned)|not happening)\b",
    re.IGNORECASE,
)

QUOTE_PATTERN = re.compile(r"[\"“]([^\"“”]{3,60})[\"”]")

# 2-4 word runs starting with a capital letter (Latin or Cyrillic) -- the
# shape of a proper noun / event name ("Boris Batula", "Krajina Evening").
# Used to pull candidate phrases out of REMOVED diff lines, since a
# cancelled item's name is not always quoted in the commit message itself
# (the actual 2026-10-29 miss: the cancellation commit quoted "Krajina
# Evening", but the resurrected draft used different wording -- "Dinner
# with Music ... Boris Batula" -- so only "Boris Batula", extracted from
# the diff, not the message, would have caught it).
PROPER_NOUN_PATTERN = re.compile(
    r"\b([A-ZА-Я][\w''’-]*(?:\s+[A-ZА-Я][\w''’-]*){1,3})\b"
)

TAG_PATTERN = re.compile(r"<[^>]+>")

# Generic calendar/institutional vocabulary that forms many legitimate
# STANDING phrases ("Special Assembly", "Parish Social Night") -- a
# candidate phrase composed ENTIRELY of these words is filtered out, since
# it's structural, not a one-off cancelled item's name. A phrase survives
# if at least one word isn't in this set (a real proper noun / distinctive
# term almost never is).
GENERIC_WORDS = {
    "the", "this", "that", "week", "weeks", "on", "at", "in", "for", "and",
    "with", "a", "an", "of", "to", "from", "is", "are", "was", "were", "be",
    "sun", "mon", "tue", "wed", "thu", "fri", "sat", "sunday", "monday",
    "tuesday", "wednesday", "thursday", "friday", "saturday",
    "nov", "oct", "dec", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep",
    "special", "assembly", "parish", "social", "night", "nights", "church",
    "serbian", "language", "school", "young", "adults", "divine", "liturgy",
    "altar", "horizon", "business", "businesses", "board", "input", "needs",
    "our", "own", "caring", "library", "forget", "don't", "support", "your",
    "priest", "need", "issue", "feature", "week's", "sisters", "circle",
    "slava", "great", "vespers", "pascha", "feast", "day", "liturgy", "it",
    "hall", "classifieds", "orthodox", "elkins", "park", "sale", "free",
    "community", "browse", "post", "listings", "full", "details", "give",
    "monthly", "once", "if", "st",
    # Cyrillic equivalents of the above -- the draft is bilingual, so
    # standing institutional vocabulary needs covering in both scripts.
    "ове", "недеље", "недељу", "наше", "нашу", "наша", "цркве", "цркви",
    "парохијску", "парохијска", "парохијски", "свете", "свету", "света",
    "литургије", "литургија", "литургију", "српске", "српска", "школе",
    "школу", "деце", "децу", "младе", "младих", "дружења", "дружење",
    "вечери", "вече", "скупштина", "скупштину", "ванредна", "ванредну",
    "недеља", "окт", "нов", "суб", "нед", "петак", "субота", "недеља",
}

# Record separators unlikely to appear in real commit text.
REC_START, FIELD_SEP, REC_END = "\x02", "\x1f", "\x03"

MIN_PHRASE_LEN = 4  # skip trivially short quoted fragments
MIN_PHRASE_WORDS = 2  # a single word ("Other") is almost never a specific cancelled item

# Standing section/UI names that get quoted in commit messages for completely
# unrelated reasons (renamed, restructured, a build.py regression fixed) --
# these recur in every issue by design, so quoting them near a resolution
# keyword is noise, not a signal. Keep in sync with the template's own H2
# headers in drafts/*.both.html.
STANDING_SECTION_NAMES = {
    "in this issue", "this week at the altar", "on the horizon",
    "parish community board", "parishioner businesses", "parish businesses",
    "caring for our own", "need a priest", "support your parish",
    "don't forget our parish library", "church school",
    "serbian language school", "young adults", "special assembly",
    "this week's feature", "ove nedelje", "needs board input",
}


def git_log_records():
    """Yield (hash, date, message) for every commit, full history."""
    out = subprocess.run(
        ["git", "log", "--date=short",
         f"--format={REC_START}%H{FIELD_SEP}%ad{FIELD_SEP}%B{REC_END}"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    for rec in out.split(REC_START)[1:]:
        rec = rec.rstrip(REC_END + "\n")
        h, d, msg = rec.split(FIELD_SEP, 2)
        yield h.strip(), d.strip(), msg.rstrip(REC_END)


def git_commit_files(commit_hash):
    out = subprocess.run(
        ["git", "show", "--name-only", "--format=", commit_hash],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def git_commit_diff_lines(commit_hash):
    """(removed_text, added_text) for this commit's changes to drafts/ or
    assets/, HTML tags stripped. Needed as a PAIR, not just removed text:
    most commits matching a resolution keyword are reformats/reorders
    (e.g. "drop 'A reminder:...' lead sentence" while reformatting a list
    as bullets) where the same names get removed from one spot and
    re-added elsewhere in the SAME commit -- that's not a cancellation,
    just a rewrite, and must not be flagged. Only a phrase that is
    removed and NEVER re-added anywhere in that commit's own diff is a
    real candidate for "this specific thing was killed"."""
    out = subprocess.run(
        ["git", "show", commit_hash, "--", "drafts/", "assets/"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    removed, added = [], []
    for line in out.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    return (
        TAG_PATTERN.sub(" ", "\n".join(removed)),
        TAG_PATTERN.sub(" ", "\n".join(added)),
    )


def _is_distinctive(phrase):
    words = re.findall(r"[\w'’]+", phrase.lower())
    return any(w not in GENERIC_WORDS for w in words)


def _add_phrase(results, seen_phrases, phrase, h, d, subject):
    phrase = phrase.strip().strip("'\"“”‘’")
    key = phrase.lower()
    if (
        len(phrase) < MIN_PHRASE_LEN
        or len(phrase.split()) < MIN_PHRASE_WORDS
        or key in seen_phrases
        or key in STANDING_SECTION_NAMES
        or not _is_distinctive(phrase)
    ):
        return
    seen_phrases.add(key)
    results.append({"phrase": phrase, "hash": h[:7], "date": d, "subject": subject})


def collect_resolved_phrases(current_date):
    """Return [{phrase, hash, date, subject}] for candidate names of things
    that were cancelled/removed in past commits, skipping any commit that
    touched the CURRENT issue's own draft files (those are same-issue
    edits, not a prior issue's resolution history). Two sources, combined:
      1. Quoted phrases in the commit message (high precision).
      2. Capitalized 2-4 word runs in lines the commit REMOVED from
         drafts/ or assets/ (catches cases where the resurrected draft
         uses different wording than the cancellation commit's own
         message -- see this script's docstring)."""
    own_prefix = f"drafts/{current_date}."
    results = []
    seen_phrases = set()
    for h, d, msg in git_log_records():
        if not RESOLUTION_KEYWORDS.search(msg):
            continue
        files = git_commit_files(h)
        if any(f.startswith(own_prefix) for f in files):
            continue
        subject = msg.splitlines()[0] if msg else ""

        for phrase in QUOTE_PATTERN.findall(msg):
            _add_phrase(results, seen_phrases, phrase, h, d, subject)

        removed_text, added_text = git_commit_diff_lines(h)
        added_lower = added_text.lower()
        for phrase in PROPER_NOUN_PATTERN.findall(removed_text):
            if phrase.lower() in added_lower:
                continue  # removed from one spot, re-added elsewhere in the same commit -- a rewrite, not a cancellation
            _add_phrase(results, seen_phrases, phrase, h, d, subject)
    return results


def visible_text_excluding_board_box(path):
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for tag in soup(["style", "script"]):
        tag.decompose()
    needs_board_text = soup.find(string=re.compile(r"NEEDS BOARD INPUT before this goes out"))
    if needs_board_text:
        container = needs_board_text.find_parent(["table", "div"])
        if container:
            container.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    return soup.get_text(" ")


def main():
    args = sys.argv[1:]
    if len(args) != 1:
        print(__doc__)
        sys.exit(1)
    date = args[0]
    both_path = ROOT / f"drafts/{date}.both.html"
    email_path = ROOT / f"drafts/{date}.email.html"
    paths = [p for p in (both_path, email_path) if p.exists()]
    if not paths:
        print(f"missing drafts/{date}.both.html -- write the draft first")
        sys.exit(1)

    phrases = collect_resolved_phrases(date)
    if not phrases:
        print("No quoted cancellation/removal phrases found in git history -- nothing to check.")
        return

    draft_text = " ".join(visible_text_excluding_board_box(p) for p in paths)

    hits = []
    for entry in phrases:
        if re.search(re.escape(entry["phrase"]), draft_text, re.IGNORECASE):
            hits.append(entry)

    if not hits:
        print(f"OK -- none of the {len(phrases)} previously-cancelled/removed phrase(s) "
              f"found in git history reappear in this draft.")
        return

    print(f"REVIEW -- {len(hits)} phrase(s) from past cancellations/removals reappear "
          f"in this draft (advisory, does not block):")
    for h in hits:
        print(f'  - "{h["phrase"]}" -- flagged in commit {h["hash"]} ({h["date"]}): {h["subject"]}')
        print(f"      Check that commit before keeping this -- confirm it wasn't re-confirmed "
              f"since, not just carried forward by habit.")


if __name__ == "__main__":
    main()
