# Worklog (append-only)

Newest entries at the bottom. Never delete or rewrite an entry; correct it with a new dated entry.
Format: `## YYYY-MM-DD, title` then **Did / Files / Why / Not verified**.

## 2026-10-09, project read-through and baseline audit
**Did:** read the code, the research docs (`RESEARCH_NOVELTY.md`, `PAPER_DRAFT.md`, `CHANGES_AND_ROADMAP.md`, `eval/*`)
and the 20-paper survey table; re-ran the evals; ran the full pytest suite once (427 passed).
**Found:** (1) repo docs use "genuine" as the positive class while the ablation/sweep scripts use "fabricated"; the
threshold sweep used different tier cut-offs so its F1 (0.932) was not comparable to the main eval; (2) the Tier 1
benchmark has only 13 distinct cases; (3) the Tier 2 weights made L(t) >= 0.5, so only freezes reached low trust;
(4) the eval corpus injects liveness values (down to 0.25) the tracker could not produce; (5) labels for the 90
attribute-only scenarios follow the intended tier of each scenario.
**Not verified:** nothing was changed in this entry.

## 2026-10-09, paper scaffold and results pipeline
**Did:** created `paper/` with `main.tex` (IEEEtran journal), `references.bib`, 10 standalone figures,
`scripts/compute_results.py` (single source of truth), `results.md`, `data/results.json`, `scripts/lint_tex.py`, `README.md`.
Consistent protocol: positive = fabricated, predicted positive iff score < 50, Wilson CIs, exact McNemar.
**Headline numbers:** IG-DCTF F1 0.9756 / recall 0.9524 / FP 0 vs Advanced (Channel A only) F1 0.8113; McNemar p = 1.5e-5;
identical to Advanced on the 90 attribute-only scenarios; additive-fusion control F1 0.9138; threshold sweep flat (42/42).
**Not verified:** nothing compiled (no LaTeX installed); many `references.bib` entries are marked VERIFY; figure numbers are typed by hand.

## 2026-10-09, Tier 2 weights fixed
**Did:** changed Tier 2 weights (0.5, 0.3, 0.2) -> (1.0, 0.6, 0.5) in `video_pipeline/liveness_detector.py` and the default of
`compute_visual_liveness` in `backend/services/signal_integrity_service.py`; updated `test_tier2_compute_visual_liveness_formulation`;
re-ran the 5 dependent test files (32 passed) and `compute_results.py` (16 s); updated paper text, Prop. 5, Table VI, Fig. 5.
**Effect:** every Tier 2 attack category now ends at T_final = 30 (before: freeze 30, blur 70, mismatch 90). Main comparison unchanged.
**Why:** reachability condition w > 0.4 (Prop. 5). **Caveat recorded in paper:** weights were revised after seeing the benchmark; the
false-trip cost (a legitimate sub-stream below declared resolution trips the mismatch term) is unmeasured.
**Not verified:** full pytest suite was not re-run after the change.

## 2026-10-09, agent setup files and Q1 research
**Did:** created `CLAUDE.md`, `paper/LOG.md`, `paper/CLAIMS.md`, `paper/TODO.md`, `paper/Q1.md`, `paper/DATASETS.md`.
Ran 16 web searches (queries listed in `Q1.md` section 8) to audit novelty and survey datasets.
**Found:** prior art for Tier 2-type ideas (ENF false-frame-injection detection, SurFi looping detection, PRNU surveillance-camera
authentication), a patent on HTTP-header fingerprinting to detect IP-device spoofing (Tier 1-type), and MATE (CCS 2025) on Bayesian
trust estimation for compromised sensor agents. No work found that fuses vulnerability posture with stream integrity in one camera
trust score. A weakness of our own design was also identified: the freeze rule detects static frames, not loops of real footage.
**Not verified:** web results are search summaries; titles/claims must be checked against the actual papers before citing.

## 2026-10-09, Overleaf bundle
**Did:** added `scripts/make_preview.py` (builds `figures_preview.tex`: all 10 figures, one per page, styles kept local to each figure) and
`scripts/make_overleaf_zip.py` (builds `../COBRA_IGDCTF_paper_overleaf.zip` with `main.tex`, `references.bib`, `figures_preview.tex`,
`figures/*.tex`, `OVERLEAF_README.txt`). The zip is git-ignored (`*.zip`).
**Not verified:** nothing was compiled (no LaTeX installed). The figure PDFs do not exist yet; `main.tex` shows placeholders for them.
Re-run both scripts after editing any figure.

## 2026-10-09, fig07 compile errors fixed
**Did:** the user's Overleaf showed errors on the two `\node[cap,...]` lines of `figures/fig07_event_pipeline.tex`. `cap` is also a built-in TikZ key
(line cap), so the custom style was renamed `stagelabel`; the two `\foreach` arrow loops were replaced by explicit `\draw` lines.
Regenerated `figures_preview.tex` and the Overleaf zip.
**Not verified:** still not compiled locally; the diagnosis (name clash with TikZ's `cap` key) is the most likely cause, not confirmed from the error text.
Lesson: do not reuse TikZ/pgf key names (`cap`, `thin`, `frame`, `rule`...) for custom styles.

## 2026-10-10, figure PDFs adopted, five figures corrected, zip rebuilt
**Did:** the user compiled the figures in Overleaf and put `1.pdf`..`10.pdf` in `figures/`; they were checked (all single-page, contents match, widths 213-519 pt)
and renamed to `figNN_<name>.pdf` so `main.tex` embeds them. Rendered each to PNG and inspected: fixed `.tex` of fig02 (Corroboration box touched the
Cyber-trust box), fig03 (hyphenation, width 260 -> ~250 pt), fig05 (weight labels collided with the connector), fig09 (xbar plots were offset
against each other; added `bar shift=0pt`), fig10 (legend replaces overlapping curve labels). Moved the broken fig09 PDF to `figures/_superseded/`.
Updated the fig10 caption in `main.tex`. Zip script now includes `figures/*.pdf`; `OVERLEAF_README.txt` lists which figures to recompile.
**Not verified:** the corrected `.tex` for figs 02, 03, 05, 09, 10 have NOT been compiled; the PDFs for 02, 03, 05, 10 in the zip are the older versions.
Zip: `COBRA_IGDCTF_paper_overleaf.zip`.

## 2026-10-10, updated PDFs adopted, zip rebuilt
**Did:** user recompiled figs 02, 03, 05, 09, 10 in Overleaf and saved the PDFs into `figures/` (09 as `9.pdf`, renamed to `fig09_ablation.pdf`).
Rendered and inspected them: 02, 03, 05, 10 are clean. Fig 09 bars are now correct but the value labels ran into the right axis frame, so `fig09_ablation.tex`
was edited (frame removed with `axis x line*=bottom, axis y line*=left`; labels on a white background). Zip rebuilt with all PDFs.
**Not verified:** the edited `fig09_ablation.tex` is uncompiled; the PDF in the zip is the previous (label-overlap) version, so fig 09 must be recompiled once.

## 2026-10-10, fig 09 PDF adopted; all figures final
**Did:** user recompiled `fig09_ablation.tex`; inspected the new PDF (labels clean, no axis-frame overlap). All ten figure PDFs now match their `.tex`. Zip rebuilt.
**Not verified:** `main.tex` itself has still not been compiled by the agent; the user should confirm the full paper builds in Overleaf.

## 2026-10-10, Censys application draft and a passivity finding
**Did:** drafted the answers a Censys research-access form asked for (mentor details left as placeholders at the user's request; RQ1 clarification
restricted to metadata; venue = IEEE TIFS primary) in `CENSYS_APPLICATION.md`.
**Found:** `backend/services/heartbeat_service.py` (`tcp_ping`, `ping_camera`, routes `/api/heartbeat/*`) opens TCP connections to device IPs, which contradicts the
paper's "sends no packets to discovered devices". It is not in the scoring path (`alerts.py` passes `ping_latency_ms=None`). Paper text narrowed to "scoring path"
in the Introduction, Section III-C and the Discussion ethics paragraph; `CLAIMS.md` C15 marked at risk; code NOT changed.
**Not verified:** whether anything calls the heartbeat router in the deployed dashboard (frontend not audited); `main.tex` edits not compiled.

## 2026-10-12, new frontend integrated (old Vite dashboard replaced)
**Did:** replaced `frontend/` (36 tracked Vite/React files) with the Next.js 15 app from `cobra-watch-web.zip` (same folder, so compose/launch paths hold).
`npm install` (530 packages), `tsc`, `eslint`, `vitest` (7), `next build` all clean after fixing 4 Anime.js v4 typing errors, a clock hydration mismatch,
the deprecated `createSpring`, and a missing `metadataBase`. Verified live in the browser against the real backend: landing (WebGL), console (4,429 devices,
map, news, WebSocket alerts), analytics tabs, device page, demo scenario, no console errors.
**Frontend changes to match the real backend:** routes (`/api/simulate/*`, `/api/audit/ledger`, `/api/integrity/{id}`), GeoJSON device parsing, one request for "All India",
detection-event body (`detected_at`, `idempotency_key`), brief request built from the zone's real devices, SSE event types, map tiles (CARTO now needs a key -> OSM + CSS dark filter),
new Analytics tabs (Alerts/Integrity/Ledger/Accuracy), operator verdict buttons, per-device scoring-model comparison.
**Backend changes (additive):** CORS default + `.env.example` + local `.env` now allow :3000; `/api/devices` adds city, trust_score (static posture, no corroboration), tier, cves;
new `GET /api/config/thresholds`, `GET /api/devices/{id}/audit-trail`, `POST /api/scenarios/run`; alerts carry `demo: true` for simulator/scenario traffic (ContextVar `DEMO_MODE`);
`fetch_and_cache_city("All India")` is cache-only (it retried a failing live Shodan fetch on every request: 8 s -> 0.3 s, no external calls).
**Found, not fixed:** (1) dev DB `audit_ledger` has 32 chain starts from past test runs, so `/api/audit/verify` reports "Tamper detected at entry 1"; tests that use the real DB (`test_api.py` etc.) keep appending.
(2) My profiling and the first two console loads sent ~18 Shodan queries for the pseudo-city "All India"; all were denied (403, key has no credits/permission). (3) `DETECTION_API_KEY` is empty locally; if it is ever set, the browser's detection-event and verdict calls get 403 by design.
(4) The landing page showed a stale "309/309 tests"; updated to 431 (verified run, same command as README) in `facts.ts` and `README.md`.
**Not verified:** Docker build of the new frontend (Dockerfile + compose written, never built); satellites layer has no backend source (shows an honest empty state); the Claude-written risk brief was not triggered (costs API tokens);
`/research` still lacks the before/after trust-score table the spec asked for (no numbers supplied).

## 2026-10-13, project mark and banner (assets/logo/)
Read `FRONTEND_SPEC.md` and the DIDA web app (extracted for reference to `Downloads/sentinel_project/dida_ref/frontend`, not into this repo). DIDA's 3D hero is driven by one mark whose geometry is a script (`build_logo.py`), so I built the same kind of source for COBRA-WATCH.
**Mark ("hood"):** nine annular-sector ribs fanned over 236 degrees around one eye; the eye is the lens-shaped overlap of two circles (secure AND authentic, i.e. the IG-DCTF trust intersection; also a cobra eye and a camera aperture). Palette is the site's (void, bone, signal #00E5FF). Rejected during design: hood outline with two rings (reads as a light bulb), two rings with a bridge (reads as a smiley), plain Venn rings (generic).
**Files:** `assets/logo/build_logo.py` (single source of numbers; run it to regenerate everything), `cobra-mark.svg`, `cobra-mark-transparent.svg`, `cobra-favicon.svg` (7 fat ribs for 16 px), `cobra-logo-dark.svg` / `cobra-logo-light.svg` (light uses #0097B2 for the eye so it holds contrast on white), `cobra-banner.svg/.png` (1280x640, GitHub social preview), `cobra-mark.png`, `cobra-mark.geometry.json` (rib angles, radii, eye, for the 3D scene).
**Found:** `frontend/` is not on disk any more. `git status` shows the old Vite files deleted and no untracked new files, and `FRONTEND_SPEC.md` + `frontend.zip` (DIDA's spec and app) sit in the repo root. The Next.js app I integrated on 2026-10-12 was not committed; only `cobra-watch-web.zip` (the original, without my backend wiring) remains.
**Not verified:** the banner tagline uses a system font stack in the SVG (the PNG is the canonical copy); the mark has not been placed in a 3D scene yet.

## 2026-10-13, palette change, README rewrite, new FRONTEND_SPEC.md
**Palette:** the cyan-on-navy identity (`#00E5FF` on `#04060B`) was dropped as generic "cyber" styling. New identity: ink `#0A0C0B`, lichen bone `#E7EAE3`, sodium amber `#F3A33A` (9.5:1 on ink; light-background variant `#A85F00`, 4.9:1 on white). Contrast ratios computed with WCAG relative luminance. `assets/logo/build_logo.py` updated and all assets (SVGs, PNGs, geometry JSON) regenerated; rejected-colour audit is in `FRONTEND_SPEC.md` 1.3.
**README.md rewritten** (banner, the idea and gate formula, verified results with their limits, architecture diagram, layout, quick start, API table, tests, ethics, honest status). Numbers taken from `paper/results.md`; the stale September `eval/eval_report.md` numbers were not used. Fixed: broken links that pointed at another user's absolute path, emoji headings, the claim that a dashboard exists.
**FRONTEND_SPEC.md replaced** (the previous file was a byte-identical copy of the DIDA spec). New content: COBRA-specific ground rules (truth, estimated positions, IP masking, no active probes, synthetic-corpus chip), truth sheet from `results.md` with generated facts, "the hood is a gauge" (opening angle = gate multiplier, eye = T_final), feed-field shader that can drift/freeze/blur, twin-camera blind-spot section, gate explorer with a Python-golden parity test, MapLibre v5 + Protomaps PMTiles, contracts verified against the router files, backend touchpoints B1-B9.
**Research done (web, 2026-10-13, secondary sources):** Next.js 16 (Turbopack default; custom webpack config breaks `next build`; View Transitions via React 19.2+), MapLibre v5 globe + PMTiles, deck.gl 9.4 `@deck.gl/maplibre`, Anime.js v4 API names, Three.js WebGPURenderer/TSL status, openapi-typescript. Exact versions must be confirmed at scaffold time.
**Found, not fixed:** `frontend/` is still absent, so `docker-compose.yml` references a missing build context (README says so). No `LICENSE` file although the README states MIT. Public read routes return full IP addresses (spec B1).
**Not verified:** the India PMTiles extract size (unmeasured); deck.gl interleaved-rendering issues may still be open; nothing in the spec has been built or run; the hero line and palette are proposals awaiting the owner's approval (spec section 25).
