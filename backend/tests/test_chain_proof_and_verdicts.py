"""
test_chain_proof_and_verdicts.py — Cryptographic Chain Proof & Live Evaluation Tests
======================================================================================
Literature: BIoT SLR (MDPI, 2026), Luna et al. (Sensors, 2018), ByteTrack (ECCV 2022)
"""

import os
import sys
import pytest
import aiosqlite
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app
from config import DATABASE_PATH
from services.audit_ledger import (
    record_audit_event,
    generate_chain_proof,
    clear_ledger,
)


@pytest.fixture(autouse=True)
def setup_clean():
    clear_ledger()
    yield
    clear_ledger()


class TestChainProofAndVerdicts:

    def test_merkle_chain_proof_generation(self):
        # Add 3 events
        record_audit_event("alert-001", "cam-001", 85, "high_trust", ["corroborated"])
        record_audit_event("alert-002", "cam-002", 45, "low_trust", ["unauthenticated_stream"])
        record_audit_event("alert-003", "cam-003", 65, "medium_trust", ["standard_cve"])

        proof = generate_chain_proof("alert-002")
        assert proof is not None
        assert proof["alert_id"] == "alert-002"
        assert proof["sequence_id"] == 2
        assert proof["is_tamper_free"] is True
        assert proof["confirmations"] == 1
        assert proof["chain_depth"] == 3
        assert proof["proof_standard"] == "SHA256-Merkle-Chain-BIoT-2026"

    def test_chain_proof_nonexistent_alert(self):
        proof = generate_chain_proof("alert-nonexistent")
        assert proof is None

    @pytest.mark.asyncio
    async def test_rest_chain_proof_endpoint(self):
        record_audit_event("alert-rest-001", "cam-100", 90, "high_trust", ["corroborated"])

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/audit/chain-proof", params={"alert_id": "alert-rest-001"})
            assert res.status_code == 200
            data = res.json()
            assert data["alert_id"] == "alert-rest-001"
            assert data["is_tamper_free"] is True

            res_404 = await client.get("/api/audit/chain-proof", params={"alert_id": "missing-id"})
            assert res_404.status_code == 404

    @pytest.mark.asyncio
    async def test_operator_verdict_and_live_eval(self):
        # Insert a dummy alert into database for testing
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO alerts
                  (id, camera_id, city, event_type, detected_at, trust_score,
                   contributing_factors, action_tier)
                VALUES
                  ('eval-alert-01', 'cam-eval-1', 'Mumbai', 'loitering', '2026-08-30T09:00:00Z', 85, '[]', 'high_trust'),
                  ('eval-alert-02', 'cam-eval-2', 'Mumbai', 'perimeter_breach', '2026-08-30T09:05:00Z', 25, '[]', 'low_trust')
                """
            )
            await db.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Submit true positive verdict for alert 1
            res_v1 = await client.post(
                "/api/alerts/eval-alert-01/verdict",
                json={"verdict": "verified", "notes": "Confirmed intruder"},
            )
            assert res_v1.status_code == 200
            assert res_v1.json()["status"] == "success"

            # Submit false positive verdict for alert 2
            res_v2 = await client.post(
                "/api/alerts/eval-alert-02/verdict",
                json={"verdict": "false_alarm", "notes": "Tree branch shadow"},
            )
            assert res_v2.status_code == 200

            # Check live eval endpoint
            res_eval = await client.get("/api/eval/live")
            assert res_eval.status_code == 200
            eval_data = res_eval.json()
            assert eval_data["total_labelled"] >= 2
            assert eval_data["precision"] is not None
            assert eval_data["accuracy"] is not None

            # Test live decay parameter on alerts endpoint
            res_alerts = await client.get("/api/alerts?decayed=true&limit=5")
            assert res_alerts.status_code == 200
            alerts_list = res_alerts.json()["alerts"]
            assert len(alerts_list) > 0
            assert "live_decayed_score" in alerts_list[0]
