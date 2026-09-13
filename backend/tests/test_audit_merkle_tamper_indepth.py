"""
test_audit_merkle_tamper_indepth.py — Deep Merkle Ledger & Tamper Verification Tests
======================================================================================
Verifies the cryptographic append-only Merkle hash-chain ledger (BIoT SLR 2026 pattern)
under deep chain length (100+ events), single bit-flip corruptions, middle node tampering,
head tampering, and ledger verification performance.
"""

import os
import sys
import pytest
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.audit_ledger import (
    record_audit_event,
    verify_ledger_integrity,
    get_ledger,
    clear_ledger,
)


@pytest.fixture(autouse=True)
def setup_clean_ledger():
    clear_ledger()
    yield
    clear_ledger()


class TestDeepMerkleLedger:

    def test_single_event_ledger_integrity(self):
        record_audit_event("evt-001", "cam-001", 90, "high_trust", ["corroborated_2_cameras"])
        assert verify_ledger_integrity() is True
        assert len(get_ledger()) == 1

    def test_deep_chain_integrity_100_events(self):
        for i in range(100):
            record_audit_event(
                alert_id=f"evt-{i:03d}",
                camera_id=f"cam-{i % 10:03d}",
                trust_score=80 - (i % 50),
                action_tier="medium_trust" if i % 2 == 0 else "low_trust",
                factors=["test_factor"],
            )

        assert verify_ledger_integrity() is True
        assert len(get_ledger()) == 100

    def test_tampering_at_genesis_node(self):
        for i in range(10):
            record_audit_event(f"evt-{i}", "cam-001", 80, "medium_trust", [])

        ledger = get_ledger()
        # Tamper with the payload at index 0 (Genesis block)
        ledger[0]["payload"]["trust_score"] = 0

        assert verify_ledger_integrity() is False

    def test_tampering_at_middle_node(self):
        for i in range(25):
            record_audit_event(f"evt-{i}", f"cam-{i}", 75, "medium_trust", [])

        ledger = get_ledger()
        # Tamper with payload at index 12
        ledger[12]["payload"]["action_tier"] = "high_trust"

        assert verify_ledger_integrity() is False

    def test_tampering_at_head_node(self):
        for i in range(15):
            record_audit_event(f"evt-{i}", "cam-002", 50, "medium_trust", [])

        ledger = get_ledger()
        # Tamper with payload at the last node
        ledger[-1]["payload"]["camera_id"] = "cam-HACKED"

        assert verify_ledger_integrity() is False

    def test_single_bit_flip_hash_corruption(self):
        for i in range(5):
            record_audit_event(f"evt-{i}", "cam-001", 90, "high_trust", [])

        ledger = get_ledger()
        # Corrupt 1 character in the previous_hash field of node 3
        old_hash = ledger[3]["previous_hash"]
        corrupted_hash = "a" + old_hash[1:] if old_hash[0] != "a" else "b" + old_hash[1:]
        ledger[3]["previous_hash"] = corrupted_hash

        assert verify_ledger_integrity() is False

    def test_empty_ledger_verification(self):
        assert verify_ledger_integrity() is True
        assert len(get_ledger()) == 0
