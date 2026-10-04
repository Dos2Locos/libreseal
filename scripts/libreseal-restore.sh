#!/usr/bin/env bash
# Restore a LibreSeal database dump created by scripts/libreseal-backup.sh.
#
# Usage: scripts/libreseal-restore.sh --yes BACKUP_FILE
#
# Replaces ALL data in the running instance's database. The instance must use the
# same .env (SERVER_SECRET, SECRET_KEY, ...) as the one that produced the backup.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIRM=""
FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --yes) CONFIRM=1; shift ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) FILE="$1"; shift ;;
  esac
done

[ -n "$FILE" ] && [ -f "$FILE" ] || { echo "Backup file not found: ${FILE:-<none>}" >&2; exit 2; }
[ -n "$CONFIRM" ] || { echo "Refusing to overwrite the database without --yes" >&2; exit 2; }

cd "$ROOT"

echo "Stopping application services..."
docker compose stop nginx frontend backend worker >/dev/null

docker compose up -d postgres redis >/dev/null
until docker compose exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; do
  sleep 1
done

echo "Restoring $FILE..."
docker compose exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --single-transaction' < "$FILE"

echo "Starting LibreSeal..."
docker compose up -d >/dev/null
echo "Restore complete."
