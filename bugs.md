# COBRA-WATCH Bug Report
**Tester:** Member 1  
**Date:** 2026-10-03  
**Branch:** `deploy-step1`  
**Mode:** `PUBLIC_DEMO=1`

---

## Bug 1: Map loads but shows zero cameras (no database)
Where: Map panel (all cities)  
Steps: 1) Start backend with `PUBLIC_DEMO=1` 2) Open http://localhost:5173 3) Wait for boot splash to finish 4) Observe map  
Expected: Camera markers should appear on the map for each city  
Actual: Map renders correctly (tiles load, zoom/drag works) but zero camera markers appear. API returns `{"type":"FeatureCollection","features":[]}`. The `data/` folder only has `.gitkeep` — no `surveillancewatch.db` file is present.  
Device: laptop  
Screenshot: screenshots/bug_1.png  
Severity: **broken**  
Note: The testing guide (Part 2) says "Adi will send you a file called `public.db`". Without this file the database initializes empty. **All downstream features that depend on device data (popups, trust scores, alerts, analytics, heatmap) are empty as a result.**

---

## Bug 2: StatsBar shows hardcoded fallback numbers when DB is empty
Where: Stats bar (top of dashboard)  
Steps: 1) Load the page with empty DB 2) Observe the stats bar  
Expected: Should show 0 sensors, 0 govt, 0 telecom, or a message like "No data loaded"  
Actual: Shows **2,369** monitored sensors, **842** govt, **881** telecom, privacy risk **65**. These are hardcoded fallback values in `StatsBar.jsx` lines 59-62: `stats?.total_devices || 2369`, `stats?.by_owner?.government || 842`, etc. A visitor sees realistic-looking numbers that are completely fabricated.  
Device: laptop  
Screenshot: screenshots/bug_2.png  
Severity: **broken** — misleading data presentation, no "simulated" label

---

## Bug 3: Attack simulator returns 403 in PUBLIC_DEMO mode
Where: Attack Mode panel (🎯 FAB button, bottom-right)  
Steps: 1) Click the 🎯 button at bottom-right 2) Click "FIRE" on any attack (e.g. Replay Attack) 3) Observe result  
Expected: Either the attack runs and shows defense results, or a clear "disabled in demo mode" message appears  
Actual: API returns `403 Forbidden: "Read-only in public demo mode."` because all POST requests are blocked by `PublicDemoMiddleware`. The panel shows a generic error like `"replay-attack failed to run: HTTP 403"` which is confusing — a visitor doesn't know it's blocked intentionally.  
Device: laptop  
Screenshot: screenshots/bug_3.png  
Severity: **annoying** — expected in demo mode, but the error message is confusing for a visitor

---

## Bug 4: Demo alert trigger button returns 403 in PUBLIC_DEMO mode
Where: Live Alerts panel (bottom-left)  
Steps: 1) Click the red "THREAT ALERTS" pill (bottom-left) to expand alerts 2) Click the blue "SIMULATE EVENT" button  
Expected: A demo alert fires through the pipeline and appears in the feed  
Actual: `POST /api/detection-event` returns 403 ("Read-only in public demo mode"). The fallback in `LiveAlerts.jsx` (line 141-153) catches the error and creates a client-side-only fake alert, but it's not a real pipeline event. The button still works visually, but there's a brief network error in the console.  
Device: laptop  
Screenshot: screenshots/bug_4.png  
Severity: **annoying** — expected behavior, but console error is noisy

---

## Bug 5: AI Brief (Risk Brief) returns 403 / fails silently in PUBLIC_DEMO mode
Where: Intel & Risk Briefs panel (left sidebar)  
Steps: 1) Open the Intel panel 2) Click on a camera marker (if data exists) 3) Observe the risk brief section  
Expected: Either the brief streams or shows a clear "disabled in demo mode" message  
Actual: `POST /api/brief/stream` returns 403 ("Read-only in public demo mode"). The `RiskBrief.jsx` component's `onError` handler sets `briefState.error` but the UI just shows the brief as stuck in "ANALYZING" state with no clear error text visible to the user.  
Device: laptop  
Screenshot: screenshots/bug_5.png  
Severity: **annoying** — expected disabled, but the UI doesn't communicate it well

---

## Bug 6: Heartbeat endpoint returns 403 with no UI feedback
Where: Backend route `/api/heartbeat`  
Steps: 1) Try to access heartbeat functionality  
Expected: Clear indication that heartbeat is disabled in demo mode  
Actual: Returns `403: "Disabled in public demo mode."` — this is the only route with an explicit block in `BLOCKED_PREFIXES`. Working as designed, but noted for completeness.  
Device: laptop  
Screenshot: N/A  
Severity: **cosmetic** — expected, no UI impact

---

## Bug 7: NL Query ("Ask a Question") returns 403 with no friendly UI message
Where: Natural Language Query feature  
Steps: 1) Try to use any NL query / "ask a question" feature  
Expected: UI shows "Disabled in demo mode" or "Read-only" message  
Actual: `POST /api/nl-query` returns 403. The frontend should show a graceful disabled state.  
Device: laptop  
Screenshot: screenshots/bug_7.png  
Severity: **annoying** — expected disabled, noted as per testing guide

---

## Bug 8: Analytics panel charts show "No alert data yet" / "No timeline data yet"
Where: Analytics panel (bar chart icon FAB, bottom-right)  
Steps: 1) Click the analytics FAB button 2) Observe the panel  
Expected: Charts with data, or a clear "empty state" with guidance  
Actual: Shows "No alert data yet" for Trust Histogram, "No timeline data yet" for Threat Timeline, and all metric numbers are 0 or "—". The Audit Ledger section shows "genesis" hash with 0 entries. This is correct given empty DB, but the empty state is sparse.  
Device: laptop  
Screenshot: screenshots/bug_8.png  
Severity: **cosmetic** — correct behavior with no data, but could be more informative

---

## Bug 9: WebSocket reconnects with exponential backoff but no UI status indicator
Where: Live Alerts panel  
Steps: 1) Open the app 2) Stop the backend server 3) Observe the alerts panel  
Expected: Some indication that the real-time connection is lost  
Actual: WebSocket silently reconnects in background with exponential backoff (1s → 2s → 4s → ... up to 30s). No visible indicator to the user that real-time alerts are disconnected. The `LiveAlerts.jsx` `ws.onerror` only does `console.warn`.  
Device: laptop  
Screenshot: N/A  
Severity: **annoying**

---

## Bug 10: `buildCertInReport()` in DetailPanel includes IP address in mailto body
Where: DetailPanel.jsx, line 26-56  
Steps: 1) Select a device on the map 2) If the device is classified as "confirmed open" 3) A CERT-In report link is generated  
Expected: In PUBLIC_DEMO mode, IP should be hidden everywhere  
Actual: The `buildCertInReport()` function at line 26 reads `device.ip` directly and embeds it in the mailto body. While `public_demo.py` middleware strips `ip` from JSON responses (so `device.ip` would be `undefined` → "Unknown"), the function still constructs a report template referencing IP. If the scrubbing ever fails, the IP would leak into the email body.  
Device: laptop  
Screenshot: N/A  
Severity: **cosmetic** — defense in depth works (IP is scrubbed server-side), but the client-side code doesn't check for PUBLIC_DEMO mode

---

## Bug 11: Operator verdict button would fail in PUBLIC_DEMO mode (no UI feedback)
Where: Alert detail view / verdict recording  
Steps: 1) If verdicts are accessible, try to submit a verdict  
Expected: Clear "read-only in demo mode" message  
Actual: `POST /api/alerts/{id}/verdict` returns 403 in demo mode. The guide says "saving verdicts" is "deliberately switched off" — expected. But there's no disabled/greyed-out state on the UI.  
Device: laptop  
Screenshot: N/A  
Severity: **cosmetic** — expected per guide

---

## Bug 12: `brief` route only accepts POST, but devices.py shows `GET /api/brief` returns 405
Where: Backend routes/brief.py  
Steps: 1) Try `GET /api/brief?city=Mumbai`  
Expected: Either returns data or a clear error  
Actual: Returns `405 Method Not Allowed`. The brief endpoint only supports POST. Minor API inconsistency — the route exists but isn't GET-able for cached briefs.  
Device: laptop  
Screenshot: N/A  
Severity: **cosmetic**

---

## Summary

| Severity | Count |
|----------|-------|
| Broken   | 2     |
| Annoying | 5     |
| Cosmetic | 5     |
| **Total** | **12** |

**Critical blockers:** Bug 1 (no database file) blocks all meaningful testing of camera features. Bug 2 (hardcoded fallback stats) shows fabricated numbers with no disclaimer.

**Expected demo-mode limitations (not bugs):** Attack simulator, demo alert trigger, AI brief, NL query, and operator verdicts are all blocked by `PUBLIC_DEMO=1` middleware. These are **expected** as per the testing guide. However, the visitor-facing error experience is confusing in most cases (Bugs 3, 4, 5, 7, 11).
