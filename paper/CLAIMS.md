# Claim ledger

Every substantive claim in `main.tex`, its evidence, and its status. Update the status whenever evidence changes.
Status values: **verified** (reproduced by `scripts/compute_results.py`), **proved** (follows from the equations, proof in paper),
**design** (argued from the design, not measured), **unverified** (no evidence yet), **at risk** (prior art or weakness found).

| ID | Claim (as in the paper) | Evidence / source | Status |
|---|---|---|---|
| C1 | IG-DCTF F1 = 0.976, recall 0.952, FP = 0 on 120 scenarios | `results.md` s1 | verified (synthetic corpus) |
| C2 | Best vulnerability-only baseline (Advanced) F1 = 0.811; WA 0.753; Bayesian 0.832 | `results.md` s1 | verified (synthetic corpus) |
| C3 | IG-DCTF beats Advanced, exact McNemar p = 1.5e-5 (17 vs 0 discordant) | `results.md` s1 | verified; inherits corpus design |
| C4 | No regression on the 90 attribute-only scenarios (identical to Advanced) | `results.md` s1 stratified | verified |
| C5 | Gain is entirely from Channel-B scenarios (Advanced catches 1 of 18) | `results.md` s1 stratified | verified; true by construction of the corpus |
| C6 | Multiplicative fusion beats additive fusion (3 vs 10 misses) | `results.md` s2 | verified; additive control `T = T_cve - 70(1-s)` is one choice of control |
| C7 | Threshold sweep flat (F1 0.976 at all 42 pairs); corpus cannot select thresholds | `results.md` s3 | verified |
| C8 | Tier 1 detector: 50/50 mutated flagged, 0/50 controls; 0.005 ms/device | `results.md` s4 | verified, but only 13 distinct cases (**weak**) |
| C9 | Single-field banner changes taper but never trip the gate | Prop. 3; `results.md` s4 | proved + verified |
| C10 | Tier 2: 50/50 attacks flagged, 0/30 controls, latency 9.6 frames; all categories end at T_final = 30 | `results.md` s5 | verified on synthetic frames only; weights revised after seeing benchmark |
| C11 | Prop. 1 (non-compensation), 2 (blind spot), 3 (single-field tolerance), 4 (Lipschitz = 2), 5 (reachability w > 0.4) | proofs in `main.tex` | proved |
| C12 | Overhead 4.7 us vs 2.6 us per event | `results.md` s6 | verified (in-process Python, no I/O) |
| C13 | "To our knowledge no surveyed work fuses vulnerability posture with feed authenticity" | survey table (20 papers) + web searches 2026-10-09 | **at risk**: related prior art exists (ENF false-frame-injection, SurFi, PRNU surveillance authentication, IP-device spoofing patent, MATE). Narrow the claim and cite them. See `Q1.md` s2 |
| C14 | Tier 2 detects "stream freeze or loop" (A2) | detector flags static frames | **at risk**: a loop of real footage has natural motion and is *not* detected by the pHash freeze rule |
| C15 | Platform is passive: no packets to discovered devices | code review (`detector.py` whitelist, Shodan metadata only) | design (not independently audited) |
| C16 | Auxiliary modules (adaptive decay, cold start, collusion/GNN) are implemented and unit-tested | repo tests (427 passed on 2026-10-09 before the Tier 2 weight change) | verified functionally; not evaluated |
| C17 | Real-world effectiveness | none | **unverified**: no field data |
| C18 | Bibliography accuracy | `references.bib` | **unverified**: entries marked VERIFY were transcribed from the survey table |
