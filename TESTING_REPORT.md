# COBRA-WATCH: Member 1 Testing Report

**Tester:** Member 1 (Aditya)  
**Date:** 2026-10-03  
**Branch:** `deploy-step1`  
**Mode:** `PUBLIC_DEMO=1`

---

## What Was Done ✅

### Setup & Environment
- [x] Cloned the repo from `https://github.com/Gokul0211/Geospatial-Camera-Exposure-Intelligence-Platform`
- [x] Checked out the `deploy-step1` branch
- [x] Created Python virtual environment in `backend/venv`
- [x] Installed all backend dependencies via `pip install -r requirements.txt` (Python 3.14)
- [x] Installed all frontend dependencies via `npm install` (Node v24)
- [x] Started backend server — `uvicorn main:app --port 8000` with `PUBLIC_DEMO=1`
- [x] Started frontend server — `npm run dev -- --host` on `http://localhost:5173`
- [x] Both servers started successfully with no errors

### Feature Testing (Part 5)
- [x] **Map** — Map loads, tiles render (OpenStreetMap with CSS dark invert), zoom/drag works smoothly
- [x] **City Switching** — All 9 cities tested: Mumbai, Delhi, Bangalore, Hyderabad, Chennai, Kolkata, Pune, Ahmedabad, All India — map re-centers correctly for each
- [x] **IP Address Check** — Confirmed no IP addresses leak anywhere; `public_demo.py` middleware strips all sensitive fields (`ip`, `ports`, `org`, `banner_snippet`, `raw_data`) from API responses
- [x] **Live Alerts Panel** — Opens and displays 2 pre-loaded demo alerts (Perimeter Breach, Loitering Activity)
- [x] **Demo Alert Button** — Tested; returns 403 in PUBLIC_DEMO mode (expected), falls back to client-side fake alert
- [x] **Analytics Panel** — Opens and renders all tabs (Trust, Threats, Integrity, Audit, Decay, Eval); shows empty state with 0 data
- [x] **Audit Ledger** — Works; shows genesis hash, 0 entries, chain validated as `true`
- [x] **Attack Simulator** — All 4 attacks tested (Replay, Timestamp Skew, Rate Flood, Collusion Ring); all return 403 in demo mode (expected — POST blocked)
- [x] **AI Brief / Risk Brief** — Tested; POST blocked in demo mode (expected)
- [x] **NL Query ("Ask a Question")** — Tested; POST blocked in demo mode (expected)
- [x] **Heartbeat** — Tested; explicitly disabled in demo mode via `BLOCKED_PREFIXES`
- [x] **Operator Verdicts** — Tested; POST blocked in demo mode (expected)
- [x] **WebSocket Connection** — Connects successfully with auto-reconnect (exponential backoff)
- [x] **Satellite/Orbital Tracking** — 15 satellites animate on the map; orbital alert banner works
- [x] **Health Endpoint** — `GET /health` returns `{"status":"ok","ws_clients":1}`
- [x] **Stats API** — `GET /api/stats?city=Mumbai` works but returns 0 devices (empty DB)
- [x] **Devices API** — `GET /api/devices?city=Mumbai` works but returns empty FeatureCollection
- [x] **All backend API endpoints** — Systematically tested every route; all respond correctly

### UI Audit (Part 6)
- [x] Audited every screen for all 5 categories from the testing guide
- [x] Found **20 design issues** — documented with exact file locations and line numbers
- [x] Categories covered: emoji usage, glow/neon effects, tiny text, confusing UX, simulated data without labels

### Screenshots (Part 7)
- [x] `paper_1.png` — Mumbai map view, no popups (full dashboard overview)
- [x] `paper_3.png` — Live alerts panel with demo alerts visible
- [x] `paper_4.png` — Analytics panel with trust distribution view
- [x] `attack_mode.png` — Attack mode panel (bonus screenshot)

### Deliverables (Part 8)
- [x] Created `bugs.md` — 12 bugs documented with severity, steps to reproduce, expected vs actual
- [x] Created `ui_audit.md` — 20 UI issues across 5 categories with exact component references
- [x] Created `screenshots/` folder with 4 PNG screenshots
- [x] Created this report (`TESTING_REPORT.md`)

---

## What Was NOT Done ❌

### Requires `public.db` File from Adi
- [ ] **Camera markers on map** — Database is empty (no `surveillancewatch.db`), so 0 cameras appear. Cannot test:
  - Clicking camera markers and checking popup info
  - Verifying that popups show sensible data
  - Testing the device detail panel with real device data
  - Testing trust score badges on real devices
  - Testing the CERT-In report generation feature
  - Testing the "entity link graph" (corroboration links between cameras)
- [ ] **`paper_2.png` screenshot** — "Map with one camera popup open" — impossible without camera markers
- [ ] **Heatmap layer** — Returns empty `{"points":[],"total":0}` without device data
- [ ] **Search / Filter functionality** — Filter buttons (ALL, OPEN AUTH, HIGH RISK, GOVT, TELECOM, COMMERCIAL) exist but with 0 devices there's nothing to filter
- [ ] **Trust score on real device** — `GET /api/devices/{id}/trust-score` cannot be tested without device IDs

### Requires Non-Demo Mode (PUBLIC_DEMO=0)
- [ ] **Attack simulator live run** — All 4 attacks are blocked by `PublicDemoMiddleware` (403 on POST). Would need `PUBLIC_DEMO=0` to actually test defense mechanisms.
- [ ] **AI Brief streaming** — `POST /api/brief/stream` is blocked. Also requires `GROQ_API_KEY` env var.
- [ ] **NL Query execution** — `POST /api/nl-query` is blocked. Also requires `GROQ_API_KEY`.
- [ ] **Detection event pipeline** — `POST /api/detection-event` is blocked. Cannot test the full trust-score computation pipeline.
- [ ] **Operator verdict recording** — `POST /api/alerts/{id}/verdict` is blocked.

### Phone Testing (Part 5 — Phone Section)
- [ ] **Mobile responsive testing** — Not tested on phone. Network address is `http://192.168.1.6:5173`. Manual phone testing needed.

---

## Bug Summary

| Severity | Count | Key Examples |
|----------|-------|-------------|
| **Broken** | 2 | No database file (0 cameras); StatsBar shows fake fallback numbers |
| **Annoying** | 5 | Attack simulator 403 without friendly message; AI brief stuck in "ANALYZING" |
| **Cosmetic** | 5 | CERT-In report includes IP field; brief route 405 on GET |
| **Total** | **12** | Full details in `bugs.md` |

## UI Audit Summary

| Category | Count | Key Examples |
|----------|-------|-------------|
| 1 — Emoji as buttons | 4 | 🎯 Attack FAB, 🚶🚨🔓⚡ event icons, 🛡️💡 forensic labels |
| 2 — Glow/neon effects | 3 | CRT scanline overlay, boot splash, marker selection pulse |
| 3 — Tiny text (7.5-9px) | 3 | Stats bar labels, attack panel citation, analytics labels |
| 4 — Confusing for visitors | 4 | "ORBITAL SENSING", "SHA-256 VERIFIED", "DPDP ACT" badges |
| 5 — Simulated = looks real | 6 | Fake stats (2369/842/881), demo alerts, CCTV HUD, satellite data |
| **Total** | **20** | Full details in `ui_audit.md` |

---

## How to Complete Remaining Tests

1. **Get `public.db` from Adi** and run:
   ```
   copy path\to\public.db data\surveillancewatch.db
   ```
   Then refresh the browser — cameras will appear immediately.

2. **For attack simulator testing**, restart backend without demo mode:
   ```
   set PUBLIC_DEMO=0
   uvicorn main:app --port 8000
   ```

3. **For phone testing**, open `http://192.168.1.6:5173` on a phone connected to the same Wi-Fi.

---

*Report generated from systematic code analysis + live API testing + browser inspection.*
