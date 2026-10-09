# IG-DCTF journal manuscript (IEEE Transactions on Information Forensics and Security)

```
paper/
  main.tex              IEEEtran [journal] two-column manuscript (pdfLaTeX + BibTeX)
  references.bib        bibliography (entries marked VERIFY need a check against the originals)
  results.md            every number used in the paper (generated, do not edit by hand)
  data/results.json     machine-readable version of results.md
  figures/figNN_*.tex   one standalone TikZ/pgfplots file per figure
  scripts/compute_results.py   regenerates results.md and data/results.json
  scripts/lint_tex.py          brace/environment sanity check (not a substitute for compiling)
  LOG.md                append-only worklog          CLAIMS.md   claim -> evidence ledger
  TODO.md               open tasks and decisions     Q1.md       Q1 plan and novelty audit
  DATASETS.md           datasets and testing plan
```
Agent instructions for the whole repository are in `../CLAUDE.md`.

## Rendering the figures in Overleaf
1. Upload the whole `paper/` folder as a project.
2. For each `figures/figNN_*.tex`: open it, set it as the main document (Menu > Main document), compile with
   **pdfLaTeX**, and download `figNN_*.pdf`. (Alternatively compile once per file with a tool such as `latexmk`.)
3. Put the PDFs back into `figures/`. `main.tex` then picks them up automatically; until a PDF exists it
   shows a labelled placeholder box, so `main.tex` always compiles.
4. Set `main.tex` as the main document and compile (pdfLaTeX, BibTeX).

Required packages are all in a standard TeX Live: `newtxtext`, `newtxmath`, `tikz`, `pgfplots`, `adjustbox`, `IEEEtran`.

## Figure list and widths

| File | Content | Width |
|---|---|---|
| fig01_blind_spot | Vulnerability-only blind spot | 1 column (3.5 in) |
| fig02_architecture | System architecture | full (7.16 in) |
| fig03_threat_model | Adversary / entry point / countermeasure | 1 column |
| fig04_tier1_drift | Tier 1 drift worked example | 1 column |
| fig05_tier2_liveness | Tier 2 tracker | full |
| fig06_gate_function | Gate G(s) | 1 column |
| fig07_event_pipeline | Request path | full |
| fig08_comparison | Four-model comparison | 1 column |
| fig09_ablation | Ablation and additive control | 1 column |
| fig10_decision_map | (Drift, L) decision map with corpus points | 1 column |

Style: Times (newtx) at 8 pt (`\footnotesize` of a 10 pt class), 0.5 pt rules, black/grey plus one accent
(`#1F4E79`) used only for what is new in IG-DCTF; every figure is legible in grayscale.

## Before submission
- Replace the author block and affiliations in `main.tex`.
- Verify every `references.bib` entry marked `VERIFY` (they were transcribed from the project's survey table).
- The sources were written without a local LaTeX installation; the first Overleaf compile may need small
  layout nudges (node spacing, label positions). Report any compile error and it will be fixed.
- Re-run `python paper/scripts/compute_results.py` whenever code or the evaluation corpus changes, then update the
  affected tables and the numbers in `fig08`/`fig09`/`fig10`, which are typed in by hand from `results.md`.
