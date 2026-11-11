#!/usr/bin/env bash
# Builds the release bundle in CI or on a build machine (D8), never on the server.
#
# Planned (M1-08):
#   npm --prefix web ci && npm --prefix web run build
#   cargo build --release --target x86_64-unknown-linux-musl
#   tar the binary + VERSION into tazko-<time>-<commit>.tar.gz
set -euo pipefail
echo "build-bundle.sh is not written yet (task M1-08)" >&2
exit 1
