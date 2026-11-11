# Deploy

The web app and the API are deployed separately (docs/decisions.md D13).
Everything here is written by the agent and **run by the owner**.

```
Browser ──▶ https://tazko-dev.hugepigstudio.com       Cloudflare Pages   (frontend/dist, static)
   │
   └─────▶ https://tazko-api-dev.hugepigstudio.com   Cloudflare Tunnel ─▶ 127.0.0.1:8791 tazko serve
```

Both hosts are under the same registrable domain, so they are *same-site*:
the API's session cookie (`HttpOnly; Secure; SameSite=Lax`, host-only on the API
host) is sent with `fetch(..., { credentials: "include" })`. The API answers CORS
for exactly `TAZKO_WEB_ORIGIN` and checks `Origin` on every write and on the
WebSocket handshake.

The API host is `tazko-api-dev`, not `api.tazko-dev`: the free Cloudflare
certificate covers only one subdomain level.

## backend/ — the API (one Python service)

| File | What |
|---|---|
| `setup-host.sh` | One-time host setup: users, folders, env file, sudoers, units (M1-08) |
| `add-tunnel-rule.sh` | Adds the **API** hostname to the existing tunnel without touching other rules |
| `build-bundle.sh` | Builds the wheel + hashed, pinned requirements off the server (D8) |
| `release.sh` | Installs a bundle into its own virtualenv, restarts, health-checks `/health`, rolls back by itself |
| `tazko.service`, `tazko-backup.*` | systemd units |

## frontend/ — the static app (Cloudflare Pages)

| File | What |
|---|---|
| `deploy.sh` | `npm run build` with `VITE_API_URL`, then `wrangler pages deploy` |
| `../../frontend/public/_redirects` | SPA fallback to `index.html` |
| `../../frontend/public/_headers` | Security and cache headers |

One-time Pages setup (owner): create the Pages project `tazko-web`, attach the
custom domain `tazko-dev.hugepigstudio.com`, set `VITE_API_URL` for production.

## Release order

The API stays backward compatible for one release, so either side can roll back alone.
When a change needs both, release the API first, then the web app.
