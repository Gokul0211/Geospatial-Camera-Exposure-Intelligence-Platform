"""
test_alerts_routes.py
======================
Phase 2 integration tests for routes/alerts.py.

Full round-trip: POST /api/detection-event → GET /api/alerts
Uses a real temp SQLite DB + FastAPI TestClient (httpx).

Run with: pytest backend/tests/test_alerts_routes.py -v
"""

import sys
import os
import json
import uuid
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import aiosqlite
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Shared DB schema (must match database.py exactly)
# ---------------------------------------------------------------------------

async def _init_test_db(db_path: str):
    """Create tables needed for alerts route integration tests."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                city TEXT NOT NULL,
                ip TEXT NOT NULL,
                lat REAL, lon REAL,
                device_type TEXT,
                manufacturer TEXT,
                ports TEXT,
                owner_org TEXT,
                owner_type TEXT,
                ownership_confidence TEXT,
                first_seen TEXT, last_seen TEXT,
                banner_snippet TEXT, raw_data TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                firmware_version TEXT,
                auth_required BOOLEAN,
                known_cve_count INTEGER DEFAULT 0,
                cve_ids TEXT,
                last_patch_date TEXT,
                vuln_last_checked TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS camera_adjacency (
                camera_id TEXT NOT NULL,
                nearby_camera_id TEXT NOT NULL,
                PRIMARY KEY (camera_id, nearby_camera_id)
            )
        """)
        await db.execute("""
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
        """)
        await db.commit()


async def _insert_demo_device(db_path: str, device_id: str, city: str = "Mumbai",
                               auth_required=False, known_cve_count=2,
                               owner_type="unknown", last_patch_date="2018-01-01"):
    """Insert a device row with Phase 1 fields populated for testing."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR REPLACE INTO devices
               (id, city, ip, lat, lon, owner_type, auth_required,
                known_cve_count, last_patch_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (device_id, city, "1.2.3.4", 19.07, 72.87,
             owner_type, auth_required, known_cve_count, last_patch_date),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test_alerts.db")
    await _init_test_db(db_path)
    return db_path


@pytest_asyncio.fixture
async def app_with_db(test_db):
    """
    Return a FastAPI test app with DATABASE_PATH patched to our temp DB.
    Also sets up a dummy ConnectionManager so broadcast doesn't fail.
    """
    patches = [
        patch("config.DATABASE_PATH", test_db),
        patch("services.trust_score_service.__name__", "services.trust_score_service"),
        patch("services.corroboration_service.DATABASE_PATH", test_db),
        patch("routes.alerts.DATABASE_PATH", test_db),
    ]
    for p in patches:
        p.start()

    # Build a minimal app with just the alerts router
    from fastapi import FastAPI
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        from routes.alerts import set_connection_manager

        class DummyManager:
            async def broadcast(self, payload):
                pass  # no-op in tests

        set_connection_manager(DummyManager())
        yield

    from fastapi import FastAPI
    from routes import alerts as alerts_module

    app = FastAPI(lifespan=lifespan)
    app.include_router(alerts_module.router, prefix="/api")

    yield app

    for p in patches:
        p.stop()


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestDetectionEventEndpoint:
    @pytest.mark.asyncio
    async def test_404_for_unknown_camera(self, app_with_db):
        """POST with a camera_id that doesn't exist → 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            res = await client.post("/api/detection-event", json={
                "camera_id": "nonexistent-id",
                "event_type": "loitering",
                "confidence": 0.9,
            })
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_successful_event_returns_trust_score(self, app_with_db, test_db):
        """POST with a seeded device → 200 with trust score fields."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id, auth_required=False,
                                   known_cve_count=3, owner_type="unknown",
                                   last_patch_date="2018-01-01")

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            res = await client.post("/api/detection-event", json={
                "camera_id": cam_id,
                "event_type": "loitering",
                "confidence": 0.85,
            })

        assert res.status_code == 200
        data = res.json()
        assert "trust_score" in data
        assert "action_tier" in data
        assert "contributing_factors" in data
        assert "alert_id" in data
        assert isinstance(data["trust_score"], int)
        assert 0 <= data["trust_score"] <= 100

    @pytest.mark.asyncio
    async def test_worst_case_device_gets_low_trust(self, app_with_db, test_db):
        """A device with all bad signals → low_trust tier."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id, auth_required=False,
                                   known_cve_count=5, owner_type="unknown",
                                   last_patch_date="2018-01-01")

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            res = await client.post("/api/detection-event", json={
                "camera_id": cam_id,
                "event_type": "perimeter_breach",
                "confidence": 0.95,
            })

        data = res.json()
        assert data["action_tier"] == "low_trust"
        assert data["trust_score"] == 0

    @pytest.mark.asyncio
    async def test_alert_is_persisted_to_db(self, app_with_db, test_db):
        """After POST, the alert row should exist in the DB."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id)

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            res = await client.post("/api/detection-event", json={
                "camera_id": cam_id,
                "event_type": "loitering",
                "confidence": 0.7,
            })

        alert_id = res.json()["alert_id"]

        async with aiosqlite.connect(test_db) as db:
            async with db.execute(
                "SELECT id FROM alerts WHERE id = ?", (alert_id,)
            ) as cursor:
                row = await cursor.fetchone()

        assert row is not None, "Alert was not persisted to DB"


class TestGetAlertsEndpoint:
    @pytest.mark.asyncio
    async def test_empty_alerts_returns_empty_list(self, app_with_db):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            res = await client.get("/api/alerts")
        assert res.status_code == 200
        data = res.json()
        assert data["alerts"] == []
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_get_alerts_after_post(self, app_with_db, test_db):
        """After posting an event, GET /api/alerts should return it."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id, city="Delhi")

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            await client.post("/api/detection-event", json={
                "camera_id": cam_id,
                "event_type": "loitering",
                "confidence": 0.8,
            })
            res = await client.get("/api/alerts")

        data = res.json()
        assert data["count"] == 1
        assert data["alerts"][0]["camera_id"] == cam_id

    @pytest.mark.asyncio
    async def test_get_alerts_city_filter(self, app_with_db, test_db):
        """GET /api/alerts?city= should only return alerts for that city."""
        cam_mumbai = str(uuid.uuid4())
        cam_delhi = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_mumbai, city="Mumbai")
        await _insert_demo_device(test_db, cam_delhi, city="Delhi")

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            for cam_id in [cam_mumbai, cam_delhi]:
                await client.post("/api/detection-event", json={
                    "camera_id": cam_id,
                    "event_type": "loitering",
                    "confidence": 0.8,
                })
            res = await client.get("/api/alerts?city=Mumbai")

        data = res.json()
        assert data["count"] == 1
        assert data["alerts"][0]["city"] == "Mumbai"

    @pytest.mark.asyncio
    async def test_contributing_factors_are_list(self, app_with_db, test_db):
        """contributing_factors in GET response should be a list, not a JSON string."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id)

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            await client.post("/api/detection-event", json={
                "camera_id": cam_id, "event_type": "loitering", "confidence": 0.5,
            })
            res = await client.get("/api/alerts")

        alert = res.json()["alerts"][0]
        assert isinstance(alert["contributing_factors"], list)
        assert isinstance(alert["corroborated_by"], list)
