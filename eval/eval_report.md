# COBRA-WATCH — IIT-B BTech Project Evaluation Report

**Date**: 2026-08-09  
**Evaluation Harness**: `eval/run_eval.py`  
**Dataset**: 25 Labeled Benchmark Scenarios (`eval/labeled_events.json`)

---

## Executive Summary

COBRA-WATCH was evaluated across 25 benchmark scenarios representing real-world IoT surveillance camera deployments and threat events. The evaluation compares three trust scoring models implemented in the system:

1. **Weighted Average (WA — Baseline)**: Heuristic scoring model (v1).
2. **Advanced Category-Aware Engine (Primary BTP Engine)**: Incorporates NVD CWE vulnerability categories, signal latency penalties, and critical security gates (Swami 2025, Oliver 2025).
3. **Bayesian Log-Odds Posterior Model**: Probabilistic trust model (Ferraris 2024, Swami 2025).

---

## 3-Model Comparative Results

| Metric | WA Baseline (v1) | Advanced Primary (BTP Engine) | Bayesian Log-Odds (Probabilistic) |
|---|---|---|---|
| **Accuracy** | **84.0%** | **84.0%** | **80.0%** |
| **Precision** | 73.33% | 73.33% | **75.0%** |
| **Recall** | **100.0%** | **100.0%** | 81.82% |
| **F1 Score** | **84.62%** | **84.62%** | 78.26% |
| **Action Tier Match** | **80.0%** | **80.0%** | 76.0% |

> [!IMPORTANT]
> **Key Finding for BTP Presentation:**  
> Both WA and Advanced Primary engines achieve **100% Recall** (0 False Negatives across all 25 scenarios) — meaning **zero genuine surveillance threat events are missed or erroneously silenced**.

---

## Feature Module Summary (Grounding in Literature)

| Module | Literature Grounding | Implementation | Verification Status |
|---|---|---|---|
| **Module A: Time-Decay Volatility** | Griffioen & Doerr (ACM CCS 2020) | $S(t) = S_0 \cdot e^{-\lambda t}$ with $T_{1/2} = 48\text{h}$ | ✅ Passed (`test_decay_pipeline.py`) |
| **Module B: Probabilistic Scoring** | Swami et al. (2025), Ferraris (2024) | Bayesian log-odds posterior $P(T \mid E)$ | ✅ Passed (`test_trust_score_service.py`) |
| **Module C: CVE Category Weights** | Oliver (2025), Famera (2025) | NVD CWE tag mapping (`auth_bypass`, `rce`, `memory_corruption`) | ✅ Passed (`test_cve_categories.py`) |
| **Module D: Heartbeat & Signal Factor** | YOLO Review (ResearchGate 2025) | Async TCP ping latency & reachability penalty | ✅ Passed (`test_heartbeat_service.py`) |
| **Module E: Persistent Merkle Audit** | BIoT SLR (MDPI 2026), Zhang (2020) | SQLite-backed SHA-256 hash-chain REST API | ✅ Passed (`test_audit_persistence.py`) |
| **Module F: Re-ID Corroboration** | Nayak et al. (iSES 2019) | Cosine similarity $S_{\text{cos}} \ge 0.80$ on 64D embeddings | ✅ Passed (`test_reid_corroboration.py`) |
| **Module G: Analytics Dashboard** | Synthesis of all 5 Clusters | React `AnalyticsPanel.jsx` with histogram, timeline, audit, decay | ✅ Complete & Integrated |
| **Module H: Eval Harness** | Benchmark Evaluation | 25-scenario evaluation harness (`eval/run_eval.py`) | ✅ 261/261 Unit Tests Passed |

---

## How to Run Evaluation Harness

```powershell
# Run 3-model comparative report
python eval/run_eval.py --mode comparative

# Run specific model evaluation
python eval/run_eval.py --mode advanced

# Run full backend test suite (261 unit & integration tests)
python -m pytest tests/ -v --tb=short
```
