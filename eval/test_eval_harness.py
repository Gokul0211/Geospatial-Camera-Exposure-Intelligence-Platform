"""
test_eval_harness.py
=====================
Unit testing suite for eval/run_eval.py metrics and evaluation runner.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "eval"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from run_eval import compute_metrics, run_direct


class TestEvalMetrics:
    def test_compute_metrics_perfect_score(self):
        results = [
            {"ground_truth": "genuine", "predicted": "genuine", "correct": True},
            {"ground_truth": "genuine", "predicted": "genuine", "correct": True},
            {"ground_truth": "fabricated", "predicted": "fabricated", "correct": True},
        ]
        metrics = compute_metrics(results)
        assert metrics["accuracy"] == 1.0
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 1.0

    def test_compute_metrics_zero_division_guard(self):
        results = [
            {"ground_truth": "fabricated", "predicted": "fabricated", "correct": True},
        ]
        metrics = compute_metrics(results)
        # TP=0, FP=0, FN=0 -> Precision=0, Recall=0, F1=0 without division by zero crash
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0
        assert metrics["f1"] == 0.0

    def test_compute_metrics_empty_input(self):
        metrics = compute_metrics([])
        assert "error" in metrics


class TestEvalDirectRunner:
    def test_run_direct_executes_without_error(self):
        labeled_events = [
            {
                "id": "eval-test-01",
                "label": "genuine",
                "device_profile": {
                    "auth_required": True,
                    "known_cve_count": 0,
                    "owner_type": "government",
                    "last_patch_date": "2026-01-01",
                },
                "corroborating_cameras": ["cam_01", "cam_02"],
                "expected_tier": "high_trust",
                "expected_score_range": [80, 100],
            }
        ]
        results = run_direct(labeled_events, verbose=False)
        assert len(results) == 1
        assert results[0]["id"] == "eval-test-01"
        assert results[0]["predicted"] == "genuine"
        assert results[0]["score"] == 100
        assert results[0]["correct"] is True
