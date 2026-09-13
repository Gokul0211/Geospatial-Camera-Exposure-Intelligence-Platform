"""
test_velocity_and_anchoring.py
==============================
Unit and integration tests for:
1. Corroboration Velocity Tracker (rolling window, threshold trigger, get_velocity_alerts).
2. External Audit Anchoring Endpoint (GET /api/audit/anchor).
3. Corroboration Velocity Endpoint (GET /api/audit/velocity).
4. Protected Verdict Labelling (X-API-Key requirement on POST /api/alerts/{id}/verdict).
5. Wilson Score Confidence Interval calculations in evaluation harness.

Design note on verdict test:
  The verdict endpoint auth test deliberately uses a minimal FastAPI app with a
  temp-DB fixture (same pattern as test_security_replay_indepth.py) rather than
  the global `main.app`. This avoids the fresh-clone OperationalError that occurs
  when `ASGITransport(app=main_app)` triggers the full lifespan, which calls
  load_audit_ledger() → aiosqlite.connect(DATABASE_PATH) before the real data/
  directory exists. Using a scoped temp DB makes the test fully self-contained
  and reproducible on any machine regardless of repo state.
"""

import sys
import os
import math
import pytest
import pytest_asyncio
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import aiosqlite
from httpx import ASGITransport, AsyncClient

import config
from main import app as main_app
from services.corroboration_service import (
    _record_corroboration_pair,
    get_velocity_alerts,
    reset_velocity_tracker,
    VELOCITY_THRESHOLD,
)
from services.audit_ledger import clear_ledger, record_audit_event
from eval.run_eval import wilson_ci

# Import helpers from the existing alert test module
from test_alerts_routes import _init_test_db, _insert_demo_device
from routes import alerts as alerts_module


# ---------------------------------------------------------------------------
# 1. Corroboration Velocity Tracker Unit Tests
# ---------------------------------------------------------------------------

class TestCorroborationVelocityTracker:
    def setup_method(self):
        reset_velocity_tracker()

    def test_velocity_tracker_initial_state(self):
        alerts = get_velocity_alerts()
        assert alerts == []

    def test_velocity_tracker_records_pairs_and_flags_on_threshold(self):
        cam_a = "CAM_TEST_101"
        cam_b = "CAM_TEST_102"

        # Record events up to threshold (should NOT flag yet)
        for i in range(VELOCITY_THRESHOLD):
            flag = _record_corroboration_pair(cam_a, cam_b)
            assert flag.count_in_window == i + 1
            assert flag.flagged is False

        # One more exceeds threshold
        flag_exceeded = _record_corroboration_pair(cam_a, cam_b)
        assert flag_exceeded.count_in_window == VELOCITY_THRESHOLD + 1
        assert flag_exceeded.flagged is True

        alerts = get_velocity_alerts()
        assert len(alerts) == 1
        assert sorted(alerts[0]["camera_pair"]) == sorted([cam_a, cam_b])
        assert alerts[0]["count_in_window"] == VELOCITY_THRESHOLD + 1
        assert alerts[0]["flagged"] is True

    def test_velocity_tracker_order_invariant(self):
        """(A, B) and (B, A) must resolve to the same pair key via frozenset."""
        cam_a = "CAM_X"
        cam_b = "CAM_Y"

        for _ in range(3):
            _record_corroboration_pair(cam_a, cam_b)
        for _ in range(3):
            _record_corroboration_pair(cam_b, cam_a)  # reversed order

        alerts = get_velocity_alerts()
        assert len(alerts) == 1
        assert alerts[0]["count_in_window"] == 6

    def test_reset_velocity_tracker(self):
        _record_corroboration_pair("C1", "C2")
        reset_velocity_tracker()
        assert get_velocity_alerts() == []


# ---------------------------------------------------------------------------
# 2. Audit Anchor and Velocity API Endpoint Tests (via main_app + real data/)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAuditAnchorAndVelocityEndpoints:
    async def test_audit_anchor_endpoint(self):
        """GET /api/audit/anchor returns head_hash, chain_length, anchored_at."""
        clear_ledger()
        record_audit_event(
            alert_id="ALT-ANCHOR-001",
            camera_id="CAM-01",
            trust_score=85,
            action_tier="high_trust",
            factors=["authenticated_stream"],
        )

        transport = ASGITransport(app=main_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/audit/anchor")
            assert res.status_code == 200
            data = res.json()
            assert "head_hash" in data
            assert len(data["head_hash"]) == 64   # 256-bit SHA in hex
            assert data["chain_length"] >= 1
            assert "anchored_at" in data
            assert "anchor_instructions" in data
            assert "security_model" in data

    async def test_audit_velocity_endpoint(self):
        """GET /api/audit/velocity reports suspicious pairs correctly."""
        reset_velocity_tracker()
        transport = ASGITransport(app=main_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Clean state
            res = await client.get("/api/audit/velocity")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "clean"
            assert data["flagged_pairs"] == 0

            # Trigger a velocity flag
            for _ in range(VELOCITY_THRESHOLD + 2):
                _record_corroboration_pair("CAM_VEL_1", "CAM_VEL_2")

            res2 = await client.get("/api/audit/velocity")
            assert res2.status_code == 200
            data2 = res2.json()
            assert data2["status"] == "suspicious_activity_detected"
            assert data2["flagged_pairs"] == 1


# ---------------------------------------------------------------------------
# 3. Verdict Labelling Authentication Test
#    Uses a temp-DB scoped app (same pattern as test_security_replay_indepth.py)
#    to avoid OperationalError on fresh clones where data/ doesn't exist yet.
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def tmp_db(tmp_path):
    """Create a minimal temp SQLite DB for verdict auth tests."""
    db_path = str(tmp_path / "verdict_auth_test.db")
    await _init_test_db(db_path)
    return db_path


@pytest_asyncio.fixture
async def verdict_app(tmp_db):
    """Minimal FastAPI app wired to a temp DB for verdict endpoint tests."""
    patches = [
        patch("config.DATABASE_PATH", tmp_db),
        patch("services.corroboration_service.DATABASE_PATH", tmp_db),
        patch("routes.alerts.DATABASE_PATH", tmp_db),
    ]
    for p in patches:
        p.start()

    from fastapi import FastAPI
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(a):
        class DummyManager:
            async def broadcast(self, payload):
                pass
        alerts_module.set_connection_manager(DummyManager())
        yield

    test_app = FastAPI(lifespan=lifespan)
    test_app.include_router(alerts_module.router, prefix="/api")

    alerts_module._seen_idempotency_keys.clear()
    alerts_module._camera_request_timestamps.clear()

    yield test_app

    for p in patches:
        p.stop()


@pytest.mark.asyncio
class TestVerdictEndpointAuth:
    async def test_verdict_requires_api_key_when_configured(self, verdict_app, tmp_db):
        """
        When DETECTION_API_KEY is set, POST /api/alerts/{id}/verdict must return
        403 Forbidden for missing or incorrect keys, and 404 (not 403) when the
        key is valid but the alert_id doesn't exist.

        Uses a temp-DB fixture to avoid sqlite3.OperationalError on fresh clones
        where data/ has not yet been created by init_db().
        """
        test_key = "secret-test-key-verdict-auth-999"
        with patch("routes.alerts.DETECTION_API_KEY", test_key), \
             patch("config.DETECTION_API_KEY", test_key):

            async with AsyncClient(
                transport=ASGITransport(app=verdict_app), base_url="http://test"
            ) as client:
                # Missing key → 403
                res_no_key = await client.post(
                    "/api/alerts/nonexistent-id/verdict",
                    json={"verdict": "verified", "notes": "Test"},
                )
                assert res_no_key.status_code == 403, (
                    f"Expected 403 (missing key), got {res_no_key.status_code}: {res_no_key.text}"
                )

                # Wrong key → 403
                res_bad_key = await client.post(
                    "/api/alerts/nonexistent-id/verdict",
                    json={"verdict": "verified", "notes": "Test"},
                    headers={"X-API-Key": "definitely-wrong-key"},
                )
                assert res_bad_key.status_code == 403, (
                    f"Expected 403 (wrong key), got {res_bad_key.status_code}: {res_bad_key.text}"
                )

                # Correct key, nonexistent alert → 404 (auth passed, alert missing)
                res_valid = await client.post(
                    "/api/alerts/nonexistent-id/verdict",
                    json={"verdict": "verified", "notes": "Test"},
                    headers={"X-API-Key": test_key},
                )
                assert res_valid.status_code == 404, (
                    f"Expected 404 (valid key, alert not found), got {res_valid.status_code}: {res_valid.text}"
                )
                assert "not found" in res_valid.json()["detail"].lower()

    async def test_verdict_open_when_key_not_configured(self, verdict_app, tmp_db):
        """When DETECTION_API_KEY is empty, verdicts pass auth without a key."""
        with patch("routes.alerts.DETECTION_API_KEY", ""), \
             patch("config.DETECTION_API_KEY", ""):

            async with AsyncClient(
                transport=ASGITransport(app=verdict_app), base_url="http://test"
            ) as client:
                # No key required → should get 404 (auth bypassed, alert not found)
                res = await client.post(
                    "/api/alerts/nonexistent-id/verdict",
                    json={"verdict": "verified", "notes": "Test"},
                )
                assert res.status_code == 404, (
                    f"Expected 404 (no auth, alert not found), got {res.status_code}"
                )


# ---------------------------------------------------------------------------
# 4. Wilson Score Confidence Interval Unit Tests
# ---------------------------------------------------------------------------

class TestWilsonConfidenceIntervals:
    def test_wilson_ci_bounds(self):
        """At p=0.90, n=100, bounds should bracket the true proportion tightly."""
        lower, upper = wilson_ci(0.90, 100)
        assert 0.80 <= lower <= 0.86
        assert 0.94 <= upper <= 0.96
        assert lower < 0.90 < upper

    def test_wilson_ci_empty_sample(self):
        """n=0 should return the full [0, 1] interval (maximum uncertainty)."""
        assert wilson_ci(0.5, 0) == (0.0, 1.0)

    def test_wilson_ci_perfect_score_small_n(self):
        """100% success at n=10 should not return upper > 1.0."""
        lower, upper = wilson_ci(1.0, 10)
        assert lower > 0.65   # should not be too pessimistic
        assert upper == 1.0   # clamped at 1.0

    def test_wilson_ci_always_ordered(self):
        """Lower bound must always be ≤ upper bound for any valid input."""
        for p in [0.0, 0.25, 0.50, 0.75, 1.0]:
            for n in [5, 10, 25, 50, 100]:
                lo, hi = wilson_ci(p, n)
                assert lo <= hi, f"Bounds inverted at p={p}, n={n}: [{lo}, {hi}]"
