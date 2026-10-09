# TODO and open decisions

Tick items with the date; add new ones at the bottom of their section. Mirror important changes in `LOG.md`.

## Decisions waiting for the user
- [ ] Q1 direction: which upgrades from `Q1.md` s3 to commit to (recommended package: U1 + U2 + U3 + U4).
- [ ] Target journal after the upgrade (TIFS vs TDSC vs Computers & Security vs IoT-J), see `Q1.md` s6.
- [ ] Whether to buy/borrow a few IP cameras for a controlled field testbed (U3b) and an account for Censys research access.
- [ ] Tier 2 mismatch weight 0.5: keep, or soften to 0.4 (tapers to medium instead of low)?

## Paper hygiene (small, do soon)
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
