#!/usr/bin/env bash
# Builds frontend/ and uploads it to Cloudflare Pages. RUN BY THE OWNER (or by a CI
# job the owner sets up with a scoped Pages token). The agent never runs it.
#
# Usage: deploy/frontend/deploy.sh [--production]
#   VITE_API_URL must point at the API host, e.g. https://tazko-api-dev.hugepigstudio.com
#   TAZKO_PAGES_PROJECT defaults to tazko-web
#
# Rollback: in the Pages project, Deployments, pick the previous deployment and
# choose "Rollback to this deployment". The API is released separately
# (deploy/backend/release.sh), so a web release never restarts the server.
set -euo pipefail
cd "$(dirname "$0")/../.."

: "${VITE_API_URL:?set VITE_API_URL to the API base URL}"
project="${TAZKO_PAGES_PROJECT:-tazko-web}"
branch="preview"
[ "${1:-}" = "--production" ] && branch="main"

npm --prefix frontend ci --no-audit --no-fund
npm --prefix frontend run build
npx --yes wrangler@4 pages deploy frontend/dist --project-name "$project" --branch "$branch"
