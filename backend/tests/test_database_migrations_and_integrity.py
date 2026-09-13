"""
test_database_migrations_and_integrity.py
===========================================
Unit & integration tests for backend/database.py:
- Database table creation & schema integrity
- Idempotent schema migrations (_add_column_if_missing)
- WAL journal mode setting
- Indexes & constraint enforcement
- Connection management helper (get_db)
"""

import os
import sys
import pytest
import pytest_asyncio
import aiosqlite
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import init_db, get_db, _add_column_if_missing


class TestDatabaseIntegrity:
    @pytest.mark.asyncio
    async def test_init_db_creates_all_tables(self, tmp_path):
        db_path = str(tmp_path / "test_init.db")
        with patch("database.DATABASE_PATH", db_path):
            await init_db()

            async with aiosqlite.connect(db_path) as db:
                async with db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ) as cursor:
                    tables = {row[0] for row in await cursor.fetchall()}

            expected_tables = {
                "devices",
                "news_articles",
                "risk_briefs",
                "cities",
                "camera_adjacency",
                "alerts",
            }
            for table in expected_tables:
                assert table in tables, f"Missing table: {table}"

    @pytest.mark.asyncio
    async def test_init_db_idempotency(self, tmp_path):
        db_path = str(tmp_path / "test_idempotent.db")
        with patch("database.DATABASE_PATH", db_path):
            # Run twice to ensure no syntax/already exists errors are thrown
            await init_db()
            await init_db()

            async with aiosqlite.connect(db_path) as db:
                async with db.execute("PRAGMA table_info(devices)") as cursor:
                    cols = {row[1] for row in await cursor.fetchall()}

            assert "auth_required" in cols
            assert "known_cve_count" in cols
            assert "cve_ids" in cols
            assert "last_patch_date" in cols

    @pytest.mark.asyncio
    async def test_add_column_if_missing_helper(self, tmp_path):
        db_path = str(tmp_path / "test_alter.db")
        async with aiosqlite.connect(db_path) as db:
            await db.execute("CREATE TABLE test_tbl (id TEXT PRIMARY KEY)")
            await db.commit()

            # First addition should add column
            await _add_column_if_missing(db, "test_tbl", "new_col", "INTEGER DEFAULT 0")
            async with db.execute("PRAGMA table_info(test_tbl)") as cursor:
                cols = {row[1] for row in await cursor.fetchall()}
            assert "new_col" in cols

            # Second addition should safely no-op
            await _add_column_if_missing(db, "test_tbl", "new_col", "INTEGER DEFAULT 0")

    @pytest.mark.asyncio
    async def test_get_db_connection(self, tmp_path):
        db_path = str(tmp_path / "test_get_db.db")
        with patch("database.DATABASE_PATH", db_path):
            db = await get_db()
            try:
                assert isinstance(db, aiosqlite.Connection)
                async with db.execute("PRAGMA journal_mode") as cursor:
                    mode = await cursor.fetchone()
                    assert mode[0].lower() == "wal"
            finally:
                await db.close()

    @pytest.mark.asyncio
    async def test_camera_adjacency_primary_key_constraint(self, tmp_path):
        db_path = str(tmp_path / "test_adjacency.db")
        with patch("database.DATABASE_PATH", db_path):
            await init_db()
            async with aiosqlite.connect(db_path) as db:
                await db.execute("INSERT INTO camera_adjacency VALUES ('camA', 'camB')")
                await db.commit()

                # Duplicate insert should raise IntegrityError
                with pytest.raises(aiosqlite.IntegrityError):
                    await db.execute("INSERT INTO camera_adjacency VALUES ('camA', 'camB')")
                    await db.commit()
