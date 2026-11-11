#!/usr/bin/env bash
# Installs a bundle from /var/lib/tazko-incoming. Installed as /usr/local/bin/tazko-release
# and run as tazko-deploy by the owner.
#
# Planned (M1-08):
#   - unpack into /opt/tazko/releases/<time>-<commit>
#   - uv venv .venv --python 3.12, then
#     uv pip install --python .venv --require-hashes --compile-bytecode -r requirements.txt
#     uv pip install --python .venv --no-deps --compile-bytecode tazko-*.whl
#     (no network build step: every package is a pinned, hashed wheel)
#   - point /opt/tazko/current at the new release
#   - sudo systemctl restart tazko.service
#   - poll http://127.0.0.1:8791/health for up to 20 s; on failure point the link back,
#     restart and exit non-zero
#   - options: --rollback (one release back), --list; keep the last 5 releases
set -euo pipefail
echo "release.sh is not written yet (task M1-08)" >&2
exit 1
