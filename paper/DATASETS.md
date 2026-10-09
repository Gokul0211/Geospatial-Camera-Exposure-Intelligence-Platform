# Datasets and testing plan

_Written 2026-10-09 from web-search summaries. "Checked" means a search result described it; nothing was downloaded and no
access form was submitted. Re-check availability and licence terms on the live pages before relying on any item._

## 1. Does this work need testing?

**Yes.** The current evaluation (120 hand-written scenarios, injected Channel-B values, 13 distinct Tier 1 cases, synthetic noise
frames for Tier 2) shows that the design behaves as intended, but it cannot support a claim about real cameras. For a Q1 submission
the evaluation needs at least:

| Test | Question it answers | Data |
|---|---|---|
| T1 Benign-drift base rates | How often do real camera banners change for legitimate reasons? What FPR does a drift gate cause? | Longitudinal scan history (Censys) |
| T2 Substitution / replay with ground truth | Are real swaps, honeypots, loops and freezes detected, and how fast? | Controlled testbed (owned devices) |
| T3 Tamper detection on real surveillance video | Does Tier 2 evidence work on real footage, not synthetic noise? | UHCTD + generated freeze/loop/replay |
| T4 Adaptive attacks | What does it cost an attacker to evade each signal? | Testbed + generated attacks |
| T5 Optional evidence adapters | Do PRNU / ENF add power over pHash/blur? | VISION, ENF Moving Video Database |
| T6 Downstream decision value (optional) | Fewer false dispatches at equal misses? | Simulation on the above |

## 2. Datasets

| Dataset | Use | Contents (as reported) | Access (as reported) | Status / caveats |
|---|---|---|---|---|
| **Censys research access** | T1, T2 | Universal Internet Dataset: daily snapshots of IPv4 and known IPv6, 3,500+ ports, 100+ protocols, about five years of history; certificates dataset; deprecated ZMap IPv4 scans | Free for verified researchers; results must be shared with the community ([docs](https://docs.censys.com/docs/research-access-to-censys-data)) | Checked. Need an application. Third-party hosts must be anonymised; check terms before redistributing any raw rows |
| **Rapid7 Project Sonar** | T1 (secondary) | HTTP index-page scans and 70+ other services; no RTSP dataset found | Sources disagree: public at opendata.rapid7.com vs. via partnerships ([about](https://sonardata.rapid7.com/about/)) | Checked, access unclear. HTTP-only; IP-based, ignores virtual hosts |
| **Shodan** (academic) | T1 supplement | Banners, ports, timestamps; scan cadence reported as fewer than 40 banner grabs per month in one comparison | Academic/enterprise plans | Not re-checked this session; snapshot-style, weak history |
| **UHCTD** (Univ. of Houston) | T3 | 576 tampers, 288+ hours, two surveillance cameras; classes Normal / Covered / Defocussed / Moved; tampers are synthesised | UHCTD.zip about 26 GB plus ground truth; agreement form at [qil.uh.edu/main/datasets](http://qil.uh.edu/main/datasets/); devkit on GitHub | Checked. Does not contain freeze/replay. Not re-verified that the link still works |
| **Bremen IoT image set**, **VAP lab dataset** | T3 (secondary) | Bremen: four classes (normal, blurred, rotated, obstructed) as periodic stills; VAP: 80 sequences, 720x576 | Public (per the UHCTD paper and a 2026 arXiv paper) | Second-hand mention only; locate and check before use |
| **Xiph / other clean video** | T3 generation | Clean public video used as the source for generated attacks | Public | Mentioned in a 2026 arXiv occlusion paper; choose footage with surveillance-like fixed cameras |
| **VISION** (Shullani et al., EURASIP J. Inf. Secur. 2017) | T5 (PRNU adapter) | 35 devices, 11 brands; 34,427 images, 1,914 videos incl. YouTube/WhatsApp versions | Open access paper; dataset hosted by the authors | Checked. Smartphones, not CCTV; use for evidence-adapter calibration only |
| **ENF Moving Video Database** (Zenodo 10.5281/zenodo.3549378) | T5 (ENF adapter) | Static and non-static video recordings with mains ground truth | Public on Zenodo | Checked. Small; not surveillance cameras |
| **ENF-WHU**, **Carioca** | T5 (audio ENF) | Audio only; ENF-WHU has 130 recordings with reference ENF | GitHub (ENF-WHU) | Checked. Audio only, only relevant if cameras carry audio |
| **NVD, CISA KEV, FIRST EPSS** | Channel A | CVE, exploited-vulnerability catalogue, exploit probabilities | Public feeds | Standard sources, used by the platform already; EPSS history lets T1 study "did exploitation follow drift?" retrospectively |

## 3. What does not exist (verified gap)
No public benchmark for **freeze, loop or replay attacks** on surveillance cameras was found (searches Q5, Q12). Generate them from clean
footage with a documented protocol:
1. Take clean fixed-camera clips (UHCTD "Normal" segments, Xiph, own recordings).
2. **Freeze:** repeat one frame for N frames, with and without small additive noise (noise defeats an exact-hash rule).
3. **Loop:** splice a K-second clip repeatedly into a live stream, with and without re-encoding.
4. **Replay of earlier footage:** insert footage from the same camera recorded at another time of day.
5. **Relay degradation:** downscale and re-encode to a lower profile than declared.
Release the generator, not the footage, so the benchmark is reproducible and the licences of the sources are respected.

## 4. Controlled testbed (ground truth you own)
Owned cameras and decoys/honeypots on a lab-controlled public address, with swaps and injected loops at logged times. Because the
devices are yours, scanning them yourself is within the ethics boundary in `CLAUDE.md`; probing anyone else's devices is not.
Record: true swap times, scanner snapshot times, detector alarm times (detection latency is bounded by scan cadence).

## 5. Ethics and legal notes
- Analyse scan history passively. Do not fetch video from, log in to, or probe any camera you do not own.
- Anonymise third-party IPs in tables, figures and released data (hash or aggregate to ASN/country).
- Check each dataset's licence for redistribution and for human-subject content (UHCTD and VISION contain people or personal devices).
- Responsible disclosure: report critical findings to the relevant CERT before publication.

## 6. Order of work
T1 (apply for Censys access first, since approval takes time) -> T3 with UHCTD and the generator -> T2 testbed -> T4 attacks -> T5 adapters -> T6 if time allows.
