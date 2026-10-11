#!/usr/bin/env bash
# Checks that a running LibreSeal stack keeps routing to its own services when
# nginx (and optionally the frontend) is also attached to a shared Docker
# network whose services are called "backend" and "frontend" (e.g. a PaaS
# proxy network). Nothing is built or started besides two throwaway impostors;
# everything this script creates is removed on exit.
#
# Usage: scripts/tests/test-shared-network.sh [BASE_URL]
#   BASE_URL           URL of the running instance (default https://localhost)
#   NGINX_CONTAINER    default libreseal-nginx
#   FRONTEND_CONTAINER attached too when ATTACH_FRONTEND=1 (default libreseal-frontend)
#   KEEP_ATTACHED=1    leave the impostors up and attached until Enter is pressed
#                      (to drive the UI meanwhile)
set -euo pipefail

BASE_URL="${1:-https://localhost}"
NGINX="${NGINX_CONTAINER:-libreseal-nginx}"
FRONTEND="${FRONTEND_CONTAINER:-libreseal-frontend}"
IMPOSTOR_IMAGE="hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186"
CURL_IMAGE="curlimages/curl:8.11.1@sha256:c1fe1679c34d9784c1b0d1e5f62ac0a79fca01fb6377cdd33e90473c6f9f9a69"
NET="libreseal-shared-test-$$"
ROUNDS=20

attached=()
cleanup() {
  for c in "${attached[@]}"; do docker network disconnect "$NET" "$c" >/dev/null 2>&1 || true; done
  docker rm -f "$NET-backend" "$NET-frontend" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }

docker network create "$NET" >/dev/null
docker run -d --name "$NET-backend" --network "$NET" --network-alias backend \
  "$IMPOSTOR_IMAGE" -listen=:8000 -text=IMPOSTOR >/dev/null
docker run -d --name "$NET-frontend" --network "$NET" --network-alias frontend \
  "$IMPOSTOR_IMAGE" -listen=:3000 -text=IMPOSTOR >/dev/null

docker network connect "$NET" "$NGINX"; attached+=("$NGINX")
if [ "${ATTACH_FRONTEND:-0}" = 1 ]; then
  docker network connect "$NET" "$FRONTEND"; attached+=("$FRONTEND")
fi

# Positive control: the impostors answer under the generic names on this network.
docker run --rm --network "$NET" "$CURL_IMAGE" -fsS -A positive-control http://backend:8000/ | grep -q IMPOSTOR \
  || fail "impostor backend not reachable as 'backend' (test setup broken)"

for i in $(seq 1 "$ROUNDS"); do
  health="$(curl -sk "$BASE_URL/service/health/")"
  case "$health" in *IMPOSTOR*) fail "health request $i reached the impostor" ;; esac
  case "$health" in *'"status": "alive"'*) ;; *) fail "health request $i: unexpected response: ${health:0:120}" ;; esac
  login="$(curl -skL "$BASE_URL/login")"
  case "$login" in *IMPOSTOR*) fail "login request $i reached the impostor" ;; esac
  case "$login" in *'LibreSeal'*) ;; *) fail "login request $i did not serve LibreSeal" ;; esac
done

if [ "${KEEP_ATTACHED:-0}" = 1 ]; then
  read -r -p "Impostors attached; press Enter to check their logs and clean up. " _
fi

# Only the positive control may have reached an impostor.
requests() { docker logs "$1" 2>&1 | grep -v 'server is listening' | grep -v '"positive-control"' || true; }
back="$(requests "$NET-backend")"
front="$(requests "$NET-frontend")"
[ -z "$back$front" ] || { printf '%s\n' "$back" "$front" >&2; fail "an impostor received requests from LibreSeal"; }

echo "shared-network: $ROUNDS health + $ROUNDS login requests stayed on LibreSeal; impostors untouched"
