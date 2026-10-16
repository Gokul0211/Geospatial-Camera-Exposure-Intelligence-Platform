"""
test_alert_timeline_and_demo_flag.py
====================================
Regression tests for two fixes made while wiring the Next.js console to this backend:

1. GET /api/analytics/alert-timeline used to build its buckets from `now - hours` with the minutes still
   attached, so the CURRENT hour fell outside the window and the newest alerts never appeared.
2. Alerts produced by the attack simulator or the demo scenario runner are flagged `is_demo` in the
   database (not only in the WebSocket payload), so a client can keep labelling them after a reload.

Uses a temp SQLite DB; never touches data/surveillancewatch.db.
"""
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import aiosqlite
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import init_db  # noqa: E402


@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "timeline.db")
    with patch("database.DATABASE_PATH", db_path):
        await init_db()
    return db_path


async def _insert_alert(db_path: str, detected_at: datetime, tier: str = "low_trust") -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO alerts (id, camera_id, city, event_type, detected_at, trust_score,
                                   contributing_factors, corroborated_by, action_tier)
               VALUES (?, 'cam', 'Mumbai', 'loitering', ?, 40, '[]', '[]', ?)""",
            (str(uuid.uuid4()), detected_at.isoformat(), tier),
        )
        await db.commit()


@pytest.mark.asyncio
async def test_timeline_includes_the_current_hour(test_db):
    now = datetime.now(timezone.utc)
    await _insert_alert(test_db, now)                         # this very hour
    await _insert_alert(test_db, now - timedelta(hours=3))    # three hours ago
    with patch("routes.analytics_router.DATABASE_PATH", test_db):
        from routes.analytics_router import get_alert_timeline

        res = await get_alert_timeline(hours=24, city=None)

    buckets = res["timeline"]
    assert len(buckets) == 24
    assert buckets[-1]["hour"] == now.strftime("%H:00")       # the window ends with the current hour
    assert buckets[-1]["count"] == 1                          # the alert that used to be dropped
    assert sum(b["count"] for b in buckets) == 2
    assert res["total_alerts"] == 2


@pytest.mark.asyncio
async def test_timeline_excludes_alerts_older_than_the_window(test_db):
    now = datetime.now(timezone.utc)
    await _insert_alert(test_db, now - timedelta(hours=30))
    with patch("routes.analytics_router.DATABASE_PATH", test_db):
        from routes.analytics_router import get_alert_timeline

        res = await get_alert_timeline(hours=24, city=None)
    assert sum(b["count"] for b in res["timeline"]) == 0


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

    from routes import alerts as alerts_module

    @asynccontextmanager
    async def lifespan(app):
        class DummyManager:
            async def broadcast(self, payload):
                pass

        alerts_module.set_connection_manager(DummyManager())
        yield

    app = FastAPI(lifespan=lifespan)
    app.include_router(alerts_module.router, prefix="/api")
    yield app
    for p in patches:
        p.stop()


async def _post_event(client: AsyncClient, camera_id: str) -> None:
    res = await client.post(
        "/api/detection-event",
        json={"camera_id": camera_id, "event_type": "loitering", "idempotency_key": str(uuid.uuid4())},
    )
    assert res.status_code == 200, res.text


@pytest.mark.asyncio
async def test_is_demo_is_persisted_and_returned(app_with_db, test_db):
    from routes.alerts import DEMO_MODE

    async with aiosqlite.connect(test_db) as db:
        await db.execute(
            "INSERT INTO devices (id, city, ip, lat, lon, owner_type, auth_required, known_cve_count) "
            "VALUES ('real-cam', 'Mumbai', '203.0.113.7', 19.07, 72.87, 'unknown', 0, 0)"
        )
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
        await _post_event(client, "real-cam")                  # a normal event: not demo
        token = DEMO_MODE.set(True)
        try:
            await _post_event(client, "real-cam")              # same pipeline, flagged as demo traffic
        finally:
            DEMO_MODE.reset(token)
        alerts = (await client.get("/api/alerts?limit=10")).json()["alerts"]

    flags = sorted(a["is_demo"] for a in alerts)
    assert flags == [0, 1]
