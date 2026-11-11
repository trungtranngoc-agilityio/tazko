<!-- Converted from the owner's build plan page. The original HTML is docs/sources/tazko-build-plan.html. -->
# Tazko

A self-hosted kanban work tracker for several companies. One Rust binary, one SQLite file per company, a super admin console to run the companies, and Google sign-in for both Workspace and personal accounts.

One static Rust binaryWeb app and admin console embeddedSQLite per companyGoogle: Workspace + GmailCloudflare Tunnel, no open port

## The plan as a board

Milestones are lists. Each one ships something usable. The dashed column is what we decided not to build.

### M1 Platform 7

 Binary with embedded web app
Tunnel, systemd, deploy with rollback
Google sign-in, Workspace and Gmail
Super admin console
Create, suspend, delete companies
Invite owners and members
Nightly backup

### M2 Projects and boards 12

 Boards, lists, cards, drag and drop
Card detail, checklists, comments
Labels, assignees, due dates
Manage projects (company owners)
Project settings, owners, members, observers
Board access inside a project
Card and list actions, shortcuts
Personal settings
Rich-text description
Search, filter, activity log
Zen mode, key help, key map
Card menu, side comments, long cards

### M3 Live and files 6

 Real-time board sync
File attachments
In-app notifications, @mentions
Custom fields
Reactions on comments
Uploaded board backgrounds

### M4 Views and templates 5

 Table view
My cards page
Board and card templates
Dashboard view
Command palette

### M5 Card depth 5

 Checklist item assignee and due date
Recurring cards
Links between cards
Voting
Card aging (project setting)

### M6 Integration and email 6

 API tokens and webhooks
Command line tool
Email invites and notifications
Reminders by email
Notification preferences
REST API reference

### Later 3

 Desktop app (Tauri)
Vietnamese interface
Production host

### Not building 6

 Rule-based automation
Third-party add-ons
Personal planner and inbox
Timeline, Calendar
Map view
Imports from other products

## Decisions

| Topic | Decision | Source |
| --- | --- | --- |
| Why build | Data ownership and custom workflows. When feature parity with common kanban tools and a company's workflow conflict, the workflow wins. | You |
| Deployment | One static Rust binary (musl) with the web app compiled in. Runs under systemd on Ubuntu. Cloudflare Tunnel to `127.0.0.1:8791`. Hostname `tazko-dev.hugepigstudio.com`. | You |
| Machine | An existing Ubuntu server (192.168.86.49) that already runs another service and tunnel. Tazko must coexist with it; see Deployment. | You |
| Database | SQLite in WAL mode. `control.db` for people, companies, invites, sessions, audit log. One `tazko.db` per company for everything else. | You |
| Sign-in | Google only, Workspace and personal accounts. Invite-only: an account can sign in only if its verified email already belongs to a person or a pending invite. After the first sign-in people are identified by Google's `sub`, so an email change does not lock them out. | You |
| Super admin | A flag on a person, set from the command line. First one: `trungngo@hugepigstudio.com`. Manages companies and people from `/admin`. Sees project names, owners and counts but not boards. Every admin action is audit-logged. | You, with my default on board access |
| Company roles | Owner and member. Owners manage the company's members, other owners, invites and storage, and manage all projects. Only owners create projects. Members cannot create projects. | You |
| Projects | Company, then project, then board. Only company owners create projects, choose their owners, and can archive or delete any project. A project has settings (name, description, color, default board background, member switches, card aging) and members. Deleted projects stay in trash for 30 days. People see a project only when they are in it. Company owners manage a project but open its boards only after adding themselves, which is audit-logged. | You |
| Project access | Project roles: owner (settings, members, invites, restricted boards), member (edit boards and cards), observer (read only). Project members see every board in the project. A board can be restricted to a chosen subset of the project's members. Project switches: members can create boards (default on) and members can invite (default off). | You |
| Inviting | Project owners invite people to a project; company owners can too. If the person is not yet in the company they join it as a plain member, with access only to that project. Invites match the Google account's verified email, Workspace or personal. | You |
| Backend | Rust: Axum, rusqlite (bundled SQLite), tokio. | You |
| Web app | React, TypeScript, Vite, Tailwind, shadcn/ui, dnd-kit. Built to static files, brotli pre-compressed, embedded in the binary. English with strings in an i18n file (Vietnamese later). | Assumed |
| Desktop | Deferred. | You |
| Command line | One program, `tazko`, is both the server (`serve`, `admin`, `backup`, `check`) and a command-line client for people (`auth`, `project`, `board`, `card`, `my`, `search`, `token`, `webhook`, `api`). The client signs in through the browser with a device code, keeps a personal token in the system keychain and uses the same REST API as the web app. It offers `--json` and `--jq` for scripts. Builds for Linux, macOS and Windows are served at `/cli`. | You, shape assumed |
| Personal settings | Profile (name, job title, photo source, language), appearance (system, light or dark theme; zoom 80 to 150 percent; comfortable or compact cards; reduce motion; zen mode on or off, zen card density, quiet notices in zen), date and time (time zone, date format, 12 or 24 hour, first day of week), notification choices, personal access tokens and signed-in sessions. Stored per person and the same in every company. | You |
| Email | Optional, set up in the server settings file (SMTP). When on: invitation emails, mention and assignment emails, due-date reminders, with per-person choices for instant, hourly or daily delivery. When off, everything works in the app and invitations are shared by hand. | You |
| Integrations | Company API tokens (service identity, limited to chosen projects, with expiry) and webhooks (HMAC signed, retried with growing delay for a day, delivery log, redeliver) are managed by company owners. Personal tokens act as the person and never exceed their access. | You, details assumed |
| Card depth | Checklist items can have an assignee and a due date. Cards can repeat: completing a repeating card reopens it with the next due date. Cards can be linked (relates to, blocks, is blocked by, duplicates); an open blocker shows a Blocked badge. Comments have emoji reactions. Descriptions use a rich-text editor and are sanitized on the server. Cards can be voted on (one vote per person), with the count on the card, a Votes column in the table and a Most votes chart on the dashboard. Card aging fades cards that have had no activity: it is a project setting, on by default, starting after 7 days (3, 7, 14 or 30 to choose), and never applied to completed cards. | You |
| Look and feel | The clickable prototype in `design/` is the specification for how the product looks and behaves: layout, spacing, colors, type, icons, wording, empty states, keyboard and motion. The finished product must look and feel like it, in light and dark themes. See the section on the prototype below. Where the prototype and this plan differ on data, permissions or limits, this plan wins; where they differ on look or interaction, the prototype wins. | You |
| Card layout | The card opens as one wide dialog in two columns that scroll on their own. On the left: title, list, members, labels, votes, dates, description, custom fields, checklists, linked cards, attachments. On the right: comments and activity, with the comment box at the top, so a person can read and write comments while viewing the details. A top strip holds a Card menu button and Close (on the cover when there is one), so nothing covers the comments. The Card menu has two groups: Add to card (members, labels, checklist, linked cards, dates, attachment, cover, custom fields) and Actions (move, copy, watch, archive, share link). On a narrow screen, and in zen mode, the card is one column with the comments below. | You |
| Long cards | A card shows only the most recent few of anything long and offers Show all N and Show fewer: checklist items first 6 per checklist; linked cards the 3 newest; attachments the 3 newest; comments and activity the 4 newest. A link with no name shows shortened: protocol and www removed, and when longer than 44 characters the first 30, an ellipsis and the last 10, with the full address as a tooltip. Checklists can be added at any time and reordered (up and down buttons when a card has two or more). Checklist items reorder by a drag handle that appears on hover, also across checklists, or with Alt and the up or down arrow on the item. | You |
| Zen mode | A personal mode, toggled with the Z key or a button, that gives the cards the whole window. It hides the app header, board header and filter bar, and works on the board, table and dashboard views. Controls live in a strip at the top edge that appears when the pointer or keyboard focus goes there: board name, view tabs, Just mine, Hide done, Hide stale, card density (comfortable, compact, minimal), command palette, search, notifications and Exit zen. Quiet by default: only toasts with an Undo are shown. Keys select and move between cards, and a card opens as a side panel with previous and next buttons. Pasting several lines into the new-card box creates one card per line. It stays on across boards until turned off; Esc or Z leaves it. Not part of zen: lists that fill the screen, focusing a single list, and browser full screen. | You |
| Keyboard | Shortcuts act on the card selected with the keys, or the one under the pointer, and are off while typing. See the key map below. The backtick key shows or hides the key list, and Ctrl K opens the command palette. The Add a card row of a list is visible only while the pointer is over the list, focus is inside it, a card in it is selected by key, or the list is empty (always visible on touch screens). | You |
| Board backgrounds | Gradients, colors and uploaded pictures (up to 5 MB, stored with the company files). | You |
| Ordering | Fractional-index strings; a drag changes one row. | Assumed |

## Architecture

A request arrives over HTTPS at Cloudflare, travels through the tunnel to `cloudflared`, and reaches the binary on the loopback address. The session cookie names a person. The URL names a company. The binary checks membership in `control.db`, opens that company's file (cached after first use) and does the work there. Every change also writes an event row in the same transaction; after the commit the binary pushes it to open WebSockets from an in-memory hub.

```

flowchart LR
 B[Browser] -->|HTTPS| CF[Cloudflare]
 CF --> CD[cloudflared]
 CD -->|127.0.0.1:8791| S
 subgraph S[tazko binary]
 UI[web app and /admin console]
 API[REST and WebSocket]
 HUB[in-memory event hub]
 API --> HUB
 end
 S --> C[(control.db)]
 S --> D1[(orgs/acme/tazko.db)]
 S --> D2[(orgs/beta/tazko.db)]
 S --> F[files on disk]
 G[Google] |OAuth| S

```

### Data layout on disk

```
/var/lib/tazko/data/
 control.db
 secret random, made on first start
 orgs/
 acme/
 tazko.db
 files/ab/ab12...
 trash/ deleted companies, kept 30 days
```

### Google sign-in, step by step

- `/auth/google/start` sends the browser to Google with a random state, nonce and PKCE challenge.

- `/auth/google/callback` exchanges the code and verifies the ID token signature, audience, expiry and nonce against Google's public keys (`https://www.googleapis.com/oauth2/v3/certs`).

- Requires `email_verified`. Looks up the person by `sub`, else by email. If neither exists, looks for a pending invite. Otherwise refuses with a clear message and writes an audit entry.

- Creates a session: HTTP-only, Secure, SameSite=Lax cookie, 30 days from last use, stored in `control.db`.

### Workspace and personal accounts
The OAuth consent screen is External and published (out of Testing mode), which admits any Google account. Invites match on the lower-cased email address. A Workspace person and a Gmail person are the same kind of account to Tazko. Google's `hd` claim is stored only to show which domain an account belongs to.

### Tenant isolation
No `org_id` column and no policy to forget. A handler gets a handle to exactly one company's file. Backup, export and deletion of a company are file operations.

### Speed
One writer thread per company owns that file's write connection, plus a few readers. WAL mode, `synchronous=NORMAL`, `foreign_keys=ON`. A busy company never blocks another.

### Schema changes
Each database file carries its schema version (`PRAGMA user_version`) and migrates when first opened. Control and company databases have separate migration folders.

### Super admin console and invites

| Page | What it does |
| --- | --- |
| Companies | List with member count, boards, storage used and last activity. Create a company (makes its folder and database). Suspend and resume. Delete with a typed confirmation; the folder moves to `trash/` for 30 days. |
| Company detail | Members and roles, pending invites, storage limit. Invite a person as owner or member; change a role; remove a person. A read-only Projects tab lists project names with owners and member and board counts. |
| People | Everyone across companies, with their memberships and last sign-in. Disable or re-enable. Grant or revoke super admin. |
| Invites | Pending invites across all companies; revoke one. |
| Audit log | Who did what and when: company created or deleted, invite created or revoked, role changed, person disabled, sign-in refused. |
| Server | Version, uptime, data size, last backup result, email status with a send-test-email button. |

**Company owners** get the same member and invite screens for their own company only, inside the normal app (Company settings). **An invite** authorizes one email address for one company and role. Until email is set up (M6) the admin sends the person the site address by hand; with email on, the invitation can be emailed from the invite form. When they sign in with that Google account they join automatically. Invites stay valid until revoked.

## Command line

People can work from a terminal the way developers use the GitHub command line: one program, sign in once through the browser, then short commands. The same program, `tazko`, also runs the server on the server machine, so there is one thing to build, download and version.

### Signing in

- `tazko auth login --host tazko-dev.hugepigstudio.com` asks the server for a one-time device code and prints it.

- The browser opens `/cli/authorize`. The signed-in person checks that the code matches, sees the access requested, and approves.

- The program receives a personal token, keeps it in the system keychain (or a private file where there is none) and shows who is signed in.

- `TAZKO_TOKEN` and `TAZKO_HOST` override this for scripts. A token never has more access than its owner and can be revoked under Settings.

### Conventions

- Nouns, then verbs: `tazko card move`, `tazko board list`.

- Readable tables in a terminal. `--json fields` and `--jq` for scripts. `--web` opens the item in the browser.

- Boards and cards by name inside a project, or by id.

- Exit codes: 0 success, 1 failure, 2 wrong usage, 4 not signed in.

- Shell completion, `tazko update`, and `tazko config` for defaults.

- Linux, macOS and Windows builds and an install script, served by the server at `/cli`.

| Command | Subcommands | What it does |
| --- | --- | --- |
| `tazko auth` | login, logout, status, token | Sign in with the browser, see who you are, print a token for scripts |
| `tazko project` | list, view, members | Projects you belong to and who is in them |
| `tazko board` | list, view, create, open | Work with boards; open launches the web app on that board |
| `tazko card` | list, view, create, edit, move, done, assign, comment, link, archive | Everything on a card from the terminal |
| `tazko my` | cards, checklist | Cards and checklist items assigned to you |
| `tazko search` | "query" | Same operators as the app: @name, #label, is:overdue |
| `tazko token`, `tazko webhook` | list, create, revoke, test, deliveries | Personal tokens; company tokens and webhooks for owners |
| `tazko api` | METHOD /path | Call any API endpoint and filter the answer with `--jq` |
| `tazko config`, `completion`, `update` | | Defaults, shell completions, install the newest version from the server |

## Personal settings, integrations and email

### Personal settings

- **Profile:** display name, job title, photo from Google or initials, language (English now; Vietnamese later).

- **Appearance:** theme follows the device or is set to light or dark; zoom from 80 to 150 percent; card density; reduce motion; labels as names or small bars; zen mode (a switch, its card density, and quiet notices).

- **Date and time:** time zone (with detect), date format, 12 or 24 hour, first day of the week. Due dates and times everywhere use these.

- **Notifications:** a table of events by channel (in the app, by email), email delivery (instant, hourly digest, daily digest, never), reminder lead time, and a preview of each email.

- **Access tokens and Sessions:** personal tokens, and a list of browsers, terminals and phones that are signed in, each with Sign out.

### Integrations (company owners)

- **API tokens:** name, access level (read, read and write cards, manage), projects, expiry, last used. The secret is shown once.

- **Webhooks:** address, events (card created, updated, moved, completed, archived; comment created; member added; board created), projects, a signing secret shown once, pause switch, delivery log with redeliver and a test event.

- All of it is also reachable from the command line and the REST API.

### Email

- Set up in the server settings file. The admin Server page shows its status and can send a test email.

- Every invite form has an Email the invitation option. The email leads to Google sign-in.

- Mention, assignment and due-date emails follow each person's choices. Reminders always appear in the app.

- Emails come from one address and carry no tracking.

## Keyboard, zen mode and card layout

These come from the prototype and are part of the product, not extras. Shortcuts are off while typing in a field or editing a description, and while a popover is open.

### Key map

| Key | Does |
| --- | --- |
| ``` or `?` | Show or hide the key list |
| `Z` | Zen mode on or off |
| `Ctrl K` | Command palette |
| `/` | Search |
| `F`, `Q` | Filter; show only my cards |
| `N` | New card in the selected card's list (or the first list) |
| `J K H L` | Move the selection: next or previous card, previous or next list. Arrow keys do the same once a card is selected, and always in zen mode |
| `Enter`, `E` | Open the selected card; quick edit |
| `Space` | Mark done |
| `A`, `D`, `T`, `M` | Assign members, dates, labels, move |
| `V`, `X` | Vote; archive |
| `1` to `8` | Toggle the label in that position |
| With a card open: `J K H L` | Step to the next, previous, left or right card. Arrow keys too in zen mode, so they still scroll a long card otherwise |
| `Alt` with up or down arrow | Move a checklist item up or down |
| `Ctrl Enter` | Save the comment being written |
| `Esc` | Close what is open, one layer at a time; then leave zen |

### Command palette

- Opens with Ctrl K, or from the button in the zen strip. Type to filter; arrows and Enter run the highlighted item.

- Groups: Actions (zen, switch view, new card), Filter (just mine, hide done, hide stale, clear), Density, Zen quiet mode, and Card actions for the selected card (open, done, assign, dates, labels, move, vote, archive). A card action always works on the selected card; when none is selected the palette says so.

- Shows the key beside an item when one exists.

### Zen mode

- The Z key, the Zen button on a board, the palette, or Settings, Appearance. It stays on across boards and sessions as a personal setting.

- Header, board header, filter bar and read-only banner are hidden. The strip at the top edge appears on pointer or focus and shows the controls named in Decisions.

- Card density: comfortable, compact (smaller text, badges on one line) and minimal (titles only).

- A card opens as a panel on the right, 520 px wide, with previous and next buttons; the board stays visible behind it.

- On a touch device the controls stay visible, since there is no pointer to bring them out.

### Cards on the board

- The selected card has a clear outline while keys drive the selection; moving the pointer by more than a few pixels hands control back to the pointer.

- Pasting text with several lines into the new-card box creates one card for each non-empty line.

- The Add a card row follows the rule in Decisions: shown on hover, on focus, for the list holding the selected card, for an empty list, and always on touch screens.

## Data model

| File | Tables |
| --- | --- |
| `control.db` | `users` (id, email, google_sub, name, avatar, hd, is_super_admin, disabled, last_seen), `orgs` (id, slug, name, status, storage_limit), `org_members` (user, org, role), `invites` (org, email, company role, optional project, optional project role, created_by, revoked_at; kept here so a project-only invite can sign in), `sessions`, `audit_log`, `user_settings` (theme, zoom, time zone, formats, zen mode choices, notification choices), `personal_tokens` (hash, access, expiry, last used), `device_codes` (command-line sign-in), `email_queue` |
| `tazko.db`: structure | `people` (copy of id, name, avatar), `projects` (name, description, color, default background, members_can_create_boards, members_can_invite, aging_enabled (default on), aging_days (default 7), archived_at, deleted_at), `project_members` (user, role: owner, member, observer), `boards` (project, name, background, restricted), `board_access` (only for restricted boards), `lists`, `cards`, `labels`, `card_labels`, `card_members` |
| `tazko.db`: card content | `checklists`, `checklist_items` (text, done, assignee, due), `comments`, `comment_reactions` (comment, emoji, person), `card_links` (card, other card, type), `card_votes` (card, person), `attachments`, `custom_field_defs`, `custom_field_values`, `cards_fts` (FTS5) |
| `tazko.db`: activity | `events` (type, actor, board, payload, created_at), `notifications`, `board_templates`, `api_tokens` (company), `webhooks`, `webhook_deliveries` (status, attempts, next try), uploaded background images in the company files folder |

## Deployment

This section is complete enough to follow on a machine that has never seen the project. Target: Ubuntu 24.04 or later, 4 GB of memory, a second disk or folder for backups. The machine is `192.168.86.49` and the hostname is `tazko-dev.hugepigstudio.com`, a name in a domain already on the owner's Cloudflare account.

**The machine is shared.** It already runs another service on `127.0.0.1:8790` and an existing Cloudflare tunnel whose configuration is `/etc/cloudflared/config.yml` with a rule for another hostname. Do not touch those, that service's accounts, or its folders under `/opt`, `/etc` and `/var/lib`. Never rerun a tunnel setup script that rewrites `config.yml`. Tazko only adds a rule.

### Accounts and folders

- `tazko`: system user, no login. Runs the service. Writes only `/var/lib/tazko` (systemd sandbox).

- `tazko-deploy`: system user. Owns `/opt/tazko` and `/etc/tazko`. Through sudo it may run only `systemctl restart tazko.service` and read that unit's log.

- The administrator (a normal sudo user) runs the release script as `tazko-deploy`.

- `/var/lib/tazko/data` data; `/var/backups/tazko` backups; `/var/lib/tazko-incoming` uploaded bundles.

- Port `8791` on `127.0.0.1` only. Nothing else is opened on the network.

### Settings file

 `/etc/tazko/tazko.env`, mode 640, readable by `tazko-deploy`, the `tazko` group and root.

- `TAZKO_HOST=127.0.0.1`, `TAZKO_PORT=8791`

- `TAZKO_PUBLIC_URL=https://tazko-dev.hugepigstudio.com` (redirect addresses start with it)

- `TAZKO_DATA_DIR=/var/lib/tazko/data`

- `TAZKO_GOOGLE_CLIENT_ID`, `TAZKO_GOOGLE_CLIENT_SECRET`

- `TAZKO_SECRET` (32+ characters; empty means a random `secret` file in the data folder, made on first start)

- Email, optional: `TAZKO_SMTP_HOST`, `TAZKO_SMTP_PORT`, `TAZKO_SMTP_USER`, `TAZKO_SMTP_PASSWORD`, `TAZKO_MAIL_FROM`

### 1. Install and configure the tunnel (adds a rule, keeps the existing one)

- Read `/etc/cloudflared/config.yml` and note the tunnel name or id and the existing rules. `cloudflared` is already installed if that file exists.

- If the tunnel exists: insert a rule above the final catch-all `- service: http_status:404`:

```
 - hostname: tazko-dev.hugepigstudio.com
 service: http://127.0.0.1:8791
 originRequest:
 connectTimeout: 30s
 noHappyEyeballs: true
```

- Create the DNS record against that tunnel, using the account certificate that is already on the machine: `sudo env TUNNEL_ORIGIN_CERT=/etc/cloudflared/cert.pem cloudflared tunnel route dns <existing tunnel name> tazko-dev.hugepigstudio.com`. If that certificate is missing, run `cloudflared tunnel login` and have the owner open the printed link and pick the domain.

- Check with `cloudflared tunnel ingress validate --config /etc/cloudflared/config.yml`, then `sudo systemctl restart cloudflared` and confirm the unit is active and the old hostname still works.

- If no tunnel exists on the machine, create one instead: install `cloudflared` from Cloudflare's apt repository, run it as its own `cloudflared` user, and write a new config with the same rule plus the 404 catch-all.

### 2. The service

```
[Unit]
Description=Tazko
After=network.target

[Service]
User=tazko
Group=tazko
EnvironmentFile=/etc/tazko/tazko.env
ExecStart=/opt/tazko/current/tazko serve
Restart=on-failure
RestartSec=2
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/tazko
CapabilityBoundingSet=
SystemCallArchitectures=native

[Install]
WantedBy=multi-user.target
```

### 3. Releases, deploy and rollback

- Build on the server: `cargo build --release --target x86_64-unknown-linux-musl`. The build embeds the web app, so the bundle is one executable plus a small `VERSION` file. Name it `tazko-<time>-<commit>.tar.gz`.

- Copy it to `/var/lib/tazko-incoming`, then run the release script as `tazko-deploy` (installed at `/usr/local/bin/tazko-release`, root-owned).

- The script unpacks into `/opt/tazko/releases/<time>-<commit>`, points the symlink `/opt/tazko/current` at it, and runs `sudo systemctl restart tazko.service`.

- It then polls `http://127.0.0.1:8791/health` for up to 20 seconds. If there is no healthy answer it points the link back at the previous release, restarts the service and exits with an error. Options: `--rollback` (go back one release) and `--list`. Keep the last 5 releases.

### 4. First super admin

```
sudo -u tazko /opt/tazko/current/tazko admin \
 --data /var/lib/tazko/data --email trungngo@hugepigstudio.com
```

The server starts empty: no companies, no people. This command creates that one person with the super admin flag. They sign in with Google at the hostname and open `/admin`.

### 5. Google sign-in (the owner does this in a browser)

- In the Google Cloud console create a new project named **Tazko**.

- Open the OAuth consent screen (called Google Auth platform in the newer console). Audience: **External**. App name Tazko, a support email, authorized domain `hugepigstudio.com`. Scopes: `openid`, `email`, `profile` only; these need no Google review.

- **Publish the app** (move it from Testing to In production). While in Testing, only listed test users can sign in, which would shut out most people.

- Credentials, Create credentials, OAuth client ID, type **Web application**. Authorized redirect URI: `https://tazko-dev.hugepigstudio.com/auth/google/callback`. No JavaScript origin is needed.

- Put the client ID and secret into `/etc/tazko/tazko.env` as root, then restart the service. Never put them in the repository or in a chat.

### 6. Cloudflare settings

- No Cloudflare Access application: Tazko does its own sign-in.

- Optional and free: Security, WAF, rate limiting rule on URI path starting with `/auth/`, for example 20 requests per 10 seconds per IP, then block.

### 7. Backups and restore

- A systemd timer `tazko-backup.timer` runs at 02:30 and calls `tazko backup --data /var/lib/tazko/data --to /var/backups/tazko --keep-days 30` while the server runs. It copies each SQLite database with the online backup API, copies the `files/` folders, and keeps dated snapshots.

- It then runs `tazko check` on the copy: open every database, run `PRAGMA integrity_check`, and verify that every attachment file matches its hash.

- Optional: `rclone sync` of `/var/backups/tazko` to an object-storage bucket.

- Restore: stop the service, run `tazko backup --data /var/backups/tazko --to /var/lib/tazko/data.new`, run `tazko check` on it, move `data` to `data.old` and `data.new` to `data`, start the service.

## Milestones

**M1**
### Platform
deployed, signed in, companies managed
Tasks

- Cargo project and `web/` app (React, Tailwind, shadcn/ui); build step embeds `web/dist` (disk reload in development)

- Config from environment; commands `serve`, `admin --email`, `backup`, `check`

- `control.db`; open, cache and migrate company databases; writer thread and read pool per company

- Google sign-in as described above; sessions; sign-out; clear refusal page

- Super admin console: companies, company detail, people, invites, audit log, server page

- Company owner screens: members and invites for their own company

- Company switcher for people in several companies; empty company home page

- Everything in the Deployment section as scripts and units under `deploy/`: host setup, tunnel rule, service, release and rollback, backup timer

- `/health` endpoint; `scripts/ci.sh` including a dependency license check that allows only permissive licenses (MIT, Apache-2.0, BSD, ISC)

- README deploy guide that repeats the Deployment section for the repository

Done when

- `https://tazko-dev.hugepigstudio.com` reaches the app through the tunnel with no new port open, and the other service on the machine still works

- `tazko admin --email trungngo@hugepigstudio.com` then Google sign-in reaches `/admin`

- A Workspace account and a personal Gmail account can both be invited and both sign in

- An account with no person and no invite is refused and the refusal is in the audit log

- A company can be created, suspended, resumed and deleted (folder lands in `trash/`)

- A person in two companies sees only the chosen company's data; the two files are separate (test)

- Deploying a broken build rolls back by itself

- `tazko backup` produces a copy that `tazko check` accepts

**M2**
### Core boards
one team can run a real board
Tasks

- Boards, lists, cards: create, rename, archive, restore; star a board

- Fractional ordering; drag and drop of cards and lists

- Card modal: markdown description, assignees, labels, due date and done, cover

- Checklists with progress badge and inline expand; comments; tile badges

- Manage projects page for company owners: create a project with its first owner, rename, archive and restore, delete to trash for 30 days, add or remove project owners

- Project settings page for project owners: name, description, color, default board background, switches for members creating boards and inviting, card aging (on by default, after 7 days)

- Project members page: invite by email as owner, member or observer, change role, remove; a project invite also adds a new person to the company as a plain member

- Boards live inside a project; a board can be restricted to chosen project members

- Projects list per person shows only projects they belong to; members cannot create projects

- Search with FTS5; filter by member, label, due date

- Card actions: move, copy, archive and restore with undo, watch, copy share link; quick edit and a complete circle on the card tile on hover

- List actions: rename, collapse, copy, move, sort, move all cards, archive all cards, archive list

- Board menu: about, background (gradients and colors), labels, custom fields, archived items, activity, copy board, save as template, close board

- Global search with operators (@member, #label, is:overdue, has:attachments, is:archived) and keyboard shortcuts

- Rich-text description editor: bold, italic, strikethrough, headings, quotes, lists, inline code, links, clear formatting. The server sanitizes the HTML it stores

- Personal settings: profile, appearance (theme, zoom, density, reduce motion), date and time (time zone, formats, first day of week), sessions. Settings apply immediately and follow the person across devices

- Event row for every change; activity log from it

- Card dialog as in Decisions: two scrolling columns, comments and activity on the right with the comment box on top, a top strip with Card menu and Close, the Card menu with Add to card and Actions, one column on narrow screens

- Long cards: show the first few and Show all or Show fewer for checklist items and comments (and for linked cards and attachments as soon as M3 and M5 add them); shortened display of long unnamed links; Add checklist; reorder checklists; reorder checklist items by drag handle and by Alt and arrow keys

- Zen mode: toggle by key, button and Settings; hover or focus strip; comfortable, compact and minimal density; quiet notices; keyboard selection and movement; side-panel card with previous and next; multi-line paste into the new-card box; Add a card row shown only on hover, focus, key selection or an empty list

- Key map as in the section above, and the backtick key list

Done when

- A team runs a real sprint board end to end

- A project observer cannot edit; a company member who is not in a project cannot see it; a company owner can archive and delete it and add owners but cannot open its boards until added (tests)

- A company member who is not an owner is refused when creating a project (test)

- Inviting a new email to a project lets them sign in, join the company, and see only that project (test)

- A restricted board is hidden from project members who were not added to it (test)

- Moving 200 cards creates no rank collisions (test)

- Cold start under a second; idle memory recorded

- Description HTML is sanitized on the server: script tags and event attributes never reach another person's browser (test)

- Changing theme, zoom or time zone applies at once and is still set after signing in on another device

- With the card open the comment box is visible without scrolling and the left and right columns scroll separately; Card menu and Close never cover comments

- A checklist of 9 items shows 6 with Show all 9 items; a feed of 7 shows 4 with Show all 7 comments; Show fewer returns to the short list

- An unnamed 120-character link shows as the first 30 characters, an ellipsis and the last 10, and still opens the full address

- Reordering checklists or items by drag handle, buttons or Alt and arrows saves in the new order and survives a reload and another browser

- Pressing Z hides the header, board header and filter bar and the cards use the window; Z or Esc restores them; the choice is the same after signing in on another device; the same works on the table and dashboard

- In zen mode J K H L and the arrow keys move the selection, Enter opens the card in a side panel, J and K inside it step between cards, and Esc closes layer by layer

- The Add a card row is hidden at rest and appears on pointer, focus and key selection, and stays visible on a touch screen (tests)

- Every shortcut in the key map works and none fires while a field is being edited

**M3**
### Live and files
feels like a shared board
Tasks

- WebSocket per board with membership check; in-memory hub; optimistic UI and catch-up by event id (works through the tunnel); presence avatars of who is viewing

- Attachment uploads into the company's `files/` folder, stored by content hash; size and type limits; link attachments; thumbnails; company storage limit

- @mentions; notification bell with read state; due-soon alerts

- Custom fields: definitions per board, values on cards, show on tile, filter by value

- Reactions on comments: six emoji, one tap to add or remove yours, names on hover, live for everyone on the board

- Uploaded board backgrounds (up to 5 MB, images only) next to the gradients and colors, in the board menu, the project settings and the create-board dialog

Done when

- Two browsers on one board see each other's drags within a second

- A dropped connection reconnects and shows missed changes

- A mentioned user gets a notification and opens the card from it

- An upload past the company's limit is refused; a file downloads for members only

- A background image over 5 MB or that is not an image is refused with a clear message

**M4**
### Views and templates
repeat the same structure across companies
Tasks

- Board templates: save a board, create a board from it. A template made by a super admin can be offered to every company

- Table view: one row per card with sortable columns, group by list, show or hide columns (board custom fields become columns), edit list, dates, labels, members and fields in place, bulk move, assign and archive, copy as CSV

- Card templates: create a card from a saved template with its checklist and labels

- My cards page: assigned cards, assigned checklist items and watched cards across every project the person belongs to, grouped by due date, with a project filter, title filter and hide-completed

- Dashboard view: cards per list, member, label and due date

- Command palette: Ctrl K, filter as you type, groups and card actions as described above, available on every board view and in zen mode

Done when

- Ctrl K opens the palette; typing narrows it; Enter runs the item; a card action acts on the selected card and says so when none is selected

- A template creates an identical board in another company

- Sorting and grouping in the table never change card order on the board

- My cards lists only projects the person belongs to and updates when a card is reassigned

- Editing a due date in the table updates the card on the board and appears in its activity

- Dashboard totals equal the counts on the board view

**M5**
### Card depth
richer cards for planning work
Tasks

- Checklist items: optional assignee and due date, shown only when set. Assign and date from a small menu that appears on hover, so a plain checklist stays uncluttered. Assigned items appear in My cards and notify the assignee

- Recurring cards: repeat daily, every weekday, weekly, every 2 weeks or monthly. Completing the card reopens it with the next due date and clears its checklist, with undo

- Card links: relates to, blocks, is blocked by, duplicates. A link shows on both cards, and a card with an open blocker shows a Blocked badge

- Voting: one vote per person on a card, shown as a count on the card tile and with voter avatars in the card; vote from the tile, the card, the quick menu or the V key; sort a list by votes; Votes column in the table; Most votes chart on the dashboard

- Card aging: a switch and a threshold (3, 7, 14 or 30 days) in project settings, on by default at 7 days. Quiet cards fade in three steps at one, two and three times the threshold; completed cards never fade; pointing at a card shows it normally; any activity restores it. A Stale filter, an is:stale search operator, a Stale count on the dashboard and a Last activity column in the table help find quiet work

Done when

- A checklist item with an assignee appears in that person's My cards with its due date

- Completing a weekly card moves its due date forward a week and unticks its checklist; undo restores both

- Removing a link removes it from both cards; completing the blocking card clears the Blocked badge

- Voting twice removes the vote; the count on the tile, the table and the dashboard agree

- With aging on, a card quiet for the threshold fades and a comment on it restores it; turning the project setting off makes every card full strength at once; a completed card never fades (tests)

**M6**
### Integration and email
connect other tools, work from a terminal
Tasks

- REST API under /api/v1 with an OpenAPI document and a reference page at /api/docs

- Company API tokens for owners: service identity, access level, chosen projects, expiry, last used, revoke. Secret shown once

- Personal access tokens under Settings: act as the person and never more; created by hand or by command-line sign-in

- Webhooks for owners: events and projects, HMAC signature, retries with growing delay for a day, delivery log, redeliver, test event, pause

- Command line tool: device-code sign-in with the /cli/authorize approve screen, command groups (auth, project, board, card, my, search, token, webhook, api, config, completion, update), --json and --jq, install scripts and downloads at /cli

- Email, optional (SMTP in the settings file): an Email the invitation option on every invite form, mention and assignment emails, due-date reminders, instant, hourly or daily delivery, previews in Settings, status and test email on the admin Server page

- Notification preferences per person: in the app and by email for each event type

Done when

- tazko auth login signs in through the browser and tazko card create works from a terminal on another machine

- A token limited to one project cannot read another project (test)

- A webhook delivery carries a signature that verifies with the secret; a failing endpoint is retried and visible in the log

- With email on, an invited person gets an email that leads to Google sign-in. With email off, nothing breaks and the invite shows the address to share

- Someone who turns off mention emails still sees mentions in the app

## Clean-room and commit rules

Tazko is an original work. These rules apply to every file, commit and message the build session produces.

### Commits and pull requests

- Never mention AI, assistants or code-generation tools. No `Co-Authored-By` trailer naming one, no "generated with" line, no session or tool links.

- The author is the user's own git identity. Disable the tool's automatic commit and pull-request attribution in the repository's `.claude/settings.json` (set `attribution.commit` and `attribution.pr` to empty strings) and check the first commit message before going further.

- Messages describe the change in plain words, for example "Add invite revocation to the admin console".

### No other products by name

- Never name any other product, vendor or competitor in code, comments, identifiers, strings, tests, fixtures, sample data, documentation, commit messages, branch names, package names or UI text.

- Describe features in generic terms. Words such as board, list and card are common kanban vocabulary and are fine.

- If something seems to need a comparison with another product, ask the user instead.

### Original work only

- Do not copy another product's code, text, icons, colors, layout assets, templates, help copy or sample content. Design the visual look, icons and wording from scratch.

- Do not capture, scrape or reverse engineer another product's pages, scripts, API or network traffic. Work only from this plan.

- Use only dependencies under permissive licenses and keep the license check in CI.

## The prototype is the specification

The owner wants the finished product to look and behave like the clickable prototype. It was built screen by screen with the owner and covers every milestone. It is the visual and interaction reference for all of M1 to M6, so a milestone is not finished until its screens match it.

### What lives in design/

- `design/tazko-prototype.html`: the whole prototype in one file. Open it in a browser; start from the index page, which has one tile per screen, grouped by round.

- `design/tokens.css`: colors, spacing, radii, shadows and type for the light and dark themes, taken from the prototype. Turn these into the Tailwind theme so the product uses the same values.

- `design/README.md`: the screen index below and how the prototype is used.

- The folder is read-only reference. Do not edit it in the build; if something should change, ask the owner.

### How the build uses it

- Before each milestone, open the matching tiles and note layout, states (empty, loading, error, read-only), wording, icons and keyboard behavior.

- Recreate each screen with real components. The prototype is a mock with sample data; do not copy its scripts or structure. The CSS values, icon shapes and wording may be reused, because the prototype is the owner's own original work.

- Match: spacing, type, color in light and dark, density, hover and focus states, popovers, toasts with Undo, empty states, and every shortcut.

- The View as switch in the prototype shows what each role sees (super admin, company owner, project owner, member, observer). Build the same differences, enforced on the server.

- Things the prototype only pretends: sample data, live updates between browsers, email delivery, file uploads and the command line. Build them for real as the plan describes.

- If the plan and the prototype disagree, apply the precedence in Decisions, and tell the owner about the difference.

### Screen index by milestone

| Milestone | Prototype screens |
| --- | --- |
| M1 | Sign in, Sign-in refused, Company home (switcher, empty state), Company settings (members and invites), Manage projects, Admin: Companies, Company detail, People, Invites, Audit log, Server |
| M2 | Your projects, Project boards, Project members, Project settings (including card aging), Board (drag, composer, shortcuts), Card, Filter, Search with operators, Zen mode, Command palette, Settings: profile and appearance |
| M3 | Attachments (upload, link, cover), Custom fields, Live updates and presence, Notifications, Reactions, Board background upload |
| M4 | Templates, Table view, Dashboard, My cards |
| M5 | Checklist items with assignee and due date, Recurring cards, Linked cards, Rich text, Voting, Card aging, Long cards |
| M6 | Settings: notifications, access tokens and command line; Authorize the command line; Integrations: API tokens and webhooks; Email previews; Admin: email status |

## Repository and handoff

The Linux session starts in an empty repository. When you say "hand off", I send it the kickoff prompt below together with the full text of this plan, so it needs no access to this page or to any other repository. It builds one milestone at a time and stops for you to check, because M1 needs you for Google and Cloudflare. After M1 passes you can send the Next milestone prompt for each of M2 to M6, or, when you trust the process, the Full run prompt that continues through M6 on its own. The clickable design prototype is committed in design/ and is the specification for the look and behavior of everything built; the build recreates it with real components and does not copy its scripts.

### Layout

```
tazko/
 CLAUDE.md
 README.md deploy guide
 design/ prototype, tokens and screen index (read-only reference)
 Cargo.toml
 build.rs builds or checks web/ and embeds web/dist
 src/
 main.rs CLI: serve, admin, backup, check
 config.rs auth/ admin/ orgs/ tenant/ boards/ cards/
 realtime/ files/ notifications/ api/
 migrations/
 control/ tenant/
 web/ React + TypeScript + Vite + Tailwind + shadcn/ui
 src/ app/ admin/ components/ lib/i18n/
 deploy/
 setup-host.sh add-tunnel-rule.sh release.sh build-bundle.sh
 tazko.service tazko-backup.service tazko-backup.timer
 tests/
 scripts/ci.sh
```

### Proposed CLAUDE.md

**Copy
```
# Tazko

Self-hosted kanban work tracker for several companies. One Rust binary (Axum, rusqlite with bundled SQLite, tokio) that embeds the React/TypeScript web app and a super admin console, and stores each company's data in its own SQLite file. Deployed on Ubuntu behind a Cloudflare Tunnel at https://tazko-dev.hugepigstudio.com.

## Rules
- Work one milestone at a time (M1 to M6) in the order of the build plan. Do not start the next until every "Done when" check of the current one passes.
- Data layout: data/control.db (users, orgs, org_members, invites, sessions, audit_log) and data/orgs//tazko.db plus files/ per company. Tenant tables have no org_id. A handler receives a handle to exactly one company database.
- Each company has one writer thread owning the write connection and a small read pool. WAL, synchronous=NORMAL, foreign_keys=ON.
- Migrations: separate folders for control and tenant; PRAGMA user_version; run when a database is opened.
- Every state change inserts an events row in the same transaction. After commit, publish to the in-memory hub.
- Sign-in is Google OIDC only, for Workspace and personal accounts (consent screen External and published, scopes openid email profile). Verify the ID token signature, audience, expiry and nonce. Require email_verified. Identify people by Google sub after first sign-in. Accept a sign-in only for an existing, non-disabled person or a pending invite; otherwise refuse and audit-log it.
- Super admin is a flag on a person, set only by `tazko admin --email`. Super admins manage companies and people at /admin but do not see a company's boards unless they are members. Every admin action goes to audit_log.
- Access model: company, then project, then board. Company roles are owner and member. Only owners create projects, choose project owners, and archive or delete any project; owners get no access to a project's boards until they add themselves to it (audit-logged). Project roles are owner, member, observer. Project members see all boards in the project unless a board is restricted to a chosen subset. A project invite also joins the person to the company as a plain member. Invites, including project invites, are stored in control.db so a project-only invite can sign in.
- The server listens on 127.0.0.1 only (TAZKO_PORT, default 8791). TLS and the public hostname belong to Cloudflare Tunnel. Cookies are HttpOnly, Secure, SameSite=Lax.
- The deploy machine (192.168.86.49) is shared with another service. Never overwrite /etc/cloudflared/config.yml, never touch that service's accounts, folders or port 8790. Add the tazko-dev.hugepigstudio.com rule to the existing tunnel config and keep the existing rules.
- Deployment: accounts tazko (runs service, writes /var/lib/tazko only) and tazko-deploy (installs releases, may only restart tazko.service). Releases in /opt/tazko/releases with a current link and automatic rollback if /health does not answer within 20 seconds. Settings in /etc/tazko/tazko.env. Follow the plan's Deployment section.
- Never write secrets (Google client secret, TAZKO_SECRET) into the repository, logs or chat. The user places them in /etc/tazko/tazko.env.
- Commits and pull requests never mention AI, assistants or generation tools: no Co-Authored-By trailer naming one, no "generated with" line, no session links. Author is the user's git identity. Set attribution.commit and attribution.pr to empty strings in .claude/settings.json and verify the first commit message. Messages are short plain descriptions of the change.
- This is a clean-room, original project. Never name any other product, vendor or competitor in code, comments, identifiers, strings, tests, fixtures, docs, commit messages, branch or package names, or UI text. Do not copy another product's code, text, icons, colors, assets or templates; design visuals and wording from scratch. Do not capture, scrape or reverse engineer another product. Work only from the build plan. Use only permissively licensed dependencies (MIT, Apache-2.0, BSD, ISC) and keep the license check in CI. If a comparison seems needed, ask the user.
- The release build is one static binary (musl). Web build output embedded with brotli pre-compression; in development serve web/dist from disk.
- Look and behavior: design/ holds the clickable prototype, tokens.css and a screen index. The product must look and behave like it, in light and dark themes: same layout, spacing, colors, type, icons, wording, empty states and keyboard. Use design/tokens.css as the Tailwind theme. Recreate screens with real components; do not copy the prototype's scripts. The plan wins on data, permissions and limits; the prototype wins on look and interaction; tell the user about any difference. Never edit design/.
- Card dialog: two independently scrolling columns, details left, comments and activity right with the comment box on top; a top strip with Card menu and Close. Long lists show the first few and expand (checklist items 6, linked cards 3, attachments 3, comments 4). Unnamed long links display shortened. Checklists and items can be reordered.
- Zen mode (Z), the command palette (Ctrl K) and the key map in the plan are part of the product. Shortcuts never fire while typing.
- Web app: initial JS under 200 KB gzipped; load the card modal on demand; strings in an i18n file; no browser-only assumptions.
- Tokens (personal and company) are stored only as hashes and shown once. Webhooks are signed with HMAC and never sent to private addresses unless the owner allows it. Description HTML is sanitized on the server with an allow-list.
- The command line client is part of the same `tazko` binary: noun-then-verb commands, --json and --jq, device-code sign-in, token kept in the system keychain. It uses only the public REST API.
- Email is optional: nothing may depend on it. Every email-related feature has an in-app fallback.
- Personal settings (theme, zoom, time zone, formats) are stored per person in control.db and apply in every company.
- Do not build: rule-based automation, third-party add-ons, a personal planner or inbox, timeline, calendar or map views, imports from other products, desktop app, Postgres, Docker. Email, API tokens, webhooks and the command line client belong to M6; do not start them earlier.

## Commands
- scripts/ci.sh runs cargo fmt --check, clippy -D warnings, cargo test, web lint and test. Run before every commit.
- cargo run -- serve starts the app on 127.0.0.1.

## Working style
- Small commits, one concern each. Test every permission rule, the sign-in refusal paths and the company-isolation guarantee.
- If the plan is ambiguous, ask the user instead of guessing.
```

### Kickoff prompt

Copy
```
You are building Tazko in this empty repository on an Ubuntu server. The full build plan is attached below this prompt. Create CLAUDE.md from it, then build Milestone M1 (Platform) only.

Summary: one static Rust binary (Axum, rusqlite bundled, tokio) that embeds a React + TypeScript + Tailwind + shadcn/ui web app and a super admin console at /admin. SQLite per company: data/control.db plus data/orgs/<slug>/tazko.db. Google sign-in only, invite-only, for both Workspace and personal accounts. Deployed behind a Cloudflare Tunnel.

Values: hostname tazko-dev.hugepigstudio.com; this machine, 192.168.86.49, is shared with another service, so use port 8791, accounts tazko and tazko-deploy, /opt/tazko, /etc/tazko, /var/lib/tazko, and add a rule to the existing cloudflared tunnel without overwriting its config.yml or breaking the existing hostname. First super admin: trungngo@hugepigstudio.com. Google: a new Google Cloud project named Tazko; the user creates it and gives you the client id and secret by placing them in /etc/tazko/tazko.env. Give them exact steps when you reach that point.

The folder design/ holds the clickable prototype, tokens.css and README.md. The finished product must look and behave like it. For M1, match the prototype screens listed for M1 in the plan (sign in, refusal, company home, company settings, and the admin console pages) and use design/tokens.css for the Tailwind theme. Recreate the screens with real components; do not copy the prototype scripts.

Order of work for M1:
1. Cargo project, web/ app, build step embedding web/dist; commands serve, admin --email, backup, check.
2. control.db and company databases: open, cache, migrate; writer thread and read pool per company.
3. Google OIDC with PKCE, state and nonce, ID token verification, invite-only rule, sessions, refusal page, audit log.
4. Super admin console: companies (create, suspend, resume, delete to trash), company detail (members, roles, invites), people, invites, audit log, server page.
5. Company owner screens for their own company's members and invites; company switcher.
6. deploy/ scripts and units exactly as in the plan's Deployment section: host setup, tunnel rule, service, release with rollback, backup timer; README deploy guide.
7. scripts/ci.sh with tests for isolation between two companies, invite and refusal paths, and permissions.

Clean-room rules, which apply to every file, commit and message: this is an original work. Never name any other product or competitor anywhere in the repository or in commit messages; never copy another product's code, text, icons, colors or assets; do not look at, scrape or reverse engineer other products; work only from this plan. Commits and pull requests must not mention AI or assistants: no Co-Authored-By trailer, no "generated with" line, no session links; set attribution.commit and attribution.pr to empty strings in .claude/settings.json and check your first commit message.

Before any command that changes the machine (sudo, users, systemd, cloudflared), show the user what it will do and wait for approval. When something needs the user (Google console, Cloudflare login, sudo password), stop and ask with exact steps. Stop when every "Done when" check for M1 passes and report what you ran. Do not begin M2.
```

### Next milestone prompt (send once per milestone, M2 to M6)

Copy
```
Build Milestone M2 now (change the number for each milestone). The plan and CLAUDE.md are already in this repository. M1 is done.

Before writing code, open design/tazko-prototype.html in a browser and look at every prototype screen listed for this milestone in "The prototype is the specification" section of the plan. The finished screens must look and behave like the prototype in light and dark themes: layout, spacing, colors, type, icons, wording, empty states, hover and focus states, popovers, toasts with Undo and every shortcut. Use design/tokens.css as the theme. Recreate the screens with real components; do not copy the prototype scripts. If the plan and the prototype disagree, the plan wins on data, permissions and limits and the prototype wins on look and interaction; list every difference for me.

Build every task of the milestone, server and web, with tests for each "Done when" check, including permissions. Run scripts/ci.sh before each commit. Small commits with plain messages; the clean-room and commit rules in CLAUDE.md apply. Stop when every "Done when" check passes. Report what you built, what you ran and what you could not verify, and attach a screenshot of each new screen next to its prototype tile. Do not begin the next milestone.
```

### Full run prompt (after M1 passes)

Copy
```
M1 is done. Build Milestones M2, M3, M4, M5 and M6 in order, one after another, until the product has every feature in the plan and matches the prototype in design/.

For each milestone: open the prototype screens listed for it in the plan, build every task with tests for every "Done when" check (permissions included), run scripts/ci.sh, commit in small steps with plain messages, then write a short milestone report in docs/progress.md (what was built, checks passed, differences from the prototype, anything unverified) and continue to the next milestone without waiting. Follow the clean-room and commit rules in CLAUDE.md throughout.

Stop and ask me only when: a "Done when" check cannot pass, the plan and the prototype disagree in a way that needs my decision, something needs a secret or an account step from me (SMTP details, Google or Cloudflare settings), or a command would change the machine in a way not covered by the plan. At the end, do a pass through every screen in design/ side by side with the running app in light and dark themes, fix the differences, and send me the list of what still differs.
```

## Deferred features to revisit

### Still deferred

- Desktop app (Tauri)

- Production host and cloud deployment

- Vietnamese interface (strings are already in an i18n file)

### Not built, worth a decision

- Export a board or a whole company as a JSON file (fits the data-ownership goal)

- Watching a whole board or list, not only single cards

- Project switches for who can comment or archive cards

- Read-only public board links (leaning against, for privacy)

## Assumptions and open items

Assumed, not confirmed by you:** the web stack (React, Tailwind, shadcn/ui, dnd-kit), company and board role names, that super admins cannot see boards unless they join, invites without email in the first milestones, custom fields in M3, this CLAUDE.md, Ubuntu 24.04 on the server, one program serving as both server and command-line tool, company-wide webhooks (not per project), personal tokens limited to the person's own access, uploaded backgrounds up to 5 MB. Correct any of them and I will update the plan.

### Decided

- Hostname `tazko-dev.hugepigstudio.com`

- Machine `192.168.86.49`, shared, port 8791

- First super admin `trungngo@hugepigstudio.com`

- New Google Cloud project named Tazko, created by the owner

### Evidence behind this plan

- Deployment steps are modelled on a server the owner already runs the same way: a Rust service on loopback behind a Cloudflare Tunnel, own Google sign-in, sandboxed service account, release folders with automatic rollback, nightly backup.

- Feature scope comes from the owner's own use of kanban tools and their stated needs. It describes behavior in generic terms and contains no copied text, assets or code.

- Not yet verified on the server: the tunnel's name and current rules, the installed cloudflared version, and free disk space.
