# Control database migrations (`data/control.db`)

Files: `NNNN_short_name.sql`, applied in order. The number is the schema version stored in `PRAGMA user_version`.
A migration runs inside one transaction when the database is opened (M1-03). Never edit a migration that has shipped; add a new one.

Tables planned here (build plan, Data model): users, orgs, org_members, invites, sessions, audit_log, user_settings, personal_tokens, device_codes, email_queue.
