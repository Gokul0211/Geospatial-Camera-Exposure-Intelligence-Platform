# 📊 COBRA-WATCH: Ultra-Simple Tabular Presentation Guide

---

## 1. What is COBRA-WATCH? (30-Second Summary Table)

| Question | Simple Answer |
|---|---|
| **What is the problem?** | Normal CCTV systems blindly trust every camera. If a camera is hacked or fake, guards waste time on false alerts. |
| **What is COBRA-WATCH?** | A platform that gives every camera a **Security Trust Score (0 to 100)** before believing its video alerts. |
| **How does it help?** | High-trust alerts (80–100) are trusted instantly. Low-trust alerts (<50) are flagged for manual operator verification. |

---

## 2. The 4-Step Pipeline Table

| Step | Pipeline Stage | Technology Used | What It Does (In 1 Sentence) |
|---|---|---|---|
| **Step 1** | **Camera Discovery** | Shodan API + NVD CVEs | Finds exposed public cameras and checks if they have known security bugs. |
| **Step 2** | **Trust Score Engine** | Custom Python Algorithm | Calculates 0–100 score based on password status, bugs, age, and nearby camera proof. |
| **Step 3** | **Video AI Pipeline** | YOLOv8 + ByteTrack | Detects people/vehicles and checks if someone loiters (>10s) or crosses a line. |
| **Step 4** | **Live GIS Dashboard** | React + Leaflet + WebSockets | Displays 2,369 cameras on a dark map with instant alert toast popups. |

---

## 3. Tech Stack Cheat Sheet (Where is the Code?)

| Part of Project | Technology Used | Exact File Location | What to Say in Presentation |
|---|---|---|---|
| **User Interface** | React 18 + Vite | `frontend/src/App.jsx` | "We built a modern dark-mode dashboard." |
| **Map Engine** | Leaflet.js | `frontend/src/components/SurveillanceMap.jsx` | "Renders 2,369 camera markers smoothly at 60 FPS." |
| **Backend Server** | Python + FastAPI | `backend/main.py` | "Fast asynchronous REST API server." |
| **Database** | SQLite + aiosqlite | `backend/database.py` | "Stores camera info, news, and detection logs." |
| **Object Detection** | YOLOv8 | `video_pipeline/detector.py` | "AI neural network that detects people and vehicles." |
| **Motion Tracking** | ByteTrack | `video_pipeline/tracker.py` | "Tracks object movement across video frames." |
| **Breach Detection** | 2D Geometry Math | `video_pipeline/rules.py` | "Calculates line-crossing and loitering time." |
| **Live Alerts** | WebSockets | `frontend/src/components/LiveAlerts.jsx` | "Pushes live alert popups instantly to screen." |
| **Audit Ledger** | SHA-256 Merkle Chain | `backend/services/audit_ledger.py` | "Locks alert history so no one can alter past logs." |
| **Testing** | Pytest | `backend/tests/` | "309 automated tests passing with 100% success." |

---

## 4. Trust Score Points System (How the 0–100 Score Works)

| Security Check | Points Effect | Why? |
|---|---|---|
| **Base Starting Score** | **+100 Points** | Perfect starting score for a brand-new camera. |
| **No Password (Unauthenticated)** | **-30 Points** | High risk! Anyone on the internet can view or alter the stream. |
| **Known Security Bugs (CVEs)** | **-10 Points per Bug** | Camera has known unpatched vulnerabilities (max $-40$ points). |
| **Unknown Owner / Org** | **-20 Points** | Camera owner organization is unknown. |
| **Old Firmware (>1 year old)** | **-15 Points** | Firmware has not been updated in over a year. |
| **Confirmed by Nearby Camera** | **+20 Points Bonus** | An adjacent camera (within 500m & 15 mins) also saw the event! |

---

## 5. Reviewer Q&A Cheat Sheet (What Reviewers Ask & What You Say)

| Reviewer Question | Simple Answer to Say |
|---|---|
| **"Why not just use YOLOv8 alone?"** | "YOLO detects *what* is in the video, but can't tell if the camera is hacked. Our Trust Score checks camera security first." |
| **"How do you check if cameras corroborate?"** | "If Camera A alerts, we check if adjacent cameras within 500 meters also saw something within 15 minutes. If yes, +20 bonus!" |
| **"Is this legal under Indian privacy laws?"** | "Yes! We only use public camera metadata via Shodan OSINT, run Video AI on authorized local footage, and log everything in a tamper-proof ledger." |
| **"Is the system tested?"** | "Yes, we ran a master suite of **309 automated tests** covering APIs, security, tracking, and breach rules with a **100% pass rate**." |

---

## 6. Presentation Commands (How to Run Everything Today)

| Command | What It Does |
|---|---|
| `python backend/main.py` | Launches Backend API Server (`http://localhost:8000`) |
| `cd frontend` then `npm run dev` | Launches GIS Map Dashboard (`http://localhost:5173`) |
| `pytest backend/tests video_pipeline/tests eval/test_eval_harness.py -v` | Demonstrates all 309 tests passing ($100\%$ pass rate) |
