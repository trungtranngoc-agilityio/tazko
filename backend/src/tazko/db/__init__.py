"""SQLite access shared by control.db and every company file.

- `Database` (database.py): one file, one writer thread, a read pool, and
  migrations from tazko/migrations/<schema> tracked by PRAGMA user_version.
- `Tenants` (tenant.py): the cache of open company files under data/orgs/<slug>.

- rank.py: fractional ranks for lists and cards, with rebalance (M2-01).
- snapshot.py: `tazko backup`, `tazko check` and `tazko purge-trash` (M1-08).
"""

from tazko.db.database import Database, MigrationError

__all__ = ["Database", "MigrationError"]
