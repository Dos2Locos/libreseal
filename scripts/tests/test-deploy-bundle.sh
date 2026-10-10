#!/usr/bin/env bash
# Tests for scripts/make-deploy-bundle.sh. Run: scripts/tests/test-deploy-bundle.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAKE="$ROOT/scripts/make-deploy-bundle.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }

version="$(tr -d '[:space:]' < "$ROOT/backend/version.txt")"
version="${version#v}"

bundle="$("$MAKE" "$version" "$WORK/out")"
[ "$bundle" = "$WORK/out/libreseal-deploy-$version.tar.gz" ] || fail "unexpected bundle path $bundle"

tar -tzf "$bundle" | sed "s#^libreseal-deploy-$version/##" | sort > "$WORK/list"
for f in docker-compose.yml .env.example nginx/default.conf scripts/libreseal-init.sh \
         scripts/libreseal-backup.sh scripts/libreseal-restore.sh LICENSE NOTICE DEPLOY.md; do
  grep -qxF "$f" "$WORK/list" || fail "missing $f"
done
if grep -E '\.env$|(^|/)ee/|Dockerfile' "$WORK/list"; then fail "unexpected file in bundle"; fi

tar -xzf "$bundle" -C "$WORK"
dir="$WORK/libreseal-deploy-$version"
grep -q "LIBRESEAL_VERSION:-$version}" "$dir/docker-compose.yml" || fail "compose not pinned to $version"
if grep -q 'build:' "$dir/docker-compose.yml"; then fail "bundled compose builds images"; fi
[ -x "$dir/scripts/libreseal-init.sh" ] || fail "init script not executable"

# The bundled init script works without a clone.
(cd "$dir" && ./scripts/libreseal-init.sh >/dev/null)
[ -f "$dir/.env" ] || fail "init did not write .env in the bundle"

if "$MAKE" 9.9.9 "$WORK/bad" >/dev/null 2>&1; then fail "accepted a version that differs from backend/version.txt"; fi
[ ! -e "$WORK/bad" ] || fail "output written for a mismatched version"

echo "deploy-bundle: all tests passed"
