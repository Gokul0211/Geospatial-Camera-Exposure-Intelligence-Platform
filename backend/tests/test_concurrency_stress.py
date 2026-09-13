"""
test_concurrency_stress.py
===========================
Concurrency and database stress tests:
- High-concurrency ingestion (50 parallel POST requests)
- SQLite connection locking & WAL mode safety under concurrent read/write
"""

import os
import sys
import uuid
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import aiosqlite
from httpx import AsyncClient, ASGITransport
from test_alerts_routes import _init_test_db, _insert_demo_device
from routes import alerts as alerts_module


@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test_stress.db")
    await _init_test_db(db_path)
    return db_path


@pytest_asyncio.fixture
async def app_with_db(test_db):
    patches = [
        patch("config.DATABASE_PATH", test_db),
        patch("services.corroboration_service.DATABASE_PATH", test_db),
        patch("routes.alerts.DATABASE_PATH", test_db),
    ]
    for p in patches:
        p.start()

    from fastapi import FastAPI
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        class DummyManager:
            async def broadcast(self, payload):
                pass

        alerts_module.set_connection_manager(DummyManager())
        yield

    app = FastAPI(lifespan=lifespan)
    app.include_router(alerts_module.router, prefix="/api")

    alerts_module._seen_idempotency_keys.clear()
    alerts_module._camera_request_timestamps.clear()

    yield app

    for p in patches:
        p.stop()


class TestConcurrencyStress:
    @pytest.mark.asyncio
    async def test_50_parallel_detection_events(self, app_with_db, test_db):
        """Simulate 50 unique cameras sending detection events simultaneously."""
        camera_ids = [str(uuid.uuid4()) for _ in range(50)]

        # Pre-seed all 50 devices
        for cam_id in camera_ids:
            await _insert_demo_device(test_db, cam_id)

        # Disable per-camera rate limiting by giving each request a different camera_id
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:

            async def send_event(cid):
                return await client.post(
                    "/api/detection-event",
                    json={
                        "camera_id": cid,
                        "event_type": "loitering",
                        "confidence": 0.85,
                        "idempotency_key": str(uuid.uuid4()),
                    },
                )

            tasks = [send_event(cid) for cid in camera_ids]
            responses = await asyncio.gather(*tasks)

        for res in responses:
            assert res.status_code == 200

        # Verify all 50 alerts were committed to DB
        async with aiosqlite.connect(test_db) as db:
            async with db.execute("SELECT COUNT(*) FROM alerts") as cursor:
                count = (await cursor.fetchone())[0]

        assert count == 50

    @pytest.mark.asyncio
    async def test_concurrent_read_write_sqlite(self, test_db):
        """Perform concurrent reads and writes directly against aiosqlite connection."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id)

        async def writer(i):
            async with aiosqlite.connect(test_db) as db:
                await db.execute(
                    """INSERT INTO alerts (id, camera_id, city, event_type, trust_score, contributing_factors, action_tier)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), cam_id, "Mumbai", "loitering", 70, "[]", "medium_trust"),
                )
                await db.commit()

        async def reader():
            async with aiosqlite.connect(test_db) as db:
                async with db.execute("SELECT COUNT(*) FROM alerts") as cursor:
                    await cursor.fetchone()

        write_tasks = [writer(i) for i in range(25)]
        read_tasks = [reader() for _ in range(25)]

        await asyncio.gather(*write_tasks, *read_tasks)

        async with aiosqlite.connect(test_db) as db:
            async with db.execute("SELECT COUNT(*) FROM alerts") as cursor:
                count = (await cursor.fetchone())[0]

        assert count == 25
