#!/usr/bin/env python3
"""
Shared helpers for this repo's check_*.py scripts -- the pieces that are
genuinely duplicated logic, not just "both scripts check something."

    from check_utils import CheckError, require_files, preserve_file

Why this exists: check_build_freshness.py's check_site_html() runs
build_site_html.py for real against the live drafts/<date>.site.html
(that script hardcodes its own path regardless of its argument -- see
check_build_freshness.py's module docstring), so the checker has to
capture the original bytes, let the real file get overwritten, then
restore it in a finally block no matter what happens in between. That's
the one risky, non-obvious pattern here -- get the finally wrong (or
skip it under a new exception path added later) and a "checker" starts
leaving real production drift behind as a side effect of being run.
Worth one shared, tested implementation rather than a second hand-rolled
try/finally the next time a checker needs to run something that mutates
a file in place to see what it would produce.

require_files() is the other small duplicate: every check_*.py here
starts by confirming its input files exist and bailing with a clear
message if not -- previously copy-pasted as a few lines of
`if not p.exists(): print(...); sys.exit(1)` per script (and, in
check_build_freshness.py specifically, as `raise BuildCheckError(...)`
per call site).

Deliberately NOT included here: check_email_consistency.py's visible-text
extraction and word/date diffing. That's real logic specific to "does a
hand-written brief still match the approved full issue," not boilerplate
-- a shared module should hold the risky plumbing both scripts need, not
force two different kinds of drift-checking through one abstraction
because they're both called "check_*.py".
"""
from contextlib import contextmanager
from pathlib import Path


class CheckError(Exception):
    """Fatal precondition failure for a check_*.py script (missing file,
    a delegated build/generation step itself erroring) -- distinct from a
    drift FINDING, which each script reports in its own result shape."""


def require_files(*paths):
    """Raise CheckError with a clear message if any path doesn't exist.
    Call before doing any real work so a missing-file typo fails fast
    with one message instead of an unrelated traceback three steps in."""
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        names = ", ".join(str(p) for p in missing)
        raise CheckError(f"missing file(s): {names}")


@contextmanager
def preserve_file(path):
    """Snapshot path's bytes, yield, then restore them -- even if the
    body raises. Use around any subprocess call that overwrites a real,
    committed file in place just to see what it WOULD produce (i.e. the
    file is being inspected, not actually being changed by this run)."""
    path = Path(path)
    original = path.read_bytes()
    try:
        yield original
    finally:
        path.write_bytes(original)
