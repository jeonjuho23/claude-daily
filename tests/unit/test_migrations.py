"""Tests for database migration system"""

import asyncio
import tempfile
from pathlib import Path

import aiosqlite
import pytest

from src.storage.migrations.runner import MigrationRunner


class TestMigrationRunner:
    """Test suite for MigrationRunner"""

    @pytest.fixture
    async def db_connection(self, tmp_path):
        """Create a temporary database connection"""
        db_path = tmp_path / "test_migrations.db"
        conn = await aiosqlite.connect(str(db_path))
        conn.row_factory = aiosqlite.Row
        yield conn
        await conn.close()

    @pytest.fixture
    def migrations_dir(self, tmp_path):
        """Create a temporary migrations directory"""
        mig_dir = tmp_path / "migrations"
        mig_dir.mkdir()
        return mig_dir

    @pytest.mark.asyncio
    async def test_initialize_creates_tracking_table(self, db_connection, migrations_dir):
        """Initialize should create _schema_versions table"""
        runner = MigrationRunner(db_connection, migrations_dir)
        await runner.initialize()

        cursor = await db_connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_schema_versions'"
        )
        row = await cursor.fetchone()
        assert row is not None

    @pytest.mark.asyncio
    async def test_get_current_version_empty_db(self, db_connection, migrations_dir):
        """Empty DB should return version 0"""
        runner = MigrationRunner(db_connection, migrations_dir)
        await runner.initialize()

        version = await runner.get_current_version()
        assert version == 0

    @pytest.mark.asyncio
    async def test_get_current_version_after_apply(self, db_connection, migrations_dir):
        """After applying migration, version should update"""
        (migrations_dir / "001_test.sql").write_text(
            "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY);",
            encoding="utf-8",
        )
        runner = MigrationRunner(db_connection, migrations_dir)
        await runner.initialize()
        await runner.run_pending()

        version = await runner.get_current_version()
        assert version == 1

    @pytest.mark.asyncio
    async def test_run_pending_applies_all(self, db_connection, migrations_dir):
        """All pending migrations should be applied"""
        (migrations_dir / "001_first.sql").write_text(
            "CREATE TABLE IF NOT EXISTS first_table (id INTEGER PRIMARY KEY);",
            encoding="utf-8",
        )
        (migrations_dir / "002_second.sql").write_text(
            "CREATE TABLE IF NOT EXISTS second_table (id INTEGER PRIMARY KEY);",
            encoding="utf-8",
        )
        runner = MigrationRunner(db_connection, migrations_dir)
        await runner.initialize()

        applied = await runner.run_pending()
        assert applied == [1, 2]

    @pytest.mark.asyncio
    async def test_run_pending_skips_applied(self, db_connection, migrations_dir):
        """Already applied migrations should be skipped"""
        (migrations_dir / "001_first.sql").write_text(
            "CREATE TABLE IF NOT EXISTS first_table (id INTEGER PRIMARY KEY);",
            encoding="utf-8",
        )
        runner = MigrationRunner(db_connection, migrations_dir)
        await runner.initialize()

        # Apply first time
        applied1 = await runner.run_pending()
        assert applied1 == [1]

        # Add second migration
        (migrations_dir / "002_second.sql").write_text(
            "CREATE TABLE IF NOT EXISTS second_table (id INTEGER PRIMARY KEY);",
            encoding="utf-8",
        )

        # Should only apply the new one
        applied2 = await runner.run_pending()
        assert applied2 == [2]

    @pytest.mark.asyncio
    async def test_discover_migrations_sorted(self, db_connection, migrations_dir):
        """Migrations should be sorted by version number"""
        (migrations_dir / "003_third.sql").write_text("SELECT 1;", encoding="utf-8")
        (migrations_dir / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")
        (migrations_dir / "002_second.sql").write_text("SELECT 1;", encoding="utf-8")

        runner = MigrationRunner(db_connection, migrations_dir)
        migrations = runner._discover_migrations()

        versions = [m[0] for m in migrations]
        assert versions == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_idempotent_on_existing_db(self, db_connection, migrations_dir):
        """Running migrations on existing DB should be safe"""
        (migrations_dir / "001_initial.sql").write_text(
            "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY);",
            encoding="utf-8",
        )
        runner = MigrationRunner(db_connection, migrations_dir)
        await runner.initialize()

        # Run twice
        applied1 = await runner.run_pending()
        applied2 = await runner.run_pending()

        assert applied1 == [1]
        assert applied2 == []  # Nothing to apply

    @pytest.mark.asyncio
    async def test_multiple_migrations_sequential(self, db_connection, migrations_dir):
        """Multiple migrations should apply in sequence"""
        (migrations_dir / "001_create.sql").write_text(
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT);",
            encoding="utf-8",
        )
        (migrations_dir / "002_add_index.sql").write_text(
            "CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);",
            encoding="utf-8",
        )

        runner = MigrationRunner(db_connection, migrations_dir)
        await runner.initialize()
        applied = await runner.run_pending()

        assert applied == [1, 2]
        version = await runner.get_current_version()
        assert version == 2
