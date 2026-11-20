#!/usr/bin/env bash
# Installs a release bundle of the API server, health-checks it, and rolls back
# by itself (build plan "Releases", D36). Installed by setup-host.sh as
# /usr/local/bin/tazko-release (root-owned) and run by the owner as tazko-deploy:
#
#   sudo -u tazko-deploy tazko-release /var/lib/tazko-incoming/tazko-<time>-<commit>.tar.gz
#   sudo -u tazko-deploy tazko-release --rollback    # one healthy release back
#   sudo -u tazko-deploy tazko-release --list
#
# A release goes into /opt/tazko/releases/<time>-<commit>/ with its own
# virtualenv; every package is a pinned, hashed wheel (D8). Before switching,
# the pre-release backup unit snapshots the data. If /health does not answer
# within 20 s, the previous release comes back; if the data no longer suits it
# (a contract migration, D36), the pre-release backup is restored. Data and
# /etc/tazko/tazko.env are never touched here. The last 5 releases are kept.
#
# Exit: 0 released, 1 failed and rolled back (or nothing changed), 2 wrong
# usage, 3 still unhealthy after every fallback (see `journalctl -u tazko`).
#
# TAZKO_* variables below exist for tests/deploy/test_release.py only; sudo
# resets the environment, so they never reach a production run.
set -euo pipefail
umask 022

ROOT="${TAZKO_RELEASE_ROOT:-/opt/tazko}"
INCOMING="${TAZKO_INCOMING:-/var/lib/tazko-incoming}"
HEALTH_URL="${TAZKO_HEALTH_URL:-http://127.0.0.1:8791/health}"
HEALTH_SECONDS="${TAZKO_HEALTH_SECONDS:-20}"
PYTHON="${TAZKO_PYTHON:-/usr/bin/python3.12}"
SYSTEMCTL="${TAZKO_SYSTEMCTL:-}"
KEEP=5
RELEASES="$ROOT/releases"
CURRENT="$ROOT/current"
NAME_RE='^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}$'

say() { echo "tazko-release: $*" >&2; }
die() { local code="$1"; shift; say "$*"; exit "$code"; }

ctl() {
  # Only the exact commands that /etc/sudoers.d/tazko-deploy allows.
  if [ -n "$SYSTEMCTL" ]; then "$SYSTEMCTL" "$@"; else sudo -n /usr/bin/systemctl "$@"; fi
}

healthy() {
  local end=$((SECONDS + HEALTH_SECONDS))
  while :; do
    curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1 && return 0
    [ "$SECONDS" -ge "$end" ] && return 1
    sleep 1
  done
}

current_id() {
  [ -L "$CURRENT" ] || return 0
  basename -- "$(readlink -- "$CURRENT")"
}

list_ids() {
  [ -d "$RELEASES" ] || return 0
  find "$RELEASES" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | grep -E "$NAME_RE" | sort || true
}

switch_to() {
  # Atomic: a new link, then rename over the old one.
  ln -sfn -- "$RELEASES/$1" "$CURRENT.new"
  mv -Tf -- "$CURRENT.new" "$CURRENT"
}

prune() {
  local cur ids count i
  cur="$(current_id)"
  mapfile -t ids < <(list_ids)
  count="${#ids[@]}"
  for ((i = 0; i < count - KEEP; i++)); do
    [ "${ids[i]}" = "$cur" ] && continue
    [[ "${ids[i]}" =~ $NAME_RE ]] || continue
    rm -rf -- "${RELEASES:?}/${ids[i]}"
  done
}

unpack() {
  local bundle="$1" dest="$2" wheels
  if tar -tzf "$bundle" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
    say "the bundle has absolute or .. paths"; return 1
  fi
  tar -xzf "$bundle" -C "$dest" --no-same-owner --no-same-permissions
  wheels=("$dest"/tazko-*.whl)
  [ "${#wheels[@]}" -eq 1 ] && [ -f "${wheels[0]}" ] || { say "expected one tazko wheel"; return 1; }
  [ -f "$dest/requirements.txt" ] && [ -f "$dest/VERSION" ] || { say "VERSION or requirements.txt missing"; return 1; }
  "$PYTHON" -m venv "$dest/.venv"
  "$dest/.venv/bin/pip" install --disable-pip-version-check --no-input \
    --require-hashes --only-binary :all: --no-deps -r "$dest/requirements.txt"
  "$dest/.venv/bin/pip" install --disable-pip-version-check --no-input \
    --no-deps --no-index "${wheels[0]}"
}

install_bundle() {
  local bundle="$1" name id dest prev
  name="$(basename -- "$bundle")"
  [ "$(dirname -- "$bundle")" = "$INCOMING" ] || die 2 "the bundle must be in $INCOMING"
  [[ "$name" == tazko-*.tar.gz ]] || die 2 "expected tazko-<time>-<commit>.tar.gz, got $name"
  id="${name#tazko-}"
  id="${id%.tar.gz}"
  [[ "$id" =~ $NAME_RE ]] || die 2 "expected tazko-<time>-<commit>.tar.gz, got $name"
  [ -f "$bundle" ] || die 2 "$bundle does not exist"
  dest="$RELEASES/$id"
  [ -e "$dest" ] && die 1 "$id is already installed"

  prev="$(current_id)"
  if [ -n "$prev" ]; then
    ctl start tazko-pre-release-backup.service || die 1 "the pre-release backup failed; nothing changed"
  fi

  mkdir -p -- "$RELEASES"
  mkdir -- "$dest"
  if ! unpack "$bundle" "$dest"; then
    rm -rf -- "${dest:?}"
    die 1 "could not install $id; nothing changed"
  fi

  switch_to "$id"
  ctl restart tazko.service
  if healthy; then
    say "released $id"
    prune
    return 0
  fi
  touch -- "$dest/FAILED"

  if [ -z "$prev" ]; then
    ctl stop tazko.service
    rm -f -- "$CURRENT"
    die 1 "$id failed its health check and there is no previous release; the service is stopped"
  fi
  switch_to "$prev"
  ctl restart tazko.service
  healthy && die 1 "$id failed its health check; rolled back to $prev"

  # The data no longer suits the previous release (D36): restore the snapshot
  # taken just before this release. Writes since then are lost; they are in
  # /var/lib/tazko/data.failed-<time> for the owner.
  ctl stop tazko.service
  ctl start tazko-restore.service
  ctl start tazko.service
  healthy && die 1 "$id failed its health check; rolled back to $prev and restored the pre-release backup"
  die 3 "$id failed, and $prev is unhealthy even after the restore; see: sudo journalctl -u tazko.service"
}

rollback() {
  local cur target="" id ids
  cur="$(current_id)"
  [ -n "$cur" ] || die 1 "no current release"
  mapfile -t ids < <(list_ids)
  for id in "${ids[@]}"; do
    [[ "$id" < "$cur" ]] && [ ! -e "$RELEASES/$id/FAILED" ] && target="$id"
  done
  [ -n "$target" ] || die 1 "no healthy release before $cur"
  switch_to "$target"
  ctl restart tazko.service
  if healthy; then say "rolled back to $target"; return 0; fi
  # A manual rollback never restores data: days of work could be lost.
  switch_to "$cur"
  ctl restart tazko.service
  die 1 "$target cannot run on this data (a newer migration, D36); back on $cur. Restoring a backup by hand: deploy/README.md"
}

list_releases() {
  local cur id mark
  cur="$(current_id)"
  while IFS= read -r id; do
    [ -n "$id" ] || continue
    mark="  "
    [ "$id" = "$cur" ] && mark="* "
    if [ -e "$RELEASES/$id/FAILED" ]; then echo "$mark$id (failed)"; else echo "$mark$id"; fi
  done < <(list_ids)
}

case "${1:-}" in
  --list) list_releases ;;
  --rollback) rollback ;;
  "" | -*) die 2 "usage: tazko-release <bundle.tar.gz> | --rollback | --list" ;;
  *) install_bundle "$1" ;;
esac
