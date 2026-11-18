# Changelog

What people and API callers can notice, per release. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow `0.MINOR.PATCH` until 1.0 (a milestone bumps MINOR).

## [Unreleased]

### Added
- `tazko admin --email` creates or promotes the first super admin.
- Settings are checked at start: production needs the Google client and https URLs (D16).
- Sign in with Google (Workspace or personal accounts) for people who already exist; others are refused and the refusal is audit-logged. Sessions last 30 days from last use; `POST /auth/signout` ends one. `GET /api/me` returns the signed-in person.
- Sign in and Sign-in refused screens; signed-out visitors are sent to sign in, and the header has Sign out.
- Company invites: an invited email can sign in and joins the company. An invite lasts 14 days and works once; expired and revoked invites are refused and the reason is audit-logged.
- Company owners can list members, change a role, remove a person, and list, send and revoke invites through `/api/orgs/{slug}/members` and `/api/orgs/{slug}/invites`. The last owner can never be demoted or removed (409 `LAST_OWNER`). `GET /api/orgs` lists your companies for the switcher.
- Super admin console API under `/admin/api`: companies (list with members, storage and last activity; create), a company's members and invites, and pending invites across companies. Anyone who is not a super admin gets 403.
- Super admin console API, second part: People (search, pages, grant or revoke super admin, disable or re-enable, which signs the person out), Audit log (newest first, by kind), Server page (version, uptime, data size, email status) and Workspace domains (list, remove).
- On an email domain someone has signed in with as a Google Workspace, a personal Google account cannot claim an address of that domain (D26).

### Changed
- Every write (POST, PUT, PATCH, DELETE) from an origin other than `TAZKO_WEB_ORIGIN`, or with no Origin, answers 403 `FORBIDDEN`.
- The audit log and sessions record the visitor's address from `CF-Connecting-IP`. `TAZKO_HOST` must be a loopback address.
- Error responses carry a stable `code` and field `details`; validation errors answer 422 and conflicts 409 (D19).
