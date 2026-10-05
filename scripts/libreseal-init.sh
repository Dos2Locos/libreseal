#!/usr/bin/env bash
# Create .env for a LibreSeal Docker Compose deployment with fresh random secrets.
#
# Usage: scripts/libreseal-init.sh [--host HOST] [--https-port PORT] [--http-port PORT] [--env-file PATH]
#
# Never overwrites an existing env file. Requires openssl.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_NAME="localhost"
HTTPS_PORT="443"
HTTP_PORT="80"
ENV_FILE="$ROOT/.env"

while [ $# -gt 0 ]; do
  case "$1" in
    --host) HOST_NAME="$2"; shift 2 ;;
    --https-port) HTTPS_PORT="$2"; shift 2 ;;
    --http-port) HTTP_PORT="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

case "$HOST_NAME" in
  *://*|*/*|*:*) echo "--host must be a bare hostname (no scheme, path or port)" >&2; exit 2 ;;
esac
for p in "$HTTPS_PORT" "$HTTP_PORT"; do
  case "$p" in ''|*[!0-9]*) echo "Ports must be numeric" >&2; exit 2 ;; esac
done

if [ -e "$ENV_FILE" ]; then
  echo "$ENV_FILE already exists; leaving it untouched." >&2
  exit 0
fi

command -v openssl >/dev/null || { echo "openssl is required" >&2; exit 1; }

if [ "$HTTPS_PORT" = "443" ]; then
  PUBLIC_URL="https://$HOST_NAME"
else
  PUBLIC_URL="https://$HOST_NAME:$HTTPS_PORT"
fi

umask 077
tmp="$(mktemp "${ENV_FILE}.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    *=__GENERATED__) line="${line%__GENERATED__}$(openssl rand -hex 32)" ;;
    HOST=*) line="HOST=$HOST_NAME" ;;
    PUBLIC_URL=*) line="PUBLIC_URL=$PUBLIC_URL" ;;
    HTTP_PORT=*) line="HTTP_PORT=$HTTP_PORT" ;;
    HTTPS_PORT=*) line="HTTPS_PORT=$HTTPS_PORT" ;;
  esac
  printf '%s\n' "$line"
done < "$ROOT/.env.example" > "$tmp"

chmod 600 "$tmp"
mv "$tmp" "$ENV_FILE"
trap - EXIT

echo "Wrote $ENV_FILE (mode 600) for $PUBLIC_URL"
echo "Next: docker compose up -d --build"
