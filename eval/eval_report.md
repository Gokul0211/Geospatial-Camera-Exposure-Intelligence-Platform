# COBRA-WATCH — 4-Model Benchmark & Research Evaluation Report

**Date**: September 2026  
**Evaluation Harness**: `eval/run_eval.py`  
**Dataset**: 130 Labeled Benchmark Scenarios (`eval/labeled_events.json`)  
*(120 Direct Scoring Scenarios + 10 API-Layer Security/Protocol Scenarios)*  
**Primary Novel Architecture**: Integrity-Gated Dual-Channel Trust Fusion (IG-DCTF)

---

## Executive Summary

COBRA-WATCH was evaluated across **130 benchmark scenarios** covering diverse camera hardware profiles, CVE categories (RCE, Auth Bypass, Command Injection, Memory Corruption, Info Disclosure, XSS), spatial-temporal corroboration densities, network latency states, active adversarial attacks (replay, timestamp skew, spoofed adjacency, parameter injection, collusive velocity anomalies), and **novel integrity-tamper vectors** (decoy camera substitution, honeypot headers, RTSP loop/freeze, severe blur/occlusion, and spec-mismatch MITM).

The evaluation compares four trust scoring models:
1. **Weighted Average (WA — Baseline)**: Deterministic heuristic linear scoring (v1).
2. **Advanced Category-Aware Engine (CVE-Only)**: NVD CWE vulnerability categories, signal latency penalties, and critical authentication gates (Swami 2025, Oliver 2025, Famera 2025).
3. **Bayesian Log-Odds Posterior Model (Probabilistic)**: Probabilistic likelihood-ratio fusion model (Ferraris 2024, Swami 2025).
4. **IG-DCTF (Proposed Novel Engine)**: Multiplicatively-gated dual-channel trust fusion combining Channel A (cyber vulnerability posture) with Channel B (Tier 1 passive banner drift + Tier 2 frame-level liveness).

---

## 4-Model Comparative Results (Direct Scoring Benchmark: $n = 120$)

All proportions are reported with **95% Wilson Score Confidence Intervals** $[\text{CI}_{\text{lower}}, \text{CI}_{\text{upper}}]$.

| Metric | WA (Baseline) | Advanced (CVE-Only) | Bayesian (Probabilistic) | **IG-DCTF (Proposed Novel)** |
|---|---|---|---|---|
| **Accuracy** | 79.17% $[0.71, 0.85]$ | 83.33% $[0.76, 0.89]$ | 84.17% $[0.77, 0.90]$ | **97.50%** $[0.93, 0.99]$ |
| **Precision** | 69.51% $[0.59, 0.78]$ | 74.03% $[0.63, 0.83]$ | 77.14% $[0.66, 0.85]$ | **95.00%** $[0.86, 0.98]$ |
| **Recall** | **100.0%** $[0.94, 1.00]$ | **100.0%** $[0.94, 1.00]$ | 94.74% $[0.86, 0.98]$ | **100.0%** $[0.94, 1.00]$ |
| **F1 Score** | 0.8201 | 0.8507 | 0.8504 | **0.9744** |
| **Action Tier Match** | 76.67% | 80.00% | 76.67% | **95.00%** |

```
Comparative Performance Overview (n=120):
WA Baseline:      [======= Accuracy 79.17% =======] [==== Precision 69.51% ====]
Advanced (CVE):   [========= Accuracy 83.33% =========] [====== Precision 74.03% ======]
Bayesian Model:   [========= Accuracy 84.17% =========] [======= Precision 77.14% =======]
IG-DCTF (Novel):  [==================== Accuracy 97.50% ====================] [================= Precision 95.00% =================]
```

> [!IMPORTANT]
> **Key Finding for Research Paper & Viva Defense:**
> - **Elimination of the CVE Blind Spot**: CVE-only models (Advanced and Bayesian) assign scores of $100$ (`high_trust`) to physically swapped decoy cameras and frozen feeds whenever their network vulnerability profile is clean. IG-DCTF detects the signal tamper via Channel B and trips the multiplicative gate ($G(s) \le 0.30$), hard-capping the score at $\le 30$ (`low_trust`).
> - **Precision Jump**: IG-DCTF improves precision from $74.03\%$ to **$95.00\%$** (+20.97 percentage points) and F1 from $0.8507$ to **$0.9744$** (+0.1237 F1 points).
> - **Zero False Negatives ($100\%$ Recall)**: Across all genuine surveillance threat events, IG-DCTF maintains $100\%$ recall, verifying that signal integrity gating does not suppress legitimate physical alerts.

---

## Dedicated Synthetic Benchmarks

### 1. Tier 1 — Passive Banner-Fingerprint Drift Benchmark
- **File**: `backend/tests/test_banner_drift_benchmark.py`
- **Corpus**: 100 programmatic mutation scenarios (decoy hardware substitutions, honeypot banners, resolution downgrades, port replacements, firmware rollbacks, and benign controls).
- **Results**:
  - Precision: **1.0000 (100.0%)**
  - Recall: **1.0000 (100.0%)**
  - F1 Score: **1.0000**
  - Processing Latency: **0.0039 ms/device** (zero runtime overhead on passive OSINT metadata).

### 2. Tier 2 — Frame-Level Visual Liveness & Tamper Benchmark
- **File**: `backend/tests/test_liveness_freeze_benchmark.py`
- **Corpus**: 80 programmatic video scenarios (30 genuine-live controls, 20 freeze/loop attacks, 20 quality-drift/blur occlusions, 10 spec-mismatch MITM relays).
- **Results**:
  - Total Scenarios: **80** (TP=50, FP=0, TN=30, FN=0)
  - Precision: **1.0000 (100.0%)**
  - Recall: **1.0000 (100.0%)**
  - F1 Score: **1.0000**
  - Average Detection Latency: **9.6 frames** from attack onset
  - Average Processing Time: **130.56 ms/scenario** on standard CPU.

---

## Complete Test Suite Status

```powershell
python -m pytest backend/tests/ video_pipeline/tests/ -q
```
- **Total Tests Passing**: **343 passed**
- **Failures**: **0**
- **Execution Time**: ~61 seconds

---

## Reproducibility Commands

```powershell
# Run the 4-model comparative evaluation report:
python eval/run_eval.py --mode comparative

# Run individual model evaluation:
python eval/run_eval.py --mode ig_dctf

# Run the 80-scenario Tier 2 liveness benchmark:
python -m pytest backend/tests/test_liveness_freeze_benchmark.py::test_80_scenario_tier2_benchmark -v -s

# Run the 100-scenario Tier 1 drift benchmark:
python -m pytest backend/tests/test_banner_drift_benchmark.py -v -s

# Run the entire test suite:
python -m pytest backend/tests/ video_pipeline/tests/ -q
```
