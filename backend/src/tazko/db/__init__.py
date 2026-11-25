"""SQLite access for control.db and every company file: `Database` (one file)
and `Tenants` (the open company files)."""

from tazko.db.database import Database, MigrationError

__all__ = ["Database", "MigrationError"]
