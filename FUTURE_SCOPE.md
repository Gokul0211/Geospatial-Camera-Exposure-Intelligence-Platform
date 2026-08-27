# COBRA-WATCH — Literature-Grounded Future Scope & System Roadmap (v2 / v3)

This document presents the complete literature-grounded Future Scope and System Roadmap for **COBRA-WATCH** (Cyber-Physical Surveillance Threat Intelligence & Detection Engine), directly mapped to a 20-paper systematic literature survey across 5 research clusters.

---

## 📚 1. Literature Survey Taxonomy & Cluster Guide

| Cluster | Focus Domain | Paper Count | Key Papers Analyzed |
|---|---|---|---|
| **[A]** | IoT & Botnet Compromise Dynamics | 4 Papers | Antonakakis et al. (2017), Zhang et al. (2020), Griffioen & Doerr (2020), Famera et al. (2025) |
| **[B]** | Video AI Detection & Tracking | 5 Papers | Yilmazer & Karakose (2025), Zhang et al. (ByteTrack 2022), Luna et al. (2018), Rasal et al. (2025), YOLO Review (2025) |
| **[C]** | Multi-Camera & Cross-View Fusion | 2 Papers | Liu et al. (Epipolar 2025), Nayak et al. (Re-ID 2019) |
| **[D]** | IoT Trust & Reputation Models | 4 Papers | IoT Trust SLR (2023), BIoT SLR (2026), Swami et al. (SCI-IoT 2025), Ferraris et al. (2024) |
| **[E]** | CCTV/IoT Vulnerability Research | 5 Papers | Bernot et al. (2025), Oliver (2025), Diva Portal (2018), Auti et al. (2025), Das et al. (Kalay SDK 2022) |

---

## 📊 2. Comparative Matrix: Paper Advantage vs COBRA-WATCH & Future Scope Additions

The table below catalogs all 20 benchmarked papers, detailing their comparative advantage over COBRA-WATCH, COBRA-WATCH's advantage over them, and the specific future scope enhancement derived from each study.

| Paper / Author / Yr [Cluster] | Methodology & Dataset | Their Advantage Over COBRA-WATCH | COBRA-WATCH's Advantage Over Them | Literature-Derived Future Scope Addition |
|---|---|---|---|---|
| **[A] Antonakakis et al. (USENIX Security, 2017)** | 7-month empirical Mirai measurement (honeypots, DNS, scan traffic). | Real, Internet-scale empirical validation across millions of live devices over 7 months. | Converts empirical insights into a real-time protective decision layer; they only observe passively. | **Dynamic Threat-Trend Weighting**: Pull live Shodan/NVD threat trend data on active exploitation vectors to dynamically adjust trust weights. |
| **[A] Zhang, Upton, Beebe, Choo (2020)** | Full-stack Mirai lab deployment & digital forensic artifact reconstruction. | Rigorous forensic methodology for reconstructing attacker C2/database/loader infrastructure post-compromise. | Real-time triage before or during an incident to stop wasted dispatch; not just post-incident. | **Forensic Compromise Attribution**: Add a forensic triage module flagging probable compromise vectors (C2, default cred loader) based on artifact taxonomies. |
| **[A] Griffioen & Doerr (ACM CCS, 2020)** | Epidemiological SIS/SIR modeling across 7,500 honeypots over 1 year. | Deep mathematical rigor on IoT population reinfection dynamics (device re-compromise in hours-days). | Actionable per-alert decision scoring; their model is purely descriptive without decision output. | **Time-Decay & Volatility Erosion**: Implement exponential trust score decay over time between scans using empirical reinfection half-life models. |
| **[B] Yilmazer & Karakose (Applied Sciences, 2025)** | ResNet101v2 keyframe filter + YOLOv8 + DeepSORT + GPT-3.5 explanation (ABODA dataset). | Published 97.4% F1 accuracy and a keyframe filter cutting compute load by ~50%. | Explanation layer is trust-conditioned—explains both event context and source stream trustworthiness. | **Keyframe Pre-filtering & Trust-Conditioned LLM**: Add motion/ResNet keyframe pre-filtering and condition LLM briefs on trust scores + factors. |
| **[B] Zhang et al. — ByteTrack (ECCV 2022)** | Two-stage BYTE association with Kalman Filter and IoU (MOT17/20, BDD100K). | Benchmark tracking robustness validated on major public multi-object tracking datasets. | Gives ByteTrack output downstream operational purpose via trust-conditioned alert gating. | **Standardized MOT Benchmarking**: Quantitatively benchmark YOLOv8+ByteTrack on CCTV footage using MOTA, IDF1, and ID-switch metrics. |
| **[B] Luna, San Miguel, Ortego, Martínez (Sensors, 2018)** | 4-stage AOD benchmark survey across 21 public video sequences. | Reproducible whole-pipeline benchmarking methodology with public ground truth. | Cross-camera, trust-aware decision layer sitting above raw video object detection. | **Systematic Pipeline Stage Benchmarking**: Use standardized benchmarking software to evaluate background subtraction and candidate validation choices. |
| **[C] Liu et al. (arXiv 2503.11088, 2025)** | Epipolar-masked cross-view attention with DINOv2 ViT (Real-IAD dataset). | Precise cross-view correspondence using geometric epipolar constraints on calibrated camera rigs. | Operates across uncalibrated, arbitrary CCTV layouts with trust-weighting. | **Epipolar-Constrained Cross-Camera Corroboration**: Apply fundamental matrix epipolar constraints for overlapping views to strengthen corroboration. |
| **[C] Nayak, Behera, Girish, Pati, Das (iSES, 2019)** | YOLOv3 + DeepSORT + MobileNet triplet-loss Re-ID for loitering tracking. | True cross-camera identity continuity via visual Re-ID across non-overlapping views. | Trust-weighted corroboration rather than equal weighting of unverified camera feeds. | **Feature-Based Visual Re-ID Hand-off**: Integrate lightweight Re-ID feature embeddings into corroboration to confirm same-person identity. |
| **[B] Rasal, Sakalley, Dhatrak, Dighe, Sonawane (LNNS, 2025)** | YOLOv8 + OpenCV rules for crowd density with instant SMS alerting. | Operational alerting channel (SMS) with practical suspicious behavior rules. | Alerts are trust-gated rather than firing on unverified raw detections, cutting false alarms. | **Tiered Trust-Gated Alert Notification Routing**: Route instant SMS/push notifications for High-Trust (80–100) alerts; send Medium/Low to triage queues. |
| **[D] IoT Trust & Reputation SLR (arXiv 2304.06119, 2023)** | Systematic review of 120 trust/reputation papers across 14 metrics. | Broad theoretical taxonomy covering AI/DL trust models (DNN, RNN, LSTM). | Applies trust concrete to physical-security CCTV with human-explainable CVE/firmware factors. | **Adaptive AI/DNN Trust Classifiers**: Train adaptive DNN trust models on labeled incident data while keeping Weighted-Average formula as explainable fallback. |
| **[D] BIoT Trust Assessment SLR (MDPI, 2026)** | PRISMA review of 122 blockchain-based IoT trust assessment models. | Explores tamper-proof, decentralized trust ledgers via blockchain. | Lightweight real-time scoring without blockchain latency or consensus overhead. | **Tamper-Evident Immutable Audit Log**: Implement a lightweight append-only Merkle/hash-chain log for storing computed trust scores and factor breakdowns. |
| **[B] YOLO in Suspicious Activity Review (2025)** | Comprehensive review of YOLO variants (v3-v7) for HAR and edge deployment. | Thorough edge deployment benchmarking (Jetson Nano/TensorRT FPS/accuracy). | Reasons about source-camera failure/compromise risks rather than becoming non-functional when cameras fail. | **Camera Health & Heartbeat Volatility Factor**: Incorporate ping latency, frame drop rate, and video signal integrity into trust score calculations. |
| **[E] Bernot, Khan, Shahzad, Karakaya, Healy (J. Cybersecurity, 2025)** | CVSS pen-testing on real Hikvision, Dahua, Avigilon cameras (VPN IPVM lab). | Live empirical pen-testing confirming CVSS 9.8 exploitability on real hardware. | Converts static pen-test audit findings into dynamic per-alert runtime trust signals. | **CVSS v3.1 Temporal & Environmental Weighting**: Incorporate CVSS Temporal (exploit maturity, remediation level) and Environmental metrics into scoring. |
| **[E] Oliver (CoVaCCI Showcase, 2025)** | NVD IP-camera CVE taxonomy and temporal trend classification. | Full temporal taxonomy of IP-camera CVE types (auth bypass, weak credentials). | Operational per-alert scoring in real time rather than population-level analytics. | **Vulnerability Category-Aware Deduction Weights**: Assign higher deductions to auth-bypass and remote code execution (-30) vs info disclosure (-10). |
| **[E] Diva Portal (KTH / PerLS'18, 2018)** | Shodan discovery + CVE database keyword matching for camera vulns. | Original proof of Shodan + CVE matching viability for camera vulnerability discovery. | Operational alert-triage layer gating physical-security events above Shodan discovery. | **Dual Censys & Shodan Passive Scanner Discovery**: Add Censys API alongside Shodan to expand coverage across private and enterprise subnets. |
| **[E] Auti, Desale, Pate, Rahane (IJSRCSEIT, 2025)** | Automated VAPT tool (Nmap + ONVIF + Nikto + Metasploit + Flask/React). | Complete automated VAPT pipeline (discovery → scan → exploit → dashboard) with 89% accuracy. | Scores alert trustworthiness rather than device exploitability alone. | **Live Automated VAPT Refresh Engine**: Connect automated scanning (Nmap/Metasploit) to dynamically verify exploitability before deducting points. |
| **[E] Das, Omurzakov, Du — Palo Alto Unit 42 (2022)** | Analysis of CVE-2021-28372 (CVSS 9.6) in ThroughTek Kalay P2P SDK (86M+ devices). | Reveals invisible third-party SDK attack surface affecting 86M+ devices ("iceberg problem"). | Corroboration layer protects against hijacked SDK cameras producing fake alerts. | **Third-Party Embedded SDK Supply-Chain Risk**: Monitor outbound traffic for third-party SDK call signatures (e.g. ThroughTek Kalay) to deduct risk points. |
| **[A] Famera, Hilger, Bhunia, Heil (arXiv 2508.01909, 2025)** | Comparative study of Mirai + 4 variants (Satori, Mukashi, Moobot, Sonic). | Deep source-code analysis of botnet variants and active CVE exploit lists (e.g. Moobot). | Triage layer operating on the defender's side of active botnet exploitation. | **Mirai/Botnet Variant-Specific CVE Penalties**: Apply heavier trust penalties (-30) for CVEs actively exploited by known botnet strains. |
| **[D] Swami, Singh, Pant — SCI-IoT (arXiv 2511.18045, 2025)** | SCI-IoT framework: 30 trust tests, 7 domains, criticality weights (1.0-2.0), critical gates. | Rigorously specified certification framework for surveillance systems (Grade B2). | Per-alert runtime scoring rather than static procurement-stage certification. | **Critical Security Gate Conditions & SCI-IoT Weighting**: Adopt SCI-IoT 1.0-2.0 criticality weights and auto-fail gates for unauthenticated streams. |
| **[D] Ferraris, Fernandez-Gago, Roman, Lopez (J. Supercomputing, 2024)** | Systemic survey of IoT trust frameworks across 15 characteristics and SDLC phases. | Deepest theoretical vocabulary for IoT trust (15 characteristics, SDLC mapping). | Instantiates 5 trust characteristics specifically for the Operations/Alert-Triage SDLC phase. | **Operations/Alert-Triage SDLC Positioning**: Position COBRA-WATCH in academic literature as an Operations-phase alert-triage model. |

---

## 🎯 3. Detailed Future Scope Modules (v2 / v3 Specifications)

### Module 1: Threat Trend-Driven Dynamic Weighting
- **Source Paper**: Antonakakis et al. (2017)
- **Technical Specification**: Implement an automated threat intelligence crawler that polls NVD, CISA Known Exploited Vulnerabilities (KEV) catalog, and Shodan Trends. Dynamically adjust trust deduction weights:
  $$\text{Deduction}_{\text{CVE}} = -25 \times (1.0 + \text{KEV\_Flag} \times 0.4)$$
- **Value**: Ensures trust scoring automatically reflects active zero-day exploitation campaigns.

### Module 2: Forensic Compromise Attribution Engine
- **Source Paper**: Zhang et al. (2020)
- **Technical Specification**: Parse alert metadata and raw network packet artifacts to classify attack signatures into a forensic taxonomy (e.g. Mirai C2 loader, brute-force scanner, command-injection payload). Highlight probable compromise vectors in the alert dashboard.

### Module 3: Time-Decay & Volatility Erosion Model
- **Source Paper**: Griffioen & Doerr (2020)
- **Technical Specification**: Incorporate a temporal half-life decay function into the trust score:
  $$S(t) = S_0 \cdot e^{-\lambda (t - t_{\text{scan}})}$$
  where $\lambda = \frac{\ln(2)}{T_{1/2}}$ and $T_{1/2} = 48 \text{ hours}$. A camera's score erodes gradually between scans, forcing periodic re-verification.

### Module 4: ResNet Keyframe Pre-filtering & Trust-Conditioned LLM Briefs
- **Source Paper**: Yilmazer & Karakose (2025)
- **Technical Specification**:
  - Add a lightweight ResNet101v2 / background subtraction keyframe filter upstream of YOLOv8 to drop redundant static frames, reducing compute overhead by ~50%.
  - Condition LLM (Groq / Claude) executive risk brief generation on both visual alert details AND source stream trust metrics:
    `"Generate risk brief for event '{event_type}' on camera '{camera_id}' with trust_score={trust_score} (Tier: {action_tier}, Factors: {factors})."`

### Module 5: Standardized MOT Benchmark Harness
- **Source Paper**: Zhang et al. (ByteTrack 2022)
- **Technical Specification**: Build an automated evaluation script that runs COBRA-WATCH's YOLOv8 + ByteTrack pipeline against standard MOT17/MOT20 benchmarks, logging MOTA, IDF1, and ID-switches to validate tracking stability.

### Module 6: Epipolar-Constrained Multi-Camera Corroboration
- **Source Paper**: Liu et al. (2025)
- **Technical Specification**: For overlapping camera pairs, compute the fundamental matrix $F$ using calibrated camera points. Verify that detected objects in Camera A satisfy the epipolar line constraint in Camera B ($x'^T F x = 0$) before granting spatial corroboration bonuses.

### Module 7: Feature Embedding Visual Re-Identification (Re-ID)
- **Source Paper**: Nayak et al. (2019)
- **Technical Specification**: Extract 512-dimensional feature embeddings (using OSNet / MobileNet-ReID) for detected persons/vehicles. When an adjacent camera detects an event within the 15-minute window, compare visual feature distance (cosine similarity $\ge 0.85$) to confirm same-entity corroboration.

### Module 8: Tiered Trust-Gated Alert Dispatcher
- **Source Paper**: Rasal et al. (2025)
- **Technical Specification**: Configure multi-channel notification routing:
  - **High-Trust (80–100)**: Instant SMS / Push notifications to field officers.
  - **Medium-Trust (50–79)**: Dashboard highlight + dispatch queue.
  - **Low-Trust (<50)**: Logged silently for audit; no active alerts.

### Module 9: Tamper-Evident Immutable Audit Log
- **Source Paper**: BIoT SLR (2026)
- **Technical Specification**: Implement an append-only Merkle tree hash log for all generated alerts and trust score computations:
  $$H_i = \text{SHA256}(H_{i-1} \parallel \text{Alert\_Data}_i)$$
  Ensures tamper-evident auditability for judicial and forensic compliance.

### Module 10: Camera Health & Signal Integrity Volatility Factor
- **Source Paper**: YOLO Review (2025)
- **Technical Specification**: Monitor RTSP ping latency, frame drop rate, and video signal noise ratio (PSNR/SSIM). Deduct up to 15 points if video signal integrity degrades or latency exceeds 1,000ms.

### Module 11: CVSS v3.1 Temporal & Environmental Score Weighting
- **Source Paper**: Bernot et al. (2025)
- **Technical Specification**: Ingest CVSS v3.1 Temporal metrics:
  $$\text{Penalty}_{\text{CVE}} = -25 \times E (\text{Exploitability}) \times RL (\text{Remediation Level})$$
  Reduces penalties for vendor-patched firmware while maximizing penalties for unpatched zero-days.

### Module 12: Vulnerability Category-Aware Deduction Weights
- **Source Paper**: Oliver (2025) & Famera et al. (2025)
- **Technical Specification**: Categorize CVEs into severity buckets:
  - **Auth Bypass / RCE**: $-30 \text{ pts}$
  - **Command Injection**: $-25 \text{ pts}$
  - **Cross-Site Scripting / Info Disclosure**: $-10 \text{ pts}$

### Module 13: Dual Censys & Shodan Passive Scanner Discovery
- **Source Paper**: Diva Portal (2018)
- **Technical Specification**: Integrate Censys Search API as a secondary passive discovery engine alongside Shodan, expanding coverage over private subnets, cloud hosts, and enterprise CCTV infrastructure.

### Module 14: Automated VAPT Engine Integration
- **Source Paper**: Auti et al. (2025)
- **Technical Specification**: Schedule automated non-destructive ONVIF/Nmap scans against monitored streams to verify actual service exposure before penalizing devices.

### Module 15: Embedded SDK Supply-Chain Risk Deduction
- **Source Paper**: Das et al. — Unit 42 (2022)
- **Technical Specification**: Analyze network traffic for third-party P2P SDK signatures (e.g. ThroughTek Kalay, TUTK, Danale). Apply a $-20 \text{ pt}$ supply-chain risk penalty for unverified third-party SDK traffic.

### Module 16: Critical Security Gate Conditions (SCI-IoT Pattern)
- **Source Paper**: Swami et al. (SCI-IoT 2025)
- **Technical Specification**: Enforce critical gate auto-fails: if `auth_required == False`, the score is hard-capped at $\le 49$ (`low_trust`), overriding positive corroboration bonuses to eliminate unauthenticated risk.

---

## 📌 Summary

By incorporating all 20 literature-backed additions, COBRA-WATCH bridges the gap between **cybersecurity vulnerability management**, **computer vision detection**, and **IoT trust theory** — establishing a novel, citable benchmark in surveillance threat intelligence research.
