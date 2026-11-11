#!/usr/bin/env bash
# One-time host setup. RUN BY THE OWNER as root after reading it (P0-4).
# The agent never runs this.
#
# Planned (M1-08, see docs/build-plan.md "Deployment"):
#   - system users: tazko (no login, runs the service), tazko-deploy (owns /opt/tazko, /etc/tazko)
#   - folders: /var/lib/tazko/data, /var/backups/tazko, /var/lib/tazko-incoming, /opt/tazko/releases
#   - /etc/tazko/tazko.env (mode 640) from .env.example, values filled by the owner
#   - sudoers: tazko-deploy may only `systemctl restart tazko.service` and read its journal
#   - install tazko.service, tazko-backup.service, tazko-backup.timer; enable the timer
#   - install release.sh as /usr/local/bin/tazko-release (root-owned)
# Must not touch the other service on this machine (port 8790, its users and folders).
set -euo pipefail
echo "setup-host.sh is not written yet (task M1-08)" >&2
exit 1
