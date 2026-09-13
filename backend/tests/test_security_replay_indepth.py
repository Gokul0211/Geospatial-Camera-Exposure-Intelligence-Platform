"""
test_security_replay_indepth.py
=================================
In-depth security suite for POST /api/detection-event:
- API key authentication requirement (valid vs invalid vs missing key)
- Idempotency key replay protection (409 Conflict)
- Timestamp freshness validation (>60s skew -> 400 Bad Request)
- Per-camera rate limiting (>10 events/min -> 429 Too Many Requests)
- Cache eviction (_clean_replay_cache)
- Payload metadata injection resistance
"""

import os
import sys
import uuid
import time
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import aiosqlite
from httpx import AsyncClient, ASGITransport
from test_alerts_routes import _init_test_db, _insert_demo_device
from routes import alerts as alerts_module


@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test_security.db")
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

    # Clear internal cache structures before each test run
    alerts_module._seen_idempotency_keys.clear()
    alerts_module._camera_request_timestamps.clear()

    yield app

    for p in patches:
        p.stop()


class TestAPIKeyAuth:
    @pytest.mark.asyncio
    async def test_auth_disabled_when_key_empty(self, app_with_db, test_db):
        """When DETECTION_API_KEY is empty, request succeeds without X-API-Key header."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id)

        with patch("routes.alerts.DETECTION_API_KEY", ""):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_db), base_url="http://test"
            ) as client:
                res = await client.post(
                    "/api/detection-event",
                    json={"camera_id": cam_id, "event_type": "loitering"},
                )
            assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_blocks_missing_or_invalid_key(self, app_with_db, test_db):
        """When DETECTION_API_KEY is set, missing or wrong header yields 403 Forbidden."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id)

        test_key = "secret_test_key_123"
        with patch("routes.alerts.DETECTION_API_KEY", test_key):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_db), base_url="http://test"
            ) as client:
                # Missing header -> 403
                res_missing = await client.post(
                    "/api/detection-event",
                    json={"camera_id": cam_id, "event_type": "loitering"},
                )
                assert res_missing.status_code == 403

                # Invalid header -> 403
                res_invalid = await client.post(
                    "/api/detection-event",
                    json={"camera_id": cam_id, "event_type": "loitering"},
                    headers={"X-API-Key": "wrong_key"},
                )
                assert res_invalid.status_code == 403

                # Valid header -> 200
                res_valid = await client.post(
                    "/api/detection-event",
                    json={"camera_id": cam_id, "event_type": "loitering"},
                    headers={"X-API-Key": test_key},
                )
                assert res_valid.status_code == 200


class TestIdempotencyReplay:
    @pytest.mark.asyncio
    async def test_idempotency_key_prevents_replay(self, app_with_db, test_db):
        """Reusing an idempotency_key triggers 409 Conflict on the second attempt."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id)
        nonce = f"nonce-{uuid.uuid4()}"

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            payload = {
                "camera_id": cam_id,
                "event_type": "loitering",
                "idempotency_key": nonce,
            }

            res1 = await client.post("/api/detection-event", json=payload)
            assert res1.status_code == 200

            res2 = await client.post("/api/detection-event", json=payload)
            assert res2.status_code == 409
            assert "Replay attack blocked" in res2.json()["detail"]


class TestTimestampFreshness:
    @pytest.mark.asyncio
    async def test_stale_timestamp_rejected(self, app_with_db, test_db):
        """Timestamp older than 60 seconds returns 400 Bad Request."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id)

        old_dt = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            res = await client.post(
                "/api/detection-event",
                json={
                    "camera_id": cam_id,
                    "event_type": "loitering",
                    "detected_at": old_dt,
                },
            )
        assert res.status_code == 400
        assert "Clock skew" in res.json()["detail"]

    @pytest.mark.asyncio
    async def test_future_timestamp_rejected(self, app_with_db, test_db):
        """Timestamp >60s in the future returns 400 Bad Request."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id)

        future_dt = (datetime.now(timezone.utc) + timedelta(seconds=120)).isoformat()

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            res = await client.post(
                "/api/detection-event",
                json={
                    "camera_id": cam_id,
                    "event_type": "loitering",
                    "detected_at": future_dt,
                },
            )
        assert res.status_code == 400
        assert "Clock skew" in res.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_timestamp_format(self, app_with_db, test_db):
        """Unparseable timestamp returns 400 Bad Request."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id)

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            res = await client.post(
                "/api/detection-event",
                json={
                    "camera_id": cam_id,
                    "event_type": "loitering",
                    "detected_at": "not-a-valid-date",
                },
            )
        assert res.status_code == 400
        assert "Invalid ISO8601" in res.json()["detail"]


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_per_camera(self, app_with_db, test_db):
        """Camera sending >10 requests in 60s gets 429 Too Many Requests."""
        cam_id = str(uuid.uuid4())
        await _insert_demo_device(test_db, cam_id)

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            payload = {"camera_id": cam_id, "event_type": "loitering"}
            for i in range(10):
                r = await client.post("/api/detection-event", json=payload)
                assert r.status_code == 200, f"Request {i+1} failed"

            # 11th request triggers rate limit
            res11 = await client.post("/api/detection-event", json=payload)
            assert res11.status_code == 429
            assert "Rate limit exceeded" in res11.json()["detail"]


class TestCacheEvictionAndMetadataInjection:
    def test_clean_replay_cache_eviction(self):
        """Test cache eviction helper removes items older than window."""
        now = time.time()

        alerts_module._seen_idempotency_keys.clear()
        alerts_module._camera_request_timestamps.clear()

        # Insert old and new idempotency keys
        alerts_module._seen_idempotency_keys["old_key"] = now - 350
        alerts_module._seen_idempotency_keys["new_key"] = now - 10

        # Insert old and new timestamps
        alerts_module._camera_request_timestamps["cam1"] = [now - 70, now - 10]

        alerts_module._clean_replay_cache(now)

        assert "old_key" not in alerts_module._seen_idempotency_keys
        assert "new_key" in alerts_module._seen_idempotency_keys
        assert alerts_module._camera_request_timestamps["cam1"] == [now - 10]

    @pytest.mark.asyncio
    async def test_metadata_payload_injection_ignored(self, app_with_db, test_db):
        """Spoofed metadata in payload is ignored; trust score comes from DB only."""
        cam_id = str(uuid.uuid4())
        # DB has worst-case fields
        await _insert_demo_device(
            test_db,
            cam_id,
            auth_required=False,
            known_cve_count=5,
            owner_type="unknown",
            last_patch_date="2018-01-01",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            # Attacker POSTs spoofed metadata claiming perfect security
            res = await client.post(
                "/api/detection-event",
                json={
                    "camera_id": cam_id,
                    "event_type": "loitering",
                    "metadata": {
                        "auth_required": True,
                        "known_cve_count": 0,
                        "owner_type": "government",
                        "last_patch_date": "2026-01-01",
                    },
                },
            )

        assert res.status_code == 200
        data = res.json()
        # Trust score must STILL be 0 because DB fields are worst-case
        assert data["trust_score"] == 0
        assert data["action_tier"] == "low_trust"
