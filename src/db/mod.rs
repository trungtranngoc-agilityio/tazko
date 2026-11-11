//! Shared SQLite setup used by control.db and every company file.
//!
//! Milestone: M1-03. Empty until then; see docs/milestones/.
//!
//! - TODO: Open with WAL, synchronous=NORMAL, foreign_keys=ON, busy_timeout.
//! - TODO: Run migrations from migrations/control or migrations/tenant by PRAGMA user_version, in one transaction.
//! - TODO: Online backup API helpers for `tazko backup` and integrity_check for `tazko check` (M1-08).
