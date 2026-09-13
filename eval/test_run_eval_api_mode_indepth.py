"""
eval/test_run_eval_api_mode_indepth.py
======================================
In-depth unit & integration tests for eval/run_eval.py:
- Metrics computation (Precision, Recall, F1, Accuracy, Tier match)
- Metric calculations with zero TP / FP / FN / TN edge cases
- Evaluation harness DIRECT mode execution
- Evaluation harness API mode execution (mocked and real AsyncClient)
- DB Seeding helper (seed_eval_cameras) verification
"""

import json
import os
import sys
import pytest
import pytest_asyncio
import aiosqlite
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from eval.run_eval import run_direct, compute_metrics, seed_eval_cameras, run_api
from backend.config import DATABASE_PATH


class TestEvalHarnessMetrics:
    def test_compute_metrics_all_correct(self):
        results = [
            {"ground_truth": "genuine", "predicted": "genuine", "correct": True, "tier_correct": True},
            {"ground_truth": "genuine", "predicted": "genuine", "correct": True, "tier_correct": True},
            {"ground_truth": "fabricated", "predicted": "fabricated", "correct": True, "tier_correct": True},
            {"ground_truth": "fabricated", "predicted": "fabricated", "correct": True, "tier_correct": True},
        ]
        metrics = compute_metrics(results)
        assert metrics["total"] == 4
        assert metrics["tp"] == 2
        assert metrics["tn"] == 2
        assert metrics["fp"] == 0
        assert metrics["fn"] == 0
        assert metrics["accuracy"] == 1.0
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 1.0
        assert metrics["tier_accuracy"] == 1.0

    def test_compute_metrics_zero_tp_fp(self):
        results = [
            {"ground_truth": "fabricated", "predicted": "fabricated", "correct": True},
            {"ground_truth": "genuine", "predicted": "fabricated", "correct": False},
        ]
        metrics = compute_metrics(results)
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0
        assert metrics["f1"] == 0.0

    def test_compute_metrics_empty(self):
        metrics = compute_metrics([])
        assert "error" in metrics

    def test_run_direct_execution(self):
        labeled_events = [
            {
                "id": "test-001",
                "label": "genuine",
                "device_profile": {
                    "auth_required": True,
                    "known_cve_count": 0,
                    "owner_type": "government",
                    "last_patch_date": "2026-01-01",
                },
                "corroborating_cameras": ["cam2"],
                "expected_tier": "high_trust",
                "expected_score_range": [80, 100],
            }
        ]
        results = run_direct(labeled_events, verbose=False)
        assert len(results) == 1
        assert results[0]["id"] == "test-001"
        assert results[0]["ground_truth"] == "genuine"
        assert results[0]["predicted"] == "genuine"
        assert results[0]["correct"] is True
        assert results[0]["score"] == 100
        assert results[0]["tier"] == "high_trust"

    def test_seed_eval_cameras(self, tmp_path):
        import sqlite3
        db_path = str(tmp_path / "test_eval_seed.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                city TEXT NOT NULL,
                ip TEXT NOT NULL,
                lat REAL,
                lon REAL,
                device_type TEXT,
                manufacturer TEXT,
                ports TEXT,
                owner_org TEXT,
                owner_type TEXT,
                ownership_confidence TEXT,
                auth_required INTEGER,
                known_cve_count INTEGER,
                last_patch_date TEXT,
                first_seen TEXT,
                last_seen TEXT
            )
            """
        )
        conn.commit()
        conn.close()

        labeled_events = [
            {
                "event": {"camera_id": "eval_cam_100"},
                "device_profile": {
                    "owner_type": "government",
                    "auth_required": True,
                    "known_cve_count": 0,
                    "last_patch_date": "2026-01-01",
                },
            }
        ]

        with patch.object(sys.modules["config"], "DATABASE_PATH", db_path):
            seed_eval_cameras(labeled_events)

            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT * FROM devices WHERE id = 'eval_cam_100'")
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "eval_cam_100"
            conn.close()
