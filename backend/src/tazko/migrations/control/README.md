# Control database migrations (`data/control.db`)

Files: `NNNN_short_name.sql`, applied in order. The number is the schema version stored in `PRAGMA user_version`.
A migration runs inside one transaction when the database is opened (M1-03), together with the `user_version` bump. The runner adds `BEGIN IMMEDIATE` and `COMMIT` around the file, so a script must not contain `BEGIN`, `COMMIT`, `ROLLBACK`, `VACUUM` or `PRAGMA journal_mode`. Never edit a migration that has shipped; add a new one.

A release may run on a file that a newer release migrated only if every newer migration allows it (D21, D36). A migration that leaves the file usable by an older release (it only adds: a table, a nullable column, an index) starts with `-- readers: N`, where N is the newest migration of the oldest release that can still use the file. Without the line, only releases that have the migration can open the file. The runner stores the oldest allowed release in `PRAGMA application_id` with `user_version`; an older release that is not allowed refuses the file, and rolling back then means restoring the backup taken before the release.

Tables planned here (build plan, Data model): users, orgs, org_members, invites, sessions, audit_log, workspace_domains (D26), user_settings, personal_tokens, device_codes, email_queue.
