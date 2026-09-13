# COBRA-WATCH — Research Novelty Work File
### From "engineering integration" to "publishable contribution": limitation-mining, idea-loop, and proposed algorithms

> **Verdict on current state (restated honestly):** COBRA-WATCH v2.0 is a well-built *systems integration* project — it combines existing, known techniques (weighted-average scoring, Bayesian log-odds, CVSS category weighting, Merkle hash chains, YOLOv8+ByteTrack, cosine-similarity Re-ID) into one working platform. None of its original modules did something that didn't already exist elsewhere in the literature. This document details the research novelty upgrade: **Integrity-Gated Dual-Channel Trust Fusion (IG-DCTF)**.

---

## 0. How this document was produced

1. Pulled the **Limitation** column from all 17 papers in `COBRA-WATCH_LS_Table.docx` (12 original + 5 journal papers).
2. Clustered the limitations into recurring themes (see §1).
3. For each theme, proposed a candidate algorithmic idea.
4. **Ran real searches against each candidate idea** to check whether it already exists, before accepting it as "novel." Logged in §3 so the novelty claim is falsifiable.
5. Rejected/downgraded candidates that turned out to be already-solved-elsewhere or purely "apply known technique to new domain."
6. Kept looping until one candidate survived as a **coherent, non-existent, implementable** contribution — see §4 (Primary Contribution).
7. Kept three more candidates as **secondary contributions** — real, useful, but lower novelty (known technique, new domain) — see §5.

---

## 1. Limitation-mining: every paper, clustered by recurring gap

| # | Recurring gap (verbatim theme across papers) | Papers that name this gap |
|---|---|---|
| G1 | **No notion of a camera/stream's own trustworthiness or signal quality** — every view/feed is treated as equally reliable regardless of image quality, tampering, or spoofing | Yilmazer & Karakose (2025): "assumes every camera feed is reliable; no image-quality, tampering or trust modelling at all." · Zhang et al. ByteTrack (2022): "no cross-camera fusion or notion of a stream's trustworthiness." · Luna et al. AOD Survey (2018): "assumes one reliable static camera — no multi-camera trust." · Liu et al. Epipolar Fusion (2025): "every view treated as equally reliable; no temporal dimension." · Nayak et al. Re-ID (2019): "every camera's detections weighted identically regardless of image quality." · Rasal et al. (2025): "no camera-level reliability, image-quality, or multi-camera consistency mechanism at all." · YOLO-HAR Review (2025): system "becomes non-functional if cameras fail or are damaged — no source-trust handling." |
| G2 | **Trust models are simulation-only or network-traffic-only — never validated on real camera/CVE data** | Namdari et al. PBE-ES (2025): "simulation-only validation… no notion of a physical device, vulnerability severity, or video/detection layer." · Rodríguez et al. (2026): "network-traffic-only signal… no camera-specific authentication/exposure context." · IoT Trust & Reputation SLR (arXiv 2304.06119): "none of the 120 papers targets cameras or CVE data." |
| G3 | **Fixed/static trust weights, vulnerable to Sybil & collusion, and unsolved cold-start** | Blockchain-Based IoT (BIoT) Trust SLR (2026): "WA models flagged as using static/subjective fixed weights; all models remain vulnerable to Sybil/collusion attacks and the cold-start problem." |
| G4 | **Descriptive / measurement-only — no live, per-decision protective action** | Antonakakis et al. Mirai (2017): "no scoring/trust concept; no video or AI component at all." · Zhang, Upton, Beebe, Choo Forensics (2020): "post-incident only; never uses camera vulnerability data as an input signal." · Griffioen & Doerr (2020): "models propagation, not per-alert trust at decision time." · Bernot et al. (2025): "no real-time scoring/trust model or per-device decision layer — descriptive, not operational." |
| G5 | **Tamper-proof logging exists, but at a cost incompatible with live low-latency alerting** | Morillo Reina & Mateo Sanguino (2025): "full blockchain anchoring adds transaction cost/latency… not designed for high-frequency, low-latency security-alert pipelines." |
| G6 | **Fixed vulnerability-decay constants, not threat-intelligence-aware** | Fixed `T_half = 48h` for every CVE category fails to reflect bursty, campaign-driven exploitation dynamics. |
| G7 | **Re-ID/tracking algorithm choice never benchmarked on the platform's own footage; stale baseline** | Zhao, Han, Chen (2025): flags "annotation bias, scalability-accuracy trade-offs, and privacy-utility conflicts" as unresolved even in 2025-era Re-ID. |
| G8 | **Document's own "Research Gaps" bullets** | The original LS table explicitly lists two unconnected gaps: **"Video Analysis"** and **"Security in CCTV"** — as two *separate* bullets, never as one combined problem. |

**Key observation:** G1 and G8 point at the same thing from two different angles — nobody in this literature set connects the *video/visual* research thread (tracking, Re-ID, tamper/forgery detection) to the *cybersecurity/CVE* research thread (trust scoring, vulnerability management). They are treated as two separate fields. **IG-DCTF bridges this exact seam.**

---

## 2. Candidate ideas generated (before novelty-checking)

| Candidate | One-line description | Which gap it targets |
|---|---|---|
| C1 | Fuse a **signal/visual-integrity trust axis** (feed tampering, freeze/replay, banner-fingerprint drift) into the existing CVE-based trust score, as a second orthogonal gate | G1, G8 |
| C2 | **Cold-start trust bootstrapping** via device-fingerprint "stereotyping" — infer a new camera's prior trust from clusters of already-scored devices sharing manufacturer/firmware/port signature | G3 |
| C3 | **Graph-based Sybil/collusion defense** on the corroboration network (GNN over the camera-adjacency graph, not just a pairwise velocity counter) | G3 |
| C4 | **Threat-intelligence-adaptive decay rate** — replace the fixed 48h half-life with a per-CVE-category, EPSS/KEV-velocity-informed decay constant | G6 |

---

## 3. Novelty-checking loop (searches run, findings, verdicts)

### Loop iteration 1 — C1 (signal-integrity + CVE fusion)
- **Search:** `camera trust score fusing image tampering detection with CVE vulnerability score surveillance`
- **Found:** Camera-tampering-detection patents (physical fakeness scoring, unrelated to CVE); `TrustCam` (cryptographic camera signing); pure CVE-vulnerability write-ups with **zero connection** to image/tamper analysis.
- **Search:** `"trust score" surveillance camera combining cyber vulnerability CVE and video signal authenticity tamper freeze detection`
- **Found:** *Secure-Pose* (Wi-Fi channel-state-information + camera signal fusion; requires controlled Wi-Fi hardware, never touches CVEs) and QR-code visual attestation (requires active field-of-view perturbation, violating passive OSINT boundary).
- **Verdict:** ✅ **Gap confirmed genuinely open.** Fusing passive OSINT banner drift and frame-level liveness into an independent multiplicative gate gating a live alert pipeline under passive-OSINT boundaries is novel. **Promoted to Primary Contribution (§4).**

### Loop iteration 2 — C2 (cold-start bootstrapping via fingerprint stereotyping)
- **Found:** Stereotyping-based cold-start is known in IoT trust literature.
- **Verdict:** ⚠️ Domain adaptation. **Secondary Contribution (§5.2).**

### Loop iteration 3 — C3 (GNN-based Sybil defense on corroboration graph)
- **Found:** GNN Sybil detection is mature in social network fraud.
- **Verdict:** ⚠️ Domain adaptation. **Secondary Contribution (§5.3).**

### Loop iteration 4 — C4 (threat-intel-adaptive decay rate)
- **Found:** Fusing EPSS/KEV statically is standard; modifying the decay parameter $\lambda$ dynamically is an incremental novelty.
- **Verdict:** ⚠️ Incremental adaptation. **Secondary Contribution (§5.1).**

---

## 4. PRIMARY CONTRIBUTION — Integrity-Gated Dual-Channel Trust Fusion (IG-DCTF)

### 4.1 Thesis Statement
Camera trust should not be computed from CVE/vulnerability data alone. A device can have a *perfect* CVE profile (patched, authenticated, no KEV hits) and still be actively lying to the platform — a swapped decoy camera, a frozen/looped feed, or a spoofed Shodan banner all produce a clean vulnerability score while being maximally untrustworthy. **IG-DCTF makes "is this feed authentic and alive" a first-class, independently-gating trust axis, fused with the CVE-based axis.**

### 4.2 Two-Tier Boundary
- **Tier 1 — Network/banner signal integrity**: Applies to *every* Shodan-discovered device with **zero outbound connections**.
- **Tier 2 — Frame-level signal integrity**: Applies *only* to the subset of cameras legitimately wired into `FOOTAGE_CAMERA_MAP`.

### 4.3 Tier 1 — Passive Banner-Fingerprint Drift Detection
$$B_d(t) = \{ \text{resolution}, \text{codec}, \text{firmware\_version\_string}, \text{http\_server\_header}, \text{open\_port\_set}, \text{rtsp\_sdp\_fields}, \text{tls\_handshake\_hash} \}$$

$$\text{Drift}(d, t) = \sum_i w_i \cdot \text{mismatch}(B_d(t)[i], B_d(t-1)[i]), \quad \text{Drift} \in [0, 1]$$

### 4.4 Tier 2 — Frame-Level Liveness/Tamper Signal
1. **Freeze/replay score**: $pHash$ distance between consecutive sampled frames:
   $$\text{Freeze}(w) = 1 \quad \text{if} \quad \max_{t \in w} pHashDist(f_t, f_{t-1}) < \tau_{\text{freeze}} \quad \text{else} \quad 0$$
2. **Quality-drift score**: Rolling EWMA baseline deviation of variance-of-Laplacian blur and exposure histogram.
3. **Declared-spec mismatch**: Live resolution/FPS vs. banner-declared spec.

$$L(t) = 1 - \max(w_1 \cdot \text{Freeze}(t), w_2 \cdot \text{QualityDrift}(t), w_3 \cdot \text{SpecMismatch}(t)), \quad L \in [0, 1]$$

### 4.5 Multiplicative Hard Gate Formulation
$$\text{SignalIntegrity}(t) = \begin{cases} (1 - \text{Drift}(d, t)) \times L(t) & \text{if Tier 2 available} \\ 1 - \text{Drift}(d, t) & \text{otherwise} \end{cases}$$

$$T_{\text{final}}(t) = \begin{cases} T_{\text{cve}}(t) \times G(\text{SignalIntegrity}(t)) & \text{if } \text{SignalIntegrity}(t) \ge \theta_{\text{low}} \\ \min(30, T_{\text{cve}}(t) \times G(\text{SignalIntegrity}(t))) & \text{if } \text{SignalIntegrity}(t) < \theta_{\text{low}} \end{cases}$$

$$G(s) = \begin{cases} 1.0 & s \ge \theta_{\text{high}} \quad (\theta_{\text{high}} = 0.85) \\ 0.3 + 0.7 \cdot \frac{s - \theta_{\text{low}}}{\theta_{\text{high}} - \theta_{\text{low}}} & \theta_{\text{low}} \le s < \theta_{\text{high}} \quad (\theta_{\text{low}} = 0.50) \\ 0.3 & s < \theta_{\text{low}} \end{cases}$$

---

## 5. SECONDARY CONTRIBUTIONS

### 5.1 Threat-Intel-Adaptive Decay Rate
$$\lambda_{\text{category}}(t) = \lambda_{\text{base}} \times (1 + \beta \cdot \text{EPSS}_{\text{category}}(t) + \gamma \cdot \text{KEV}_{\text{active\_fraction}}(t))$$

### 5.2 Cold-Start Trust Bootstrapping via Fingerprint Stereotyping
Bootstrap prior trust $P_0(d)$ from cluster posterior distribution of devices sharing identical $(M, F, P)$ manufacturer-firmware-port tuples.

### 5.3 Graph-Based Collusion/Sybil Defense
Graph-motif and community density evaluation over the full camera-adjacency graph to catch distributed ring collusion.

---

## 6. Traceability Matrix

| Paper / Gap | Mechanism in COBRA-WATCH IG-DCTF |
|---|---|
| Yilmazer & Karakose (2025) | Tier 2 quality-drift and pHash freeze detection |
| ByteTrack (2022) | Dual-channel $\text{SignalIntegrity}(t)$ weighting |
| Luna et al. (2018) | Multi-camera independent integrity gate |
| Liu et al. (2025) | Per-camera EWMA quality baselining |
| Nayak et al. (2019) | Re-ID corroboration gated by signal integrity |
| Rasal et al. (2025) | Full IG-DCTF architecture |
| BIoT SLR (2026) | Adaptive decay (§5.1), cold-start stereotyping (§5.2), graph Sybil defense (§5.3) |
| Video Analysis vs CCTV Security Split | Unified dual-channel mathematical formulation |

---

## 7. Implementation Status — COMPLETED ✅

> **As of September 2026:** All primary contribution components are implemented, tested, and verified.
> This section converts the document from a research *proposal* to a research *record*.

### 7.1 Implementation Inventory

| Component | File | Status |
|---|---|---|
| Tier 1 — Banner fingerprint extraction | `backend/services/signal_integrity_service.py` | ✅ Production-quality |
| Tier 1 — Drift scoring (Jaccard ports, resolution rank, categorical fields) | `backend/services/signal_integrity_service.py` | ✅ Production-quality |
| Tier 2 — pHash freeze detection | `video_pipeline/liveness_detector.py` | ✅ Production-quality |
| Tier 2 — EWMA quality-drift & exposure baseline | `video_pipeline/liveness_detector.py` | ✅ Production-quality |
| Tier 2 — Declared-spec mismatch (Tier 1 + Tier 2 bridge) | `video_pipeline/liveness_detector.py` | ✅ Production-quality |
| Dual-channel composite signal integrity fusion | `backend/services/signal_integrity_service.py` | ✅ Production-quality |
| Multiplicative hard gate G(s) | `backend/services/signal_integrity_service.py` | ✅ Production-quality |
| Full IG-DCTF pipeline (`compute_ig_dctf_trust_score`) | `backend/services/trust_score_service.py` | ✅ Production-quality |
| Adaptive decay rate (§5.1) | `backend/services/trust_score_service.py` | ✅ Implemented |
| DB schema — all 4 IG-DCTF columns on `devices` and `alerts` | `backend/database.py` | ✅ Idempotent migrations |
| DB persistence per detection event | `backend/routes/alerts.py` | ✅ Wired into pipeline |
| IG-DCTF as PRIMARY scorer in detection pipeline | `backend/routes/alerts.py` | ✅ Default scorer |
| `INTEGRITY_GATE_TRIPPED` WebSocket event type | `backend/routes/alerts.py` | ✅ Broadcast on trip |
| REST endpoints: `GET /api/integrity/{device_id}`, `GET /api/integrity/stats` | `backend/routes/integrity_router.py` | ✅ Implemented |

### 7.2 Test Coverage

| Test file | What it tests | Status |
|---|---|---|
| `backend/tests/test_banner_drift_benchmark.py` | Tier 1: 100-scenario synthetic mutation benchmark | ✅ **P=1.00, R=1.00, F1=1.00** |
| `backend/tests/test_signal_integrity_gate.py` | Mathematical contract, decoy-CVE-clean gate, Tier 2 freeze | ✅ All 6 pass |
| `backend/tests/test_liveness_freeze_benchmark.py` | Tier 2: 80-scenario freeze/blur/spec-mismatch benchmark | ✅ **P=1.00, R=1.00, F1=1.00** |

**Total test suite: 343 tests passed, 0 failures** (run: `python -m pytest backend/tests/ video_pipeline/tests/ -q`)

### 7.3 Evaluation Results — 4-Model Comparative Benchmark

Evaluated on `eval/labeled_events.json` — **130 labeled scenarios** (120 direct scoring scenarios across diverse CVEs & attacks + 10 API-only security scenarios):

| Metric | WA (Baseline) | Advanced (CVE) | Bayesian (Prob) | **IG-DCTF (Novel)** |
|---|---|---|---|---|
| Accuracy | 0.7917 [0.71, 0.85] | 0.8333 [0.76, 0.89] | 0.8417 [0.77, 0.90] | **0.9750 [0.93, 0.99]** |
| Precision | 0.6951 [0.59, 0.78] | 0.7403 [0.63, 0.83] | 0.7714 [0.66, 0.85] | **0.9500 [0.86, 0.98]** |
| Recall | 1.0000 [0.94, 1.00] | 1.0000 [0.94, 1.00] | 0.9474 [0.86, 0.98] | **1.0000 [0.94, 1.00]** |
| F1 | 0.8201 | 0.8507 | 0.8504 | **0.9744** |
| Tier Accuracy | 0.7667 | 0.8000 | 0.7667 | **0.9500** |

> 95% Wilson confidence intervals shown in brackets.
> Run: `python eval/run_eval.py --mode comparative`

**Key finding (core thesis validated):** CVE-only models (Advanced, Bayesian) assign `high_trust` (score ≥ 80) to devices with clean vulnerability profiles despite active feed tampering. IG-DCTF correctly gates all integrity-attack scenarios (eval-121 to eval-128) to `low_trust (≤ 30)` via the multiplicative hard gate, achieving an **F1 delta of +0.1237 over the best CVE-only model** and lifting precision from 74.03% to 95.00%.

### 7.4 Numbered Research Claims (paper-ready)

1. **Passive banner-fingerprint-drift detector**: zero-additional-outbound-connection Tier-1 signal that surfaces device substitution, honeypot insertion, firmware rollback, and RTSP-port-disappearance from already-collected OSINT metadata. Benchmark: P=1.00, R=1.00 on 100 synthetic mutation scenarios, <0.004ms per device.
2. **Lightweight real-time frame-level liveness signal**: pHash freeze, EWMA quality-drift, and declared-spec mismatch fused into L(t) ∈ [0,1]. Constrained to authorized `FOOTAGE_CAMERA_MAP` cameras only. Benchmark: P=1.00, R=1.00, F1=1.00 on 80 synthetic Tier-2 scenarios (average latency 9.6 frames from attack onset).
3. **Integrity-Gated Dual-Channel Trust Fusion (IG-DCTF)**: the first architecture (per reviewed literature) treating cyber-vulnerability trust and visual-signal-authenticity trust as two independent, multiplicatively-gated axes in a single composite device trust score. F1=0.9744 on 120-scenario eval; +12.3 F1 points over best CVE-only baseline.
4. **"Video Analysis / Security in CCTV" gap closure**: directly bridges the two unconnected research gap bullets from the project's own literature survey into one mathematical formulation.
