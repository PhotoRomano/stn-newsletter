#!/usr/bin/env python3
"""
Reusable guard: before any script/draft loads a parish sign-up sheet's
contacts into a recipient list, make the minors-in-the-data question
structural instead of something a session has to notice by eye.

    from check_minor_safety import partition_by_age, require_visible_list_safe

Why this exists: 2026-10-27, building the Young Adults intro email, the
sign-up sheet turned out to still be the old "Teens" form under the hood
(columns never relabeled after the group was renamed) -- real entries
included a 13- and 15-year-old, each with their own personal email on
file. That was caught by reading the raw data by hand mid-session, not by
any tooling. This module exists so the next script that pulls a sign-up
sheet doesn't have to re-derive that caution from scratch, or worse, skip
it because nobody thought to look.

RESOLVED POLICY (Max, 2026-10-27, in two parts across the same
conversation -- both halves matter, don't collapse them into one rule):
  1. "These adults need to know who the others are so they can self
     organize" -> a VISIBLE recipient list (To/Cc) for an adult peer
     group is fine and wanted.
  2. "Parents who signup for this list want their kids to receive email
     for this social group" -> minors SHOULD receive these emails; a
     parent opting a child into the sign-up is explicit, informed
     consent for that child to get this communication. Excluding minors
     outright (this module's first version) was MORE cautious than Max
     actually wants.
  Those two instructions are not in conflict once kept separate: whether
  a minor receives the email at all (yes, per #2) is a different
  question from whether a minor's personal contact address gets EXPOSED
  to a visible, self-organizing list of adult strangers (per #1, which
  was framed around adults specifically). This module only gates the
  second question. It does not gate, and must never be read as
  justification to gate, whether a minor is included as a recipient.

What `require_visible_list_safe` actually does: given a set of entries
with an age field, if any are minors AND the caller is building a VISIBLE
list (To/Cc), it raises unless the caller explicitly acknowledges it
(`acknowledge_minors=True`) -- forcing a conscious choice (BCC the minor
instead so they still get the invite but their address isn't broadcast
to the group, or get explicit confirmation this specific list is fine to
expose) rather than a silent default either way. There is no such gate
for BCC/hidden-recipient or parent-addressed sends -- those are always
fine for a minor whose parent opted them in.
"""

MIN_ADULT_AGE = 18


def partition_by_age(entries, age_key="age", min_adult_age=MIN_ADULT_AGE):
    """entries: list of dicts each containing at least `age_key` (int).
    Returns (adults, minors)."""
    adults, minors = [], []
    for e in entries:
        (adults if e[age_key] >= min_adult_age else minors).append(e)
    return adults, minors


class VisibleMinorExposure(Exception):
    """Raised when a visible (To/Cc) recipient list would include a
    minor's personal contact address without explicit acknowledgement."""


def require_visible_list_safe(entries, age_key="age", name_key="name",
                               acknowledge_minors=False, min_adult_age=MIN_ADULT_AGE):
    """Call this before populating a VISIBLE (To/Cc) field from sign-up
    data. Does nothing if there are no minors in `entries`. If there ARE
    minors and acknowledge_minors is not True, raises
    VisibleMinorExposure listing who would be exposed -- the caller
    should either drop those entries (route them BCC/parent-addressed
    instead) or pass acknowledge_minors=True after a real decision to
    include them visibly for this specific send.

    Never use acknowledge_minors=True as a default -- it exists for a
    one-off, deliberate exception, not to silence this check routinely."""
    _, minors = partition_by_age(entries, age_key, min_adult_age)
    if minors and not acknowledge_minors:
        names = ", ".join(f"{e[name_key]} ({e[age_key]})" for e in minors)
        raise VisibleMinorExposure(
            f"{len(minors)} minor(s) would be exposed in a VISIBLE recipient list: {names}. "
            f"This is about VISIBILITY only -- minors are still fine to include as BCC/hidden "
            f"recipients or via a parent's address (see this module's docstring, 'RESOLVED "
            f"POLICY'). Either route these entries BCC/hidden instead, or re-call with "
            f"acknowledge_minors=True if a visible list is genuinely intended for this send."
        )
