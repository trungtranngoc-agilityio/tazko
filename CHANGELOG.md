# Changelog

What people and API callers can notice, per release. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow `0.MINOR.PATCH` until 1.0 (a milestone bumps MINOR).

## [Unreleased]

### Added
- `tazko admin --email` creates or promotes the first super admin.
- Settings are checked at start: production needs the Google client and https URLs (D16).
- Sign in with Google (Workspace or personal accounts) for people who already exist; others are refused and the refusal is audit-logged. Sessions last 30 days from last use; `POST /auth/signout` ends one. `GET /api/me` returns the signed-in person.
- Sign in and Sign-in refused screens; signed-out visitors are sent to sign in, and the header has Sign out.

### Changed
- Error responses carry a stable `code` and field `details`; validation errors answer 422 and conflicts 409 (D19).
