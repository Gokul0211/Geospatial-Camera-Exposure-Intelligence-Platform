"""
test_tier2_live_wiring.py
===========================
Tests that Tier-2 (frame-level visual liveness) is genuinely wired end-to-end
through the live `POST /api/detection-event` pipeline, not just available in
isolated unit tests/benchmarks. Before this change, `DetectionEvent` had no
`visual_liveness` field at all and the live pipeline call hardcoded
`visual_liveness=None` — IG-DCTF was Tier-1-only in production regardless of
what `video_pipeline.liveness_detector.FrameLivenessTracker` computed.

This posts real DetectionEvent payloads (with and without `visual_liveness`)
against a live ASGI test app and asserts the response's
`signal_integrity_score` / `integrity_gate_tripped` actually reflect the
Tier-2 value that was sent — proving the field reaches
`compute_ig_dctf_trust_score()`, not just Pydantic validation.
"""

import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
import aiosqlite
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from database import init_db


async def _init_test_db(db_path: str):
    with patch("database.DATABASE_PATH", db_path):
        await init_db()


async def _insert_clean_device(db_path: str, device_id: str):
    """A device with a pristine CVE profile and no raw_data (drift=0 baseline)."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR REPLACE INTO devices
               (id, city, ip, lat, lon, owner_type, auth_required,
                known_cve_count, last_patch_date, manufacturer)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (device_id, "Mumbai", "1.2.3.4", 19.07, 72.87,
             "government", True, 0, "2025-06-01", "Hikvision"),
        )
        await db.commit()


@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test_tier2.db")
    await _init_test_db(db_path)
    return db_path


@pytest_asyncio.fixture
async def app_with_db(test_db):
    patches = [
        patch("config.DATABASE_PATH", test_db),
        patch("services.corroboration_service.DATABASE_PATH", test_db),
        patch("routes.alerts.DATABASE_PATH", test_db),
        patch("services.signal_integrity_service.DATABASE_PATH", test_db),
        patch("services.cold_start_service.DATABASE_PATH", test_db),
    ]
    for p in patches:
        p.start()

    from fastapi import FastAPI
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        from routes.alerts import set_connection_manager

        class DummyManager:
            async def broadcast(self, payload):
                pass

        set_connection_manager(DummyManager())
        yield

    from routes import alerts as alerts_module

    app = FastAPI(lifespan=lifespan)
    app.include_router(alerts_module.router, prefix="/api")

    yield app

    for p in patches:
        p.stop()


class TestTier2LiveWiring:
    @pytest.mark.asyncio
    async def test_omitting_visual_liveness_defaults_to_tier1_only_nominal(self, app_with_db, test_db):
        cam_id = str(uuid.uuid4())
        await _insert_clean_device(test_db, cam_id)

        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            res = await client.post("/api/detection-event", json={
                "camera_id": cam_id, "event_type": "loitering", "confidence": 0.9,
            })

        assert res.status_code == 200
        data = res.json()
        # No raw_data on the device -> Tier-1 drift is 0 -> signal_integrity == 1.0 (Tier-1-only, nominal)
        assert data["signal_integrity_score"] == 1.0
        assert data["gate_status"] == "nominal"
        assert data["integrity_gate_tripped"] is False

    @pytest.mark.asyncio
    async def test_low_visual_liveness_trips_gate_via_live_api(self, app_with_db, test_db):
        """
        A clean-CVE device that WOULD score high_trust on cyber signals alone,
        but a live Tier-2 liveness score of 0.1 (severely frozen/blurred feed)
        sent in the POST body must be enough to trip the gate through the
        real API path — proving visual_liveness reaches compute_ig_dctf_trust_score.
        """
        cam_id = str(uuid.uuid4())
        await _insert_clean_device(test_db, cam_id)

        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            res = await client.post("/api/detection-event", json={
                "camera_id": cam_id, "event_type": "loitering", "confidence": 0.9,
                "visual_liveness": 0.1,
            })

        assert res.status_code == 200
        data = res.json()
        # signal_integrity = (1 - drift=0) * liveness=0.1 = 0.1 < theta_low(0.50)
        assert data["signal_integrity_score"] == 0.1
        assert data["gate_status"] == "hard_gated"
        assert data["integrity_gate_tripped"] is True
        assert data["trust_score"] <= 30
        assert data["action_tier"] == "low_trust"
        assert any("hard_gate_cap_30" in f for f in data["contributing_factors"])

    @pytest.mark.asyncio
    async def test_high_visual_liveness_stays_nominal(self, app_with_db, test_db):
        cam_id = str(uuid.uuid4())
        await _insert_clean_device(test_db, cam_id)

        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            res = await client.post("/api/detection-event", json={
                "camera_id": cam_id, "event_type": "loitering", "confidence": 0.9,
                "visual_liveness": 0.98,
            })

        data = res.json()
        assert data["gate_status"] == "nominal"
        assert data["integrity_gate_tripped"] is False

    @pytest.mark.asyncio
    async def test_visual_liveness_out_of_range_rejected(self, app_with_db, test_db):
        cam_id = str(uuid.uuid4())
        await _insert_clean_device(test_db, cam_id)

        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            res = await client.post("/api/detection-event", json={
                "camera_id": cam_id, "event_type": "loitering", "confidence": 0.9,
                "visual_liveness": 1.5,
            })
        assert res.status_code == 422
