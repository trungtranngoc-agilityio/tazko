#!/usr/bin/env bash
# Restores the newest pre-release snapshot over /var/lib/tazko/data (D36, D37).
# Installed as /usr/local/lib/tazko/restore-pre-release.sh (root-owned) and run
# only by tazko-restore.service, as the tazko user, with tazko.service stopped
# (tazko-release stops it first; the unit also conflicts with it). The data it
# replaces is kept as /var/lib/tazko/data.failed-<UTC time>; nothing is deleted.
#
# It refuses a snapshot older than 30 minutes: tazko-release takes one right
# before each switch, so an older one means this was started by hand, and
# restoring it would throw away everything written since.
#
# TAZKO_* variables exist for tests/deploy/test_restore.py only; the unit sets
# none of them (it does not load tazko.env).
set -euo pipefail
umask 077

BASE="${TAZKO_BASE:-/var/lib/tazko}"
SNAPSHOTS="${TAZKO_SNAPSHOTS:-/var/backups/tazko/pre-release}"
TAZKO="${TAZKO_BIN:-/opt/tazko/current/.venv/bin/tazko}"
MAX_AGE_MINUTES="${TAZKO_MAX_AGE_MINUTES:-30}"
DATA="$BASE/data"
NEW="$BASE/data.new"

die() { echo "restore: $*" >&2; exit 1; }

newest="$(find "$SNAPSHOTS" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended \
  -regex '.*/[0-9]{8}T[0-9]{6}Z' -printf '%f\n' 2>/dev/null | sort | tail -n 1)"
[ -n "$newest" ] || die "no pre-release snapshot in $SNAPSHOTS"

stamp="${newest:0:4}-${newest:4:2}-${newest:6:2}T${newest:9:2}:${newest:11:2}:${newest:13:2}Z"
taken="$(date -u -d "$stamp" +%s)" || die "cannot read the time of snapshot $newest"
age=$(( ($(date -u +%s) - taken) / 60 ))
[ "$age" -le "$MAX_AGE_MINUTES" ] \
  || die "the newest pre-release snapshot is $age minutes old; restore by hand (deploy/README.md)"

# A leftover from an earlier failed restore: a fixed path, never a variable one.
rm -rf -- "$NEW"
cp -a -- "$SNAPSHOTS/$newest" "$NEW"
"$TAZKO" check --data "$NEW" || die "snapshot $newest failed the check; $DATA is unchanged"

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
