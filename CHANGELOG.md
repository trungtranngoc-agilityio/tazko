# Changelog

What people and API callers can notice, per release. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow `0.MINOR.PATCH` until 1.0 (a milestone bumps MINOR).

## [Unreleased]

### Added
- Your projects shows your Starred boards above the projects.
- A project opens on its Boards tab: starred boards apart, every board as a tile with its open lists and cards, Create board (title and background), stars, and closed boards with Reopen.
- Boards add `lists` and `cards` (the open lists and the open cards on them); `GET /api/orgs/{slug}/starred-boards` lists the open boards you starred and may still open, across your projects.
- Lists and cards on a board under `/api/orgs/{slug}/projects/{id}/boards/{board_id}`: `GET .../lists` returns the open lists in order with their open cards; add, rename, archive and restore lists and cards; move a list (`PUT .../lists/{id}/position`) or a card within or across the board's lists (`PUT .../cards/{id}/position`). Observers only read; a closed board takes no changes (409 `BOARD_CLOSED`); nothing goes into an archived list (409 `LIST_ARCHIVED`) and an archived card is restored before it moves (409 `CARD_ARCHIVED`). A board holds at most 200 open lists and 5000 open cards (409 `TOO_MANY_LISTS`, `TOO_MANY_CARDS`).
- Project screens: Your projects (your projects with their people, boards and your role), Manage projects for company owners (create, choose owners, archive, restore, delete), and each project's Members (invite, roles, pending invites) and Settings (name, description, colour, default board background, member switches, card aging). `GET /api/orgs/{slug}/projects` adds `members`, `people` and `boards`; a project's members add `account` and `last_seen_at`.
- Project invites under `/api/orgs/{slug}/projects/{id}/invites`: invite an email as owner, member or observer, list pending invites and revoke one. Someone not yet in the company joins it as a plain member when they sign in and sees only that project; someone already in it gets the project at their next request. Removing a person from the company or the project revokes their unused invites; an invite whose maker may no longer invite is revoked when used. At most 500 pending invites per project (409 `TOO_MANY_INVITES`).
- Boards in a project under `/api/orgs/{slug}/projects/{id}/boards`: create, rename, change background, close and reopen; project owners restrict a board to chosen project members, and a restricted board is hidden (404) from everyone else; personal stars (`PUT`/`DELETE .../star`). A company owner opens a project's boards only once in the project (403 `NOT_IN_PROJECT`).
- Projects API under `/api/orgs/{slug}/projects`: company owners create, rename, archive, restore and delete projects and manage their owners (`?view=manage` lists every project); project owners change settings and members; members and observers read; people see only their projects. The last project owner is kept (409 `LAST_OWNER`); removing someone takes them off assignees, watchers and restricted boards.
- Deploy scripts (deploy/): host setup, tunnel rule, release bundle, `tazko-release` with a pre-release snapshot, health check and automatic rollback (restoring the snapshot when the older release cannot use migrated data), nightly backup with trash cleanup and an optional off-machine copy, and the Pages deploy.
- `tazko backup` writes a dated snapshot of every database, the company files and the secret while the server runs, keeping 30 days; `tazko check` verifies a data folder or snapshot; `tazko purge-trash` removes deleted companies after 30 days in trash.
- A migration can mark itself usable by the previous release (`-- readers: N`), so a rollback does not always need a restore.
- Super admins can suspend, resume and delete a company on Company detail (`POST /admin/api/companies/{slug}/suspend` and `/resume`, `DELETE /admin/api/companies/{slug}` with the short name typed). Suspending blocks its members at once; a member whose companies are all suspended is refused at sign-in and told why. Delete moves the company folder to `data/trash/` for 30 days. `GET /auth/refusal` adds `reason`.
- `tazko admin --email` creates or promotes the first super admin.
- Settings are checked at start: production needs the Google client and https URLs (D16).
- Sign in with Google (Workspace or personal accounts) for people who already exist; others are refused and the refusal is audit-logged. Sessions last 30 days from last use; `POST /auth/signout` ends one. `GET /api/me` returns the signed-in person.
- Sign in and Sign-in refused screens; signed-out visitors are sent to sign in, and the header has Sign out.
- Company invites: an invited email can sign in and joins the company. An invite lasts 14 days and works once; expired and revoked invites are refused and the reason is audit-logged.
- Company owners can list members, change a role, remove a person, and list, send and revoke invites through `/api/orgs/{slug}/members` and `/api/orgs/{slug}/invites`. The last owner can never be demoted or removed (409 `LAST_OWNER`). `GET /api/orgs` lists your companies for the switcher.
- Super admin console API under `/admin/api`: companies (list with members, storage and last activity; create), a company's members and invites, and pending invites across companies. Anyone who is not a super admin gets 403.
- Super admin console API, second part: People (search, pages, grant or revoke super admin, disable or re-enable, which signs the person out), Audit log (newest first, by kind), Server page (version, uptime, data size, email status) and Workspace domains (list, remove).
- Company screens: a sidebar with the company switcher, the Projects empty state, and Company settings for owners (invite someone, members with role and Remove, pending invites with Revoke). `/` opens your first company.
- Super admin console screens at `/admin`: a sidebar, Companies (with New company, which invites the first owner) and Company detail (members and invites, read-only while the company is suspended).
- Console screens: People (search, super admin and active switches), Invites across companies, and the Audit log (filter by kind).
- Console screen: Server (version, uptime, data size, email) and Workspace domains with Forget.
- On an email domain someone has signed in with as a Google Workspace, a personal Google account cannot claim an address of that domain (D26).

### Changed
- Sidebars and buttons show the prototype's icons, and avatars take one of five colours from the name, as in the prototype.
- The soft accent colour (selected sidebar item, Workspace badges) follows the prototype in light and dark; in dark mode it was a pale block with hard-to-read text (D33).
- Every write (POST, PUT, PATCH, DELETE) from an origin other than `TAZKO_WEB_ORIGIN`, or with no Origin, answers 403 `FORBIDDEN`.
- The audit log and sessions record the visitor's address from `CF-Connecting-IP`. `TAZKO_HOST` must be a loopback address.
- Error responses carry a stable `code` and field `details`; validation errors answer 422 and conflicts 409 (D19).
