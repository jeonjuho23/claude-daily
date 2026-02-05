"""Database migration runner"""

import aiosqlite
from pathlib import Path
from typing import List, Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)


class MigrationRunner:
    """Runs SQL migrations from files in version order"""

    def __init__(self, connection: aiosqlite.Connection, migrations_dir: Path):
        self._conn = connection
        self._migrations_dir = migrations_dir

    async def initialize(self) -> None:
        """Create migration tracking table"""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS _schema_versions (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self._conn.commit()

    async def get_current_version(self) -> int:
        """Get the current schema version"""
        cursor = await self._conn.execute("SELECT MAX(version) FROM _schema_versions")
        row = await cursor.fetchone()
        return row[0] if row and row[0] else 0

    async def run_pending(self) -> List[int]:
        """Run all pending migrations and return applied version numbers"""
        current = await self.get_current_version()
        migrations = self._discover_migrations()
        applied = []

        for version, name, sql in migrations:
            if version > current:
                logger.info("Applying migration", version=version, name=name)
                await self._conn.executescript(sql)
                await self._conn.execute(
                    "INSERT INTO _schema_versions (version, name) VALUES (?, ?)",
                    (version, name),
                )
                await self._conn.commit()
                applied.append(version)

        return applied

    def _discover_migrations(self) -> List[Tuple[int, str, str]]:
        """Discover SQL migration files, sorted by version"""
        migrations = []
        for f in sorted(self._migrations_dir.glob("*.sql")):
            parts = f.stem.split("_", 1)
            version = int(parts[0])
            name = parts[1] if len(parts) > 1 else f.stem
            sql = f.read_text(encoding="utf-8")
            migrations.append((version, name, sql))
        return sorted(migrations, key=lambda x: x[0])
