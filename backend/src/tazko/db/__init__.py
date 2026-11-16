"""SQLite access shared by control.db and every company file.

- `Database` (database.py): one file, one writer thread, a read pool, and
  migrations from tazko/migrations/<schema> tracked by PRAGMA user_version.
- `Tenants` (tenant.py): the cache of open company files under data/orgs/<slug>.

TODO(M1-08): online backup helpers for `tazko backup` and integrity_check for `tazko check`.
"""

from tazko.db.database import Database, MigrationError

__all__ = ["Database", "MigrationError"]
