#!/usr/bin/env bash
# Builds frontend/ and uploads it to Cloudflare Pages (D13). RUN BY THE OWNER (or by
# a CI job the owner sets up with a Pages-only API token). The agent never runs it.
#
#   VITE_API_URL=https://tazko-api-dev.hugepigstudio.com deploy/frontend/deploy.sh [--production]
#
# Without --production it uploads a preview deployment. TAZKO_PAGES_PROJECT
# defaults to tazko-web. wrangler asks for a Cloudflare login (or reads
# CLOUDFLARE_API_TOKEN from the environment); never put the token in a file here.
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

# The Content-Security-Policy must allow the API host, or every API call fails
# in the browser (M1.md, security review).
csp="$(grep -m1 'Content-Security-Policy:' frontend/public/_headers)"
for scheme in https wss; do
  [[ "$csp" == *"$scheme://$api_host"* ]] || {
    echo "deploy: frontend/public/_headers connect-src does not allow $scheme://$api_host" >&2
    exit 1
  }
done

npm --prefix frontend ci --no-audit --no-fund
npm --prefix frontend run build
# Pinned: wrangler 4.x from npm (npx caches it; the lock file pins the web app only).
npx --yes wrangler@4.158.0 pages deploy frontend/dist --project-name "$project" --branch "$branch"
