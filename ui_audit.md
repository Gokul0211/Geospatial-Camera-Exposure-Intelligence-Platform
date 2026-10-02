# COBRA-WATCH UI Audit Report
**Tester:** Member 1  
**Date:** 2026-10-03  
**Branch:** `deploy-step1`  
**Mode:** `PUBLIC_DEMO=1`

Categories:
1. Emoji used as buttons or labels
2. Glowing borders, neon colours, heavy shadows
3. Tiny ALL-CAPS labels or text too small to read
4. Confusing for a first-time visitor
5. Simulated data that looks real (needs "simulated data" label)

---

## 1. Attack Mode FAB uses 🎯 emoji as button icon
Category: 1  
Where: Bottom-right corner of the dashboard, second FAB from the right  
What's wrong: The Attack Mode toggle button (`App.jsx` line 352) uses the 🎯 emoji as its sole icon. Unlike the Analytics FAB next to it (which uses a proper SVG bar-chart icon), this one has no tooltip context until hovered. On some systems/fonts the emoji renders differently or not at all.  
Screenshot: screenshots/ui_1.png

---

## 2. LiveAlerts uses emojis as event-type icons
Category: 1  
Where: Live Alerts panel (bottom-left, expanded)  
What's wrong: `LiveAlerts.jsx` lines 10-14 — event types use emoji icons: 🚶 (loitering), 🚨 (perimeter breach), 🔓 (unauthorized access), ⚡ (anomalous motion). These render inconsistently across OS/browser and look unprofessional in a "military-grade intelligence" UI. SVG icons would be more consistent.  
Screenshot: screenshots/ui_2.png

---

## 3. TrustScoreBadge uses emojis for factor labels
Category: 1  
Where: Device detail panel, trust score breakdown section  
What's wrong: `TrustScoreBadge.jsx` lines 42-48 — factor labels use emojis: 🔓 (unauthenticated stream), ⚠️ (unpatched CVE), ❓ (unknown owner), 🕹 (outdated firmware), 📷 (no corroboration), ✅ (corroborated). Mixed with the otherwise clean monospace design.  
Screenshot: screenshots/ui_3.png

---

## 4. ForensicAttributionCard uses emojis as section labels
Category: 1  
Where: Device detail panel, Forensic section  
What's wrong: `DetailPanel.jsx` lines 367, 376 — uses 🛡️ emoji for the section header and 💡 emoji for the remedy. The Satellite panel (line 245) also uses 🛰 emoji.  
Screenshot: screenshots/ui_4.png

---

## 5. Boot splash uses heavy glow and neon effects
Category: 2  
Where: Boot splash screen (first 3 seconds on load)  
What's wrong: The boot splash has animated radar rings, glowing cyan accents, and a loading bar with heavy neon glow. While intentional for the "intelligence platform" aesthetic, the overall brightness of the cyan glow + dark background + CRT scanline overlay creates visual noise. The compliance text "DPDP ACT COMPLIANT" during splash is too much detail for a loading screen.  
Screenshot: screenshots/ui_5.png

---

## 6. CRT scanline overlay covers entire viewport
Category: 2  
Where: Entire application (always visible)  
What's wrong: `globals.css` lines 183-216 — a `scanline-overlay` div with `z-index: 9998` covers the entire viewport with repeating thin horizontal lines + a slow animated scan travel effect. While subtle, it adds visual noise to all content including map tiles, text, and charts. The effect is purely decorative with no functional purpose, and slightly reduces text clarity especially on the stats bar.  
Screenshot: screenshots/ui_6.png

---

## 7. Multiple layers of glow on selected map markers
Category: 2  
Where: Map, when clicking a camera marker  
What's wrong: Selected markers get: `outline: 2px solid rgba(0,229,255,0.8)`, `outline-offset: 3px`, PLUS a `pulse-marker` animation that oscillates between `scale(1)` with 8px glow and `scale(1.12)` with 20px glow. This is 3 overlapping glow effects on a ~12px marker — visually intense.  
Screenshot: screenshots/ui_7.png

---

## 8. Stats bar text is extremely small (7.5px–9px)
Category: 3  
Where: Stats bar (second row of header)  
What's wrong: Almost all labels in the stats bar are 9px uppercase monospace (`MONITORED SENSORS`, `GOVT / TELECOM`, `PRIVACY DENSITY RISK`, etc.). The risk level badge (`CRITICAL`/`ELEVATED`/`MODERATE`) is only **7.5px** (`StatsBar.jsx` line 205). The "DPDP ACT 2023 COMPLIANT" badge is 9px. These are extremely hard to read at normal viewing distance, especially on lower-resolution screens.  
Screenshot: screenshots/ui_8.png

---

## 9. Audit ledger footer citation text is 9px and grey-on-grey
Category: 3  
Where: Attack Mode panel, bottom footer  
What's wrong: `AttackModePanel.jsx` line 322-327 — the citation text "Every attack here exercises real backend code paths..." is 9px italic with color `#3b4a5a` on a `#1a1010` dark background. Nearly invisible.  
Screenshot: screenshots/ui_9.png

---

## 10. Analytics panel score labels are 9px uppercase
Category: 3  
Where: Analytics panel → Average scores section  
What's wrong: `AnalyticsPanel.jsx` line 74 — labels like "Weighted Avg", "Bayesian", "Decayed" are rendered at 9px uppercase. The bar chart labels are 11px but with low-contrast color `#94a3b8` on dark background. Hard to read at a glance.  
Screenshot: screenshots/ui_10.png

---

## 11. "ORBITAL SENSING" alert banner is confusing for first-time visitors
Category: 4  
Where: Stats bar, orange-red banner at top (when orbital alerts fire)  
What's wrong: An orbital threat alert banner can appear showing text like "ORBITAL SENSING: CARTOSAT-3 PASS — HIGH RESOLUTION EO CAPABILITY" with a pulsing red dot. A first-time visitor has no context for what "orbital sensing" means, why satellites are relevant to a camera surveillance platform, or whether this is a real alert. There's no tooltip or help icon to explain.  
Screenshot: screenshots/ui_11.png

---

## 12. "SHA-256 VERIFIED" Merkle ledger badge has no explanation
Category: 4  
Where: Stats bar, right side  
What's wrong: `StatsBar.jsx` lines 258-272 — shows a purple dot with "SHA-256 VERIFIED" label. A visitor has no idea what this refers to (it's the tamper-evident audit ledger chain validation). No tooltip. No link to explanation. Appears decorative.  
Screenshot: screenshots/ui_12.png

---

## 13. "DPDP ACT 2023 COMPLIANT" badge appears without explanation
Category: 4  
Where: Stats bar, far right  
What's wrong: A green compliance badge reads "DPDP ACT 2023 COMPLIANT". No tooltip text explains what this means. The `title` attribute does exist (`legal.detail`) but it only shows on hover — a mobile user would never see it. A first-time visitor, especially outside India, won't know what DPDP Act is.  
Screenshot: screenshots/ui_13.png

---

## 14. Dock buttons "INTEL BRIEF" and "DEVICE INTEL" are not immediately obvious
Category: 4  
Where: Map overlay (top-left and top-right corners when panels are collapsed)  
What's wrong: When the Intel or Device panels are hidden, small dock buttons appear at map corners. They use tiny SVG icons + uppercase text. A new visitor won't understand what "INTEL BRIEF" or "DEVICE INTEL" panels contain, or that they can be toggled. No tooltip beyond the generic title attribute.  
Screenshot: screenshots/ui_14.png

---

## 15. StatsBar hardcoded fallback numbers look like real data
Category: 5  
Where: Stats bar, all stats  
What's wrong: When the API returns 0 devices (empty DB), `StatsBar.jsx` shows fallback values: **2,369** sensors, **842** govt, **881** telecom, privacy risk **65**. These are hardcoded in lines 59-62 and animate in with a smooth counter animation, making them look like live data. There is NO "simulated data" label, "demo data" disclaimer, or visual distinction. A visitor will believe these are real numbers.  
Screenshot: screenshots/ui_15.png

---

## 16. LiveAlerts shows pre-loaded demo alerts that look like real events
Category: 5  
Where: Live Alerts panel (bottom-left)  
What's wrong: `LiveAlerts.jsx` lines 16-37 — two hardcoded `INITIAL_DEMO_ALERTS` are shown on load: a "Perimeter Line Breach" from `mumbai_cam_502` with trust score 20, and a "Loitering Activity Detected" from `mumbai_cam_108` with trust score 65. These include realistic camera IDs, city names, contributing factors like `auth_required:false` and `known_cve_count:3`. No "DEMO" or "SIMULATED" label anywhere.  
Screenshot: screenshots/ui_16.png

---

## 17. DetailPanel shows simulated CVE data, vulnerability details, and forensic attribution without disclaimer
Category: 5  
Where: Device detail panel (right sidebar), when a camera is selected  
What's wrong: The `ForensicAttributionCard` component shows text like "CRITICAL: UNAUTHENTICATED EXPOSURE + ACTIVE CVEs", "Device streams video unauthenticated while carrying high-severity unpatched vulnerabilities. High risk of automated botnet takeover (Mirai/Moobot)." These are generated from device metadata fields (`cve_categories`, `known_cve_count`, `auth_required`) which are populated from the database. Even though the data is from Shodan OSINT scanning, the device-level details are enriched/simulated and presented as authoritative security assessments next to map positions. No "simulated data" disclaimer.  
Screenshot: screenshots/ui_17.png

---

## 18. CCTV Feed Viewer shows "LIVE TRANSCODE (H264 / WebRTC)" for non-live content
Category: 5  
Where: Device detail panel, public feed viewer  
What's wrong: `DetailPanel.jsx` lines 127-129 — the `CctvFeedViewer` displays "LIVE TRANSCODE (H264 / WebRTC)" and animated HUD overlays including "YOLO_DET [89%]" bounding boxes, "FPS: 30.0 BITRATE: 4.8 Mbps", and a red "● REC" timestamp. These are entirely canvas-rendered animations (`DetailPanel.jsx` lines 64-118) — not real video analytics. The HUD makes it look like live AI-processed video when it's just an animation. No "demonstration/simulated" label.  
Screenshot: screenshots/ui_18.png

---

## 19. Satellite/orbital telemetry data appears as live real-time tracking
Category: 5  
Where: Stats bar orbital section, satellite panel  
What's wrong: The `OrbitalTracker` and `SatellitePanel` show satellites like CARTOSAT-3, RISAT-2BR1, etc. with "live telemetry" data (latitude, longitude, inclination, period). The `satelliteData.js` has 17,394 bytes of detailed orbital assets. These are presented with smooth animations suggesting real-time tracking. The data is static/hardcoded with simulated orbital calculations. No "simulated" disclaimer.  
Screenshot: screenshots/ui_19.png

---

## 20. Trust score dial and "Grade: A/C/F" system looks like official security rating
Category: 5  
Where: Device detail panel, TrustScoreBadge component  
What's wrong: `TrustScoreBadge.jsx` shows a circular SVG gauge with an animated score counter and grade letter (A/C/F). Colors suggest security certification: cyan for "HIGH TRUST", amber for "MEDIUM TRUST", red for "LOW TRUST". For a visitor, this could be mistaken for an official security certification grade. The scores are computed from simulated/enriched data. No "research model output" or "simulated" disclaimer.  
Screenshot: screenshots/ui_20.png

---

## Summary

| Category | Count | Description |
|----------|-------|-------------|
| 1 — Emoji as buttons/labels | 4 | Attack Mode FAB, LiveAlerts event icons, TrustScore factors, Forensic/Satellite headers |
| 2 — Glowing/neon/heavy shadows | 3 | Boot splash, CRT overlay, marker selection glow |
| 3 — Tiny ALL-CAPS / unreadable text | 3 | Stats bar 7.5-9px labels, attack panel citation, analytics labels |
| 4 — Confusing for first-time visitor | 4 | Orbital sensing, SHA-256 badge, DPDP badge, dock buttons |
| 5 — Simulated data looks real | 6 | StatsBar fallbacks, demo alerts, CVE/forensic data, CCTV HUD, satellite telemetry, trust grades |
| **Total** | **20** |
