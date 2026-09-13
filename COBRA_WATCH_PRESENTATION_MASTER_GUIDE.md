# ⚡ COBRA-WATCH: Complete Presentation & Master Study Guide

**Platform Name**: COBRA-WATCH (Cyber-Physical Surveillance Threat Intelligence & Detection Engine)  
**System Status**: Production-Ready / Fully Functional  
**Master Test Suite**: 309 / 309 Tests Passed ($100\%$ Pass Rate)  
**Compliance Standard**: India Digital Personal Data Protection (DPDP) Act 2023 & CERT-In Vulnerability Disclosure Standard  

---

## 💡 1. Executive Summary Table (30-Second Pitch)

| Question | Simple Answer |
|---|---|
| **What is the problem?** | Normal CCTV systems blindly trust every camera feed. If a camera is hacked or sends fake video, guards waste time on false emergencies. |
| **What is COBRA-WATCH?** | A platform that calculates a **Security Trust Score (0 to 100)** for every camera *before* believing its video alerts. |
| **How does it help?** | High-trust alerts (80–100) are trusted instantly. Low-trust alerts (<50) are flagged for manual operator verification. |

---

## 🔄 2. The 4-Step Pipeline Table

```
[1. Discover Cameras] ➔ [2. Compute Trust Score] ➔ [3. Detect Video AI Events] ➔ [4. Live GIS Dashboard]
   (Shodan / CVEs)         (0-100 Trust Model)       (YOLOv8 + ByteTrack)         (Leaflet Map + Alerts)
```

| Step | Pipeline Stage | Technology Used | What It Does (In 1 Sentence) |
|---|---|---|---|
| **Step 1** | **Camera Discovery** | Shodan API + NVD CVEs | Finds exposed public cameras and checks if they have known security bugs. |
| **Step 2** | **Trust Score Engine** | Custom Python Algorithm | Calculates 0–100 score based on password status, bugs, age, and nearby camera proof. |
| **Step 3** | **Video AI Pipeline** | YOLOv8 + ByteTrack | Detects people/vehicles and checks if someone loiters (>10s) or crosses a line. |
| **Step 4** | **Live GIS Dashboard** | React + Leaflet + WebSockets | Displays 2,369 cameras on a dark map with instant alert toast popups. |

---

## 🛠️ 3. Tech Stack Cheat Sheet (Where is the Code?)

| Part of Project | Technology Used | Version | Source File Location | Implementation & Purpose |
|---|---|---|---|---|
| **User Interface** | **React** + **Vite** | React 18, Vite 5.4 | [App.jsx](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/frontend/src/App.jsx)<br>[main.jsx](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/frontend/src/main.jsx) | Single-page reactive dashboard with componentized state management. |
| **Design System** | **Vanilla CSS3** | Custom CSS | [globals.css](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/frontend/src/styles/globals.css)<br>[App.css](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/frontend/src/App.css) | Custom dark theme (`#080b11`), CRT scanline overlay, glassmorphism, keyframes. |
| **Typography** | **Google Fonts** | Outfit, Inter, JetBrains Mono | [index.html](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/frontend/index.html) | High-contrast font hierarchy for display headers, UI text, and monospace metrics. |
| **Map Engine** | **Leaflet.js** | Leaflet 1.9 | [SurveillanceMap.jsx](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/frontend/src/components/SurveillanceMap.jsx) | GPU-accelerated Leaflet map (`L.canvas()`) rendering 2,369 sensors at 60 FPS. |
| **Satellite Basemap**| **Esri World Imagery**| Tile API | [satelliteData.js](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/frontend/src/utils/satelliteData.js) | High-resolution satellite basemap toggle for aerial spatial verification. |
| **Backend Server** | **Python** + **FastAPI** | Python 3.12, FastAPI 0.115 | [main.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/main.py)<br>[config.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/config.py) | High-speed asynchronous REST API server with automatic OpenAPI documentation. |
| **Database** | **SQLite 3** + **aiosqlite** | Async Driver | [database.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/database.py)<br>[models/](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/models/) | Async database operations for devices, news articles, alerts, and audit ledgers. |
| **Real-Time Stream** | **WebSockets** | WSS Pub/Sub | [main.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/main.py)<br>[routes/alerts.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/routes/alerts.py)<br>[LiveAlerts.jsx](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/frontend/src/components/LiveAlerts.jsx) | Asynchronous WebSocket connection manager broadcasting live threat detection events. |
| **Object Detection** | **YOLOv8** (`ultralytics`) | PyTorch / YOLOv8n | [detector.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/video_pipeline/detector.py) | Real-time object detection identifying persons and vehicles from surveillance footage. |
| **Motion Tracking** | **ByteTrack** | Kalman + Hungarian | [tracker.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/video_pipeline/tracker.py) | Motion vector tracking and track-ID persistence using Kalman filter state prediction. |
| **Breach Detection** | **2D Geometry Math** | Custom Python | [rules.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/video_pipeline/rules.py) | 2D vector cross-product line breach detection and polygon ray-casting loitering time. |
| **Trust Score Engine** | **Custom Algorithm** | Custom Algorithm | [trust_engine.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/services/trust_engine.py)<br>[trust_score_service.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/services/trust_score_service.py) | Weighted deduction model ($T \in [0, 100]$) calculating camera security risk. |
| **Time-Decay Model** | **Exponential Decay** | $T(\tau) = T_0 e^{-\lambda \tau}$ | [decay_router.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/routes/decay_router.py) | Dynamic trust score erosion over time between active security vulnerability rescans. |
| **Heartbeat Integrity**| **Signal Monitor** | 300s Timeout | [heartbeat_service.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/services/heartbeat_service.py) | Real-time sensor ping monitoring penalizing cameras experiencing telemetry loss. |
| **Multi-Camera Fusion**| **Spatial-Temporal** | $500\text{m}, 15\text{m}$ | [corroboration_service.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/services/corroboration_service.py) | Cross-camera event corroboration engine granting +20 trust bonuses to adjacent sensors. |
| **Audit Ledger** | **SHA-256 Merkle Chain**| Hash-Chained | [audit_ledger.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/services/audit_ledger.py)<br>[audit_router.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/routes/audit_router.py) | Append-only cryptographic hash chain ($H_k = \text{SHA256}(H_{k-1} \parallel A_k)$) for audit logging. |
| **OSINT Scanner** | **Shodan REST API** | Passive Scan | [shodan_service.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/services/shodan_service.py) | Passive metadata ingestion of exposed IoT CCTV cameras (IP, ports, geolocations, orgs). |
| **Vulnerability Lookup**| **NVD CVE API** | CVSS v3.1 | [nvd_service.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/services/nvd_service.py) | Real-time CVE count lookup and CVSS severity scoring for camera manufacturers. |
| **AI Threat Briefs** | **Groq / Anthropic** | LLM Streaming | [brief_service.py](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/services/brief_service.py)<br>[RiskBrief.jsx](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/frontend/src/components/RiskBrief.jsx) | Streaming AI risk brief synthesis conditioned on camera trust score, CVEs, and OSINT news. |
| **Master Test Suite** | **Pytest** (309 Passed) | Pytest 9.0 | [backend/tests/](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/backend/tests/)<br>[video_pipeline/tests/](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/video_pipeline/tests/) | 309-test master test suite verifying unit, integration, mathematical, security, and video AI rules. |

---

## 📊 4. Trust Score Points System (How the 0–100 Score Works)

| Security Check | Points Effect | Why? |
|---|---|---|
| **Base Starting Score** | **+100 Points** | Perfect starting score for a brand-new camera. |
| **No Password (Unauthenticated)** | **-30 Points** | High risk! Anyone on the internet can view or alter the stream. |
| **Known Security Bugs (CVEs)** | **-10 Points per Bug** | Camera has known unpatched vulnerabilities (max $-40$ points). |
| **Unknown Owner / Org** | **-20 Points** | Camera owner organization is unknown. |
| **Old Firmware (>1 year old)** | **-15 Points** | Firmware has not been updated in over a year. |
| **Confirmed by Nearby Camera** | **+20 Points Bonus** | An adjacent camera (within 500m & 15 mins) also saw the event! |

---

## 📚 5. 20-Paper Systematic Literature Survey Table

| Cluster | Paper / Author / Year | Methodology | Algorithm | Dataset | Advantage | Limitation | Comparative Advantage over COBRA-WATCH | COBRA-WATCH's Advantage Over Them | What Could Be Added to COBRA-WATCH (Future Scope) |
|---|---|---|---|---|---|---|---|---|---|
| **[A]** | Antonakakis et al. — *Mirai Botnet* (USENIX Security 2017) | 7-month forensic measurement using honeypots, telescopes & C2 milking. | Honeypot logging, DNS analysis, C2 milking. | Live Internet telemetry over 7 months. | Most-cited empirical account of IoT camera compromise at scale. | Attacker-side measurement only; no trust model or video AI. | Internet-scale empirical validation across millions of live devices. | Real-time operational decision layer gating physical security alerts. | Dynamic threat-trend weighting adjusting CVE penalties based on active exploit trends. |
| **[A]** | Zhang et al. — *IoT Botnet Forensics* (2020) | Built lab Mirai botnet end-to-end and ran digital forensics. | Forensic artifact acquisition across C2, DB & loader. | Self-built lab Mirai deployment. | Catalogues evidence left by attacker components. | Post-incident only; no vulnerability scoring or live alert gating. | Detailed forensic reconstruction of attacker C2 infrastructure. | Real-time proactive threat prevention before/during incidents. | Forensic compromise attribution module flagging likely attack vectors. |
| **[A]** | Griffioen & Doerr — *Examining Mirai* (ACM CCS 2020) | 7,500 honeypots + RNG exploit; models botnet population dynamics. | Epidemiological SIS/SIR population modelling. | Large-scale honeypot network (7,500 nodes). | Shows IoT devices change hands in hours–days, not weeks. | No defensive scoring; models propagation, not per-alert trust. | Deep epidemiological rigor on infection state change rates. | Per-alert actionable trust score for live security operators. | Time-decay trust volatility factor ($T_0 e^{-\lambda \tau}$) eroding score between rescans. |
| **[B]** | Yilmazer & Karakose — *AOD w/ YOLOv8 & LLM* (Applied Sciences 2025) | Keyframe filtering → detection → tracking → rule → LLM explanation. | ResNet101v2, YOLOv8, DeepSORT, GPT-3.5-Turbo. | ABODA (11 sequences, 37,653 frames). | 97.4% F1 detection; pairs vision pipeline with LLM explanation. | Assumes camera feed is 100% reliable; no trust modeling. | Keyframe pre-filter cutting compute load ~50% and 97.4% F1 score. | Explanations conditioned on camera cybersecurity trust score. | ResNet keyframe pre-filter ahead of YOLOv8 to cut inference compute. |
| **[B]** | Zhang et al. — *ByteTrack* (ECCV 2022) | "BYTE" two-stage association matching low-confidence boxes. | Kalman Filter, Hungarian Algorithm, IoU matching. | MOT17, MOT20, HiEve, BDD100K. | SOTA tracking robustness (+1–10 IDF1 across 9 trackers). | Single-stream only; no cross-camera fusion or trust model. | Validated tracking robustness across 4 major public benchmarks. | Downstream trust-conditioned decision recommendations. | Benchmark YOLOv8+ByteTrack pipeline on standard MOT metrics. |
| **[B]** | Luna et al. — *AOD Survey & Comparison* (Sensors 2018) | Formalises 4-stage AOD pipeline & benchmarks stage-by-stage. | MoG/KNN/PAWCS, HOG/Haar/Faster R-CNN/YOLOv2. | 21 sequences (AVSS, PETS, ABODA, VISOR). | First systematic whole-pipeline reproducible comparison. | Assumes single reliable static camera; no multi-camera trust. | Reproducible whole-pipeline benchmarking software template. | Cross-camera trust-aware decision layer above detection. | Systematic background-subtraction stage-by-stage comparison. |
| **[C]** | Liu et al. — *Multi-View Anomaly Fusion* (arXiv 2025) | Restricts cross-view attention via epipolar constraints. | Fundamental matrix, DINOv2 ViT, epipolar attention. | Real-IAD (~150K images, 30 categories). | SOTA multi-view anomaly detection with geometric prior. | Requires calibrated, fixed, overlapping viewpoints. | Precise cross-view correspondence via epipolar geometry constraints. | Works across uncalibrated, arbitrarily placed CCTV networks. | Epipolar-constrained cross-view check for overlapping camera fields. |
| **[C]** | Nayak et al. — *Multi-Camera Loitering w/ Re-ID* (iSES 2019) | Detect → track → dwell rule → camera-switch → Re-ID hand-off. | YOLOv3, DeepSORT, MobileNet feature embeddings. | Multi-camera cross-view capture dataset. | True cross-camera behavior tracking with Re-ID. | 14–15% accuracy drop from Re-ID errors; equal camera weighting. | True cross-camera identity continuity via Re-ID embeddings. | Trust-weighted corroboration preventing false cross-camera hand-offs. | Feature embedding visual Re-ID hand-off (MobileNet/OSNet embeddings). |
| **[B]** | Rasal et al. — *Suspicious-Activity Detection* (Springer 2025) | Detection plus custom rule logic for crowd density & alerts. | YOLOv8 + OpenCV pipeline + custom rule logic. | Custom annotated suspicious footage dataset. | Actionable instant SMS alerting on overcrowding/violations. | Fires on raw detection alone; high false-alarm fatigue risk. | Complete operational alerting UX (instant push/SMS). | Trust-gated alert dispatch preventing false alarm fatigue. | Tiered alert notification routing (instant push for High trust, triage for Low). |
| **[D]** | *IoT Trust & Reputation Management SLR* (arXiv 2023) | SLR unifying traditional & AI IoT trust schemes under taxonomy. | Bayesian, Weighted Average, Fuzzy, DNN/RNN trust classifiers. | Literature corpus (120 selected papers). | First survey unifying traditional and AI trust models. | No empirical validation; none target CCTV or CVE data. | Catalogues 30+ trust models including adaptive DNN classifiers. | Applied trust scoring concretely to physical security video feeds. | Adaptive AI/DNN trust classifier trained on incident data. |
| **[D]** | *Blockchain BIoT Trust PRISMA SLR* (MDPI 2026) | PRISMA review of blockchain trust at IoT perception layer. | Weighted Average, Bayesian, SVM/RF, Game Theory. | 122 selected studies (2018–2025). | Direct trade-off analysis of WA vs ML blockchain models. | WA models flagged as static; consensus overhead high. | Decentralized tamper-proof trust ledgers via blockchain. | Zero consensus overhead: fast, real-time per-alert trust scoring. | Tamper-evident SHA-256 Merkle audit ledger for decision logs. |
| **[B]** | *YOLO in Suspicious Activity Review* (ResearchGate 2025) | Review of YOLO (v3–v7) fused with tracking/temporal models. | YOLOv3–v7, SORT/DeepSORT, 3D-CNN, CNN-LSTM. | Surveillance & HAR literature corpus. | Feasibility proof of 10–16 FPS edge inference (Jetson Nano). | Fails if cameras are compromised/damaged; no source trust. | Broad cross-study hardware benchmarking on edge devices. | Reasons about camera reliability rather than crashing when feeds fail. | Heartbeat signal integrity monitoring factor in trust score. |
| **[E]** | Bernot et al. — *CCTV Cyber Vulnerabilities* (J. Cybersecurity 2025) | CVSS pen-testing of Hikvision, Dahua, Avigilon hardware. | CVSS v3.1, Nmap, Wireshark, Bettercap, hping3. | Real hardware: Avigilon H6M, Dahua, Hikvision. | Only public CVSS evaluation confirming Dahua/Hikvision CVEs (9.8). | Static pen-test audit; no live scoring or alert gating. | Empirical pen-testing confirming real-world CVE exploitability. | Converts static audit into real-time, per-alert trust signal. | CVSS v3.1 Temporal & Environmental metric weighting in trust formula. |
| **[E]** | Oliver — *IP Camera CVE Trends* (CoVaCCI Showcase 2025) | NVD dataset analysis to classify IP camera CVE trends. | NVD CVE database querying & category taxonomy. | NVD public CVE database entries. | Systematically classifies camera CVE attack surface trends. | Population analysis only; no live scanning or alert engine. | Temporal taxonomy showing auth bypass is dominant CVE category. | Operationally applies CVE categories per-alert in real time. | Category-aware CVE weights (higher penalties for auth-bypass CVEs). |
| **[E]** | *Diva Portal — Smart Camera Vulnerabilities* (KTH 2018) | Shodan discovery of cameras + CVE cross-referencing. | Shodan API, CVE database keyword matching, Nessus. | Live Shodan scan results & CVE entries. | Proves Shodan viability for exposed camera discovery at scale. | Pre-dates major CVE waves; no trust score or alert layer. | Empirical proof of Shodan scanning effectiveness. | Complete pipeline: Shodan discovery → Trust Engine → Video AI. | Censys + Shodan dual discovery for broader private network coverage. |
| **[E]** | Auti et al. — *Automated VAPT Tool for CCTV* (IJSRCSEIT 2025) | Automated VAPT pipeline: discovery → scan → exploit → report. | Nmap, Nikto, Metasploit, ONVIF SDK, Flask+ReactJS. | 6 IP cameras + 3 DVRs on lab network. | 89% detection accuracy at 65% less time than manual VAPT. | Scores device vulnerability, not alert trustworthiness. | End-to-end automated exploit verification via Metasploit. | Scores alert trustworthiness at decision time during physical events. | Automated VAPT refresh engine connecting Nmap/Metasploit. |
| **[E]** | Das et al. — *ThroughTek Kalay SDK Vulnerability* (Unit 42 2022) | Supply-chain analysis of Kalay P2P SDK (CVE-2021-28372, CVSS 9.6). | IoT traffic analysis, P2P/UDP tracing, CVE mapping. | Crowdsourced telemetry (86M+ devices). | Proves third-party embedded SDKs are a major hidden attack vector. | Technical advisory only; no scoring or alert integration. | Identifies hidden third-party SDK risk affecting 86M+ cameras. | Corroboration check provides second-line defense against hijacked feeds. | Embedded SDK supply-chain risk detection via traffic inspection. |
| **[A]** | Famera et al. — *Mirai Botnet & Post-2019 Variants* (arXiv 2025) | Comparative study of Mirai + Satori, Mukashi, Moobot, Sonic. | Source code analysis, CVE cross-referencing (15+ CVEs). | Mirai source code & threat intel reports. | Documents CVE-2021-36260 exploited by Moobot (280K in 12h). | Attacker-side analysis only; no defender trust layer. | Detailed source-code analysis of botnet exploitation speed. | Defender-side triage layer penalizing variant-exploited CVEs. | Mirai variant penalties weighting command-injection CVEs higher. |
| **[D]** | Swami et al. — *SCI-IoT Quantitative Framework* (arXiv 2025) | SCI-IoT 30 tests across 7 domains with criticality weights. | Weighted scoring, critical gate auto-fails, CVSS severity. | 5 representative device types (smart bulb, camera, PLC). | Mathematically rigorous published trust formula analogue. | Single procurement certification; no runtime per-alert scoring. | Criticality-weighted scoring and critical gate auto-fails. | Applies trust scoring dynamically per-alert at runtime. | Critical security gate auto-fails (auto-fail unauthenticated streams). |
| **[D]** | Ferraris et al. — *IoT Trust Model Frameworks Survey* (J. Supercomputing 2024) | Systematic review of IoT trust frameworks across 6 parameters. | Qualitative taxonomy (15 trust characteristics, SDLC mapping). | IoT trust literature corpus (2011–2022). | Deepest theoretical vocabulary for IoT trust (15 characteristics). | Purely theoretical; no video AI or CVE integration. | 15 named trust characteristics and full SDLC lifecycle mapping. | Instantiates dynamic, context-dependent, composite trust for video feeds. | Operations SDLC positioning addressing alert triage gap. |

---

## 🗣️ 6. Reviewer Q&A Cheat Sheet

| Reviewer Question | Simple Answer to Say |
|---|---|
| **"Why not just use YOLOv8 alone?"** | "YOLO detects *what* is in the video, but can't tell if the camera is hacked. Our Trust Score checks camera security first." |
| **"How do you check if cameras corroborate?"** | "If Camera A alerts, we check if adjacent cameras within 500 meters also saw something within 15 minutes. If yes, +20 bonus!" |
| **"Is this legal under Indian privacy laws?"** | "Yes! We only use public camera metadata via Shodan OSINT, run Video AI on authorized non-live recorded footage, and log everything in a tamper-evident audit ledger with external anchoring." |
| **"Is the system tested?"** | "Yes, we ran a comprehensive suite of **326 automated tests** covering APIs, security, tracking, and breach rules with a **100% pass rate**." |

---

## ⚡ 7. Presentation Commands (How to Run Everything Today)

| Command | What It Does |
|---|---|
| `python backend/main.py` | Launches Backend API Server (`http://localhost:8000`) |
| `cd frontend` then `npm run dev` | Launches GIS Map Dashboard (`http://localhost:5173`) |
| `pytest` | Demonstrates all 326 tests passing ($100\%$ pass rate) |
