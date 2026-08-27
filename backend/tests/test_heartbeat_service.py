"""
test_heartbeat_service.py
==========================
Module D (IIT-B BTP) — Tests for camera heartbeat & signal integrity trust factor.
Literature: YOLO in Suspicious Activity Review (ResearchGate, 2025)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.heartbeat_service import get_heartbeat_trust_factor, ping_camera


class TestHeartbeatTrustFactor:
    def test_offline_camera_deducts_15(self):
        ping = {"reachable": False, "latency_ms": None}
        factor = get_heartbeat_trust_factor(ping)
        assert factor["deduction"] == 15
        assert factor["factor"] == "camera_offline"
        assert factor["status"] == "offline"

    def test_high_latency_deducts_10(self):
        ping = {"reachable": True, "latency_ms": 600.0}
        factor = get_heartbeat_trust_factor(ping)
        assert factor["deduction"] == 10
        assert "high_signal_latency" in factor["factor"]
        assert factor["status"] == "degraded"

    def test_elevated_latency_deducts_5(self):
        ping = {"reachable": True, "latency_ms": 200.0}
        factor = get_heartbeat_trust_factor(ping)
        assert factor["deduction"] == 5
        assert "elevated_signal_latency" in factor["factor"]
        assert factor["status"] == "elevated"

    def test_healthy_camera_no_deduction(self):
        ping = {"reachable": True, "latency_ms": 30.0}
        factor = get_heartbeat_trust_factor(ping)
        assert factor["deduction"] == 0
        assert factor["factor"] is None
        assert factor["status"] == "healthy"

    def test_boundary_exactly_500ms_is_high_latency(self):
        ping = {"reachable": True, "latency_ms": 501.0}
        factor = get_heartbeat_trust_factor(ping)
        assert factor["deduction"] == 10

    def test_boundary_exactly_150ms_is_elevated(self):
        ping = {"reachable": True, "latency_ms": 151.0}
        factor = get_heartbeat_trust_factor(ping)
        assert factor["deduction"] == 5

    def test_exactly_150ms_is_healthy(self):
        ping = {"reachable": True, "latency_ms": 150.0}
        factor = get_heartbeat_trust_factor(ping)
        assert factor["deduction"] == 0
        assert factor["status"] == "healthy"

    def test_latency_factor_string_includes_ms_value(self):
        ping = {"reachable": True, "latency_ms": 750.0}
        factor = get_heartbeat_trust_factor(ping)
        assert "750" in factor["factor"]

    def test_none_latency_treated_as_zero_healthy(self):
        ping = {"reachable": True, "latency_ms": None}
        factor = get_heartbeat_trust_factor(ping)
        assert factor["deduction"] == 0
        assert factor["status"] == "healthy"


class TestPingCamera:
    @pytest.mark.asyncio
    async def test_unreachable_host_returns_not_reachable(self):
        """Ping a non-routable IP — should return reachable=False without raising."""
        result = await ping_camera("192.0.2.1", timeout=0.5)  # TEST-NET-1 (RFC 5737)
        assert result["reachable"] is False
        assert result["latency_ms"] is None
        assert "checked_at" in result

    @pytest.mark.asyncio
    async def test_result_has_required_keys(self):
        result = await ping_camera("192.0.2.1", timeout=0.5)
        for key in ("reachable", "latency_ms", "port_used", "checked_at"):
            assert key in result
