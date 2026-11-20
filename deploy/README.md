# Deploy

The web app and the API are deployed separately (docs/decisions.md D13).
Everything here is written by the agent and **run by the owner**. Read each script
before you run it; the deploy-reviewer agent has checked it against the build plan.

```
Browser ──▶ https://tazko-dev.hugepigstudio.com       Cloudflare Pages   (frontend/dist, static)
   │
   └─────▶ https://tazko-api-dev.hugepigstudio.com   Cloudflare Tunnel ─▶ 127.0.0.1:8791 tazko serve
```

Both hosts are under the same registrable domain, so they are *same-site*: the API's
session cookie (`HttpOnly; Secure; SameSite=Lax`, host-only on the API host) is sent with
`fetch(..., { credentials: "include" })`. The API answers CORS for exactly
`TAZKO_WEB_ORIGIN` and checks `Origin` on every write. The API host is `tazko-api-dev`,
not `api.tazko-dev`: the free Cloudflare certificate covers one subdomain level.

Target: Ubuntu 24.04 (setup-host.sh installs `python3.12` from its archive).

**The machine is shared.** It already runs another service on `127.0.0.1:8790` and a
Cloudflare tunnel with a rule for another hostname. Nothing here touches them: Tazko
adds its own users, folders, units and one tunnel rule.

## What is where on the host

| Path | Owner, mode | What |
|---|---|---|
| `/opt/tazko/releases/<time>-<commit>/` | tazko-deploy, 755 | one release: wheel, requirements, `.venv` |
| `/opt/tazko/current` | link | the running release |
| `/var/lib/tazko/data` | tazko, 700 | `control.db`, `secret`, `orgs/<slug>/`, `trash/` |
| `/var/backups/tazko/<time>/` | tazko, 700 | nightly snapshots, 30 days |
| `/var/backups/tazko/pre-release/<time>/` | tazko, 700 | snapshot before each release, 7 days |
| `/var/lib/tazko-incoming` | tazko-deploy, 750 | bundles waiting to be released |
| `/etc/tazko/tazko.env` | root:tazko, 640 | settings, including the Google client secret |
| `/usr/local/bin/tazko-release` | root, 755 | `release.sh` |

Users: `tazko` runs the service (no login, writes only `/var/lib/tazko`); `tazko-deploy`
owns the releases and may, through sudo, only restart, stop and start `tazko.service`,
start the pre-release backup, check and restore units, and read the last 200 log lines.

Before step 3, check how cloudflared runs: `systemctl cat cloudflared` must show
`--config /etc/cloudflared/config.yml` (or no `--config`) and no `--token`. A tunnel
managed with a dashboard token ignores `config.yml`; add the hostname in the dashboard
instead (the script refuses to run in that case).

## First time

1. **Host** (once, as root): copy `deploy/backend/` to the host, read it, then
   ```bash
   sudo bash deploy/backend/setup-host.sh
   ```
   It installs Python 3.12 from the Ubuntu archive, makes the users, folders, sudoers
   file and units, and writes `/etc/tazko/tazko.env` if there is none. Run it again after
   pulling a newer `deploy/backend/`: it keeps your settings and replaces only Tazko's
   units and scripts.

2. **Google client** (browser, build plan "Google sign-in"): authorized redirect URI
   `https://tazko-api-dev.hugepigstudio.com/auth/google/callback`. Put the client ID and
   secret into `/etc/tazko/tazko.env` as root (`sudoedit /etc/tazko/tazko.env`). Never in
   the repository or a chat. The file must keep `TAZKO_ENV=production`.

3. **Tunnel rule** (once, as root):
   ```bash
   sudo bash deploy/backend/add-tunnel-rule.sh
   ```
   It backs up `/etc/cloudflared/config.yml`, adds the API hostname above the 404
   catch-all, validates, routes DNS, restarts cloudflared and checks the other hostname
   still answers (it puts the old file back if not).

4. **First release**: on your machine, in a clean checkout of `main` (or the release
   branch):
   ```bash
   deploy/backend/build-bundle.sh                 # prints dist/tazko-<time>-<commit>.tar.gz
   scp dist/tazko-*.tar.gz <you>@192.168.86.49:/tmp/
   ```
   On the host:
   ```bash
   sudo install -o tazko-deploy -g tazko-deploy -m 640 /tmp/tazko-<time>-<commit>.tar.gz /var/lib/tazko-incoming/
   sudo -u tazko-deploy tazko-release /var/lib/tazko-incoming/tazko-<time>-<commit>.tar.gz
   curl -s http://127.0.0.1:8791/health          # {"status":"ok","version":"0.1.0"}
   curl -s http://127.0.0.1:8790/ -o /dev/null -w '%{http_code}\n'   # the other service still answers
   ```

5. **First super admin** (once): your shell does not load `tazko.env`, so pass `--data`.
   ```bash
   sudo -u tazko /opt/tazko/current/.venv/bin/tazko admin --data /var/lib/tazko/data --email trantrungdng@gmail.com
   ```

6. **Web app** (Cloudflare Pages, once): create the Pages project `tazko-web`, attach the
   custom domain `tazko-dev.hugepigstudio.com`. Then from your machine:
   ```bash
   VITE_API_URL=https://tazko-api-dev.hugepigstudio.com deploy/frontend/deploy.sh --production
   ```
   Sign in at `https://tazko-dev.hugepigstudio.com` and open `/admin`.

## Releasing the API

Build and copy the bundle as in step 4, then `tazko-release <bundle>`. The script:

1. installs the bundle into its own folder and virtualenv (pinned, hashed wheels only,
   downloaded from PyPI: the host needs outbound HTTPS while a release installs); if that
   fails, nothing changes;
2. takes a snapshot of the data with the running release (`tazko-pre-release-backup.service`);
3. switches `/opt/tazko/current`, restarts, and waits up to 20 s for `/health`;
4. if `/health` fails, switches back, restarts the previous release, and runs
   `tazko check` on the data (`tazko-check.service`): `/health` opens only `control.db`,
   while a company file may hold a migration the previous release refuses;
5. if the previous release cannot use the data (the new release ran a migration it does
   not allow, D36), restores the pre-release snapshot and starts again. The data it
   replaced is kept as `/var/lib/tazko/data.failed-<time>`; remove those folders by hand
   once you no longer need them.

A release that failed can be tried again with the same bundle name (after fixing
`tazko.env`, say). Only one `tazko-release` runs at a time. The restore unit refuses a
snapshot older than 30 minutes, so starting it by hand never throws away days of work;
it still stops `tazko.service` first (the units conflict), so start that again after.
`build-bundle.sh` and `deploy.sh --production` run only from `main` or a `release/` branch.

Exit 0 released; 1 failed and rolled back (or nothing changed); 3 still unhealthy, look
at `sudo journalctl -u tazko.service -n 200 --no-pager`.

```bash
sudo -u tazko-deploy tazko-release --list        # * marks the running release
sudo -u tazko-deploy tazko-release --rollback    # one healthy release back; never restores data
```

The API stays backward compatible for one release, so either side can roll back alone.
When a change needs both, release the API first, then the web app.

## Releasing the web app

```bash
VITE_API_URL=https://tazko-api-dev.hugepigstudio.com deploy/frontend/deploy.sh             # preview
VITE_API_URL=https://tazko-api-dev.hugepigstudio.com deploy/frontend/deploy.sh --production
```

It refuses to deploy an uncommitted tree, or when `connect-src` in
`frontend/public/_headers` does not list the API host for https and wss. wrangler is
pinned with hashes in `deploy/frontend/package-lock.json`; `--production` deploys the
branch `main`, which must be the Pages project's production branch. Rollback: Pages project, Deployments, the previous one, "Rollback to this
deployment".

## Backups

`tazko-backup.timer` runs every night at 02:30: it removes companies kept in
`data/trash/` for more than 30 days, writes `/var/backups/tazko/<time>/` (every database
with SQLite's online backup, the company files and the secret) while the server runs,
keeps 30 days, and checks the snapshot. Check by hand at any time:

```bash
sudo -u tazko /opt/tazko/current/.venv/bin/tazko check --data /var/backups/tazko
systemctl list-timers tazko-backup.timer
```

Snapshots contain `data/secret`, which signs sessions: keep them private (they are 700/600).

**Off-machine copy (optional):** `apt install rclone`, then create
`/etc/tazko/rclone.conf` (root:tazko, 640) with a remote named `tazko-offsite` pointing at a
private bucket, ideally an rclone `crypt` remote over it. Use a remote with static keys
(rclone cannot rewrite the read-only config to refresh a token). The nightly job then runs
`rclone copy /var/backups/tazko tazko-offsite:tazko`: copy, not sync, so a local folder
emptied by mistake never empties the remote. Give the bucket a lifecycle rule that deletes
objects after 40 days. Without the config file the step skips.

**Restore by hand** (for example from a nightly snapshot):

```bash
sudo systemctl stop tazko.service
sudo -u tazko cp -a /var/backups/tazko/<time> /var/lib/tazko/data.new
sudo -u tazko /opt/tazko/current/.venv/bin/tazko check --data /var/lib/tazko/data.new
sudo -u tazko mv /var/lib/tazko/data /var/lib/tazko/data.old
sudo -u tazko mv /var/lib/tazko/data.new /var/lib/tazko/data
sudo -u tazko mv /var/lib/tazko/data.old/trash /var/lib/tazko/data/trash
sudo systemctl start tazko.service
```

A deleted company stays in `data/trash/<slug>-<time>/` for 30 days. To bring it back,
stop the service, move that folder to `data/orgs/<slug>/`, set its row back with
`UPDATE orgs SET status = 'suspended', deleted_at = NULL WHERE slug = '<slug>'` in
`control.db`, start the service and resume it in the console.
