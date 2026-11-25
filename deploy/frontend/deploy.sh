#!/usr/bin/env bash
# Builds frontend/ and uploads it to Cloudflare Pages. RUN BY THE OWNER
# (or by a CI job the owner sets up with a Pages-only API token). The agent never runs it.
#
#   VITE_API_URL=https://tazko-api-dev.hugepigstudio.com deploy/frontend/deploy.sh [--production]
#
# Without --production it uploads a preview deployment. TAZKO_PAGES_PROJECT
# defaults to tazko-web; --production deploys the branch `main`, which must be the
# Pages project's production branch. wrangler asks for a Cloudflare login (or reads
# CLOUDFLARE_API_TOKEN from the environment); never put the token in a file here.
# wrangler is pinned with hashes in deploy/frontend/package-lock.json.
#
# Rollback: in the Pages project, Deployments, pick the previous deployment and
# choose "Rollback to this deployment". The API is released separately
# (tazko-release on the server), so a web release never restarts the server.
set -euo pipefail
cd "$(dirname "$0")/../.."

: "${VITE_API_URL:?set VITE_API_URL to the API base URL, e.g. https://tazko-api-dev.hugepigstudio.com}"
[[ "$VITE_API_URL" =~ ^https://[a-z0-9.-]+$ ]] \
  || { echo "deploy: VITE_API_URL must be https://<host> with no path, got $VITE_API_URL" >&2; exit 1; }
api_host="${VITE_API_URL#https://}"
project="${TAZKO_PAGES_PROJECT:-tazko-web}"
branch="preview"
[ "${1:-}" = "--production" ] && branch="main"

if [ -n "$(git status --porcelain)" ]; then
  echo "deploy: commit or stash your changes first; a deployment names one commit" >&2
  exit 1
fi
if [ "$branch" = main ]; then
  case "$(git rev-parse --abbrev-ref HEAD)" in
    main | release/*) ;;
    *) echo "deploy: --production deploys from main or a release/ branch only" >&2; exit 1 ;;
  esac
fi

# connect-src must list the API host for https and wss, or every API call fails in
# the browser (security review). Whole tokens of that directive only.
csp="$(grep -m1 'Content-Security-Policy:' frontend/public/_headers || true)"
connect="$(tr ';' '\n' <<<"$csp" | sed -n 's/^[[:space:]]*connect-src[[:space:]]\{1,\}//p')"
for scheme in https wss; do
  tr ' ' '\n' <<<"$connect" | grep -qx "$scheme://$api_host" || {
    echo "deploy: connect-src in frontend/public/_headers does not list $scheme://$api_host" >&2
    exit 1
  }
done

npm --prefix frontend ci --no-audit --no-fund
npm --prefix frontend run build
npm --prefix deploy/frontend ci --no-audit --no-fund
npm --prefix deploy/frontend exec --no -- wrangler pages deploy frontend/dist \
  --project-name "$project" --branch "$branch" --commit-hash "$(git rev-parse HEAD)"
