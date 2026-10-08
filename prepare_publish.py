#!/usr/bin/env python3
"""
Run every LOCAL/scriptable step of "prepare the newsletter for publish" in
one command, so the sequence can't be partially skipped by hand.

    python3 prepare_publish.py 2026-10-08

Chains, in order (each is also runnable standalone -- see each script's
own docstring):
  1. build.py              -- regenerate .html/.serbian.html/.other.html
                               from the approved .both.html
  2. check_calendar.py     -- advisory only, never blocks (see its own
                               docstring on why it can't be exhaustive)
  3. check_email_consistency.py -- HARD GATE: email.html's dates must
                               match both.html's approved dates (the
                               2026-10-08 bug class -- see that script's
                               docstring). Warnings print but don't block;
                               pass --strict to make them blocking too.
  4. commit + push drafts/*
  5. archive_publish.py    -- publish to the GitHub Pages archive
  6. commit + push archive/*
  7. build_site_html.py    -- produce drafts/<date>.site.html for the CMS paste
  8. add_utm_tags.py       -- tag email.html's links
  9. check_links.py --no-fetch -- fast offline pass only; the live-fetch
                               pass is run again at the end of Step 10
                               below, once the parish CMS page may exist
 10. commit + push drafts/*.email.html (if changed)
 11. check_publish_status.py -- reports what's live vs. still needed;
                               at THIS point in the workflow the parish
                               CMS page, Newsletter Archive listing, and
                               Beehiiv draft are expected to show MISSING
                               -- those three remain human/browser-gated
                               (2FA, Cloudflare bot detection on Beehiiv's
                               login, a drag-and-drop block editor) and
                               are NOT attempted by this script. Re-run
                               check_publish_status.py again after doing
                               them to confirm everything landed.

Does NOT touch Send -- that's always Max's own click in Beehiiv, per the
two-gate rule (board approves content, Max approves the send).

Stops immediately (non-zero exit) if any hard gate fails, so a bad draft
never reaches the manual CMS/Beehiiv steps.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.stdout.reconfigure(line_buffering=True)


def run(cmd, allow_fail=False, label=None):
    label = label or " ".join(cmd)
    print(f"\n{'=' * 70}\n>>> {label}\n{'=' * 70}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0 and not allow_fail:
        print(f"\nSTOPPED -- '{label}' failed (exit {result.returncode}).")
        sys.exit(result.returncode)
    return result.returncode


def git(args, label):
    status = subprocess.run(["git", "status", "--short"] + args, cwd=ROOT, capture_output=True, text=True)
    if not status.stdout.strip():
        print(f"\n(no changes to commit for {label})")
        return
    run(["git", "add"] + args, label=f"git add {label}")
    run(["git", "commit", "-m", label], label=f"git commit: {label}")
    run(["git", "push"], label="git push")


def main():
    args = sys.argv[1:]
    strict = "--strict" in args
    args = [a for a in args if a != "--strict"]
    if len(args) != 1:
        print(__doc__)
        sys.exit(1)
    date = args[0]
    both = f"drafts/{date}.both.html"
    email = f"drafts/{date}.email.html"
    if not (ROOT / both).exists():
        print(f"missing {both} -- write the draft first (README Step 1)")
        sys.exit(1)

    run([sys.executable, "build.py", both], label="1. build.py (regenerate EN/SR/other variants)")
    run([sys.executable, "check_calendar.py", date], allow_fail=True, label="2. check_calendar.py (advisory)")

    consistency_cmd = [sys.executable, "check_email_consistency.py", date]
    if strict:
        consistency_cmd.append("--strict")
    run(consistency_cmd, label="3. check_email_consistency.py (HARD GATE)")

    git(["drafts/"], f"Rebuild {date} newsletter drafts")

    run([sys.executable, "archive_publish.py", both], label="5. archive_publish.py")
    git(["archive/"], f"Publish {date} issue to GitHub Pages archive")

    run([sys.executable, "build_site_html.py", both], label="7. build_site_html.py (produces .site.html for CMS paste)")
    run([sys.executable, "add_utm_tags.py", email, date], label="8. add_utm_tags.py")
    run([sys.executable, "check_links.py", "--no-fetch", email],
        label="9. check_links.py --no-fetch (fast pass; full fetch happens after CMS page exists)")

    git(["drafts/" + Path(email).name], f"Tag {date} email brief links with UTM params")

    status_rc = run([sys.executable, "check_publish_status.py", date], allow_fail=True,
                     label="11. check_publish_status.py")

    if status_rc == 0:
        print(f"""
{'=' * 70}
LOCAL STEPS DONE -- and the three URL-checkable surfaces are already live
(check_publish_status.py confirmed it above). Only remaining:
{'=' * 70}
  - Confirm the Beehiiv draft manually (no reliable API check available)
  - Max reviews and sends in Beehiiv (README Step 7) -- never automated
""")
    else:
        print(f"""
{'=' * 70}
LOCAL STEPS DONE. Still needed (human/browser-gated, not automated here --
see the check_publish_status.py output above for exactly what's missing):
{'=' * 70}
  - Create/update the parish CMS page and paste in drafts/{date}.site.html
    (README Step 4), then re-run: python3 check_links.py {email}
    (full fetch this time, now that the parish page exists)
  - Add the Newsletter Archive listing entry (README Step 6)
  - Load drafts/{email.split('/')[-1]} into the Beehiiv draft as an HTML
    Snippet block (README Step 5)
  - Re-run: python3 check_publish_status.py {date}  -- confirm all live
  - Max reviews and sends in Beehiiv (README Step 7) -- never automated
""")


if __name__ == "__main__":
    main()
