# COBRA-WATCH: Cyber-Physical Surveillance Threat Intelligence & Detection Engine

COBRA-WATCH is a real-time cyber-physical surveillance intelligence platform. It ingests public/OSINT camera streams, calculates device trust scores using multi-factor security signals, runs video AI detection rules (loitering, perimeter breach), corroborates events via spatial-temporal adjacency, and broadcasts real-time alerts.

---

## 🌟 Key Capabilities

- **Trust Score Engine**: Deterministic & Bayesian probabilistic trust scoring based on authentication status, NVD CVE count, ownership org type, firmware patch currency, and spatial-temporal corroboration.
- **Video AI Pipeline**: Real-time YOLOv8 + ByteTrack object tracking and rule evaluation engine (loitering detection with customizable dwell thresholds, perimeter line breach detection).
- **Security & Replay Protection**: Constant-time `X-API-Key` authentication, `idempotency_key` deduplication (HTTP 409), timestamp freshness validation (max 60s skew), and per-camera rate limiting (HTTP 429).
- **Interactive Dashboard**: React + Vite + Leaflet mapping interface with live WebSocket alert feeds, risk briefs, and surveillance density statistics.
- **Master Test Suite**: Comprehensive 309-test suite covering unit, integration, security, mathematical, geometric, and concurrency tests (100% pass rate).

---

## 🚀 Presentation & Quick Start Commands

```powershell
# 1. Run Backend Server (http://localhost:8000)
python backend/main.py

# 2. Run GIS Dashboard (http://localhost:5173)
cd frontend
npm install
npm run dev

# 3. Run Master Test Suite (309/309 Passed)
pytest backend/tests video_pipeline/tests eval/test_eval_harness.py -v

# 4. Run Evaluation Harness
python eval/run_eval.py --verbose
```

---

## 📚 Complete Presentation & Study Guides

- **Master Presentation Guide**: **[COBRA_WATCH_PRESENTATION_MASTER_GUIDE.md](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/COBRA_WATCH_PRESENTATION_MASTER_GUIDE.md)**
- **Ultra-Simple Tabular Guide**: **[COBRA_WATCH_ULTRA_SIMPLE_TABLES.md](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/COBRA_WATCH_ULTRA_SIMPLE_TABLES.md)**
- **Detailed Literature & Tech Dossier**: **[COBRA_WATCH_MASTER_PRESENTATION_DOSSIER.md](file:///c:/Users/goldi/Downloads/COBRA-WATCH-Project/COBRA_WATCH_MASTER_PRESENTATION_DOSSIER.md)**

---

## 📄 License
MIT License
