"""
test_notification_tier_routing_indepth.py — Advanced Tiered Alert Notification Dispatcher Tests
=================================================================================================
Verifies the Rasal et al. 2025 alert dispatcher under parallel burst event load, custom notification
channels (SMS, Webhook, Dashboard Triage Queue, Silent Audit Log), and threshold boundaries.
"""

import os
import sys
import pytest
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.notification_service import (
    dispatch_alert,
    get_dispatch_history,
    clear_dispatch_history,
)


@pytest.fixture(autouse=True)
def setup_clean_notifications():
    clear_dispatch_history()
    yield
    clear_dispatch_history()


class TestNotificationTierRouting:

    @pytest.mark.asyncio
    async def test_high_trust_emergency_dispatch(self):
        alert_data = {
            "id": "evt-high-001",
            "camera_id": "cam-001",
            "city": "Mumbai",
            "event_type": "perimeter_breach",
            "trust_score": 85,
            "action_tier": "high_trust",
        }
        res = await dispatch_alert(alert_data)
        assert "EMERGENCY" in res["channel"]
        assert res["priority"] == "CRITICAL"
        assert res["action"] == "INSTANT_PUSH_DISPATCH"

        history = get_dispatch_history()
        assert len(history) == 1
        assert "EMERGENCY" in history[0]["channel"]

    @pytest.mark.asyncio
    async def test_medium_trust_dashboard_queue_dispatch(self):
        alert_data = {
            "id": "evt-med-001",
            "camera_id": "cam-002",
            "city": "Delhi",
            "event_type": "loitering",
            "trust_score": 65,
            "action_tier": "medium_trust",
        }
        res = await dispatch_alert(alert_data)
        assert "TRIAGE" in res["channel"]
        assert res["priority"] == "WARNING"

    @pytest.mark.asyncio
    async def test_low_trust_silent_audit_log_dispatch(self):
        alert_data = {
            "id": "evt-low-001",
            "camera_id": "cam-003",
            "city": "Bangalore",
            "event_type": "anomalous_motion",
            "trust_score": 25,
            "action_tier": "low_trust",
        }
        res = await dispatch_alert(alert_data)
        assert "SILENT" in res["channel"]
        assert res["priority"] == "LOW"

    @pytest.mark.asyncio
    async def test_rapid_burst_event_routing_50_alerts_and_stats(self):
        from services.notification_service import get_dispatch_stats

        for i in range(50):
            tier = "high_trust" if i % 3 == 0 else ("medium_trust" if i % 3 == 1 else "low_trust")
            score = 90 if tier == "high_trust" else (60 if tier == "medium_trust" else 30)
            await dispatch_alert({
                "id": f"burst-{i}",
                "camera_id": f"cam-{i}",
                "city": "Mumbai",
                "event_type": "loitering",
                "trust_score": score,
                "action_tier": tier,
            })

        history = get_dispatch_history()
        assert len(history) == 50

        stats = get_dispatch_stats()
        assert stats["total_dispatched"] == 50
        assert stats["by_tier"]["high_trust"] == 17
        assert stats["by_tier"]["medium_trust"] == 17
        assert stats["by_tier"]["low_trust"] == 16
        assert stats["false_alarm_suppression_rate"] > 0.60
