#!/usr/bin/env bash
# Tests for scripts/set-version.sh. Run: scripts/tests/test-set-version.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }

# Work on a copy so the repository is never modified.
mkdir -p "$WORK/scripts" "$WORK/backend" "$WORK/frontend"
cp "$ROOT/scripts/set-version.sh" "$WORK/scripts/"
cp "$ROOT/backend/version.txt" "$WORK/backend/"
cp "$ROOT/frontend/package.json" "$WORK/frontend/"
cp "$ROOT/docker-compose.yml" "$WORK/"
SET="$WORK/scripts/set-version.sh"

"$SET" 1.2.3-rc.4 >/dev/null
[ "$(cat "$WORK/backend/version.txt")" = "v1.2.3-rc.4" ] || fail "backend/version.txt"
grep -q '"version": "1.2.3-rc.4"' "$WORK/frontend/package.json" || fail "frontend/package.json"
grep -q 'LIBRESEAL_VERSION:-' "$WORK/docker-compose.yml" || fail "compose has no version default"
if grep -o 'LIBRESEAL_VERSION:-[^}]*' "$WORK/docker-compose.yml" | grep -vq ':-1.2.3-rc.4$'; then
  fail "a compose default was not updated"
fi

"$SET" v2.0.0 >/dev/null
[ "$(cat "$WORK/backend/version.txt")" = "v2.0.0" ] || fail "leading v not accepted"

for bad in 1.2 1.2.3-beta 1.2.3.4 ""; do
  if "$SET" "$bad" >/dev/null 2>&1; then fail "accepted invalid version '$bad'"; fi
done
[ "$(cat "$WORK/backend/version.txt")" = "v2.0.0" ] || fail "invalid version modified files"

echo "set-version: all tests passed"
