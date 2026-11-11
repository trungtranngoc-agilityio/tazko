#!/usr/bin/env bash
# Builds the API server release bundle in CI or on a build machine (D8), never on the server.
#
# Planned (M1-08):
#   (the web app is NOT part of this bundle; see deploy/frontend/)
#   uv build --project backend --wheel                      -> tazko-<version>-py3-none-any.whl
#   uv export --project backend --frozen --no-dev --no-emit-project #       --format requirements-txt > requirements.txt     (pinned, with hashes)
#   tar the wheel + requirements.txt + VERSION into tazko-<time>-<commit>.tar.gz
set -euo pipefail
echo "build-bundle.sh is not written yet (task M1-08)" >&2
exit 1
