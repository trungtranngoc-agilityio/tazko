#!/usr/bin/env bash
# Optional off-machine copy of /var/backups/tazko (build plan "Backups").
# Installed as /usr/local/lib/tazko/offsite.sh (root-owned); tazko-backup.service
# runs it after the nightly check, as the tazko user.
#
# Off until the owner creates /etc/tazko/rclone.conf (mode 640, root:tazko) with a
# remote named `tazko-offsite`, and installs rclone from the Ubuntu archive
# (`apt install rclone`). Snapshots contain the server secret: use a private
# bucket, ideally with rclone's `crypt` remote on top (deploy/README.md).
set -euo pipefail

CONF=/etc/tazko/rclone.conf
if [ ! -f "$CONF" ]; then
  echo "offsite: skipped ($CONF does not exist)"
  exit 0
fi
command -v rclone >/dev/null || { echo "offsite: rclone is not installed" >&2; exit 1; }
# sync, not copy: the remote keeps the same 30 days as the local folder.
rclone --config "$CONF" sync /var/backups/tazko tazko-offsite:tazko --fast-list
echo "offsite: synced /var/backups/tazko"
