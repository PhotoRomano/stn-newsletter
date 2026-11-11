#!/usr/bin/env bash
# run_qa.sh <date> -- run every pre-send QA check for one issue in one shot.
#
#     ./run_qa.sh 2026-11-12
#
# Built 2026-11-11 after repeatedly chaining these by hand every prep
# session. Runs, in order: title/date, calendar cross-check, email
# consistency, board-resolution regressions, link validation (both/site/
# email variants), build freshness, business-owner sync, publish status.
# check_minor_safety.py is NOT included -- it's an importable guard module
# for scripts that load sign-up-sheet contacts, not a per-issue report.
#
# Several of these (check_calendar.py, check_business_owner_sync.py,
# check_publish_status.py, check_links.py) make real network calls to
# hosts that are not on a sandboxed Claude Code session's allowlist
# (stnicholasphilly.org, facebook.com, tithe.ly, *.workers.dev,
# github.io) and will FALSE-FAIL with "Tunnel connection failed: 403
# Forbidden" / IncompleteRead errors inside that sandbox. If you see
# those specific errors, re-run this script with the sandbox override
# rather than trusting the failure.
#
# Advisory checks (calendar, board-resolutions, email-consistency) print
# their own REVIEW/WARNING output and never affect this script's exit
# code -- read them, they don't gate anything. Hard-fail checks
# (title-date, links, build-freshness, business-owner-sync) set FAILED=1
# on any non-zero exit. publish-status is expected to report NOT READY
# before send day -- it's informational here, not a failure.
set -u
cd "$(dirname "$0")"

if [ $# -ne 1 ]; then
  echo "usage: $0 <date>  e.g. $0 2026-11-12" >&2
  exit 1
fi
DATE="$1"
FAILED=0

run() {
  echo "=== $* ==="
  python3 "$@"
  status=$?
  if [ $status -ne 0 ]; then
    FAILED=1
    echo "--> exit $status"
  fi
  echo
}

run check_title_date.py "$DATE"
run check_calendar.py "$DATE"
run check_email_consistency.py "$DATE"
run check_board_resolutions.py "$DATE"
for f in "drafts/$DATE.both.html" "drafts/$DATE.site.html" "drafts/$DATE.email.html"; do
  [ -f "$f" ] && run check_links.py "$f"
done
run check_build_freshness.py "$DATE"
run check_business_owner_sync.py "$DATE"

echo "=== check_publish_status.py $DATE (informational -- NOT READY is expected before send day) ==="
python3 check_publish_status.py "$DATE"
echo

if [ $FAILED -ne 0 ]; then
  echo "QA: one or more hard checks FAILED -- if the failures are network/Tunnel/403 errors, re-run outside the sandbox before trusting this."
  exit 1
fi
echo "QA: all hard checks passed."
