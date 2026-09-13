"""
test_audit_gate_trip_entries.py
=================================
Tests for the dedicated `INTEGRITY_GATE_TRIP` Merkle ledger entry type
(research_work.md §4.6): gate trips are now independently queryable instead
of only existing as a factor string buried inside the normal TRUST_DECISION
entry. Verifies:
  1. `record_integrity_gate_trip` appends onto the SAME hash chain (not a
     parallel one) and chain integrity still verifies across mixed types.
  2. `get_ledger_entries_by_type` filters correctly and treats legacy
     entries (no `entry_type` key) as TRUST_DECISION for backward compat.
  3. `record_audit_event` entries are correctly tagged TRUST_DECISION.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.audit_ledger import (
    record_audit_event,
    record_integrity_gate_trip,
    get_ledger_entries_by_type,
    verify_ledger_integrity_report,
    clear_ledger,
    _ledger_chain,
)


class TestGateTripEntryType:
    def setup_method(self):
        clear_ledger()

    def teardown_method(self):
        clear_ledger()

    def test_trust_decision_entries_are_tagged(self):
        record_audit_event(
            alert_id="a1", camera_id="cam1", trust_score=80,
            action_tier="high_trust", factors=["corroborated"],
        )
        entries = get_ledger_entries_by_type("TRUST_DECISION")
        assert len(entries) == 1
        assert entries[0]["payload"]["entry_type"] == "TRUST_DECISION"

    def test_gate_trip_entry_is_independently_recorded(self):
        record_audit_event(
            alert_id="a1", camera_id="cam1", trust_score=25,
            action_tier="low_trust", factors=["ig_dctf_hard_gate_cap_30"],
        )
        record_integrity_gate_trip(
            camera_id="cam1", drift_score=0.72, signal_integrity=0.28,
            gate_status="hard_gated", alert_id="a1",
        )

        trust_entries = get_ledger_entries_by_type("TRUST_DECISION")
        gate_entries = get_ledger_entries_by_type("INTEGRITY_GATE_TRIP")

        assert len(trust_entries) == 1
        assert len(gate_entries) == 1
        assert gate_entries[0]["payload"]["camera_id"] == "cam1"
        assert gate_entries[0]["payload"]["drift_score"] == 0.72
        assert gate_entries[0]["payload"]["signal_integrity"] == 0.28
        assert gate_entries[0]["payload"]["gate_status"] == "hard_gated"
        assert gate_entries[0]["payload"]["alert_id"] == "a1"

    def test_gate_trip_shares_same_chain_and_integrity_holds(self):
        """A mix of TRUST_DECISION and INTEGRITY_GATE_TRIP entries must still form one unbroken, verifiable chain — not two parallel ledgers."""
        record_audit_event(alert_id="a1", camera_id="cam1", trust_score=25, action_tier="low_trust", factors=[])
        record_integrity_gate_trip(camera_id="cam1", drift_score=0.7, signal_integrity=0.3, gate_status="hard_gated", alert_id="a1")
        record_audit_event(alert_id="a2", camera_id="cam2", trust_score=90, action_tier="high_trust", factors=[])
        record_integrity_gate_trip(camera_id="cam3", drift_score=0.9, signal_integrity=0.1, gate_status="hard_gated", alert_id="a3")

        assert len(_ledger_chain) == 4
        report = verify_ledger_integrity_report()
        assert report["valid"] is True
        assert report["chain_length"] == 4

        # Sequence IDs must be monotonic across BOTH entry types (single chain)
        seq_ids = [e["sequence_id"] for e in _ledger_chain]
        assert seq_ids == [1, 2, 3, 4]

    def test_get_ledger_entries_by_type_respects_limit(self):
        for i in range(5):
            record_integrity_gate_trip(
                camera_id=f"cam{i}", drift_score=0.6, signal_integrity=0.4, gate_status="hard_gated",
            )
        entries = get_ledger_entries_by_type("INTEGRITY_GATE_TRIP", limit=2)
        assert len(entries) == 2

    def test_get_ledger_entries_by_type_newest_first(self):
        record_integrity_gate_trip(camera_id="first", drift_score=0.6, signal_integrity=0.4, gate_status="hard_gated")
        record_integrity_gate_trip(camera_id="second", drift_score=0.6, signal_integrity=0.4, gate_status="hard_gated")
        entries = get_ledger_entries_by_type("INTEGRITY_GATE_TRIP")
        assert entries[0]["payload"]["camera_id"] == "second"
        assert entries[1]["payload"]["camera_id"] == "first"

    def test_legacy_entry_without_entry_type_key_treated_as_trust_decision(self):
        """Entries recorded before entry_type existed (loaded from an older DB) must still classify correctly."""
        # Simulate a legacy entry by appending directly, bypassing record_audit_event
        from services.audit_ledger import _append_to_chain
        _append_to_chain({"alert_id": "legacy1", "camera_id": "camX", "trust_score": 50, "action_tier": "medium_trust", "factors": [], "timestamp": "2020-01-01T00:00:00+00:00"})

        entries = get_ledger_entries_by_type("TRUST_DECISION")
        assert len(entries) == 1
        assert entries[0]["payload"]["alert_id"] == "legacy1"
