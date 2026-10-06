#!/usr/bin/env bash
# Branch protection for `main` in the LibreSeal repositories.
#
#   scripts/github/protect-main.sh            # check: show differences, change nothing
#   scripts/github/protect-main.sh --apply    # apply the documented protection
#   scripts/github/protect-main.sh --disable  # remove protection (emergencies only)
#
# Requires an authenticated `gh` with admin rights on the repositories
# (e.g. GH_TOKEN=$(gh auth token --user <admin>)). No token is stored.
# Protection: changes only via pull request (no required approvals: single
# maintainer), required CI checks up to date with main, enforced for admins,
# no force-push, no deletion. See openspec/specs/continuous-integration.
set -euo pipefail

ORG="${LIBRESEAL_GH_ORG:-Dos2Locos}"

# Required checks per repository (names as reported by `gh pr checks`).
checks_for() {
  case "$1" in
    libreseal) printf '%s\n' guard backend frontend compose-build ;;
    libreseal-skills) printf '%s\n' validate ;;
    libreseal-cli)
      printf '%s\n' \
        "test / Go Test & Vet (ubuntu-latest)" \
        "test / Go Test & Vet (macos-latest)" \
        "test / Go Test & Vet (windows-latest)" \
        install-from-source
      ;;
    *) return 1 ;;
  esac
}
REPOS=(libreseal libreseal-cli libreseal-skills)

mode="check"
case "${1:-}" in
  "") ;;
  --apply) mode="apply" ;;
  --disable) mode="disable" ;;
  -h | --help) sed -n '2,12p' "$0"; exit 0 ;;
  *) echo "unknown option: $1" >&2; exit 2 ;;
esac

desired_json() {
  python3 - "$@" <<'PY'
import json, sys
print(json.dumps({
    "required_status_checks": {"strict": True, "contexts": sys.argv[1:]},
    "enforce_admins": True,
    "required_pull_request_reviews": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews": False,
        "require_code_owner_reviews": False,
    },
    "restrictions": None,
    "allow_force_pushes": False,
    "allow_deletions": False,
}))
PY
}

# Normalise the GET response (or "unprotected") for comparison.
current_summary() {
  local repo="$1" body
  if ! body="$(gh api "repos/$ORG/$repo/branches/main/protection" 2>/dev/null)"; then
    echo "unprotected"
    return
  fi
  python3 -c '
import json, sys
p = json.load(sys.stdin)
rsc = p.get("required_status_checks") or {}
pr = p.get("required_pull_request_reviews")
print(json.dumps({
    "strict": rsc.get("strict"),
    "contexts": sorted(rsc.get("contexts") or []),
    "enforce_admins": (p.get("enforce_admins") or {}).get("enabled"),
    "pull_request": pr is not None,
    "approvals": (pr or {}).get("required_approving_review_count"),
    "force_pushes": (p.get("allow_force_pushes") or {}).get("enabled"),
    "deletions": (p.get("allow_deletions") or {}).get("enabled"),
}, sort_keys=True))' <<<"$body"
}

desired_summary() {
  python3 -c '
import json, sys
print(json.dumps({"strict": True, "contexts": sorted(sys.argv[1:]), "enforce_admins": True,
                  "pull_request": True, "approvals": 0, "force_pushes": False,
                  "deletions": False}, sort_keys=True))' "$@"
}

# Warn when a required check has not run on the latest main commit: requiring
# a check that never reports would block every pull request.
check_names_seen() {
  local repo="$1"; shift
  local sha seen missing=0
  sha="$(gh api "repos/$ORG/$repo/commits/main" -q .sha)"
  seen="$(gh api "repos/$ORG/$repo/commits/$sha/check-runs" --paginate -q '.check_runs[].name')"
  for c in "$@"; do
    if ! grep -qxF "$c" <<<"$seen"; then
      echo "  warning: check '$c' has not run on main ($sha)" >&2
      missing=1
    fi
  done
  return "$missing"
}

status=0
for repo in "${REPOS[@]}"; do
  mapfile -t checks < <(checks_for "$repo")
  echo "== $ORG/$repo"
  case "$mode" in
    check)
      have="$(current_summary "$repo")"
      want="$(desired_summary "${checks[@]}")"
      if [ "$have" = "$want" ]; then
        echo "  protection: as documented"
      else
        echo "  protection differs"
        echo "    current: $have"
        echo "    desired: $want"
        status=1
      fi
      check_names_seen "$repo" "${checks[@]}" || status=1
      ;;
    apply)
      if ! check_names_seen "$repo" "${checks[@]}"; then
        echo "  refusing to require checks that have not run on main" >&2
        status=1
        continue
      fi
      desired_json "${checks[@]}" |
        gh api -X PUT "repos/$ORG/$repo/branches/main/protection" --input - >/dev/null
      echo "  protection applied"
      ;;
    disable)
      if gh api -X DELETE "repos/$ORG/$repo/branches/main/protection" >/dev/null 2>&1; then
        echo "  protection removed"
      else
        echo "  not protected"
      fi
      ;;
  esac
done
exit "$status"
