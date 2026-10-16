# TODO and open decisions

Tick items with the date; add new ones at the bottom of their section. Mirror important changes in `LOG.md`.

## Decisions waiting for the user
- [ ] Q1 direction: which upgrades from `Q1.md` s3 to commit to (recommended package: U1 + U2 + U3 + U4).
- [ ] Target journal after the upgrade (TIFS vs TDSC vs Computers & Security vs IoT-J), see `Q1.md` s6.
- [ ] Whether to buy/borrow a few IP cameras for a controlled field testbed (U3b) and an account for Censys research access.
- [ ] Tier 2 mismatch weight 0.5: keep, or soften to 0.4 (tapers to medium instead of low)?

## Paper hygiene (small, do soon)
- [x] 2026-10-10 all figure PDFs final (fig 09 recompiled)
- [ ] Add missing prior art to Related Work and soften the novelty claim (C13): ENF false-frame injection (Sensors 2019),
      SurFi looping detection (arXiv 1904.01350), PRNU surveillance-camera authentication (Expert Syst. Appl. 2026),
      US 8,806,632 (IP-device spoofing via HTTP/TCP fingerprints), MATE trust-aware fusion (CCS 2025), camera tamper datasets (UHCTD).
- [ ] Verify every `references.bib` entry marked VERIFY.
- [ ] Fill in authors/affiliations in `main.tex`.
- [ ] Compile all 10 figures and `main.tex` in Overleaf; fix layout issues; tell the agent about compile errors.
- [ ] Re-run the full pytest suite once after the Tier 2 weight change (only 5 dependent files were run).

## Technical debt found in audit
- [ ] Tier 2 freeze rule misses loops of real footage (C14): add hash-sequence periodicity / self-similarity detection.
- [ ] Tier 1 benchmark has 13 distinct cases (C8): replace with real or properly randomised cases.
- [ ] Evaluation corpus labels are partly tautological: replace with externally grounded labels (see `DATASETS.md`).
- [ ] `RESEARCH_NOVELTY.md`, `PAPER_DRAFT.md`, `eval/eval_report.md`, `PROJECT_SUMMARY_AND_FUTURE_SCOPE.md` still carry the old
      metric convention and numbers; mark them superseded by `paper/results.md` (needs user's OK to edit).
- [ ] Figures 8-10 numbers are typed by hand; generate them from `results.json` if the figures change often.

## Q1 work (see Q1.md)
- [ ] U1 Calibrated evidence + conformal gate
- [ ] U2 Loop/replay detection + adaptive-attacker evaluation
- [ ] U3 Real data: (a) longitudinal Censys, (b) controlled testbed
- [ ] U4 Adaptive-adversary analysis
- [ ] U5 Decision-theoretic dispatch evaluation (optional)

## Ethics guard (found 2026-10-10)
- [ ] Decide how to neutralise `backend/services/heartbeat_service.py` / `/api/heartbeat/*` (it opens TCP connections to device IPs): disable by default behind an
      env flag, or remove, before any study that touches third-party hosts. Not changed yet (needs the user's decision). Related: `CENSYS_APPLICATION.md`.
- [ ] Send the Censys application answers (`CENSYS_APPLICATION.md`) after filling the mentor details.

## Frontend follow-ups (2026-10-12)
- [ ] Decide what to do with the dev DB ledger (`audit_ledger` has 32 chain starts; verify says tamper at entry 1): clear the table, or make tests use a temp DB.
- [ ] Try `docker compose build frontend` once; the new Dockerfile/compose were never built.
- [ ] Confirm the footer credit ("Built by Gokul Annamalai and team") and add the repo URL via `NEXT_PUBLIC_REPO_URL`.
- [ ] `/research` page: add the before/after trust-score table from `paper/results.md` (numbers not in the spec).
- [ ] Optional: a real satellite source, or remove the Satellites layer toggle.

## Frontend follow-ups (2026-10-16)
- [ ] FULL AUDIT of frontend + backend edits: run backend tests (against a DB copy), `npm run lint/test/e2e`, check the Alerts timeline and demo labels after a reload
- [ ] Tune basemap tones (land vs water contrast), Alerts chart axes and tooltips, remaining visual polish
- [ ] Ledger tab shows "Chain broken at entry 1" on the dev DB: clear or archive `audit_ledger`, make tests use a temp DB (B6)
- [ ] Add a "dataset provenance" chip in the console (seeded vs scanned) and word the live-eval tab (high_trust = positive there)
- [ ] Decide on `frontend/AGENTS.md` (Next 16 generates it) and commit/ignore `frontend/qa` screenshots


## Frontend rebuild (FRONTEND_SPEC.md section 22)
- [x] 2026-10-14 Phase 1: scaffold, API contracts, facts sync, basemap config (basemap file NOT built)
- [x] 2026-10-14 Phase 2: tokens, primitives, HoodGauge, TierTag, SourceNote, contrast table re-verified
- [ ] Build `public/tiles/india.pmtiles` locally: `bash frontend/scripts/build-basemap.sh 11 <planet URL>`; record the size
- [ ] Phase 3 onward (nav/footer, landing sections, 3D hood, gate explorer, console)
- [ ] Backend touchpoints still awaiting approval: B1 server-side IP masking, B2 heartbeat decision, B3 operation ids/tags, B4 OpenAPI + WS/SSE docs and response models, B5 demo scenario list, B6 temp test DB / ledger reset, B7 `geo_precision`, B8 `/api/results`, B9 LICENSE
- [ ] Decide: keep the dev-only `/design-system` route (not in spec section 4)?
- [ ] Spec 3.2 / 7.6: change WA F1 from 0.753 to 0.752
