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

# Internal routing must use the unique libreseal-* aliases: generic service
# names can resolve to other projects' containers on shared Docker networks.
if grep -nE '//(backend|frontend):' nginx/default.conf docker-compose.yml; then
  fail "generic backend/frontend host in nginx/default.conf or docker-compose.yml; use libreseal-backend / libreseal-frontend"
fi

# One server version: backend/version.txt, frontend/package.json and the
# default image tag in docker-compose.yml must agree (see scripts/set-version.sh).
backend_version="$(tr -d '[:space:]' < backend/version.txt)"
frontend_version="$(python3 -c 'import json; print(json.load(open("frontend/package.json"))["version"])')"
compose_versions="$(grep -oE 'LIBRESEAL_VERSION:-[^}]*' docker-compose.yml | cut -d- -f2- | sort -u)"
if [ "$backend_version" != "v$frontend_version" ] || [ "$compose_versions" != "$frontend_version" ]; then
  fail "versions disagree: backend/version.txt=$backend_version frontend/package.json=$frontend_version docker-compose.yml=$(echo "$compose_versions" | paste -sd, -)"
fi

[ $status -eq 0 ] && echo "LibreSeal guard: OK"
exit $status
