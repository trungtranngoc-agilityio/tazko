"""Shared SQLite setup used by control.db and every company file
(`tenant.py` holds the per-company handle).

Milestone: M1-03. Empty until then; see docs/milestones/.

- TODO: Open with WAL, synchronous=NORMAL, foreign_keys=ON, busy_timeout.
- TODO: Run migrations from tazko/migrations/control or tazko/migrations/tenant by PRAGMA user_version, in one transaction.
- TODO: Online backup API helpers for `tazko backup` and integrity_check for `tazko check` (M1-08).
"""
