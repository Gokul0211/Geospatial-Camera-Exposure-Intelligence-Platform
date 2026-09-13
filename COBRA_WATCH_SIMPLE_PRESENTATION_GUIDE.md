# 🎯 COBRA-WATCH: Simple Presentation Cheat Sheet & Tech Overview

---

## 💡 1. What is COBRA-WATCH in Simple Words?

> **The Big Problem**:  
> Normal CCTV alert systems blindly trust every camera feed. If an attacker hacks a camera or sends a fake video stream, guards waste time responding to false emergencies.
>
> **The COBRA-WATCH Solution**:  
> COBRA-WATCH assigns a **Security Trust Score (0–100)** to every camera *before* believing its alerts.  
> If a camera has no password, outdated firmware, or known security vulnerabilities (CVEs), its alert is marked as **LOW TRUST** for operator review. If nearby cameras confirm the event, its score goes **UP**.

---

## 🔄 2. How it Works (Simple 4-Step Pipeline)

```
[1. Discover Cameras] ➔ [2. Compute Trust Score] ➔ [3. Detect Video AI Events] ➔ [4. Live GIS Dashboard]
   (Shodan / CVEs)         (0-100 Trust Model)       (YOLOv8 + ByteTrack)         (Leaflet Map + Alerts)
```

1. **Discover & Audit**: Scans public IP camera metadata (Shodan API) and checks NVD vulnerability databases for security bugs.
2. **Calculate Trust Score**: Evaluates password protection, firmware age, vulnerability count, and nearby camera confirmation (+20 bonus).
3. **Run Video AI**: Uses **YOLOv8** object detection and **ByteTrack** motion tracking to detect loitering (dwelling inside a zone) and line crossing (perimeter breach).
4. **Display Live**: Shows 2,369 monitored sensors on a dark GIS map with instant WebSocket threat popups and AI risk summaries.

---

## 🛠️ 3. Tech Stack Made Simple (What We Used & Where)

| Part | Technology We Used | File Location in Project | What it Does (Simple Explanation) |
|---|---|---|---|
| **Dashboard UI** | **React 18** + **Vite** | `frontend/src/App.jsx` | Powers the interactive dark-mode user interface. |
| **Styling** | **Vanilla CSS3** | `frontend/src/styles/globals.css` | Handles dark tactical layout, glassmorphism blur, and CRT scan lines. |
| **Interactive Map** | **Leaflet.js** | `frontend/src/components/SurveillanceMap.jsx` | Renders 2,369 camera sensors on a smooth 60 FPS map. |
| **Satellite Imagery** | **Esri Tiles** | `frontend/src/utils/satelliteData.js` | Toggles high-res satellite aerial map view. |
| **Backend API** | **Python 3.12** + **FastAPI** | `backend/main.py` | High-speed server handling all requests and data processing. |
| **Database** | **SQLite 3** + **aiosqlite** | `backend/database.py` | Stores camera metadata, news, and detection logs. |
| **Real-Time Alerts** | **WebSockets** | `backend/routes/alerts.py`<br>`frontend/src/components/LiveAlerts.jsx` | Pushes instant alert toasts to the screen without refreshing. |
| **Video Object Detection** | **YOLOv8** (`ultralytics`) | `video_pipeline/detector.py` | Detects people and vehicles in video feeds. |
| **Motion Tracking** | **ByteTrack** | `video_pipeline/tracker.py` | Tracks objects across frames and assigns unique Track IDs. |
| **Breach & Loitering Math** | **2D Vector Math** | `video_pipeline/rules.py` | Detects when someone crosses a boundary line or loiters >10s. |
| **Trust Score Engine** | **Custom Algorithm** | `backend/services/trust_score_service.py` | Calculates the 0–100 camera trust score and time-decay. |
| **Multi-Camera Fusion** | **Spatial-Temporal Fusion** | `backend/services/corroboration_service.py` | Checks if adjacent cameras within 500m/15min confirm the alert. |
| **Tamper Protection** | **SHA-256 Merkle Chain** | `backend/services/audit_ledger.py` | Locks alert history in a hash chain so no one can edit past logs. |
| **AI Risk Summaries** | **LLM Stream** | `backend/services/brief_service.py`<br>`frontend/src/components/RiskBrief.jsx` | Generates streaming plain-English risk summaries for selected cameras. |
| **Test Suite** | **Pytest** | `backend/tests/`<br>`video_pipeline/tests/` | 309 automated tests passing with 100% success rate. |

---

## 📊 4. How the Trust Score Math Works

$$\text{Trust Score} = 100 - \underbrace{30}_{\text{No Password}} - \underbrace{(10 \times \text{CVEs})}_{\text{Max 40 pts}} - \underbrace{20}_{\text{Unknown Owner}} - \underbrace{15}_{\text{Old Firmware}} + \underbrace{20}_{\text{Nearby Camera Confirm}}$$

- **Unauthenticated Stream**: $-30$ points
- **Known NVD CVE Vulnerabilities**: $-10$ points per bug (up to $-40$)
- **Unknown Owner / Org**: $-20$ points
- **Outdated Firmware (>1 year old)**: $-15$ points
- **Corroborated by Nearby Camera (within 500m & 15 min)**: $+20$ points bonus

---

## 🚀 5. Future Scope (What Comes Next?)

1. **Dynamic Threat-Trend Weighting**: Adjusting CVE penalties based on active real-time internet exploit waves.
2. **Person Re-Identification (Re-ID)**: Matching person feature vectors to confirm identity across non-overlapping cameras.
3. **Epipolar View Geometry**: Checking exact 3D camera overlap angles for calibrated camera pairs.
4. **Automated Penetration Refresh**: Running automated vulnerability scans (Nmap / Metasploit) to verify exploitability live.

---

## 🚀 6. Demo Launch Commands for Today

```powershell
# 1. Start Backend API Server (http://localhost:8000)
python backend/main.py

# 2. Start Dashboard (http://localhost:5173)
cd frontend
npm run dev

# 3. Show 309 Passing Tests
pytest backend/tests video_pipeline/tests eval/test_eval_harness.py -v
```
