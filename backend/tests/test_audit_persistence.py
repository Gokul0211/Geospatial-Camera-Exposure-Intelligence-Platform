"""
test_audit_persistence.py
==========================
Module E (IIT-B BTP) — Tests for persistent Merkle hash-chain audit ledger.
Literature: BIoT Trust Assessment SLR (MDPI Applied Sciences, 2026)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.audit_ledger import (
    record_audit_event,
    verify_ledger_integrity,
    verify_ledger_integrity_report,
    get_ledger,
    get_ledger_entry_by_alert_id,
    get_ledger_stats,
    compute_entry_hash,
    clear_ledger,
    _GENESIS_HASH,
)


@pytest.fixture(autouse=True)
def reset_ledger():
    clear_ledger()
    yield
    clear_ledger()


class TestAuditLedgerCore:
    def test_genesis_state(self):
        stats = get_ledger_stats()
        assert stats["chain_length"] == 0
        assert stats["head_hash"] == _GENESIS_HASH

    def test_record_single_event(self):
        entry = record_audit_event(
            alert_id="test-001",
            camera_id="cam-a",
            trust_score=80,
            action_tier="high_trust",
            factors=["corroborated"],
        )
        assert entry["sequence_id"] == 1
        assert entry["previous_hash"] == _GENESIS_HASH
        assert len(entry["hash"]) == 64  # SHA-256 hex
        assert entry["payload"]["alert_id"] == "test-001"
        assert entry["payload"]["trust_score"] == 80

    def test_chain_links_correctly(self):
        e1 = record_audit_event("a-001", "cam-1", 80, "high_trust", [])
        e2 = record_audit_event("a-002", "cam-2", 40, "low_trust", ["no_corroboration"])
        assert e2["previous_hash"] == e1["hash"]
        assert e2["sequence_id"] == 2

    def test_hash_deterministic(self):
        payload = {"alert_id": "x", "camera_id": "c", "trust_score": 70,
                   "action_tier": "medium_trust", "factors": [], "timestamp": "2026-01-01T00:00:00+00:00"}
        h1 = compute_entry_hash(_GENESIS_HASH, payload)
        h2 = compute_entry_hash(_GENESIS_HASH, payload)
        assert h1 == h2

    def test_integrity_passes_on_valid_chain(self):
        for i in range(5):
            record_audit_event(f"alert-{i}", "cam", 70, "medium_trust", [])
        assert verify_ledger_integrity() is True
        report = verify_ledger_integrity_report()
        assert report["chain_length"] == 5

    def test_integrity_empty_chain(self):
        assert verify_ledger_integrity() is True
        report = verify_ledger_integrity_report()
        assert report["chain_length"] == 0

    def test_get_ledger_returns_newest_first(self):
        for i in range(3):
            record_audit_event(f"alert-{i}", "cam", 70, "medium_trust", [])
        entries = get_ledger(limit=3)
        assert entries[0]["sequence_id"] == 3
        assert entries[-1]["sequence_id"] == 1

    def test_get_ledger_entry_by_alert_id(self):
        record_audit_event("find-me", "cam", 90, "high_trust", ["corroborated"])
        entry = get_ledger_entry_by_alert_id("find-me")
        assert entry is not None
        assert entry["payload"]["alert_id"] == "find-me"
        assert entry["payload"]["trust_score"] == 90

    def test_get_ledger_entry_not_found(self):
        entry = get_ledger_entry_by_alert_id("does-not-exist")
        assert entry is None

    def test_extended_payload_fields(self):
        entry = record_audit_event(
            alert_id="extended-001",
            camera_id="cam-x",
            trust_score=70,
            action_tier="medium_trust",
            factors=["outdated_firmware"],
            probabilistic_score=65,
            decayed_score=55,
            max_cvss=9.8,
        )
        payload = entry["payload"]
        assert payload["probabilistic_score"] == 65
        assert payload["decayed_score"] == 55
        assert payload["max_cvss"] == 9.8

    def test_stats_reflects_current_state(self):
        for i in range(7):
            record_audit_event(f"stat-{i}", "cam", 50, "medium_trust", [])
        stats = get_ledger_stats()
        assert stats["chain_length"] == 7

    def test_integrity_chain_length_50(self):
        """Stress test: 50-entry chain should still verify clean."""
        for i in range(50):
            record_audit_event(f"stress-{i}", "cam", i * 2, "medium_trust", [])
        assert verify_ledger_integrity() is True
        report = verify_ledger_integrity_report()
        assert report["chain_length"] == 50

    def test_paginated_ledger(self):
        for i in range(10):
            record_audit_event(f"page-{i}", "cam", 70, "medium_trust", [])
        page1 = get_ledger(limit=5, offset=0)
        page2 = get_ledger(limit=5, offset=5)
        assert len(page1) == 5
        assert len(page2) == 5
        # No overlap
        ids1 = {e["sequence_id"] for e in page1}
        ids2 = {e["sequence_id"] for e in page2}
        assert ids1.isdisjoint(ids2)
