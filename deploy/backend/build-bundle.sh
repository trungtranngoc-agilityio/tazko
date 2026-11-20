#!/usr/bin/env bash
# Builds the API server release bundle on a build machine or in CI, never on the
# server (D8). Needs git and uv. Run from anywhere in a clean checkout:
#
#   deploy/backend/build-bundle.sh            -> dist/tazko-<UTC time>-<commit>.tar.gz
#
# The bundle holds the tazko wheel, requirements.txt pinned with hashes (from
# backend/uv.lock, no dev tools) and VERSION. The web app is not in it; see
# deploy/frontend/. Copy it to /var/lib/tazko-incoming/ on the server and run
# tazko-release there (deploy/README.md).
set -euo pipefail
cd "$(dirname "$0")/../.."

if [ -n "$(git status --porcelain)" ]; then
  echo "build-bundle: commit or stash your changes first; a bundle names one commit" >&2
  exit 1
fi
branch="$(git rev-parse --abbrev-ref HEAD)"
case "$branch" in
  main | release/*) ;;
  *) echo "build-bundle: build from main or a release/ branch, not $branch" >&2; exit 1 ;;
esac
commit="$(git rev-parse --short=12 HEAD)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
name="tazko-$stamp-$commit"

work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT

uv build --project backend --wheel --out-dir "$work"
uv export --project backend --frozen --no-dev --no-emit-project \
  --format requirements-txt --output-file "$work/requirements.txt" >/dev/null
grep -q -- '--hash=sha256:' "$work/requirements.txt" || {
  echo "build-bundle: requirements.txt has no hashes" >&2
  exit 1
}
version="$(sed -n 's/^version = "\(.*\)"$/\1/p' backend/pyproject.toml | head -n 1)"
printf 'version=%s\ncommit=%s\nbuilt=%s\n' "$version" "$commit" "$stamp" > "$work/VERSION"

mkdir -p dist
tar -czf "dist/$name.tar.gz" -C "$work" VERSION requirements.txt "$(cd "$work" && ls tazko-*.whl)"
echo "dist/$name.tar.gz"
