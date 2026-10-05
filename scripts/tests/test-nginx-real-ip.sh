#!/usr/bin/env bash
# Tests for nginx/real-ip.sh. Run: scripts/tests/test-nginx-real-ip.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GEN="$ROOT/nginx/real-ip.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
export REAL_IP_CONF="$WORK/real-ip.conf"

# Default: no trusted proxies, no real_ip directives.
env -u NGINX_REAL_IP_FROM -u NGINX_REAL_IP_HEADER "$GEN" >/dev/null
grep -q 'set_real_ip_from\|real_ip_header' "$REAL_IP_CONF" && fail "default must not trust any proxy"

# Trusted proxies (IPv4, CIDR, IPv6) with the default header.
NGINX_REAL_IP_FROM="172.30.0.5, 10.0.0.0/8,2001:db8::/32" "$GEN" >/dev/null
for d in "set_real_ip_from 172.30.0.5;" "set_real_ip_from 10.0.0.0/8;" \
  "set_real_ip_from 2001:db8::/32;" "real_ip_header X-Forwarded-For;" "real_ip_recursive on;"; do
  grep -qxF "$d" "$REAL_IP_CONF" || fail "missing '$d'"
done

# Custom header (Cloudflare).
NGINX_REAL_IP_FROM="173.245.48.0/20" NGINX_REAL_IP_HEADER="CF-Connecting-IP" "$GEN" >/dev/null
grep -qxF "real_ip_header CF-Connecting-IP;" "$REAL_IP_CONF" || fail "custom header not used"

# Invalid values fail and leave the previous config untouched.
cp "$REAL_IP_CONF" "$WORK/before"
NGINX_REAL_IP_FROM="10.0.0.0/8; include /etc/passwd" "$GEN" 2>/dev/null && fail "invalid entry accepted"
NGINX_REAL_IP_FROM="10.0.0.0/8" NGINX_REAL_IP_HEADER='X-Real-IP;evil' "$GEN" 2>/dev/null && fail "invalid header accepted"
for everyone in "0.0.0.0/0" "::/0" "10.0.0.0/8, 0.0.0.0/0"; do
  NGINX_REAL_IP_FROM="$everyone" "$GEN" 2>/dev/null && fail "'$everyone' accepted (trusts every client)"
done
cmp -s "$REAL_IP_CONF" "$WORK/before" || fail "config modified on invalid input"
[ ! -e "$REAL_IP_CONF.tmp" ] || fail "temporary file left behind"

echo "OK: nginx/real-ip.sh"
