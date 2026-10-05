#!/usr/bin/env bash
# Tests for scripts/libreseal-init.sh. Run: scripts/tests/test-libreseal-init.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INIT="$ROOT/scripts/libreseal-init.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
val() { grep "^$2=" "$1" | cut -d= -f2-; }

"$INIT" --env-file "$WORK/a.env" >/dev/null
"$INIT" --env-file "$WORK/b.env" --host secrets.lan --https-port 8443 --http-port 8080 >/dev/null

for f in "$WORK/a.env" "$WORK/b.env"; do
  grep -q "=__GENERATED__" "$f" && fail "placeholder left in $f"
  perm="$(stat -c %a "$f" 2>/dev/null || stat -f %Lp "$f")"
  [ "$perm" = "600" ] || fail "$f has mode $perm, expected 600"
done

for k in SECRET_KEY SERVER_SECRET NEXTAUTH_SECRET DATABASE_PASSWORD; do
  a="$(val "$WORK/a.env" $k)"; b="$(val "$WORK/b.env" $k)"
  [ ${#a} -eq 64 ] || fail "$k is not 64 hex chars"
  [ "$a" != "$b" ] || fail "$k identical across installs"
  grep -q "$a" "$ROOT/.env.example" && fail "$k matches the template"
done
[ "$(val "$WORK/a.env" SECRET_KEY)" != "$(val "$WORK/a.env" SERVER_SECRET)" ] || fail "secrets reused within one file"

[ "$(val "$WORK/a.env" PUBLIC_URL)" = "https://localhost" ] || fail "default PUBLIC_URL"
[ "$(val "$WORK/b.env" PUBLIC_URL)" = "https://secrets.lan:8443" ] || fail "custom PUBLIC_URL"
[ "$(val "$WORK/b.env" HOST)" = "secrets.lan" ] || fail "custom HOST"
[ "$(val "$WORK/b.env" HTTP_PORT)" = "8080" ] || fail "custom HTTP_PORT"

before="$(shasum "$WORK/a.env")"
out="$("$INIT" --env-file "$WORK/a.env" 2>&1)"
[ "$before" = "$(shasum "$WORK/a.env")" ] || fail "existing env file was modified"
echo "$out" | grep -q "already exists" || fail "no 'already exists' message"

if "$INIT" --env-file "$WORK/c.env" --host "https://bad" >/dev/null 2>&1; then fail "accepted URL as host"; fi

echo "libreseal-init: all tests passed"
