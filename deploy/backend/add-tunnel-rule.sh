#!/usr/bin/env bash
# Adds the Tazko API hostname to the EXISTING Cloudflare tunnel (build plan
# "Deployment" step 1, D13, D37). RUN BY THE OWNER as root, after reading it:
#
#   sudo bash deploy/backend/add-tunnel-rule.sh [hostname]   # default tazko-api-dev.hugepigstudio.com
#
# It backs up /etc/cloudflared/config.yml, inserts one rule above the final
# `service: http_status:404` catch-all, validates the new file BEFORE installing
# it, routes DNS, restarts cloudflared, and waits up to 30 s for every hostname
# that answered before to answer again (502, 503, 504, 530 or no answer count as
# down: Cloudflare's edge answers even when the tunnel is broken). If cloudflared
# does not come back or a hostname stays down, it puts the old file back and
# restarts. It never removes or edits other rules. Running it again only makes
# sure the DNS record exists.
set -euo pipefail
umask 077

HOST="${1:-tazko-api-dev.hugepigstudio.com}"
CONFIG=/etc/cloudflared/config.yml
CERT=/etc/cloudflared/cert.pem
SERVICE="http://127.0.0.1:8791"

say() { echo "tunnel: $*"; }
die() { echo "tunnel: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run as root (sudo)"
[[ "$HOST" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$ ]] \
  || die "'$HOST' is not a hostname"
command -v cloudflared >/dev/null || die "cloudflared is not installed"
[ -f "$CONFIG" ] || die "$CONFIG not found; see deploy/README.md (no tunnel yet)"

# The rule only counts if cloudflared reads this file (not a dashboard token).
unit="$(systemctl cat cloudflared 2>/dev/null || true)"
[ -n "$unit" ] || die "no cloudflared unit; see deploy/README.md"
grep -q -- '--token' <<<"$unit" \
  && die "cloudflared runs with --token (managed in the dashboard): add the hostname there instead"
if grep -q -- '--config' <<<"$unit" && ! grep -q -- "--config[ =]$CONFIG" <<<"$unit"; then
  die "cloudflared reads another config file than $CONFIG; check 'systemctl cat cloudflared'"
fi

tunnel="$(sed -n 's/^tunnel:[[:space:]]*["'\'']\{0,1\}\([^"'\''[:space:]#]*\).*/\1/p' "$CONFIG" | head -n 1)"
[ -n "$tunnel" ] || die "no 'tunnel:' line in $CONFIG"

route_dns() {
  if [ -f "$CERT" ]; then
    env TUNNEL_ORIGIN_CERT="$CERT" cloudflared tunnel route dns "$tunnel" "$HOST" \
      || echo "tunnel: route dns failed (the record may exist already); check the DNS record for $HOST" >&2
  else
    echo "tunnel: $CERT is missing: run 'cloudflared tunnel login', then this script again" >&2
  fi
}

if grep -Eq "^[[:space:]]*-?[[:space:]]*hostname:[[:space:]]*['\"]?${HOST//./\\.}['\"]?[[:space:]]*$" "$CONFIG"; then
  say "$HOST is already in $CONFIG; making sure its DNS record exists"
  route_dns
  exit 0
fi

catchall_line="$(grep -nE '^[[:space:]]*-[[:space:]]*service:[[:space:]]*http_status:404[[:space:]]*$' "$CONFIG" | tail -n 1 | cut -d: -f1)"
[ -n "$catchall_line" ] || die "no '- service: http_status:404' catch-all in $CONFIG"
indent="$(sed -n "${catchall_line}p" "$CONFIG" | sed 's/-.*//')"

status() { curl -s -o /dev/null --max-time 10 -w '%{http_code}' "https://$1/" 2>/dev/null || true; }
up() { case "$(status "$1")" in 000 | 502 | 503 | 504 | 530 | "") return 1 ;; *) return 0 ;; esac; }

# Hostnames that answer now, to check after the restart.
mapfile -t others < <(sed -n 's/^[[:space:]]*-\{0,1\}[[:space:]]*hostname:[[:space:]]*["'\'']\{0,1\}\([^"'\'' #]*\).*/\1/p' "$CONFIG")
before=()
for h in "${others[@]}"; do
  if up "$h"; then before+=("$h"); say "$h answers ($(status "$h"))"; else say "$h does not answer now; not checked"; fi
done

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
say "the new rule for $HOST is valid:"
cloudflared tunnel --config "$new" ingress rule "https://$HOST/health" || true

backup="$CONFIG.bak-$(date -u +%Y%m%dT%H%M%SZ)"
cp -p -- "$CONFIG" "$backup"
cat -- "$new" > "$CONFIG"   # keeps the file's owner and mode
say "installed; the old file is $backup"

restore() {
  echo "tunnel: $1; putting $backup back" >&2
  cat -- "$backup" > "$CONFIG"
  systemctl restart cloudflared || true
  sleep 5
  if systemctl is-active --quiet cloudflared; then
    echo "tunnel: cloudflared runs on the old config again" >&2
  else
    echo "tunnel: CLOUDFLARED IS DOWN even on the old config: sudo journalctl -u cloudflared -n 100" >&2
  fi
  exit 1
}

route_dns
systemctl restart cloudflared || restore "cloudflared did not restart with the new file"
for h in "${before[@]}"; do
  ok=""
  for _ in $(seq 1 15); do
    if up "$h"; then ok=1; break; fi
    sleep 2
  done
  [ -n "$ok" ] || restore "$h answered before the change and does not now ($(status "$h"))"
  say "$h still answers ($(status "$h"))"
done
systemctl is-active --quiet cloudflared || restore "cloudflared is not active"
say "done. $HOST reaches $SERVICE once tazko.service runs."
