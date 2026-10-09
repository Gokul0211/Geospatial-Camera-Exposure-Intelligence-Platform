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
