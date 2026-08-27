# 📖 COBRA-WATCH: Complete Presentation & Study Guide

> **How to use this guide**: Read through this document once before your presentation. It breaks down the entire project, technical concepts, code architecture, and sample reviewer questions into plain, simple English so you can speak confidently.

---

## 🧠 1. The Core Concept (Explain Like I'm 5)

### The Problem
Imagine a security room in a smart city with 100 CCTV screens. 
Current security systems **blindly trust every camera**. But in the real world:
- Millions of public cameras are discoverable on Shodan with **no passwords**.
- Many run **5-year-old firmware** with known security bugs (CVEs).
- An attacker could **hack a camera feed** or trigger fake alerts to distract guards.

### The Solution: COBRA-WATCH
COBRA-WATCH is a **Cyber-Physical Surveillance Threat Engine**.
Instead of trusting every camera, it evaluates every camera's security health and calculates a **Trust Score (0–100)**:
- **High Trust (80–100)**: Clean camera, strong security $\rightarrow$ Alert is trusted automatically.
- **Medium Trust (50–79)**: Minor issues $\rightarrow$ Placed in operator triage queue.
- **Low Trust (<50)**: Unauthenticated, unpatched, or compromised $\rightarrow$ Flagged as suspicious alert; requires manual verification.

---

## 🔄 2. The 4-Step System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. OSINT Scan   │ ➔ │ 2. Trust Engine │ ➔ │ 3. Video AI     │ ➔ │ 4. Live Map UI  │
│ (Shodan / CVEs) │    │ (0-100 Score)   │    │ (YOLOv8 + Track)│    │ (Leaflet + WS)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

1. **OSINT Scanner**: Discovers camera metadata (IP, open ports, manufacturer) using the **Shodan API** and matches vulnerability bugs from **NVD (National Vulnerability Database)**.
2. **Trust Engine**: Calculates a 0–100 score based on authentication, CVE count, owner organization, firmware patch age, and nearby camera confirmation.
3. **Video AI Pipeline**: Ingests video streams, runs **YOLOv8** object detection to find people/vehicles, **ByteTrack** for tracking IDs, and checks rules (loitering >10s, boundary line crossing).
4. **Live GIS Dashboard**: Shows all 2,369 sensors on a smooth dark-themed Leaflet map with instant **WebSocket** alert popups and streaming AI risk summaries.

---

## 🛠️ 3. Tech Stack Guide (Where is the Code?)

Here is your exact technical stack and where each piece lives in the codebase:

### Frontend (User Interface)
- **React 18 + Vite 5** (`frontend/src/App.jsx`): Powers the single-page dashboard application.
- **Vanilla CSS3** (`frontend/src/styles/globals.css`): Custom dark theme (`#080b11`), CRT scanlines, and glassmorphic panels.
- **Leaflet.js** (`frontend/src/components/SurveillanceMap.jsx`): Renders 2,369 sensors on a GPU-accelerated canvas (`L.canvas()`) at 60 FPS.
- **Google Fonts** (`frontend/index.html`): *Outfit* (display headers), *Inter* (body text), and *JetBrains Mono* (telemetry counters).

### Backend (Server & Intelligence)
- **Python 3.12 + FastAPI** (`backend/main.py`): High-speed asynchronous web server handling REST endpoints and WebSockets.
- **SQLite 3 + aiosqlite** (`backend/database.py`): Asynchronous database storing devices, OSINT news, alerts, and audit ledgers.
- **WebSockets** (`backend/routes/alerts.py`): Real-time pub/sub manager pushing live alert popups to the browser.

### Video AI & Computer Vision
- **YOLOv8** (`video_pipeline/detector.py`): Real-time neural network object detector for persons and vehicles.
- **ByteTrack** (`video_pipeline/tracker.py`): Multi-object motion tracking with Kalman filtering and Hungarian matching.
- **2D Geometry Rules** (`video_pipeline/rules.py`): Cross-product determinant math for perimeter breaches and ray-casting for loitering dwell times.

### Security & Audit
- **Merkle Ledger** (`backend/services/audit_ledger.py`): Cryptographic SHA-256 hash chain preventing alert log tampering.
- **Heartbeat Service** (`backend/services/heartbeat_service.py`): Detects camera signal loss (>300s timeout).

---

## 📐 4. The 4 Core Algorithms (Explained Simply)

### Algorithm 1: Multi-Factor Trust Score
$$\text{Trust Score} = 100 - 30(I_{\text{unauth}}) - 10(\min(N_{\text{cve}}, 4)) - 20(I_{\text{no\_owner}}) - 15(\text{Firmware Age}) + 20(\text{Corroboration})$$

- **Unauthenticated Stream**: $-30$ points
- **Known NVD CVEs**: $-10$ points per bug (max $-40$)
- **Unknown Owner**: $-20$ points
- **Outdated Firmware (>1 year old)**: $-15$ points
- **Nearby Camera Corroboration**: $+20$ points bonus (if an adjacent camera within 500m & 15min confirms the event).

### Algorithm 2: Volatility Time-Decay Model
$$T(d, \tau) = T_0(d) \cdot e^{-\lambda \tau}$$
Between scans, a camera's trust score slowly erodes over time ($\lambda = 0.005$ per day) because new security vulnerabilities emerge daily.

### Algorithm 3: Vector Line Boundary Crossing (Perimeter Breach)
Determined using the 2D cross-product determinant of the object's position relative to the line:
$$S(Q, P_1, P_2) = (x_2 - x_1)(y_q - y_1) - (y_2 - y_1)(x_q - x_1)$$
If the sign of $S$ changes between frame $k-1$ and frame $k$, the object has physically crossed the boundary line!

### Algorithm 4: SHA-256 Merkle Audit Ledger
Each alert is linked to the previous alert using a cryptographic hash:
$$H_k = \text{SHA256}(H_{k-1} \parallel \text{Alert\_Data}_k)$$
If anyone tries to edit or delete a past alert, the hash chain breaks instantly, proving evidence tampering!

---

## 🗣️ 5. Reviewer Q&A (Sample Questions & Perfect Answers)

### Q1: Why not just use YOLOv8 directly? Why do you need a Trust Score?
> **Your Answer**:  
> "YOLOv8 only answers *what is in the video* (e.g., 'person detected'). It cannot answer *whether the camera stream itself is authentic*. If a hacker compromises an unauthenticated CCTV camera and feeds fake video, standard YOLOv8 will trigger false alerts. COBRA-WATCH evaluates cybersecurity health (CVEs, authentication, firmware age, spatial corroboration) so operators know whether to trust the alert."

### Q2: How does spatial-temporal corroboration work?
> **Your Answer**:  
> "When Camera A detects a breach, our backend searches for adjacent cameras within a 500-meter radius and a 15-minute time window. If Camera B also detects an event nearby, Camera A gets a **+20 Trust Score bonus**, confirming physical reality across multiple sensors."

### Q3: Is this legal under privacy laws like the DPDP Act 2023?
> **Your Answer**:  
> "Yes! COBRA-WATCH enforces a strict ethical boundary:
> 1. We only discover public camera metadata via OSINT scanning (Shodan API).
> 2. Our Video AI engine strictly processes authorized local footage (`_assert_source_is_authorized`) and never hacks or breaches private camera streams.
> 3. All alert actions are logged in an immutable Merkle Ledger for compliance auditing."

### Q4: How well-tested is your codebase?
> **Your Answer**:  
> "We have built a master test suite of **309 automated tests** covering backend API routes, trust engine math, security replay protection, YOLOv8 tracking, and geometric breach rules. We have a **100% pass rate (309/309 passed)**."

---

## 📚 6. Literature Grounding (The 5 Research Clusters)

Our design is backed by **20 peer-reviewed research papers**:

1. **[Cluster A] IoT & Botnet Compromise (4 Papers)**: Proves cameras are compromised in hours/days (*Griffioen & Doerr, ACM CCS 2020*).
2. **[Cluster B] Video AI & Tracking (5 Papers)**: Uses YOLOv8 + ByteTrack for multi-object tracking (*Zhang et al., ByteTrack ECCV 2022*).
3. **[Cluster C] Multi-Camera Fusion (2 Papers)**: Uses spatial-temporal adjacency matrix ($500\text{m}, 15\text{min}$) (*Nayak et al., IEEE iSES 2019*).
4. **[Cluster D] IoT Trust & Reputation (4 Papers)**: Uses weighted deduction scoring and critical security fail gates (*Swami et al., SCI-IoT 2025*).
5. **[Cluster E] CCTV Vulnerability Research (5 Papers)**: Uses NVD CVE lookup and CVSS v3.1 severity metrics (*Bernot et al., J. Cybersecurity 2025*).

---

## ⚡ 7. Quick Terminal Commands for Presentation Today

```powershell
# 1. Start Backend API Server
python backend/main.py

# 2. Start GIS Dashboard
cd frontend
npm run dev

# 3. Show Master Test Suite (309/309 Passed)
pytest backend/tests video_pipeline/tests eval/test_eval_harness.py -v
```
