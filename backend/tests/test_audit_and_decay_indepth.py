"""
test_audit_and_decay_indepth.py
================================
In-depth test suite for literature-grounded extensions:
- Tamper-Evident Merkle Hash-Chain Audit Ledger (BIoT SLR 2026)
- Exponential Trust Score Decay (Griffioen & Doerr 2020)
- Advanced Category-Aware Trust Scoring & Critical Security Gates (Oliver 2025, Swami 2025)
- Tiered Notification Dispatch Routing (Rasal et al. 2025)
"""

import os
import sys
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.audit_ledger import (
    record_audit_event,
    verify_ledger_integrity,
    get_ledger,
    clear_ledger,
)
from services.trust_score_service import (
    apply_trust_decay,
    compute_advanced_trust_score,
)
from services.notification_service import (
    dispatch_alert,
    get_dispatch_history,
    clear_dispatch_history,
)


class TestAuditLedger:
    def setup_method(self):
        clear_ledger()

    def test_hash_chain_integrity(self):
        e1 = record_audit_event("alert_1", "cam_1", 90, "high_trust", ["corroborated"])
        e2 = record_audit_event("alert_2", "cam_2", 20, "low_trust", ["unauthenticated_stream"])

        assert e2["previous_hash"] == e1["hash"]
        assert verify_ledger_integrity() is True

    def test_tamper_detection(self):
        record_audit_event("alert_1", "cam_1", 90, "high_trust", [])
        record_audit_event("alert_2", "cam_2", 20, "low_trust", [])

        ledger = get_ledger()
        assert len(ledger) == 2

        # Tamper with payload of entry 1
        ledger[0]["payload"]["trust_score"] = 100

        # Integrity verification fails
        assert verify_ledger_integrity() is False


class TestTrustDecayModel:
    def test_fresh_scan_no_decay(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        res = apply_trust_decay(100.0, now_iso, half_life_hours=48.0)
        assert res["decayed_score"] == 100
        assert res["decay_factor"] == 1.0

    def test_48_hour_half_life_decay(self):
        two_days_ago = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        res = apply_trust_decay(100.0, two_days_ago, half_life_hours=48.0)
        # Score decayed by 50% -> 50
        assert res["decayed_score"] == 50
        assert pytest.approx(res["decay_factor"], abs=0.05) == 0.5


class TestAdvancedTrustScoreEngine:
    def test_category_aware_cve_deductions(self):
        device = {"auth_required": True, "known_cve_count": 1, "owner_type": "corporate"}

        critical_cve = compute_advanced_trust_score(
            device, ["c1", "c2"], cve_categories=["auth_bypass"]
        )
        standard_cve = compute_advanced_trust_score(
            device, ["c1", "c2"], cve_categories=["info_disclosure"]
        )

        assert critical_cve["score"] < standard_cve["score"]
        assert "critical_cve_auth_bypass_rce" in critical_cve["factors"]

    def test_critical_security_gate_auto_fail(self):
        # Unauthenticated device with positive corroboration
        device = {"auth_required": False, "known_cve_count": 0, "owner_type": "government"}
        res = compute_advanced_trust_score(device, ["c1", "c2", "c3"], enforce_critical_gates=True)

        # Unauthenticated gate hard-caps score at low_trust (< 50)
        assert res["score"] <= 49
        assert res["tier"] == "low_trust"
        assert "critical_gate_unauthenticated_cap" in res["factors"]


class TestTieredNotificationDispatch:
    def setup_method(self):
        clear_dispatch_history()

    @pytest.mark.asyncio
    async def test_tiered_dispatch_routing(self):
        high_res = await dispatch_alert({"alert_id": "a1", "trust_score": 90, "action_tier": "high_trust"})
        med_res = await dispatch_alert({"alert_id": "a2", "trust_score": 60, "action_tier": "medium_trust"})
        low_res = await dispatch_alert({"alert_id": "a3", "trust_score": 20, "action_tier": "low_trust"})

        assert high_res["channel"] == "EMERGENCY_DISPATCH_SMS"
        assert med_res["channel"] == "DASHBOARD_TRIAGE_QUEUE"
        assert low_res["channel"] == "SILENT_AUDIT_LOG"
        assert len(get_dispatch_history()) == 3
