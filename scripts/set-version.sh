#!/usr/bin/env bash
# Set the LibreSeal server version in every place that declares it.
#
# Usage: scripts/set-version.sh X.Y.Z[-rc.N]
#
# Updates backend/version.txt (vX.Y.Z), frontend/package.json (X.Y.Z) and the
# default image tag in docker-compose.yml (${LIBRESEAL_VERSION:-X.Y.Z}).
# scripts/check-libreseal-guard.sh fails when these disagree.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ $# -ne 1 ]; then
  sed -n '4p' "$0" >&2
  exit 2
fi
version="${1#v}"
if ! printf '%s' "$version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$'; then
  echo "invalid version: $1 (expected X.Y.Z or X.Y.Z-rc.N)" >&2
  exit 2
fi

printf 'v%s\n' "$version" > "$ROOT/backend/version.txt"

python3 - "$ROOT" "$version" <<'PY'
import pathlib, re, sys

root, version = pathlib.Path(sys.argv[1]), sys.argv[2]

pkg = root / "frontend" / "package.json"
text, n = re.subn(r'("version":\s*")[^"]*(")', rf'\g<1>{version}\g<2>', pkg.read_text(), count=1)
if n != 1:
    sys.exit(f"no version field in {pkg}")
pkg.write_text(text)

compose = root / "docker-compose.yml"
text, n = re.subn(r'\$\{LIBRESEAL_VERSION:-[^}]*\}', '${LIBRESEAL_VERSION:-%s}' % version, compose.read_text())
if n == 0:
    sys.exit(f"no ${{LIBRESEAL_VERSION:-...}} default in {compose}")
compose.write_text(text)
PY

echo "LibreSeal version set to v$version"
