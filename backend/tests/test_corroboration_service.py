"""
test_corroboration_service.py
==============================
Phase 2 unit tests for corroboration_service.py.

Uses an in-memory SQLite DB so no real DB file is touched.
Run with: pytest backend/tests/test_corroboration_service.py -v
"""

import sys
import os
import json
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# We mock DATABASE_PATH to point at an in-memory DB per test
import aiosqlite
import asyncio


# ---------------------------------------------------------------------------
# Helpers to build an in-memory DB and inject rows
# ---------------------------------------------------------------------------

CREATE_ADJACENCY = """
CREATE TABLE IF NOT EXISTS camera_adjacency (
    camera_id TEXT NOT NULL,
    nearby_camera_id TEXT NOT NULL,
    PRIMARY KEY (camera_id, nearby_camera_id)
)
"""

CREATE_ALERTS = """
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    camera_id TEXT NOT NULL,
    city TEXT,
    event_type TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trust_score INTEGER NOT NULL,
    contributing_factors TEXT NOT NULL,
    corroborated_by TEXT,
    action_tier TEXT NOT NULL
)
"""


async def _make_db():
    """Open a fresh in-memory aiosqlite DB with the required schema."""
    db = await aiosqlite.connect(":memory:")
    await db.execute(CREATE_ADJACENCY)
    await db.execute(CREATE_ALERTS)
    await db.commit()
    return db


async def _insert_adjacency(db, cam_a, cam_b):
    await db.execute(
        "INSERT OR IGNORE INTO camera_adjacency VALUES (?, ?)", (cam_a, cam_b)
    )
    await db.execute(
        "INSERT OR IGNORE INTO camera_adjacency VALUES (?, ?)", (cam_b, cam_a)
    )
    await db.commit()


async def _insert_alert(db, camera_id, event_type, detected_at):
    await db.execute(
        "INSERT INTO alerts (id, camera_id, event_type, detected_at, trust_score, "
        "contributing_factors, action_tier) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), camera_id, event_type, detected_at, 50, "[]", "medium_trust"),
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Fixture: patch DATABASE_PATH so corroboration_service uses our in-memory DB
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


# We can't easily share a single in-memory connection across imports because
# aiosqlite.connect(":memory:") creates a new DB each time. Instead, we patch
# the DATABASE_PATH to a temp file path and clean up after each test.

import tempfile


@pytest_asyncio.fixture
async def tmp_db(tmp_path):
    """Create a temp SQLite file, initialise schema, yield the path."""
    db_path = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(CREATE_ADJACENCY)
        await db.execute(CREATE_ALERTS)
        await db.commit()
    return db_path


# ---------------------------------------------------------------------------
# Tests — patching corroboration_service.DATABASE_PATH
# ---------------------------------------------------------------------------

class TestGetNearbyCamera:
    @pytest.mark.asyncio
    async def test_no_adjacency_returns_empty(self, tmp_db):
        with patch("services.corroboration_service.DATABASE_PATH", tmp_db):
            from services.corroboration_service import get_nearby_cameras
            result = await get_nearby_cameras("cam_unknown")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_adjacent_cameras(self, tmp_db):
        async with aiosqlite.connect(tmp_db) as db:
            await _insert_adjacency(db, "cam_a", "cam_b")
            await _insert_adjacency(db, "cam_a", "cam_c")

        with patch("services.corroboration_service.DATABASE_PATH", tmp_db):
            from services.corroboration_service import get_nearby_cameras
            result = await get_nearby_cameras("cam_a")

        assert set(result) == {"cam_b", "cam_c"}

    @pytest.mark.asyncio
    async def test_adjacency_is_bidirectional(self, tmp_db):
        """Inserting A→B should mean B can also find A."""
        async with aiosqlite.connect(tmp_db) as db:
            await _insert_adjacency(db, "cam_a", "cam_b")

        with patch("services.corroboration_service.DATABASE_PATH", tmp_db):
            from services.corroboration_service import get_nearby_cameras
            result = await get_nearby_cameras("cam_b")

        assert "cam_a" in result


class TestCheckCorroboration:
    @pytest.mark.asyncio
    async def test_no_adjacent_cameras_returns_empty(self, tmp_db):
        with patch("services.corroboration_service.DATABASE_PATH", tmp_db):
            from services.corroboration_service import check_corroboration
            result = await check_corroboration("cam_a", "loitering")
        assert result == []

    @pytest.mark.asyncio
    async def test_adjacent_camera_with_recent_same_event_corroborates(self, tmp_db):
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        async with aiosqlite.connect(tmp_db) as db:
            await _insert_adjacency(db, "cam_a", "cam_b")
            await _insert_alert(db, "cam_b", "loitering", recent)

        with patch("services.corroboration_service.DATABASE_PATH", tmp_db):
            from services.corroboration_service import check_corroboration
            result = await check_corroboration("cam_a", "loitering")

        assert "cam_b" in result

    @pytest.mark.asyncio
    async def test_old_alert_outside_window_does_not_corroborate(self, tmp_db):
        """Alert older than the window (default 15 min) should not count."""
        old = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
        async with aiosqlite.connect(tmp_db) as db:
            await _insert_adjacency(db, "cam_a", "cam_b")
            await _insert_alert(db, "cam_b", "loitering", old)

        with patch("services.corroboration_service.DATABASE_PATH", tmp_db):
            from services.corroboration_service import check_corroboration
            result = await check_corroboration("cam_a", "loitering")

        assert result == []

    @pytest.mark.asyncio
    async def test_different_event_type_does_not_corroborate(self, tmp_db):
        """'perimeter_breach' from neighbor does NOT corroborate a 'loitering' event."""
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        async with aiosqlite.connect(tmp_db) as db:
            await _insert_adjacency(db, "cam_a", "cam_b")
            await _insert_alert(db, "cam_b", "perimeter_breach", recent)

        with patch("services.corroboration_service.DATABASE_PATH", tmp_db):
            from services.corroboration_service import check_corroboration
            result = await check_corroboration("cam_a", "loitering")

        assert result == []

    @pytest.mark.asyncio
    async def test_custom_window_minutes_respected(self, tmp_db):
        """Alert at 20 min ago is inside a 30-min custom window."""
        somewhat_old = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
        async with aiosqlite.connect(tmp_db) as db:
            await _insert_adjacency(db, "cam_a", "cam_b")
            await _insert_alert(db, "cam_b", "loitering", somewhat_old)

        with patch("services.corroboration_service.DATABASE_PATH", tmp_db):
            from services.corroboration_service import check_corroboration
            result = await check_corroboration("cam_a", "loitering", window_minutes=30)

        assert "cam_b" in result

    @pytest.mark.asyncio
    async def test_multiple_corroborators(self, tmp_db):
        """Two adjacent cameras both fire within window → both returned."""
        recent = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
        async with aiosqlite.connect(tmp_db) as db:
            await _insert_adjacency(db, "cam_a", "cam_b")
            await _insert_adjacency(db, "cam_a", "cam_c")
            await _insert_alert(db, "cam_b", "loitering", recent)
            await _insert_alert(db, "cam_c", "loitering", recent)

        with patch("services.corroboration_service.DATABASE_PATH", tmp_db):
            from services.corroboration_service import check_corroboration
            result = await check_corroboration("cam_a", "loitering")

        assert set(result) == {"cam_b", "cam_c"}

    @pytest.mark.asyncio
    async def test_camera_does_not_corroborate_itself(self, tmp_db):
        """A camera should not be in its own adjacency list."""
        recent = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
        async with aiosqlite.connect(tmp_db) as db:
            # No self-adjacency inserted — this verifies the query doesn't return self
            await _insert_alert(db, "cam_a", "loitering", recent)

        with patch("services.corroboration_service.DATABASE_PATH", tmp_db):
            from services.corroboration_service import check_corroboration
            result = await check_corroboration("cam_a", "loitering")

        assert "cam_a" not in result
