#!/usr/bin/env bash
# Guards LibreSeal invariants: no Enterprise-licensed ee/ code and no
# commercial/telemetry dependencies may come back (e.g. via an upstream merge).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

status=0
fail() { echo "GUARD FAILED: $*" >&2; status=1; }

ee_files="$(git ls-files | grep -E '(^|/)ee/' || true)"
[ -z "$ee_files" ] || fail "ee/ files are tracked:
$ee_files"

if grep -rnE '^\s*(from ee[. ]|import ee([. ]|$))|(include|import_module)\(["'"'"']ee\.' backend --include='*.py'; then
  fail "backend imports Enterprise ee modules"
fi
if grep -rnE "from ['\"](@/ee/|(\.\./)+ee/)" frontend --include='*.ts' --include='*.tsx' \
     --exclude-dir=node_modules --exclude-dir=.next; then
  fail "frontend imports ee modules"
fi
if grep -nE '"(posthog-js|@stripe/[^"]+)"' frontend/package.json; then
  fail "telemetry or billing dependency in frontend/package.json"
fi
if grep -niE '^(stripe|posthog)' backend/requirements.txt; then
  fail "billing or telemetry dependency in backend/requirements.txt"
fi

[ $status -eq 0 ] && echo "LibreSeal guard: OK"
exit $status
