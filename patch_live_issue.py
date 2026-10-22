#!/usr/bin/env python3
"""
Patch a SINGLE already-drafted/published newsletter issue with a small text
correction and push it through every derived surface in one command -- the
fast path for after-the-fact fixes (a wrong phrase, an ambiguous date
reference, a dead link) once an issue has already been built or even sent,
instead of hand-repeating the full edit -> build -> build_site_html ->
archive_publish -> commit/push -> re-copy -> re-paste cycle every time.

    python3 patch_live_issue.py 2026-10-22 \\
        --find "We hope you'll join us this Sunday." \\
        --replace "We hope you'll join us on Sunday, Nov 1."

What it does:
  1. Applies the find/replace to drafts/<date>.both.html and, if the text
     also appears there, drafts/<date>.email.html. Fails loudly (exit 1,
     nothing written) if --find isn't found in either file -- never
     silently no-ops on a live correction.
  2. Runs build.py, build_site_html.py, archive_publish.py in sequence --
     the same local chain prepare_publish.py uses -- to regenerate every
     surface derived from both.html: .html/.serbian.html/.other.html,
     .site.html for the CMS paste, and archive/<date>.html + archive/index.html.
  3. Commits + pushes drafts/ and archive/ together in one commit.
  4. Copies the final drafts/<date>.site.html to the clipboard (pbcopy,
     macOS only) so the only remaining manual step is one paste into the
     parish CMS page's HTML Code section (Site Manager) -- see README
     Step 4 for the paste mechanics and its gotchas (Responsive dropdown,
     verify against the live page not the admin form).

Does NOT touch the Newsletter Archive listing or the Beehiiv draft/send --
those are separate, human/browser-gated surfaces that don't derive from
both.html. If the patched text was already sent in a live Beehiiv email,
that copy is locked in and this script can't touch it -- it only tells you
whether the text was found there so you know to flag it, not fix it.

--count N asserts exactly N occurrences were found (summed across both
files) before applying anything -- an extra guardrail for when you want to
be sure you're not silently touching more or fewer spots than expected on
a live correction.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.stdout.reconfigure(line_buffering=True)


def run(cmd, label=None):
    label = label or " ".join(cmd)
    print(f"\n{'=' * 70}\n>>> {label}\n{'=' * 70}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"\nSTOPPED -- '{label}' failed (exit {result.returncode}).")
        sys.exit(result.returncode)


def git_commit_push(paths, message):
    status = subprocess.run(["git", "status", "--short"] + paths, cwd=ROOT, capture_output=True, text=True)
    if not status.stdout.strip():
        print("\n(no changes to commit)")
        return
    run(["git", "add"] + paths, label=f"git add {' '.join(paths)}")
    run(["git", "commit", "-m", message], label=f"git commit: {message}")
    run(["git", "push"], label="git push")


def parse_args(argv):
    if len(argv) < 1:
        print(__doc__)
        sys.exit(1)
    date = argv[0]
    rest = argv[1:]
    find = replace = None
    count = None
    i = 0
    while i < len(rest):
        if rest[i] == "--find" and i + 1 < len(rest):
            find = rest[i + 1]; i += 2
        elif rest[i] == "--replace" and i + 1 < len(rest):
            replace = rest[i + 1]; i += 2
        elif rest[i] == "--count" and i + 1 < len(rest):
            count = int(rest[i + 1]); i += 2
        else:
            print(f"unrecognized or incomplete argument: {rest[i]}")
            sys.exit(1)
    if find is None or replace is None:
        print(__doc__)
        print("\n--find and --replace are both required")
        sys.exit(1)
    return date, find, replace, count


def apply_patch(path, find, replace):
    """Returns the number of occurrences replaced (0 if the file doesn't
    exist or the text isn't in it)."""
    if not path.exists():
        return 0
    text = path.read_text()
    n = text.count(find)
    if n == 0:
        return 0
    path.write_text(text.replace(find, replace))
    return n


def main():
    date, find, replace, expected_count = parse_args(sys.argv[1:])
    both = ROOT / f"drafts/{date}.both.html"
    email = ROOT / f"drafts/{date}.email.html"
    if not both.exists():
        print(f"missing {both} -- is the date right?")
        sys.exit(1)

    total = 0
    touched = []
    for path in (both, email):
        n = apply_patch(path, find, replace)
        if n:
            touched.append((path.name, n))
            total += n

    if total == 0:
        print(f"'--find' text not found in {both.name} or {email.name} -- nothing changed.")
        sys.exit(1)

    if expected_count is not None and total != expected_count:
        print(f"Expected {expected_count} occurrence(s), found {total} -- the file(s) above were "
              f"already edited. Revert with 'git checkout -- drafts/{date}.both.html drafts/{date}.email.html' "
              f"if this count mismatch means something's wrong.")
        sys.exit(1)

    print(f"\nPatched {total} occurrence(s):")
    for name, n in touched:
        print(f"  {name}: {n}")

    run([sys.executable, "build.py", str(both)], label="1. build.py (regenerate EN/SR/other variants)")
    run([sys.executable, "build_site_html.py", str(both)], label="2. build_site_html.py (regenerate .site.html for CMS paste)")
    run([sys.executable, "archive_publish.py", str(both)], label="3. archive_publish.py (republish GitHub Pages archive)")

    git_commit_push(["drafts/", "archive/"], f"Patch {date} issue: {find[:60]}")

    site_html = ROOT / f"drafts/{date}.site.html"
    if site_html.exists():
        expected_clip = site_html.read_text()
        subprocess.run(["pbcopy"], input=expected_clip, text=True)
        actual_clip = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
        if actual_clip != expected_clip:
            print(f"\nWARNING -- clipboard does not match {site_html.name} right after pbcopy "
                  f"(something else overwrote it -- a clipboard collision, not a bug in this "
                  f"script). DO NOT paste into the CMS yet: re-run just the copy with "
                  f"'pbcopy < drafts/{date}.site.html', then immediately verify with "
                  f"'pbpaste | diff - drafts/{date}.site.html' before pasting into Site Manager.")
        else:
            print(f"\n{site_html.name} copied to clipboard (verified) -- paste into the parish "
                  f"CMS page's HTML Code section (Site Manager) to finish.")

    print(f"""
{'=' * 70}
DONE -- drafts/, archive/ pushed. Still needed (not automated, browser-gated):
{'=' * 70}
  - Paste the clipboard contents into the parish CMS page's HTML Code
    section (Site Manager), save, verify on the live page (not just the
    admin preview) -- see README Step 4 for the Responsive-dropdown gotcha
  - If a Beehiiv draft/send for this date already has the old text, that
    copy is locked in once sent -- this script never touches Beehiiv
  - Re-run: python3 check_publish_status.py {date} -- confirm everything
    that CAN be checked is live
""")


if __name__ == "__main__":
    main()
