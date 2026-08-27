"""
test_corroboration_indepth.py
==============================
In-depth test suite for corroboration_service.py:
- 15-minute temporal window boundary tests (14m59s vs 15m01s)
- Event type isolation (matching event_type only)
- Bidirectional adjacency addition
- Unseeded camera / empty DB edge cases
"""

import os
import sys
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import aiosqlite
from test_alerts_routes import _init_test_db
from services.corroboration_service import (
    check_corroboration,
    get_nearby_cameras,
    add_adjacency,
)


@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test_corroboration.db")
    await _init_test_db(db_path)
    return db_path


class TestCorroborationTimeWindow:
    @pytest.mark.asyncio
    async def test_15_min_window_boundary(self, test_db):
        """Events within 15 mins corroborate; events >15 mins old do NOT."""
        target_cam = "cam_target"
        adj_cam_recent = "cam_recent"
        adj_cam_stale = "cam_stale"

        with patch("services.corroboration_service.DATABASE_PATH", test_db):
            await add_adjacency(target_cam, adj_cam_recent)
            await add_adjacency(target_cam, adj_cam_stale)

            now = datetime.now(timezone.utc)
            recent_time = (now - timedelta(minutes=14, seconds=50)).isoformat()
            stale_time = (now - timedelta(minutes=15, seconds=10)).isoformat()

            async with aiosqlite.connect(test_db) as db:
                await db.execute(
                    """INSERT INTO alerts (id, camera_id, city, event_type, detected_at, trust_score, contributing_factors, action_tier)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), adj_cam_recent, "Mumbai", "loitering", recent_time, 80, "[]", "high_trust"),
                )
                await db.execute(
                    """INSERT INTO alerts (id, camera_id, city, event_type, detected_at, trust_score, contributing_factors, action_tier)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), adj_cam_stale, "Mumbai", "loitering", stale_time, 80, "[]", "high_trust"),
                )
                await db.commit()

            corroborating = await check_corroboration(target_cam, "loitering")

            assert adj_cam_recent in corroborating
            assert adj_cam_stale not in corroborating


class TestEventTypeIsolation:
    @pytest.mark.asyncio
    async def test_event_type_mismatch_ignored(self, test_db):
        """Alert for 'loitering' from adjacent camera does NOT corroborate 'perimeter_breach'."""
        target_cam = "cam_target"
        adj_cam = "cam_adj"

        with patch("services.corroboration_service.DATABASE_PATH", test_db):
            await add_adjacency(target_cam, adj_cam)

            now_iso = datetime.now(timezone.utc).isoformat()
            async with aiosqlite.connect(test_db) as db:
                await db.execute(
                    """INSERT INTO alerts (id, camera_id, city, event_type, detected_at, trust_score, contributing_factors, action_tier)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), adj_cam, "Mumbai", "loitering", now_iso, 80, "[]", "high_trust"),
                )
                await db.commit()

            corroborating = await check_corroboration(target_cam, "perimeter_breach")
            assert len(corroborating) == 0


class TestAdjacencyManagement:
    @pytest.mark.asyncio
    async def test_bidirectional_adjacency(self, test_db):
        cam_a = "cam_a"
        cam_b = "cam_b"

        with patch("services.corroboration_service.DATABASE_PATH", test_db):
            await add_adjacency(cam_a, cam_b)

            nearby_a = await get_nearby_cameras(cam_a)
            nearby_b = await get_nearby_cameras(cam_b)

            assert cam_b in nearby_a
            assert cam_a in nearby_b

    @pytest.mark.asyncio
    async def test_unseeded_camera_returns_empty(self, test_db):
        with patch("services.corroboration_service.DATABASE_PATH", test_db):
            nearby = await get_nearby_cameras("unknown_cam")
            corroborating = await check_corroboration("unknown_cam", "loitering")

            assert nearby == []
            assert corroborating == []
