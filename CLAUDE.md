# Tazko

Multi-tenant board app. One Rust binary (Axum, rusqlite, tokio) that embeds the React web app.
Specs: docs/build-plan.md (data, permissions, deploy) and design/tazko-prototype.html (UI).
If they disagree: plan wins on data and permissions, prototype wins on UI. If neither says, stop and ask.

## Commands
- scripts/ci.sh          fmt, clippy -D warnings, cargo test, web lint + vitest, license check
- cargo run -- serve     dev server on 127.0.0.1:8791 (web/dist read from disk in dev)
- npm --prefix web run dev
- npx playwright test    e2e (tests/e2e)

## Layout
- src/<area>/mod.rs: one module per area, map in src/lib.rs. Server routes mount in src/server.rs.
- web/src/app (product), web/src/admin (/admin console), web/src/lib/i18n (every UI string).
- deploy/ is written by the agent and run by the owner. design/ is never edited.

## How we work
- One milestone per branch: milestone/m2-core. One task per commit. Task list lives in docs/milestones/Mx.md.
- Write the test for a "Done when" line before the code. Never weaken or delete a test to make it pass.
- Run scripts/ci.sh before every commit. Commit messages: short, plain description of the change.
- Record every judgment call in docs/decisions.md (date, question, choice, why).
- Before a UI task, open the matching screen in design/ and note layout, states (empty, loading, error, read-only), text, keys.
- design/KNOWN-DEVIATIONS.md lists prototype behaviour that is wrong. Do not copy it; each entry has a regression test.

## Data
- data/control.db: users, companies, memberships, invites, sessions, audit log.
- data/orgs/<slug>/tazko.db and data/orgs/<slug>/files/: one company each. No org_id columns.
- One writer thread per company, small read pool. WAL, synchronous=NORMAL, foreign_keys=ON.
- Migrations: migrations/control and migrations/tenant, tracked with PRAGMA user_version.
- Every change writes an events row in the same transaction.

## Auth and permissions
- Google OIDC with PKCE. Sign-in only for existing users or valid invites. Invites expire after 14 days.
- Match account by sub; match by email only when the user has no sub yet.
- Check Origin on every state-changing request and on the WebSocket handshake.
- Permissions are checked on the server for every request. The UI hiding a button is not a check.
- Observer is read-only, including comments and custom fields. Restricted boards are hidden from unlisted members.
- Tokens are stored as hashes only. Webhooks never call private addresses (check after DNS resolve).

## Never
- Run sudo, systemctl, cloudflared or anything on the production host. Write a script in deploy/ and ask.
- Read or print secrets (.env, data/secret). Ask the owner to set them.
- Merge PRs, push --force, or push to main.
- Add Postgres, Docker, or a library that is not MIT, Apache-2.0, BSD or ISC.
- Name other products in code, text, tests or docs. Copy code, text or icons from other products.

## UI
- Tailwind theme from design/tokens.css. Light and dark must both match the prototype.
- Initial JS under 200 KB gzip. No key shortcut fires while typing in a field.
