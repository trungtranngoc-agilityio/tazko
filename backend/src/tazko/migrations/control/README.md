# Control database migrations (`data/control.db`)

Files: `NNNN_short_name.sql`, applied in order. The number is the schema version stored in `PRAGMA user_version`.
A migration runs inside one transaction when the database is opened (M1-03), together with the `user_version` bump. The runner adds `BEGIN IMMEDIATE` and `COMMIT` around the file, so a script must not contain `BEGIN`, `COMMIT`, `ROLLBACK`, `VACUUM` or `PRAGMA journal_mode`. Never edit a migration that has shipped; add a new one.

A database whose `user_version` is newer than the newest script is refused, so an older release never runs on a newer schema (roll back by restoring the backup taken before the release).

Tables planned here (build plan, Data model): users, orgs, org_members, invites, sessions, audit_log, user_settings, personal_tokens, device_codes, email_queue.
