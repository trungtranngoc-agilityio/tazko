#!/usr/bin/env bash
# One-time host setup for the Tazko API (build plan "Deployment", D13, D36).
# RUN BY THE OWNER as root, from a copy of this deploy/backend folder on the host,
# after reading it. Safe to run again: it creates what is missing and replaces only
# Tazko's own units, sudoers file and helper scripts. It never touches the other
# service on this machine (127.0.0.1:8790), its users or folders, or cloudflared.
#
#   sudo bash deploy/backend/setup-host.sh
set -euo pipefail
umask 022

[ "$(id -u)" -eq 0 ] || { echo "setup-host: run as root (sudo)" >&2; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
for f in tazko.service tazko-backup.service tazko-backup.timer tazko-pre-release-backup.service \
  tazko-restore.service tazko-check.service release.sh restore-pre-release.sh offsite.sh; do
  [ -f "$HERE/$f" ] || { echo "setup-host: $HERE/$f is missing" >&2; exit 1; }
done

step() { echo "== $*"; }

step "packages: Python 3.12 with venv, curl (Ubuntu archive, signed)"
installed() { dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q 'ok installed'; }
if ! installed python3.12 || ! installed python3.12-venv || ! installed curl; then
  apt-get update
  apt-get install -y --no-install-recommends python3.12 python3.12-venv curl
fi

step "users: tazko (runs the service), tazko-deploy (installs releases)"
id -u tazko >/dev/null 2>&1 || useradd --system --user-group --home-dir /var/lib/tazko \
  --no-create-home --shell /usr/sbin/nologin tazko
id -u tazko-deploy >/dev/null 2>&1 || useradd --system --user-group --home-dir /opt/tazko \
  --no-create-home --shell /usr/sbin/nologin tazko-deploy

step "folders"
install -d -o tazko -g tazko -m 700 /var/lib/tazko /var/lib/tazko/data /var/lib/tazko/data/trash
install -d -o tazko -g tazko -m 700 /var/backups/tazko
install -d -o tazko-deploy -g tazko-deploy -m 755 /opt/tazko /opt/tazko/releases
install -d -o tazko-deploy -g tazko-deploy -m 750 /var/lib/tazko-incoming
install -d -o root -g tazko -m 750 /etc/tazko
install -d -o root -g root -m 755 /usr/local/lib/tazko

step "settings: /etc/tazko/tazko.env"
ENV_FILE=/etc/tazko/tazko.env
if [ ! -e "$ENV_FILE" ]; then
  install -o root -g tazko -m 640 /dev/null "$ENV_FILE"
  cat > "$ENV_FILE" <<'EOF'
# Tazko API settings (deploy/README.md). Owner fills in the Google client.
# TAZKO_ENV=production turns on the production checks and stops .env reading.
TAZKO_ENV=production
TAZKO_HOST=127.0.0.1
TAZKO_PORT=8791
TAZKO_PUBLIC_URL=https://tazko-api-dev.hugepigstudio.com
TAZKO_WEB_ORIGIN=https://tazko-dev.hugepigstudio.com
TAZKO_DATA_DIR=/var/lib/tazko/data
TAZKO_LOG=INFO
TAZKO_GOOGLE_CLIENT_ID=
TAZKO_GOOGLE_CLIENT_SECRET=
# Empty: a random secret file is made in the data folder on first start.
TAZKO_SECRET=
EOF
  echo "   wrote $ENV_FILE: fill in TAZKO_GOOGLE_CLIENT_ID and TAZKO_GOOGLE_CLIENT_SECRET"
else
  chown root:tazko "$ENV_FILE"
  chmod 640 "$ENV_FILE"
  grep -qx 'TAZKO_ENV=production' "$ENV_FILE" \
    || echo "   WARNING: $ENV_FILE does not say TAZKO_ENV=production"
  echo "   kept the existing $ENV_FILE"
fi

step "sudoers: tazko-deploy may only restart Tazko and run its release units"
SUDOERS=/etc/sudoers.d/tazko-deploy
tmp="$(mktemp)"
trap 'rm -f -- "$tmp"' EXIT
cat > "$tmp" <<'EOF'
# Written by deploy/backend/setup-host.sh. Exact commands only, no wildcards.
tazko-deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart tazko.service, \
  /usr/bin/systemctl stop tazko.service, \
  /usr/bin/systemctl start tazko.service, \
  /usr/bin/systemctl start tazko-pre-release-backup.service, \
  /usr/bin/systemctl start tazko-restore.service, \
  /usr/bin/systemctl start tazko-check.service, \
  /usr/bin/journalctl -u tazko.service -n 200 --no-pager
EOF
visudo -cf "$tmp" >/dev/null
install -o root -g root -m 440 "$tmp" "$SUDOERS"

step "release and helper scripts (root-owned)"
install -o root -g root -m 755 "$HERE/release.sh" /usr/local/bin/tazko-release
install -o root -g root -m 755 "$HERE/restore-pre-release.sh" /usr/local/lib/tazko/restore-pre-release.sh
install -o root -g root -m 755 "$HERE/offsite.sh" /usr/local/lib/tazko/offsite.sh

step "systemd units"
for unit in tazko.service tazko-backup.service tazko-backup.timer \
  tazko-pre-release-backup.service tazko-restore.service tazko-check.service; do
  install -o root -g root -m 644 "$HERE/$unit" "/etc/systemd/system/$unit"
done
systemctl daemon-reload
# Enabled now; until the first release, a reboot or the 02:30 run only logs a
# failed unit (there is no /opt/tazko/current yet).
systemctl enable tazko.service >/dev/null
systemctl enable --now tazko-backup.timer >/dev/null
if systemctl is-active --quiet tazko.service; then
  echo "   tazko.service is running: changed units apply at its next restart"
fi

step "checks"
if ss -Hltn 'sport = :8791' | grep -q . && ! systemctl is-active --quiet tazko.service; then
  echo "   WARNING: something other than tazko.service listens on port 8791"
fi
echo "done. Next: deploy/README.md, 'First release'."
