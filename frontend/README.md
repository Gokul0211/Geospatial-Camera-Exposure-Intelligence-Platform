# COBRA-WATCH web app

Next.js 16 (App Router, Turbopack) front end for COBRA-WATCH. The single source of truth is `../FRONTEND_SPEC.md`.
**Status: complete v1** (spec defaults: sodium amber, no deck.gl, no WebGPU, no `/verify`). Landing (hero with the WebGL hood, blind spot, walk the gate, gate explorer, results, pipeline, map, ethics, run it, CTA), `/research`, `/ethics`, `/lab`, `/console` (live stream, map, inspector, analytics, zone brief, command palette) and `/console/devices/[id]`.

## Run

```bash
# 1. backend (separate terminal, repo root)
python backend/main.py                 # http://localhost:8000

# 2. web app
cd frontend
cp .env.example .env.local             # optional
npm install
npm run sync                           # paper/data/results.json -> facts, assets/logo -> hood geometry
npm run dev                            # http://localhost:3000
```

Open `/console` after running a scenario (top bar) to see live demo traffic. The design system is at <http://localhost:3000/design-system> in dev (production 404 unless `ENABLE_DESIGN_PAGE=true`).

## Scripts

| Script | What it does |
|---|---|
| `npm run sync` | Regenerates `src/lib/content/facts.generated.ts` and `src/lib/three/hood-geometry.json`, copies brand assets. Run it when `paper/data/results.json` or `assets/logo` change. A unit test fails when the facts are stale. |
| `npm run gen:api` | Fetches `/openapi.json` from the running backend, writes `openapi.snapshot.json` and `src/lib/api/schema.d.ts`. `-- --check` fails if the snapshot is stale. |
| `npm run lint`, `typecheck`, `test`, `build` | The definition of done for a phase. |
| `npm run e2e` | Playwright on three viewports (1366x768, 768, 375) with axe. Needs `npm run build && npm run start` (it starts the server itself). |
| `bash scripts/build-basemap.sh 11 <planet.pmtiles URL>` | Optional. Builds `public/tiles/india.pmtiles` and flips `public/tiles/basemap.json` to available. Without it the map uses a self-hosted Natural Earth outline (public domain). |
| `python scripts/export-golden.py` | Regenerates `tests/fixtures/gate_golden.json` from the Python scoring code for the parity test. |
| `node scripts/tour.mjs qa/full 1366 768` | Screenshots every landing section (needs the server running). |

## Rules that are enforced in code

* Numbers come only from `src/lib/content/facts*.ts` (generated from `paper/data/results.json`). Offline backend means an offline state, never sample data.
* An IP address reaches the DOM only through `maskIp()` (`/24` by default). ESLint rejects `{x.ip}` in JSX. Masking is client-side until backend touchpoint B1 lands.
* No scroll listeners (ESLint). Anime.js is imported in exactly one module (`src/lib/animations`).
* Colour tokens, z-scale and contrast pairs are asserted in `tests/contrast.test.ts` against `tokens.css`.
* Passive only: nothing in this app calls `/api/heartbeat/*` or contacts a device.
