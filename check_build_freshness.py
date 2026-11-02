#!/usr/bin/env python3
"""
Catch a generated draft variant that was hand-edited (or a .both.html edit
that was never rebuilt) instead of going through build.py / build_site_html.py.

    python3 check_build_freshness.py 2026-11-05

Why this exists: `<date>.html`, `<date>.serbian.html`, `<date>.other.html`,
and `<date>.site.html` are documented as generated-only -- build.py's own
docstring says "Never hand-edit those three files -- the next build
overwrites them" -- but nothing actually enforced that. This bit for real
on 2026-11-05: a same-day edit (removing a surname from one line, adding a
banner image above the weekly intro paragraph) was applied by hand,
file-by-file, to .both.html AND all four generated variants, instead of
editing .both.html once and re-running build.py + build_site_html.py.
The hand edit to .site.html was also incomplete -- it only added the new
image to the English half, silently missing the Serbian half -- a drift
class a real `build.py` run can't produce (it derives both halves from the
same master source) but a manual multi-file edit can.

Rebuilds the four generated variants into a temp directory from the
CURRENT .both.html and byte-diffs each against what's actually committed
in drafts/. Any difference is a hard failure: either a generated file was
hand-edited, or .both.html changed without a rebuild.

Run this BEFORE committing drafts/ (README Step 1, right after editing
.both.html -- before or alongside check_title_date.py/check_calendar.py).
It does not run archive_publish.py or any publish step -- safe during
board review, well before Max approves the Thursday send.

Also runs automatically, WARN-ONLY, from hooks/pre-commit whenever a
drafts/<date>.both.html is part of the commit -- same pattern as that
hook's existing business_owner_map.json check, and for the same reason
(feedback_always_commit_git is HARD: nothing in this repo blocks an
ordinary commit). check(date) is the importable entry point the hook
uses; main() is the CLI wrapper that turns the same result into a hard
exit code for standalone/README use.
"""
import filecmp
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent
DRAFTS_DIR = ROOT / "drafts"


class BuildCheckError(Exception):
    """Fatal -- a precondition failed (missing file, build.py/build_site_html.py itself errored).
    Distinct from a drift finding (a generated file not matching a fresh build), which is
    reported as a plain string in check()'s returned list instead."""

# build.py writes its outputs next to whatever .both.html path it's given
# (master_path.parent), so it's safe to point at a temp copy. build_site_html.py
# is NOT -- it hardcodes DRAFTS_DIR = ROOT/"drafts" for both its .html/.serbian.html
# inputs and its .site.html output, regardless of the path argument it's passed.
# It genuinely can't be run against an isolated temp copy, so site.html is checked
# by running it for real against the live repo and restoring the original bytes
# afterward -- see check_site_html() below.
BUILD_PY_SUFFIXES = ("html", "serbian.html", "other.html")


def check_build_py(date, both_path):
    committed = {
        suffix: DRAFTS_DIR / f"{date}.{suffix}" for suffix in BUILD_PY_SUFFIXES
    }
    for suffix, path in committed.items():
        if not path.exists():
            raise BuildCheckError(f"missing file: {path}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        tmp_both = tmp / both_path.name
        shutil.copy(both_path, tmp_both)

        result = subprocess.run(
            [sys.executable, str(ROOT / "build.py"), str(tmp_both)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise BuildCheckError(f"build.py failed:\n{result.stdout}\n{result.stderr}")

        stale = []
        for suffix, committed_path in committed.items():
            fresh_path = tmp / f"{date}.{suffix}"
            if not fresh_path.exists():
                stale.append(f"{committed_path.name}: build.py did not produce this file at all")
                continue
            if not filecmp.cmp(committed_path, fresh_path, shallow=False):
                stale.append(f"{committed_path.name}: differs from a fresh build.py run")
        return stale


def check_site_html(date, both_path):
    site_path = DRAFTS_DIR / f"{date}.site.html"
    if not site_path.exists():
        raise BuildCheckError(f"missing file: {site_path}")

    original = site_path.read_bytes()
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "build_site_html.py"), str(both_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise BuildCheckError(f"build_site_html.py failed:\n{result.stdout}\n{result.stderr}")
        fresh = site_path.read_bytes()
        return [] if fresh == original else [f"{site_path.name}: differs from a fresh build_site_html.py run"]
    finally:
        # build_site_html.py always overwrites the real file in place --
        # this checker must not leave that change behind, pass or fail.
        site_path.write_bytes(original)


def check(date):
    """Returns a list of drift strings (empty = clean). Raises BuildCheckError
    on a fatal precondition failure (missing file, build script itself errored)."""
    both_path = DRAFTS_DIR / f"{date}.both.html"
    if not both_path.exists():
        raise BuildCheckError(f"missing file: {both_path}")

    stale = check_build_py(date, both_path)
    # site.html is derived FROM .html/.serbian.html, not from .both.html
    # directly -- if those are already stale, check it anyway (it still
    # answers "is site.html in sync with its immediate inputs"), but call
    # that out so the fix instructions aren't misread as two unrelated bugs.
    stale += check_site_html(date, both_path)
    return stale


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    date = sys.argv[1]

    try:
        stale = check(date)
    except BuildCheckError as e:
        print(str(e))
        sys.exit(1)

    if stale:
        print(f"FAILED -- {len(stale)} generated file(s) out of sync with drafts/{date}.both.html:")
        for s in stale:
            print(f"  - {s}")
        print(
            "\nFix: run `python3 build.py drafts/{d}.both.html` then "
            "`python3 build_site_html.py drafts/{d}.both.html`, "
            "re-diff, then commit the regenerated files. "
            "Never hand-edit .html/.serbian.html/.other.html/.site.html directly.".format(d=date)
        )
        sys.exit(1)

    print(f"OK -- all four generated variants match a fresh build from drafts/{date}.both.html")


if __name__ == "__main__":
    main()
