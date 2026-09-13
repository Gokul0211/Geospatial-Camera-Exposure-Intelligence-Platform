"""
test_attack_simulator.py
==========================
Tests for Module H — the live attack-mode simulator. These exercise the
simulator endpoints against a real temp DB + real in-process pipeline calls
(not mocks) — the whole point of this module is that it drives the ACTUAL
defenses, so the tests verify the same thing a demo click would show.
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


@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test_attack_sim.db")
    await _init_test_db(db_path)
    return db_path


@pytest_asyncio.fixture
async def app_with_db(test_db):
    patches = [
        patch("config.DATABASE_PATH", test_db),
        patch("services.corroboration_service.DATABASE_PATH", test_db),
        patch("routes.alerts.DATABASE_PATH", test_db),
        patch("routes.attack_simulator_router.DATABASE_PATH", test_db),
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
    from routes import attack_simulator_router

    app = FastAPI(lifespan=lifespan)
    app.include_router(alerts_module.router, prefix="/api")
    app.include_router(attack_simulator_router.router, prefix="/api")

    yield app

    for p in patches:
        p.stop()

    # Reset module-level in-memory state so tests don't bleed into each other
    from services.corroboration_service import reset_velocity_tracker
    reset_velocity_tracker()
    from routes.alerts import _seen_idempotency_keys, _camera_request_timestamps
    _seen_idempotency_keys.clear()
    _camera_request_timestamps.clear()


class TestReplayAttackSimulator:
    @pytest.mark.asyncio
    async def test_replay_attack_gets_blocked(self, app_with_db):
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            res = await client.post("/api/simulate/replay-attack")
        assert res.status_code == 200
        data = res.json()
        assert data["defense_triggered"] is True
        assert data["second_attempt"]["status_code"] == 409
        assert data["first_attempt"]["blocked"] is False


class TestTimestampSkewSimulator:
    @pytest.mark.asyncio
    async def test_timestamp_skew_gets_blocked(self, app_with_db):
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            res = await client.post("/api/simulate/timestamp-skew")
        assert res.status_code == 200
        data = res.json()
        assert data["defense_triggered"] is True
        assert data["attempt"]["status_code"] == 400


class TestRateFloodSimulator:
    @pytest.mark.asyncio
    async def test_rate_flood_gets_partially_blocked(self, app_with_db):
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            res = await client.post("/api/simulate/rate-flood")
        assert res.status_code == 200
        data = res.json()
        assert data["defense_triggered"] is True
        assert data["blocked_count"] >= 3
        assert data["allowed_count"] == 10  # MAX_EVENTS_PER_MINUTE


class TestCollusionRingSimulator:
    @pytest.mark.asyncio
    async def test_collusion_ring_detected_via_graph_not_pairwise(self, app_with_db):
        """
        Core claim of the simulator: the ring is caught by the GRAPH detector
        even though no single pairwise edge crosses the pairwise velocity
        threshold — demonstrating the exact blind spot §5.3 targets.
        """
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            res = await client.post("/api/simulate/collusion-ring")
        assert res.status_code == 200
        data = res.json()
        assert data["defense_triggered"] is True
        assert data["pairwise_velocity_tracker_flagged_any_edge"] is False
        assert len(data["graph_collusion_clusters"]) == 1
        cluster = data["graph_collusion_clusters"][0]
        assert cluster["node_count"] == 4
        assert set(cluster["camera_ids"]) == set(data["ring_cameras"])


class TestResetEndpoint:
    @pytest.mark.asyncio
    async def test_reset_clears_simulator_devices(self, app_with_db, test_db):
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            await client.post("/api/simulate/replay-attack")
            reset_res = await client.post("/api/simulate/reset")

        assert reset_res.status_code == 200
        async with aiosqlite.connect(test_db) as db:
            async with db.execute("SELECT COUNT(*) FROM devices WHERE id = 'SIM_ATTACK_SOLO'") as cur:
                count = (await cur.fetchone())[0]
        assert count == 0
