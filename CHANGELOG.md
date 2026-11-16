# Changelog

What people and API callers can notice, per release. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow `0.MINOR.PATCH` until 1.0 (a milestone bumps MINOR).

## [Unreleased]

### Added
- `tazko admin --email` creates or promotes the first super admin.
- Settings are checked at start: production needs the Google client and https URLs (D16).

### Changed
- Error responses carry a stable `code` and field `details`; validation errors answer 422 and conflicts 409 (D19).
