#!/usr/bin/env bash
# Adds the Tazko API hostname to the EXISTING Cloudflare tunnel (build plan
# "Deployment" step 1, D13). RUN BY THE OWNER as root, after reading it:
#
#   sudo bash deploy/backend/add-tunnel-rule.sh [hostname]   # default tazko-api-dev.hugepigstudio.com
#
# It backs up /etc/cloudflared/config.yml, inserts one rule above the final
# `service: http_status:404` catch-all, validates the new file BEFORE installing
# it, routes DNS, restarts cloudflared, and checks that every hostname that
# answered before still answers. If not, it puts the old file back and restarts.
# It never removes or edits other rules. Running it again changes nothing.
set -euo pipefail
umask 077

HOST="${1:-tazko-api-dev.hugepigstudio.com}"
CONFIG=/etc/cloudflared/config.yml
CERT=/etc/cloudflared/cert.pem
SERVICE="http://127.0.0.1:8791"

[ "$(id -u)" -eq 0 ] || { echo "tunnel: run as root (sudo)" >&2; exit 1; }
[[ "$HOST" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$ ]] \
  || { echo "tunnel: '$HOST' is not a hostname" >&2; exit 1; }
command -v cloudflared >/dev/null || { echo "tunnel: cloudflared is not installed" >&2; exit 1; }
[ -f "$CONFIG" ] || { echo "tunnel: $CONFIG not found; see deploy/README.md (no tunnel yet)" >&2; exit 1; }

tunnel="$(sed -n 's/^tunnel:[[:space:]]*\([^[:space:]#]*\).*/\1/p' "$CONFIG" | head -n 1)"
[ -n "$tunnel" ] || { echo "tunnel: no 'tunnel:' line in $CONFIG" >&2; exit 1; }

if grep -Eq "^[[:space:]]*-?[[:space:]]*hostname:[[:space:]]*['\"]?${HOST//./\\.}['\"]?[[:space:]]*$" "$CONFIG"; then
  echo "tunnel: $HOST is already in $CONFIG; nothing to do"
  exit 0
fi

catchall_line="$(grep -nE '^[[:space:]]*-[[:space:]]*service:[[:space:]]*http_status:404[[:space:]]*$' "$CONFIG" | tail -n 1 | cut -d: -f1)"
[ -n "$catchall_line" ] || { echo "tunnel: no '- service: http_status:404' catch-all in $CONFIG" >&2; exit 1; }
indent="$(sed -n "${catchall_line}p" "$CONFIG" | sed 's/-.*//')"

# Hostnames that answer now, to check after the restart.
mapfile -t others < <(sed -n 's/^[[:space:]]*-\{0,1\}[[:space:]]*hostname:[[:space:]]*["'\'']\{0,1\}\([^"'\'' #]*\).*/\1/p' "$CONFIG")
answers() { curl -sS -o /dev/null --max-time 10 "https://$1/" 2>/dev/null; }
before=()
for h in "${others[@]}"; do answers "$h" && before+=("$h"); done

work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
new="$work/config.yml"
{
  head -n "$((catchall_line - 1))" "$CONFIG"
  printf '%s- hostname: %s\n' "$indent" "$HOST"
  printf '%s  service: %s\n' "$indent" "$SERVICE"
  printf '%s  originRequest:\n' "$indent"
  printf '%s    connectTimeout: 30s\n' "$indent"
  printf '%s    noHappyEyeballs: true\n' "$indent"
  tail -n "+$catchall_line" "$CONFIG"
} > "$new"
cloudflared tunnel --config "$new" ingress validate
echo "tunnel: the new rule for $HOST is valid:"
cloudflared tunnel --config "$new" ingress rule "https://$HOST/health" || true

backup="$CONFIG.bak-$(date -u +%Y%m%dT%H%M%SZ)"
cp -p -- "$CONFIG" "$backup"
cat -- "$new" > "$CONFIG"   # keeps the file's owner and mode
echo "tunnel: installed; the old file is $backup"

restore() {
  echo "tunnel: $1; putting $backup back" >&2
  cat -- "$backup" > "$CONFIG"
  systemctl restart cloudflared
  exit 1
}

if [ -f "$CERT" ]; then
  env TUNNEL_ORIGIN_CERT="$CERT" cloudflared tunnel route dns "$tunnel" "$HOST" \
    || echo "tunnel: route dns failed (it may exist already); check the DNS record for $HOST" >&2
else
  echo "tunnel: $CERT is missing: run 'cloudflared tunnel login', then" >&2
  echo "        cloudflared tunnel route dns $tunnel $HOST" >&2
fi

systemctl restart cloudflared
sleep 5
systemctl is-active --quiet cloudflared || restore "cloudflared did not come back"
for h in "${before[@]}"; do
  answers "$h" || restore "$h answered before the change and does not now"
  echo "tunnel: $h still answers"
done
echo "tunnel: done. $HOST reaches $SERVICE once tazko.service runs."
