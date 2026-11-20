#!/usr/bin/env bash
# Restores the newest pre-release snapshot over /var/lib/tazko/data (D36).
# Installed as /usr/local/lib/tazko/restore-pre-release.sh (root-owned) and run
# only by tazko-restore.service, as the tazko user, with tazko.service stopped
# (tazko-release stops it first). The data it replaces is kept as
# /var/lib/tazko/data.failed-<UTC time> for the owner; nothing is deleted.
set -euo pipefail
umask 077

BASE=/var/lib/tazko
DATA="$BASE/data"
NEW="$BASE/data.new"
SNAPSHOTS=/var/backups/tazko/pre-release
TAZKO=/opt/tazko/current/.venv/bin/tazko

newest="$(find "$SNAPSHOTS" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended \
  -regex '.*/[0-9]{8}T[0-9]{6}Z' -printf '%f\n' 2>/dev/null | sort | tail -n 1)"
[ -n "$newest" ] || { echo "restore: no pre-release snapshot in $SNAPSHOTS" >&2; exit 1; }

# A leftover from an earlier failed restore: a fixed path, never a variable one.
rm -rf -- "$NEW"
cp -a -- "$SNAPSHOTS/$newest" "$NEW"
"$TAZKO" check --data "$NEW"

failed="$BASE/data.failed-$(date -u +%Y%m%dT%H%M%SZ)"
mv -T -- "$DATA" "$failed"
mv -T -- "$NEW" "$DATA"
# Snapshots leave out data/trash/; keep the deleted companies it held.
if [ -d "$failed/trash" ]; then
  mv -T -- "$failed/trash" "$DATA/trash"
else
  mkdir -p -- "$DATA/trash"
fi
echo "restore: $DATA is now snapshot $newest; the replaced data is in $failed"
