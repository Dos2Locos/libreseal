#!/usr/bin/env bash
# Back up the LibreSeal PostgreSQL database of a running Docker Compose deployment.
#
# Usage: scripts/libreseal-backup.sh [OUTPUT_DIR]   (default: ./backups)
#
# The dump contains encrypted secrets, user keyrings and audit logs. To restore a
# working instance you ALSO need the same .env (SERVER_SECRET, SECRET_KEY, ...),
# and users still need their passwords / recovery phrases to decrypt secrets.
# Store the dump and .env separately and securely.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-$ROOT/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="$OUT_DIR/libreseal-$STAMP.dump"

cd "$ROOT"
umask 077
mkdir -p "$OUT_DIR"

docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$FILE.partial"
mv "$FILE.partial" "$FILE"

# A custom-format dump must be readable by pg_restore; fail loudly otherwise.
docker compose exec -T postgres pg_restore --list < "$FILE" > /dev/null

echo "Backup written to $FILE ($(wc -c < "$FILE" | tr -d ' ') bytes)"
