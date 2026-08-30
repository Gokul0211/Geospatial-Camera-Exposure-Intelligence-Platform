"""
test_velocity_and_anchoring.py
==============================
Unit and integration tests for:
1. Corroboration Velocity Tracker (rolling window, threshold trigger, get_velocity_alerts).
2. External Audit Anchoring Endpoint (GET /api/audit/anchor).
3. Corroboration Velocity Endpoint (GET /api/audit/velocity).
4. Protected Verdict Labelling (X-API-Key requirement on POST /api/alerts/{id}/verdict).
5. Wilson Score Confidence Interval calculations in evaluation harness.
"""

import sys
import os
import math
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import config
from main import app
from services.corroboration_service import (
    _record_corroboration_pair,
    get_velocity_alerts,
    reset_velocity_tracker,
    VELOCITY_THRESHOLD,
)
from services.audit_ledger import clear_ledger, record_audit_event
from eval.run_eval import wilson_ci


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

        # Record events up to threshold
        for i in range(VELOCITY_THRESHOLD):
            flag = _record_corroboration_pair(cam_a, cam_b)
            assert flag.count_in_window == i + 1
            assert flag.flagged is False

        # Exceed threshold by 1
        flag_exceeded = _record_corroboration_pair(cam_a, cam_b)
        assert flag_exceeded.count_in_window == VELOCITY_THRESHOLD + 1
        assert flag_exceeded.flagged is True

        alerts = get_velocity_alerts()
        assert len(alerts) == 1
        assert sorted(alerts[0]["camera_pair"]) == sorted([cam_a, cam_b])
        assert alerts[0]["count_in_window"] == VELOCITY_THRESHOLD + 1
        assert alerts[0]["flagged"] is True

    def test_velocity_tracker_order_invariant(self):
        # (A, B) and (B, A) map to the same pair key
        cam_a = "CAM_X"
        cam_b = "CAM_Y"

        for _ in range(3):
            _record_corroboration_pair(cam_a, cam_b)
        for _ in range(3):
            _record_corroboration_pair(cam_b, cam_a)

        alerts = get_velocity_alerts()
        assert len(alerts) == 1
        assert alerts[0]["count_in_window"] == 6

    def test_reset_velocity_tracker(self):
        _record_corroboration_pair("C1", "C2")
        reset_velocity_tracker()
        assert get_velocity_alerts() == []


# ---------------------------------------------------------------------------
# 2. Audit Anchor and Velocity API Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAuditAnchorAndVelocityEndpoints:
    async def test_audit_anchor_endpoint(self):
        clear_ledger()
        record_audit_event(
            alert_id="ALT-ANCHOR-001",
            camera_id="CAM-01",
            trust_score=85,
            action_tier="high_trust",
            factors=["authenticated_stream"],
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/audit/anchor")
            assert res.status_code == 200
            data = res.json()
            assert "head_hash" in data
            assert len(data["head_hash"]) == 64
            assert data["chain_length"] >= 1
            assert "anchored_at" in data
            assert "anchor_instructions" in data
            assert "security_model" in data

    async def test_audit_velocity_endpoint(self):
        reset_velocity_tracker()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/audit/velocity")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "clean"
            assert data["flagged_pairs"] == 0

            # Trigger velocity flag
            for _ in range(VELOCITY_THRESHOLD + 2):
                _record_corroboration_pair("CAM_VEL_1", "CAM_VEL_2")

            res2 = await client.get("/api/audit/velocity")
            assert res2.status_code == 200
            data2 = res2.json()
            assert data2["status"] == "suspicious_activity_detected"
            assert data2["flagged_pairs"] == 1


# ---------------------------------------------------------------------------
# 3. Verdict Labelling Authentication Test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestVerdictEndpointAuth:
    async def test_verdict_endpoint_requires_api_key_when_configured(self, monkeypatch):
        test_key = "secret-test-key-999"
        monkeypatch.setattr(config, "DETECTION_API_KEY", test_key)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Without key -> 403
            res = await client.post(
                "/api/alerts/nonexistent-id/verdict",
                json={"verdict": "verified", "notes": "Test label"},
            )
            assert res.status_code == 403

            # With invalid key -> 403
            res_invalid = await client.post(
                "/api/alerts/nonexistent-id/verdict",
                json={"verdict": "verified", "notes": "Test label"},
                headers={"X-API-Key": "wrong-key"},
            )
            assert res_invalid.status_code == 403

            # With valid key -> 404 because nonexistent-id is not in DB, but auth passed!
            res_valid = await client.post(
                "/api/alerts/nonexistent-id/verdict",
                json={"verdict": "verified", "notes": "Test label"},
                headers={"X-API-Key": test_key},
            )
            assert res_valid.status_code == 404
            assert "not found" in res_valid.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 4. Wilson Score Confidence Interval Unit Tests
# ---------------------------------------------------------------------------

class TestWilsonConfidenceIntervals:
    def test_wilson_ci_bounds(self):
        # Proportion 0.90 at n=100
        lower, upper = wilson_ci(0.90, 100)
        assert 0.80 <= lower <= 0.86
        assert 0.94 <= upper <= 0.96
        assert lower < 0.90 < upper

    def test_wilson_ci_edge_cases(self):
        # Empty sample
        assert wilson_ci(0.5, 0) == (0.0, 1.0)
        # 100% success at small n
        lower, upper = wilson_ci(1.0, 10)
        assert lower > 0.65
        assert upper == 1.0
