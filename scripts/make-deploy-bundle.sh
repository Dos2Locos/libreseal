#!/usr/bin/env bash
# Build the deployment bundle attached to a LibreSeal server release.
#
# Usage: scripts/make-deploy-bundle.sh X.Y.Z[-rc.N] [OUTPUT_DIR]
#
# Writes OUTPUT_DIR/libreseal-deploy-X.Y.Z.tar.gz (default OUTPUT_DIR: dist/)
# with everything needed to run the published images without a clone. Fails
# unless the version matches backend/version.txt, so the bundled
# docker-compose.yml already pins the right images.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
  sed -n '4p' "$0" >&2
  exit 2
fi
version="${1#v}"
out_dir="${2:-$ROOT/dist}"

declared="$(tr -d '[:space:]' < "$ROOT/backend/version.txt")"
if [ "v$version" != "$declared" ]; then
  echo "version $version does not match backend/version.txt ($declared)" >&2
  exit 1
fi

FILES=(
  docker-compose.yml
  .env.example
  nginx/default.conf
  scripts/libreseal-init.sh
  scripts/libreseal-backup.sh
  scripts/libreseal-restore.sh
  LICENSE
  NOTICE
)

name="libreseal-deploy-$version"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/$name"
for f in "${FILES[@]}"; do
  mkdir -p "$stage/$name/$(dirname "$f")"
  cp "$ROOT/$f" "$stage/$name/$f"
done

cat > "$stage/$name/DEPLOY.md" <<EOF
# LibreSeal $version — deployment bundle

LibreSeal is an independent fork of Phase Console, not affiliated with or
endorsed by Phase / Phi Security Inc.

This bundle runs the published images ghcr.io/dos2locos/libreseal-*:$version
with Docker Compose. Nothing is built locally.

    ./scripts/libreseal-init.sh      # writes .env with random secrets (never overwrites)
    docker compose up -d
    # open https://localhost/

Verify the images before running them (requires cosign):

    cosign verify ghcr.io/dos2locos/libreseal-backend:$version \\
      --certificate-identity-regexp '^https://github.com/Dos2Locos/libreseal/.github/workflows/release.yml@refs/tags/v' \\
      --certificate-oidc-issuer https://token.actions.githubusercontent.com

Backups: ./scripts/libreseal-backup.sh and ./scripts/libreseal-restore.sh <file>.
Full documentation: https://github.com/Dos2Locos/libreseal/tree/v$version#readme
EOF

mkdir -p "$out_dir"
tar -C "$stage" -czf "$out_dir/$name.tar.gz" "$name"
echo "$out_dir/$name.tar.gz"
