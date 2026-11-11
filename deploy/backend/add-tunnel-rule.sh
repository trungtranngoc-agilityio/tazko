#!/usr/bin/env bash
# Adds the Tazko API hostname to the EXISTING Cloudflare tunnel. RUN BY THE OWNER (P0-3).
#
# Planned (M1-08):
#   - back up /etc/cloudflared/config.yml
#   - insert, above the final `service: http_status:404` catch-all:
#       - hostname: <TAZKO API hostname, e.g. tazko-api-dev.hugepigstudio.com>
#         service: http://127.0.0.1:8791
#         originRequest: { connectTimeout: 30s, noHappyEyeballs: true }
#   - cloudflared tunnel route dns <tunnel> <hostname>
#   - cloudflared tunnel ingress validate, then restart cloudflared
#   - confirm the existing hostname still answers
# Never rewrites config.yml and never removes existing rules.
set -euo pipefail
echo "add-tunnel-rule.sh is not written yet (task M1-08)" >&2
exit 1
