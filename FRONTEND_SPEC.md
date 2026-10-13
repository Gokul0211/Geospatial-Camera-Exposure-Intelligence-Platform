# COBRA-WATCH Frontend Specification

**Status:** spec, not built yet. Written 2026-10-13.
**Replaces:** the Vite/React dashboard (removed from the working tree 2026-10-12) and the Next.js integration of `cobra-watch-web.zip` (never committed, no longer on disk).
**New app location:** `frontend/` (Next.js), served separately from the FastAPI backend on `:8000`.
**Derived from:** the DIDA frontend spec, whose structure and technology choices produced a result you liked. This document keeps the engineering discipline and replaces the identity, the story, the colour, the map, and everything that is specific to camera trust.

This is the single source of truth for the rebuild: the product being presented, the design system, every page and section, the motion and WebGL architecture, the data contracts with the real backend, performance, accessibility, and the build order. Anything not written here is not built without updating this file first.

---

## 0. Ground rules

These override every visual ambition below.

1. **Nothing is faked.** No invented statistics, no hand-written "live" output, no simulated stream presented as real. Every number on a marketing page comes from `paper/data/results.json` through a generated facts file (section 3.4) and carries a source key. Every value in the console comes from the running backend.
2. **When the backend is offline, say so.** Live views show an honest offline state ("Backend not reachable at `localhost:8000`. Start it with `python backend/main.py`.") instead of placeholder data.
3. **Every performance number wears its limits.** Each accuracy figure is shown with the chip `Synthetic corpus, n = 120` and links to the limits block. The site never says "detects X% of real attacks". Real-world effectiveness is unverified (claim C17) and the site says so.
4. **Illustrations are labelled as illustrations.** The hero hood, the twin-camera comparison and the feed preview are procedural visuals of the method. Their captions name the corpus category they depict. Particles and frames are never presented as traffic.
5. **Scripted traffic is labelled.** Scenario runs and attack simulators create alerts with `demo: true`. The UI marks them `Demo scenario` wherever they appear, and never counts them in a fleet statistic without saying so.
6. **A trust score has a basis, and the UI shows it.** The score on the map is `static_posture_no_corroboration`: posture only, no live corroboration, no live Channel B. The on-demand score in the inspector is the authoritative one. The two are never presented as the same quantity.
7. **Positions are estimates.** Device coordinates are IP-geolocation results (`geo_source`), city-level at best. The map legend and every popup say "Estimated position", never "camera location".
8. **Ethics is a UI requirement.** Public views show IP addresses masked to the /24 (`203.0.113.•`) unless the operator sets `NEXT_PUBLIC_REVEAL_IP=true` for a local session. No view offers to connect to, scan, or fetch video from a discovered device. The active heartbeat route is never wired (section 16, B2).
9. **Motion must be motivated.** Every animation answers one of: hierarchy, storytelling, feedback, state change. "It looked cool" is not a reason.
10. **Performance and accessibility are features.** Reduced motion, keyboard use and low-power devices are first-class targets.
11. **Colour is a decision, not a default.** The palette in section 5.1 is the only palette. Section 1.3 lists what is banned and why.

---

## 1. Design read and dials

> **Reading this as:** a security-research product site plus a live operations console, for technical reviewers, municipal security teams and paper reviewers. A precise, dark, engineered language, warm instead of neon, built from Tailwind v4 + owned shadcn/ui primitives + Geist + Anime.js choreography + one restrained WebGL centrepiece + a real vector map.

| Surface | DESIGN_VARIANCE | MOTION_INTENSITY | VISUAL_DENSITY | Why |
|---|:---:|:---:|:---:|---|
| Landing (`/`) | 7 | 7 | 3 | Premium product story, rich but purposeful motion |
| Research (`/research`) | 5 | 4 | 4 | Reading first, motion only for figures |
| Lab (`/lab`) | 5 | 5 | 6 | Interactive instruments, feedback-driven motion |
| Console (`/console`) | 3 | 4 | 8 | Operational tool: density and clarity beat flourish |
| Verify, Ethics | 3 | 3 | 3 | Reference pages |

### 1.1 What stays from the DIDA spec

Ground-rule discipline (nothing faked, honest offline states), the dial table, Anime.js v4 as the only animation library, vanilla Three.js with one explicit loop per canvas, hand-written GLSL, the protected-core idea (the eye), dark-only v1, Geist, owned primitives, sentence case, the z-scale, one RAF loop per stage, quality tiers with a runtime governor, `lib/content/facts` as the only place numbers live, and the build-order discipline.

### 1.2 Deliberate deviations from the DIDA spec and the installed taste skills

| Default | This project | Reason |
|---|---|---|
| Signal orange `#FF4F1F`, ink and bone as DIDA | **Sodium amber `#F3A33A` on green-black ink, lichen bone** (5.1) | Not DIDA's identity, not neon, and meaningful: amber is the colour of sodium street lamps over a city at night, which is where this product looks |
| Leaflet + raster tiles | **MapLibre GL JS v5 + self-hosted Protomaps PMTiles** | A vector map can be styled in the palette, rotated, tilted and rendered as a globe. Self-hosted tiles make zero third-party requests per pan, which fits a privacy-first project |
| Contour-field shader | **"Feed field" shader** that behaves like a camera feed and can drift, freeze and mis-scale | The product is about feeds that lie. The background is allowed to lie, on purpose, in the sections that are about lying (section 9.1) |
| Walls light up per layer | **The hood is a gauge**: its opening angle encodes the gate multiplier | The mark carries data, so it can be the same object in the hero, the explorer, the inspector and the favicon (section 6) |
| Glow allowed only inside WebGL | Same rule | Keeps DOM text and UI free of glow |
| Phosphor icons | Same | One family, `light` and `regular` |
| Playground | Renamed **Lab** | It holds instruments (gate explorer, simulators), not just forms |
| No photography | Same | The product is infrastructure; visuals are procedural |
| `createSpring` | `spring` | Confirmed against the installed Anime.js v4 in the 2026-10-12 integration; `createSpring` is deprecated |
| Next.js 15, webpack GLSL rule | **Next.js 16, Turbopack GLSL rule only** | Turbopack is the default in 16 and a custom webpack config makes `next build` fail (verified 2026-10-13, sources in 14.5) |

### 1.3 The AI-slop colour audit

The palette was chosen by elimination. Everything below is banned from every surface, including the logo and the OG image.

| Banned | Why | What replaces it |
|---|---|---|
| Neon cyan or electric blue on navy (`#00E5FF`, the previous mark and site) | The default "cyber" look of generated sites; also the old brand | Amber on green-black |
| Purple, indigo, violet, or blue-to-purple gradients | The most recognisable generated-site signature | One warm accent, no gradients at all |
| Teal-to-pink or any multi-stop gradient, gradient text | Decoration with no information | Flat surfaces; tone steps for elevation |
| Glassmorphism cards with coloured glows | Dated and expensive | Solid surfaces; glass only on two fixed elements (5.3) |
| Red / amber / green traffic lights for severity | Cliched, poor for colour-blind users, and amber already means "attention" here | Shape + one-hue intensity ramp + text label (5.1) |
| Dot-grid and mesh-blob backgrounds | Filler | The feed field, which has a job |
| Radar sweeps, matrix rain, terminal typing, "hacker" green | Surveillance-product clichés, and the old logo was a radar eye | Real data, real states |
| Emoji and sparkle icons, "Powered by AI" badges | Slop | Phosphor icons, plain text |
| Identical card grids | Slop layout | Layout families never repeat (section 7) |

Brand note: the paper's accent (`#1F4E79`) is a print colour chosen to survive greyscale. The web uses amber. They are intentionally separate systems.

---

## 2. What we are replacing, and what must survive

### 2.1 Functionality that must exist in the new app

The old dashboard and the 2026-10-12 integration established what the console needs. Every item is rebuilt in the new design, not dropped.

| Capability | Backend | New home |
|---|---|---|
| City selector (8 cities + All India), device map with clustering | `GET /api/devices?city=` | Console map |
| Trust tier per device on the map | enriched GeoJSON (`trust_score`, `action_tier`, `integrity_gate_tripped`) | Map symbols |
| Device inspector: owner, ports, CVEs, factors | `GET /api/devices/{id}/trust-score` | Inspector |
| Live alerts with demo labelling | `WS /api/ws/alerts` | Alert stream |
| Operator verdict (verified / false alarm) | `POST /api/alerts/{id}/verdict` | Inspector and stream row |
| Analytics: fleet, alerts, integrity, ledger, accuracy | `/api/analytics/*`, `/api/integrity/stats`, `/api/audit/*`, `/api/eval/live` | Analytics drawer |
| Scoring-model comparison (4 models) | `/api/analytics/score-comparison` | Inspector and `/research` |
| Merkle ledger with chain verification | `/api/audit/ledger`, `/verify`, `/chain-proof` | Analytics Ledger tab and `/verify` |
| Risk brief for a drawn zone, streamed | `POST /api/brief/stream` (SSE) | Zone brief panel |
| City news | `GET /api/news` | Zone brief panel |
| Natural-language device query | `POST /api/nl-query` | Command palette |
| Trust decay | `GET /api/decay-curve`, `/decay-preview` | Inspector |
| Attack simulators and demo scenario | `/api/simulate/*`, `POST /api/scenarios/run` | Lab |

### 2.2 Fabricated or unsupported content to leave behind

| What | Problem |
|---|---|
| Satellite layer with positions | No backend source existed; it was invented |
| "Public camera feeds" placeholders | Contradicts the ethics policy: the project never fetches discovered feeds |
| Hard-coded legal badges per city | Not derived from anything the backend returns. Policy text lives on `/ethics`, sourced from `ETHICS_AND_SCOPE_POLICY.md` |
| Any stat with no source key | Banned by ground rule 1 |
| The "radar eye" mark and cyan identity | Replaced (section 6) |
| Test counts from old docs | The verified count is 431 passed on 2026-10-12 |

### 2.3 Lessons from the 2026-10-12 integration (carried into the contracts, section 15)

Routes in the zip did not match the real backend (`/api/simulate/*`, `/api/audit/ledger`, `/api/integrity/{id}`); `/api/devices` returns GeoJSON whose properties must be flattened; the detection-event body is `{camera_id, event_type, detected_at, idempotency_key}`; SSE messages are `type: text|chunk|done|error`; `All India` is served from cache only; CORS defaulted to the wrong origin; the dev database's audit chain was already broken and the UI reported that honestly. These cost hours. Section 14.2 removes the first class of problem with generated types.

---

## 3. Product truth sheet (content source of truth)

All copy is written from this section. Numbers are copied from `paper/results.md` (generated, canonical per `CLAUDE.md`). `eval/eval_report.md` predates the Tier 2 weight change of 2026-10-09 and must not be used.

### 3.1 The method

| Part | What it does | Key constants |
|---|---|---|
| **Channel A** posture | `T_cve` from NVD and CISA KEV CVEs by category, authentication, owner type, firmware patch age, corroboration, latency | tiers: high >= 80, medium 50-79, low < 50 |
| **Channel B, Tier 1** banner drift | Passive comparison of a device's current banner fingerprint with its baseline. No packets to the device. Weights: firmware .25, server .20, ports .20 (Jaccard), resolution .20, product .10, codec .05 | drift threshold 0.15 |
| **Channel B, Tier 2** liveness | `L = 1 - max(1.0 * Freeze, 0.6 * q, 0.5 * m)`: pHash freeze (>= 25 frames, Hamming distance <= 1), blur and exposure drift against a per-camera EWMA (alpha = 0.05), declared-spec mismatch. Runs only on authorized footage | weights (1.0, 0.6, 0.5) since 2026-10-09 |
| **Signal integrity** | `s = (1 - Drift) * L` (just `1 - Drift` when Tier 2 is unavailable) | |
| **Gate** | `G(s) = 1` if `s >= 0.85`; `0.3 + 0.7 (s - 0.50) / 0.35` if `0.50 <= s < 0.85`; `0.3` and the score capped at 30 if `s < 0.50` | theta_low 0.50, theta_high 0.85, floor 0.3, hard cap 30 |
| **Fusion** | `T_final = T_cve * G(s)` | |

The thresholds are served live by `GET /api/config/thresholds`. The UI never hard-codes them: the static copy in the landing facts is the fallback and is labelled as such.

### 3.2 Headline results (verified, synthetic corpus, n = 120: 63 fabricated, 57 genuine)

| Key | Claim | Value |
|---|---|---|
| `res.model.wa` | Weighted average: accuracy / recall / F1 / FP | 0.792 / 0.603 / 0.753 / 0 |
| `res.model.advanced` | CVE-only (best vulnerability baseline) | 0.833 / 0.683 / 0.811 / 0 |
| `res.model.bayesian` | Bayesian log-odds | 0.842 / 0.746 / 0.832 / 3 |
| `res.model.igdctf` | IG-DCTF | 0.975 / 0.952 / 0.976 / 0 (95% Wilson accuracy interval 0.929 to 0.991) |
| `res.mcnemar` | Exact McNemar, IG-DCTF vs CVE-only | 17 vs 0 discordant, p = 1.53e-5 |
| `res.strat.with_b` | Accuracy on the 30 scenarios with Channel B: WA / Advanced / Bayesian / IG-DCTF | 0.433 / 0.433 / 0.467 / 1.000 |
| `res.strat.without_b` | Accuracy on the 90 scenarios without Channel B | 0.911 / 0.967 / 0.967 / 0.967 |
| `res.ablation` | Channel A only / Channel B only / additive / multiplicative, F1 | 0.811 / 0.444 / 0.914 / 0.976 (misses 20 / 45 / 10 / 3) |
| `res.sweep` | Threshold sweep | F1 0.976 at all 42 grid points within 0.01: the corpus cannot select the thresholds |
| `res.tier1` | Tier 1 benchmark | 100 cases, 0 FP, 0 FN, 0.0038 ms per device; **13 distinct cases** |
| `res.tier2` | Tier 2 benchmark | 80 cases, 0 FP, 0 FN, mean latency 9.6 frames; synthetic frames only |
| `res.t2.end2end` | Genuine live, freeze loop, quality drift, spec mismatch: mean `T_final` | 100.0 / 30.0 / 30.0 / 30.0 (with `T_cve` = 100, drift = 0) |
| `res.overhead` | Cost per event: Channel A only / full IG-DCTF | 2.60 us / 4.69 us (in-process Python, no I/O) |
| `eval.tests` | Test suite | 431 passed, 2026-10-12 |

### 3.3 The limits block (mandatory wherever results appear)

Shown in full on `/research`, summarised on the landing results section, each line with its claim id from `paper/CLAIMS.md`.

- The corpus is synthetic and hand-authored; labels for the 90 attribute-only scenarios follow the intended tier (C1).
- All of the gain comes from the 30 scenarios that carry Channel B fields; on the other 90 IG-DCTF equals the CVE-only model (C4, C5).
- The corpus cannot choose the gate thresholds (C7).
- Tier 1 was benchmarked on 13 distinct cases (C8). Tier 2 on synthetic frames, with weights revised after seeing the benchmark (C10).
- A loop of real footage has natural motion and is not caught by the frozen-frame rule (C14).
- No field data. Real-world effectiveness is unverified (C17).

### 3.4 Facts are generated, not typed

`frontend/scripts/sync-facts.mjs` reads `paper/data/results.json` and writes `src/lib/content/facts.generated.ts` (keys above, each with `{ value, source, section }`). Hand-written facts live only in `facts.manual.ts` (constants from 3.1, the test count). Rules:

- A test fails if any component renders a number that is not imported from facts.
- A test fails if `facts.generated.ts` is older than `paper/data/results.json`.
- `facts.manual.ts` entries without a `source` field fail the lint.

This makes ground rule 1 mechanical instead of a promise.

### 3.5 Copy rules

Sentence case. No em-dashes or en-dash separators in visible copy. No filler verbs ("unlock", "supercharge", "seamless"), no "AI-powered", no "revolutionary", no cute phrases. Where a claim needs a hedge, the hedge is in the same sentence.

---

## 4. Information architecture

| Route | Purpose | Rendering |
|---|---|---|
| `/` | Landing: the blind spot, the method, the results with their limits, the architecture, ethics, the console | Server Components with client islands for motion and WebGL |
| `/research` | The method in full: propositions with equations (KaTeX), the figures redrawn as SVG from `results.json`, limits block, paper download | Static (SSG) |
| `/lab` | Instruments: gate explorer, attack simulators, scenario replay. All demo-labelled | Client |
| `/console` | Live operations: map, alert stream, device inspector, analytics, zone brief, command palette | Client app over REST, SSE and WebSocket |
| `/console/devices/[id]` | Device forensics: factor breakdown, Channel B detail, models, decay, audit trail, verdict | Client; shared-element view transition from the map marker |
| `/verify/[alertId]` | Public proof page: the alert's Merkle path to the anchor, recomputed in the browser | Client |
| `/ethics` | Scope and governance, sourced from `ETHICS_AND_SCOPE_POLICY.md` | Static |
| `/not-found` | Branded 404 (the hood, closed) | Static |

Global nav (single line, <= 72 px): mark + wordmark, `Method` (anchor), `Research`, `Lab`, `Ethics`, `GitHub`, primary CTA **Open console**. "Open console" is the only console CTA label on the whole site.

---

## 5. Design system

### 5.1 Colour tokens (dark, theme-locked)

Defined once as CSS variables in `src/styles/tokens.css`, mapped into Tailwind v4 `@theme`. Contrast ratios were computed 2026-10-13 (WCAG relative luminance).

| Token | Value | Use | Contrast |
|---|---|---|---|
| `--ink-0` | `#0A0C0B` | Page background, map water | |
| `--ink-1` | `#101311` | Raised surface, map land | |
| `--ink-2` | `#171B19` | Elevated surface, popovers | |
| `--ink-3` | `#202522` | Hover surface, input fill | |
| `--line` | `rgb(231 234 227 / 0.08)` | Hairlines, used sparingly | |
| `--line-strong` | `rgb(231 234 227 / 0.16)` | Active tabs, focus-adjacent borders | |
| `--bone` | `#E7EAE3` | Primary text (lichen bone, a cool grey-green, not DIDA's warm bone) | 16.1:1 on ink-0, 14.3:1 on ink-2 |
| `--bone-2` | `#A4AAA1` | Secondary text | 8.3:1 / 7.3:1 |
| `--bone-3` | `#6E746C` | Tertiary text, captions, only >= 18 px or non-essential | 4.1:1 / 3.6:1 |
| `--signal` | `#F3A33A` | Sodium amber, the one accent: primary CTA, focus ring, the eye, low-trust state | 9.5:1 on ink-0, 8.4:1 on ink-2 |
| `--signal-dim` | `rgb(243 163 58 / 0.14)` | Accent tints | |

Button labels are `ink-0` on `signal` (9.5:1), never white on amber. The logo on light backgrounds uses `#A85F00` (4.9:1 on white).

**Accent lock:** amber is the only hue on every page. There is no second colour for "good", "bad" or "warning". The meaning of colour is "attention": the more attention a device deserves, the more amber it carries.

**Severity encoding (real state, never decoration).** Colour is never the only carrier: shape, text and the hood gauge say it too.

| State | Map symbol | Colour | Label (always shown) | Hood gauge |
|---|---|---|---|---|
| High trust (>= 80) | filled circle, 4 px | `bone-2` at 70% | High | open |
| Medium trust (50-79) | ring, 6 px, 1.5 px stroke | `signal` at 55% | Medium | partly closed |
| Low trust (< 50) | filled diamond, 8 px | `signal` 100% | Low | nearly closed |
| Gate tripped | filled diamond + one outer ring that pulses once on appearance | `signal` 100% | Gate tripped | closed at the floor |
| Demo | any symbol with a dashed outline | as above | Demo | as above |

### 5.2 Typography

- **Geist** (display and UI) and **Geist Mono** (numbers, identifiers, code) via `next/font` from the `geist` package. Self-hosted, `display: swap`, no Google Fonts link.
- Display: weight 600, tracking `-0.035em`, leading 1.02. Hero `clamp(2.75rem, 5.2vw, 4.75rem)`, max 2 lines.
- H2: `clamp(2rem, 3.4vw, 3rem)`, weight 600, tracking `-0.025em`.
- Body 16 to 17 px, leading 1.6, max 62ch, `text-wrap: pretty`; headings `text-wrap: balance`.
- All numbers in Geist Mono with `font-variant-numeric: tabular-nums`, including every score, drift value and hash.
- Equations on `/research` are KaTeX with the Latin Modern face, set at body size, kept visually quiet.
- Sentence case everywhere. No serif swap for emphasis.

### 5.3 Shape, space, depth

- **Radius lock:** controls are full pill; panels and cards 14 px; inputs 10 px; chips 6 px; WebGL canvases and the map have no radius (they bleed).
- **Spacing:** 4 px base. Landing sections `py-28 md:py-36`; console on an 8 px grid.
- **Container:** `max-w-[1360px] mx-auto px-5 md:px-8`.
- **Depth:** no drop shadows on dark. Elevation is tone (ink-1 to ink-2) plus a 1 px inner highlight `inset 0 1px 0 rgb(231 234 227 / 0.06)`.
- **Grain:** one fixed, `pointer-events-none` SVG-noise overlay at 3% over the whole page (never on scrolling containers or the map).
- **Glass:** only the floating nav and the command palette use `backdrop-filter: blur(16px)`, both fixed, with a solid `ink-1/95` fallback under `prefers-reduced-transparency`.
- **Borders:** hairlines only where they organise content. No decorative grid lines.

### 5.4 Z-index scale (`src/lib/constants/z.ts`)

`canvas: 0`, `map: 5`, `content: 10`, `overlay: 15`, `sticky: 20`, `nav: 30`, `panel: 35`, `modal: 40`, `toast: 50`, `grain: 60`. Nothing else is allowed.

### 5.5 Motion tokens (`src/lib/animations/tokens.ts`)

| Token | Value | Use |
|---|---|---|
| `dur.micro` | 160 ms | hover, press |
| `dur.short` | 260 ms | state changes, tabs |
| `dur.base` | 520 ms | reveals |
| `dur.long` | 900 ms | hero beats |
| `dur.scene` | 1600 ms | WebGL camera moves |
| `ease.out` | `cubicBezier(0.16, 1, 0.3, 1)` | entrances |
| `ease.inOut` | `cubicBezier(0.65, 0, 0.35, 1)` | camera, uniforms |
| `ease.spring` | `spring({ stiffness: 170, damping: 22 })` | magnetic, tilt return, hood flare |
| `stagger.text` | 18 ms per character, 45 ms per word | text reveals |

No `linear` easing except time-driven shader uniforms.

### 5.6 Components (owned, `src/components/ui/`)

On shadcn/ui and Radix primitives (Tabs, Tooltip, Dialog, ScrollArea, Separator, Popover), customised to the tokens, never shipped in default state: `Button` (primary / secondary / ghost / link), `MagneticButton`, `Badge` (square), `Kbd`, `Stat`, `SourceNote` (footnote marker linking to the `results.md` section), `CodeBlock`, `TierTag` (shape + label), `HoodGauge` (6.3), `EmptyState`, `Skeleton`, `InlineError`, `OfflineState`, `DemoTag`, `SyntheticChip`.

---

## 6. The mark and the hood

### 6.1 Source of truth

`assets/logo/build_logo.py` generates every static asset and `assets/logo/cobra-mark.geometry.json` (centre, nine rib angles, `rIn` 34, `rOut` 90, eye radius 24, half-distance 13.2). The web app imports that JSON; it never redraws the mark by hand. Changing the mark means changing the script and re-running it.

Meaning: nine ribs fan like a cobra flaring its hood, around one eye. The eye is the lens-shaped overlap of two circles: the region where the device is secure **and** its signal is authentic, which is the IG-DCTF trust intersection. It is also a cobra's eye and a camera aperture. Rejected during design: an outline hood with two rings (reads as a light bulb), rings with a bridge (reads as a smiley), plain Venn rings (generic).

### 6.2 Assets

`cobra-mark.svg` and `.png`, `cobra-mark-transparent.svg`, `cobra-favicon.svg` (seven fat ribs for 16 px), `cobra-logo-dark.svg` and `cobra-logo-light.svg`, `cobra-banner.svg` and `.png` (1280 x 640, GitHub social preview). The OG image (`/opengraph-image`) is generated with `next/og` from the same geometry, so it cannot drift from the mark. All SVG colour literals match section 5.1.

### 6.3 The hood is a gauge

The mark carries data. Everywhere a gate state exists, the same component draws it.

- **Spread** = `236 deg * G(s)`. Ribs keep the 4.5 degree gap; rib width is `(spread - 4.5 * 8) / 9`. At the floor `G = 0.3` the spread is 70.8 degrees and each rib is 3.9 degrees wide, so a tripped gate is nearly closed but never invisible.
- **Eye intensity** = `T_final / 100`. A device at the hard cap of 30 shows a dim eye.
- **Alert flare:** a live `INTEGRITY_GATE_TRIPPED` message closes the top-bar gauge with `ease.spring` over `dur.short` and flashes the matching stream row once.
- `HoodGauge` renders SVG at 16 to 160 px (table rows, popups, inspector) and shares its geometry function with the WebGL hood, so the two cannot disagree.
- Under reduced motion the gauge snaps to its state with no transition.

---

## 7. Landing page (`/`)

One continuous story: **"A secure camera can still lie."** The hood introduced in the hero is the visual spine; every later section reuses its geometry and the amber eye, so the page reads as one experience. Eyebrow budget: at most 3 across the page. No section numbering, no scroll cue, no version strings. Layout families never repeat.

### 7.1 Navigation

Floating pill, detached 16 px from the top, centred, `max-w-fit`, glass as in 5.3, height 56 px. Left: mark + wordmark. Right: links + **Open console** (MagneticButton, small). Hides on scroll down and returns on scroll up (Anime.js `onScroll` direction, no raw scroll listener). The active link's underline slides between links (`dur.short`). Mobile: mark + two-line hamburger that morphs to an X, opening a full-screen ink overlay with staggered links. *Purpose: state, and getting out of the way of reading.*

### 7.2 Hero (asymmetric split, `min-h-[100dvh]`, top padding <= `pt-24`)

- **Left (5/12):** headline "A secure camera can still lie."; subtext (16 words) "COBRA-WATCH scores exposed cameras on how vulnerable they are and whether their feed is still real."; CTAs **Open console** (primary, magnetic) and **Read the research** (text link with a moving arrow). No eyebrow, no trust strip, no tagline.
- **Right (7/12, bleeding off the right edge):** the 3D hood (section 8) on the feed-field background (section 9.1).
- **LCP strategy:** the headline is the LCP element and renders on the server. The canvas lazy-loads after hydration; until then the static mark SVG sits at the same position and scale, and the WebGL scene cross-fades over it, so there is no layout shift.

**Entrance timeline (one Anime.js `createTimeline`, about 2.4 s):**

| t (ms) | Beat | Purpose |
|---:|---|---|
| 0 | Feed field `uIntro` 0 to 1 (rises from black) | sets the stage |
| 120 | Nav slides down 12 px and fades in | orientation |
| 200 | The eye ignites first: amber intensity 0 to 1 over `dur.base` | the protected core, the thing being decided |
| 360 | Headline words: blur 8 px and y 24 px to sharp, 45 ms stagger | message first |
| 800 | Subtext lines reveal (line mask) | reading order |
| 1100 | CTAs scale 0.96 to 1 and fade | action after message |
| 700-2200 | The hood opens: nine ribs start stacked closed and fan out to 236 degrees with `ease.spring`, 70 ms stagger, camera dollies 6% closer | storytelling: the hood flares, the cobra wakes |

Reduced motion: everything appears at once with a 200 ms opacity fade; the scene renders one static frame with the hood open.

### 7.3 The blind spot ("twin cameras")

Layout family: **two-column comparison**.

Two camera cards side by side. Both show the same banner text in Geist Mono (identical product string, server, firmware, ports) and the same CVE-only score, **100**. Below each, a small feed pane drawn by the feed shader (9.4): the left feed moves; the right feed has frozen. A frame counter beside the right pane stops at 25 and a tag reads `25 identical frames`. Then a gate row: IG-DCTF score **100** on the left, **30** on the right, with the two hood gauges (open and at the floor).

Caption, always visible: "Illustration of the `genuine_live` and `freeze_loop_attack` categories (results, section 5). The decoy has the same banner and a clean CVE record."

Scroll beat: the section's background feed field (9.1) freezes when the right feed freezes, and resumes when the section leaves. *Purpose: storytelling. The reader sees in ten seconds why a clean vulnerability record is not trust.*

### 7.4 "Walk the gate" (sticky stage)

Layout family: **sticky 3D stage with scrolling panels**. A 400vh section; the canvas is sticky on the left (CSS `position: sticky`, native scroll, no scroll hijack), five panels scroll past on the right.

| Panel | Stage shows | Copy source |
|---|---|---|
| 1. Posture | One outlined circle appears: Channel A | 3.1: CVEs, authentication, owner, patch age |
| 2. Integrity | A second circle appears: Channel B, with two arcs for Tier 1 drift and Tier 2 liveness | 3.1 |
| 3. Both must hold | The overlap fills amber and becomes the eye | "Trusted only where both hold", `P(secure and authentic)` |
| 4. The gate | The ribs fan out; the opening angle is `G(s)` | gate function and thresholds from `/api/config/thresholds` |
| 5. Trips, tapers, passes | The hood closes to the floor, partly, and fully; three small labelled states | "Single-field banner changes taper but never trip the gate" (C9) |

Pointer: camera parallax of +/- 3 degrees. Each panel is <= 25 words plus one metric with a `SourceNote`. Mobile: the canvas becomes a 60vh block at the top of each panel group. *Purpose: storytelling; the 3D object explains the method rather than decorating it.*

### 7.5 Gate explorer (interactive)

Layout family: **tabbed workspace** (the same component as `/lab`, in compact form). Controls: `T_cve` slider, banner drift slider, freeze toggle, blur slider, spec-mismatch toggle, and a "Tier 2 unavailable" toggle. Outputs update live from the in-browser scoring port (14.4): `Drift`, `L`, `s`, `G`, `T_final`, tier, gate status. Visuals: the feed pane (9.4) degrades with the controls (blur applies, freeze stops time, spec mismatch letterboxes and mislabels the resolution), the `G(s)` curve with a moving point and the two threshold lines, the hood gauge, and a strip comparing "CVE-only would say" with "IG-DCTF says".

Header chip: `Computed in your browser, same formula as the backend (parity-tested)`. If `/api/config/thresholds` is unreachable, the explorer uses the static constants and shows `Static thresholds (backend offline)`. *Purpose: feedback and proof. Every motion reports a computed value.*

### 7.6 Results, with their limits

Layout family: **one giant comparison + a supporting row**.

- Main: four horizontal bars (no background tracks) for F1 on the synthetic corpus: weighted average 0.753, CVE-only 0.811, Bayesian 0.832, IG-DCTF 0.976, each with its 95% Wilson accuracy whisker in a detail view and confusion counts on hover and focus. Bars grow on enter; `AnimatedCounter` counts once from 0 in Geist Mono. Persistent chip: `Synthetic corpus, n = 120`.
- Supporting row (4 stats, not cards): `17 vs 0` discordant scenarios (McNemar p = 1.5e-5); `3 vs 10` misses, multiplicative vs additive fusion; `4.7 us` per event; `431` tests passed.
- **Where it helps, and where it does not:** a two-row small multiple of the stratified accuracies (3.2): with Channel B (n = 30) the CVE-only model reaches 0.433 and IG-DCTF 1.000; without Channel B (n = 90) they are equal at 0.967.
- The limits block (3.3) follows as plain text with claim ids. It is part of the section, not a footer link.

*Purpose: hierarchy, and the honesty of a result shown beside its weaknesses.*

### 7.7 "From event to ledger" (architecture)

Layout family: **horizontal annotated pipeline** (vertical on mobile).

Six stages drawn as one SVG: detection event, corroboration, Channel A, Channel B, the gate, alert and audit ledger. A single event packet travels the path as the section enters (Anime.js `createDrawable` and a motion path). The gate stage is the only one that shows a measured number (`4.7 us`, `res.overhead`); stages without a measurement show none. Under the pipeline, three facts with sources: idempotency and 60 s freshness on writes, Merkle-chained audit entries, passive-only sources. *Purpose: storytelling and feedback.*

### 7.8 "Seen from above" (live map teaser)

Layout family: **full-bleed media band**. A MapLibre globe (v5 globe projection) that flies to India when the section enters, then shows the device layer from the real backend with the severity encoding of 5.1, positions flagged as estimates, IPs masked. If the backend is offline the band shows the offline state and the static mark, never sample data. Interaction: none beyond pan and zoom; the CTA is **Open console**. *Purpose: proof that this runs on real data.*

### 7.9 "What it will never do" (ethics)

Layout family: **three-column plain text** (no cards). Passive only; no live video from discovered devices; no biometrics or personal data. Each column has two lines from `ETHICS_AND_SCOPE_POLICY.md` and a link to `/ethics`. The known active-check gap is stated honestly on `/ethics` (C15). *Purpose: trust.*

### 7.10 Process: "Run it"

Layout family: **vertical stepped code rail**. Steps (all real): clone and `cp .env.example .env`; `pip install -r backend/requirements.txt`; `python backend/main.py` (API and docs on `:8000`); `cd frontend && npm install && npm run dev` (`:3000`); `docker compose up --build`. The code panel swaps with a 140 ms cross-fade and 8 px slide; a progress line on the rail fills as steps scroll past; the copy button gives success feedback.

### 7.11 Interactive CTA

Full-width band. Headline "Open the console." One button: **Open console**. A large hood beside it is closed at rest. On hover or focus of the button the hood opens to full spread and the eye brightens to full (the same `ease.spring` as the hero); on blur it relaxes to 70%. *Purpose: feedback on intent, and the mark demonstrating its own meaning.*

### 7.12 Footer

Mark, one-line description, links: Research, Lab, Console, Ethics, GitHub, `results.md`. No version strings, no locale strip. Credit line to be confirmed (open decision 7).

---

## 8. Three.js system

### 8.1 Decision: vanilla Three.js on WebGL, thin React layer (no react-three-fiber)

One renderer and one loop per canvas, owned by `<Stage>`. Child components register objects and per-frame callbacks through context and dispose everything on unmount. Reasons: Anime.js drives Three.js objects and uniforms directly; one explicit loop makes the performance governor and offscreen pausing simple; and react-three-fiber v10 is still alpha (checked 2026-10-13), so adopting it now would trade a stable path for a reconciler we do not need.

WebGPU: Three.js's `WebGPURenderer` with TSL and automatic WebGL2 fallback is production-ready in 2026 per several sources and WebGPU is on by default in the major browsers. We do **not** adopt it for v1: the hand-written GLSL path is smaller to reason about and Anime.js already drives it. It is a Phase 9 spike with a decision gate (section 14.2).

### 8.2 Components (`src/components/three/`)

| Component | Responsibility |
|---|---|
| `Stage` | Creates `WebGLRenderer` (`antialias` on the high tier only, `powerPreference: 'high-performance'`), the single RAF loop, `ResizeObserver`, DPR policy, visibility and offscreen pausing, context-loss handling. Exposes `useStage()` (scene, camera, `onFrame(cb)`, `invalidate()`) |
| `Camera` | Perspective rig: base pose, scroll pose targets, pointer parallax (Anime.js animated) |
| `Lighting` | One key directional light and a hemisphere fill; the eye is emissive, so no point lights |
| `HoodRibs` | Nine `ExtrudeGeometry` annular sectors built from `cobra-mark.geometry.json`, one shared material, per-rib `uSpread` offset so the hood fans open and shut by changing one uniform |
| `EyeLens` | The lens-shaped overlap as a bevelled `ExtrudeGeometry` (convex dome), emissive amber, plus a camera-facing additive glow sprite |
| `FrameParticles` | Small 16:9 quads as one `InstancedMesh` (high tier) or `Points` (low tier). Frames drift toward the eye through the gaps; in the blind-spot beat, attack-tagged frames stop at the closed ribs. Illustrative only |
| `CircleRings` | The two outlined circles of "Walk the gate", drawn as thin tori that animate into the overlap |
| `InteractionController` | Normalises pointer (-1 to 1), scroll progress per section, hover and active section into one mutable state object that frame callbacks read. No React state |
| `QualityGovernor` | Tier selection and the runtime FPS governor (17.2) |

### 8.3 Scenes

- **Hero and Walk the gate:** the same `Stage` persists across both (the canvas stays mounted while either is near the viewport), so geometry never re-initialises.
- **Console:** no WebGL hood. The console uses the SVG `HoodGauge`; the only WebGL in the console is the map (MapLibre, and deck.gl in Phase 2).
- **Background feed field:** a separate small `Stage`, fixed behind content, in an `OffscreenCanvas` worker where supported (9.1).

### 8.4 Interaction behaviour (subtle by rule)

Pointer parallax of +/- 3 degrees with `ease.spring`. On the high tier, hovering a rib (raycast) brightens it and shows its index in a DOM tooltip; the tooltip text is the nearest-meaning label (for example "Rib 1 of 9") and never invents a mapping. Scroll drives camera dolly and the `uSpread` of the hood. When the console CTA is hovered anywhere, the page-state signal brightens the eye.

### 8.5 Disposal contract

Every component that creates a geometry, material, texture or render target registers it with `Stage`'s disposer. On unmount: dispose in reverse order, `renderer.dispose()`, `forceContextLoss()` only on route exit, remove listeners, cancel the RAF loop. A dev-only assertion checks that `renderer.info.memory` returns to zero after a mount and unmount cycle.

---

## 9. Shaders (`src/shaders/`)

All GLSL lives in separate files imported as strings through Turbopack's `raw-loader` rule for `*.glsl|*.vert|*.frag` (the webpack rule is not used: Next.js 16 fails the build if a webpack config exists). Uniform interfaces are typed in `src/lib/shaders/uniforms.ts`.

### 9.1 `feed.vert` / `feed.frag`: the feed field

The page background is a fake camera feed, on purpose: a slow, dark, low-contrast procedural scene (soft horizontal banding like scan lines, a faint drifting luminance field, a slow vertical "tracking" band), tinted by one dim amber pool where the hood sits. It behaves like a healthy feed until a section is about a feed going wrong. The scene is abstract and unlabelled in the background (it carries no data), which is acceptable under ground rule 4 because it is decoration that never claims to depict a device; the labelled feed panes in 7.3 and 7.5 use the same shader in a bounded canvas.

| Uniform | Type | Controls |
|---|---|---|
| `uTime` | float | seconds, linear |
| `uResolution` | vec2 | canvas px |
| `uPointer` | vec2 | eased pointer 0..1 |
| `uIntro` | float | 0..1 fade from black (Anime.js) |
| `uScroll` | float | 0..1 page progress, shifts band phase |
| `uDrift` | float | 0..1: tracking band amplitude and colour-channel offset, the visual of Tier 1 drift |
| `uFreeze` | float | 0 or 1: when 1, `uTime` is held at the captured value, the visual of a frozen feed |
| `uBlur` | float | 0..1: separable blur radius, the visual of quality drift |
| `uSpec` | float | 0..1: letterbox and resolution mismatch overlay, the visual of declared-spec mismatch |
| `uAccentPos` | vec2 | where the amber light pools (follows the hood) |
| `uAccentStrength` | float | 0..0.25, animated on CTA hover |
| `uOctaves` | int (define) | noise octaves: 4 high, 3 medium, 2 low |
| `uGrain` | float | in-shader dither against banding |

Frame rate is capped at 30 fps for the background layer and it pauses when the tab is hidden. Reduced motion renders one static frame.

### 9.2 `ribs.vert` / `ribs.frag`

Rim lighting (fresnel) in bone with a soft amber bounce from the eye; `uSpread` rotates each rib about the hood origin; `uHighlight` per rib for hover.

### 9.3 `frames.vert` / `frames.frag`

Frame particles: size attenuation, a thin rectangular outline sprite in the fragment shader, per-instance seed for phase. `uProgress` moves a frame along a path through the rib gaps; attack-tagged frames stop at the ribs and flare once (`uFlare`).

### 9.4 `glow.frag`, and the feed pane

`glow.frag` is radial falloff for the eye (additive, depth-write off). It is the only bloom in the project. The labelled feed panes reuse `feed.frag` with bounded `uFreeze`, `uBlur`, `uSpec` and `uDrift` driven by the explorer or the twin-camera section.

---

## 10. Console (`/console`)

A tool, not a landing page. Density 8, motion only for state changes.

### 10.1 Layout (desktop >= 1280)

- **Top bar:** mark and `HoodGauge` (reflects the latest gate state), city select (8 cities + All India), connection status (`connecting` / `live` / `disconnected` with retry countdown), counts from `GET /api/stats`, **Run scenario**, theme-free. Demo traffic is always visibly tagged.
- **Left (3 cols):** alert stream, virtualised, newest on top. Row: time, tier shape, device label, `TierTag`, action, score (mono), demo tag. New rows slide in over `dur.short`; gate-tripped rows flash once. Filters: tier, gate tripped, demo, owner type.
- **Centre (6 cols):** the map (10.2).
- **Right (3 cols):** the inspector (10.3), or the zone brief when a zone is drawn.
- Tablet: two panes and a segmented control. Mobile: single column with tabs (Map / Stream / Detail); nothing is hidden.

### 10.2 Map

- **Engine:** MapLibre GL JS v5 with a vector basemap from a self-hosted Protomaps PMTiles file, styled from `@protomaps/basemaps` with a custom flavour in the palette: land `ink-1`, water `ink-0`, roads and boundaries as `bone` hairlines at 6 to 14%, labels `bone-3`, no POI icons. Fonts and sprites are self-hosted too, so a pan makes no third-party request.
- **Basemap build:** `pmtiles extract` of an India bounding box (`68.1,6.7,97.4,35.7`) with `--maxzoom` chosen to fit the hosting budget; the size is **unmeasured** and must be recorded at Phase 1 (sources say each extra zoom level roughly doubles size). Fallback if the file is too large: zoom 0-10 only, with the city views falling back to raster OSM through the CSS dark filter proven in the 2026-10-12 integration.
- **Device layer:** MapLibre native source with clustering for the 4,000+ cached devices; clusters are `ink-3` discs with a bone count; unclustered devices use the severity encoding (5.1). Popup: estimated position note, masked IP, owner type, tier, `HoodGauge`.
- **Overlays:** `GET /api/heatmap` as a heat layer toggle. Phase 2: deck.gl `@deck.gl/maplibre` (interleaved) for corroboration and collusion-ring arcs between devices (`GET /api/audit/collusion`) and an H3 hexagon density layer. Both are off by default.
- **Zone:** draw a circle or polygon to select devices; the zone opens the brief (10.5).
- **Marker to page:** selecting a device and pressing Enter or "Open forensics" runs a View Transition (the marker's `HoodGauge` morphs into the forensics header).

### 10.3 Inspector

Sections, top to bottom, each with a designed loading, empty and error state:

1. **Header:** masked IP, manufacturer, device type, owner and owner type (with the ownership confidence), estimated city, `TierTag`, `HoodGauge`, score and its **basis** label (`static posture` or `on demand`).
2. **Channel A factors:** the factors returned by the trust-score endpoint as bars with their labels; CVEs with CISA KEV flagged.
3. **Channel B:** Tier 1 drift as six weighted rows (product .10, server .20, firmware .25, ports .20, resolution .20, codec .05) with the baseline and current banner values side by side; Tier 2 liveness shown only for authorized footage cameras, otherwise `Tier 2 unavailable: no authorized footage for this device` (never a fabricated zero).
4. **Gate:** `s`, `G(s)`, multiplier, hard cap, gate status, drawn on the `G(s)` curve with the live thresholds.
5. **Scoring models:** the four models side by side (weighted average, CVE-only, Bayesian log-odds, IG-DCTF) plus the decayed variant, from `score-comparison` and the trust-score endpoint.
6. **Decay:** the adaptive decay curve (`/api/decay-curve`, `/decay-preview`) as a hand-built SVG.
7. **Audit trail:** `GET /api/devices/{id}/audit-trail`, each entry linking to `/verify/{alertId}`.
8. **Verdict:** Verified / False alarm. If the backend answers 403 (a detection API key is set and the browser has none), the UI says exactly that and offers no retry loop.

### 10.4 Analytics drawer

Tabs: **Fleet** (trust distribution), **Alerts** (timeline, demo series visually separate), **Integrity** (`/api/integrity/stats`, gate trips), **Ledger** (entries, chain stats, "Verify full chain" calling `/api/audit/verify`, and the honest result including a failed verification), **Accuracy** (`/api/eval/live` and the static results with their limits chip). Charts are hand-built SVG from `d3-scale` and `d3-shape`; no chart library.

### 10.5 Zone brief

`POST /api/brief/stream` (SSE; message types `text`, `chunk`, `done`, `error`) with a request built from the zone's real devices, news from `GET /api/news`, and a streaming text reveal. The panel labels the text `Generated by a language model from the devices in this zone` and shows the model's error verbatim when the key is missing.

### 10.6 Command palette (cmdk)

`Ctrl or Cmd K`: navigate, jump to a city, find a device, run a scenario, and **ask in plain language** through `POST /api/nl-query`. The palette shows the parsed filters the model returned (so a query is auditable), applies them to the map, and falls back to plain text search when no key is configured (the router already does this). Glass as in 5.3.

### 10.7 States

Every panel has designed loading (skeleton rows matching the final layout), empty ("No alerts yet. Run a scenario or send an event."), error and disconnected states. A polite `aria-live` region announces gate-tripped alerts, throttled to one per 5 s.

---

## 11. Device forensics (`/console/devices/[id]`)

The inspector at full width: the six inspector sections in a two-column reading layout, the feed pane and gate curve enlarged, the full audit trail with Merkle proof links, and the model comparison as a table with the confusion-relevant columns. The header `HoodGauge` is the shared element of the View Transition from the map.

## 12. Lab (`/lab`)

All content is demo-labelled. Tabs:

| Tool | Backend | Notes |
|---|---|---|
| Gate explorer | none (in-browser port, parity-tested) | The full-size version of 7.5 |
| Attack simulators | `POST /api/simulate/replay-attack`, `timestamp-skew`, `rate-flood`, `collusion-ring`, `reset` | Shows the real response (status code, reason) and the resulting alert |
| Scenario replay | `POST /api/scenarios/run` | Twelve synthetic events, two seconds apart, streamed into the stream with `demo: true`; 409 and 404 shown verbatim |
| Natural-language query | `POST /api/nl-query` | Same as the palette, with the parsed filters visible |

## 13. Research, Verify, Ethics

- **`/research`:** the method in reading order: problem, the two channels, the gate, the five propositions (non-compensation, blind spot, single-field tolerance, Lipschitz constant 2, reachability for `w > 0.4`) typeset with KaTeX at build time, the results with the limits block (3.3), the ablation and fusion control, threshold sweep, Tier 1 and Tier 2 benchmarks, overhead. Figures are redrawn as SVG from `results.json` (not screenshots) and each links to its `results.md` section. A reading-progress rail uses CSS `animation-timeline: scroll()` where supported and Anime.js `onScroll` otherwise. Paper PDF link set at build.
- **`/verify/[alertId]`:** loads `/api/audit/ledger/{alert_id}` and `/api/audit/chain-proof`, recomputes the hashes in the browser with `crypto.subtle`, and animates the Merkle path to the anchor from `/api/audit/anchor`. If the recomputation fails, the page says so plainly. Phase 2.
- **`/ethics`:** the policy text, the in-scope and out-of-scope tables, the legal framework summary, the dual-use mitigations, and the active-heartbeat gap, from `ETHICS_AND_SCOPE_POLICY.md` and `paper/CLAIMS.md`.

---

## 14. Technology decisions

### 14.1 Stack (carried over, with versions to verify at scaffold)

| Package | Why |
|---|---|
| `next` 16.x, `react` and `react-dom` 19.2+ | App Router; Turbopack is the default bundler and View Transitions are available in React 19.2+ (stable in 19.3 per Next.js 16.4 notes) |
| `typescript` strict plus `noUncheckedIndexedAccess`, `@types/*` | typing |
| `tailwindcss` v4, `@tailwindcss/postcss` | styling, CSS-first config |
| `animejs` v4 | the only animation library |
| `three` | WebGL |
| `geist` | Geist and Geist Mono via `next/font` |
| `@phosphor-icons/react` | icons |
| shadcn/ui (copied source), `@radix-ui/*`, `class-variance-authority`, `clsx`, `tailwind-merge` | accessible primitives |
| `zustand` | live event store (WebSocket) |
| `eslint`, `eslint-config-next`, `prettier`, `vitest` | quality |

### 14.2 Additions (new beyond the DIDA spec)

| Addition | Verdict | Why it earns its place |
|---|---|---|
| **MapLibre GL JS v5** (+ globe projection) | Adopt | WebGL vector map, styleable in the palette, native clustering, globe for the landing teaser, no token |
| **Protomaps PMTiles + `@protomaps/basemaps`, `pmtiles`** | Adopt | One static file, no tile server, no third-party requests; light, dark and greyscale flavours generate styles we then override |
| **deck.gl 9.4 (`@deck.gl/maplibre`)** | Adopt in Phase 2 | Arcs for corroboration and collusion links, H3 hexagon density, interleaved with MapLibre. Heavier than needed for the first release; native MapLibre layers carry v1. Check the open interleaved-rendering issues before relying on it |
| **`openapi-typescript` + `openapi-fetch`** | Adopt | Generates types and a typed client from FastAPI's `/openapi.json`. The 2026-10-12 integration lost hours to route and shape drift; this removes that class of bug. CI fails when the committed schema snapshot is stale |
| **`zod`** | Adopt | Runtime validation for what OpenAPI does not describe (WebSocket and SSE messages) and for the flattening of GeoJSON properties |
| **TanStack Query v5, TanStack Virtual** | Adopt | Caching, retries and dedup for REST; virtualised alert stream. Replaces the hand-rolled loader hook |
| **`cmdk`** | Adopt | Command palette with the natural-language query |
| **KaTeX** | Adopt | Server-rendered equations on `/research` |
| **`d3-scale`, `d3-shape`, `d3-array`** | Adopt | Headless maths for hand-built SVG figures; no chart library |
| **OffscreenCanvas + Worker** | Adopt | Moves the background feed field off the main thread to protect INP; falls back to the main thread when unsupported |
| **View Transitions (React 19.2+)** | Adopt | Marker to forensics-page shared-element morph, the one place a route change deserves motion |
| **`next/og`** | Adopt | Generates the OG image from the mark's geometry |
| **React Compiler** | Spike | Stable in Next.js 16 but opt-in; enable only if profiling shows re-render cost in the stream |
| **Three.js `WebGPURenderer` + TSL** | Spike (Phase 9 decision gate) | Production-ready with automatic WebGL2 fallback per 2026 sources, but a migration of the GLSL pipeline. Adopt only if the spike shows a measured frame-time or maintainability win |
| **CSS scroll-driven animations** | Progressive enhancement | The `/research` progress rail; Anime.js `onScroll` is the baseline |
| **Playwright, `@axe-core/playwright`, Lighthouse CI** | Adopt | End-to-end, accessibility and performance gates in section 19 |
| **MSW** | Tests only | Mock the API in unit and e2e tests. Never in the running app (ground rule 1) |

### 14.3 Considered and rejected

| Technology | Reason |
|---|---|
| react-three-fiber, drei, postprocessing | v10 is alpha; an extra reconciler; Anime.js needs direct object access |
| GSAP, Framer Motion, Lenis | Anime.js v4 is the single animation library; no scroll hijack |
| Mapbox GL JS | Needs an access token and phones home |
| Leaflet | The 2026-10-12 map needed a CSS filter hack to look dark and could not rotate, tilt or render a globe |
| CesiumJS, Spline, Lottie, Rive | Weight or an external authoring tool, for no extra meaning |
| Any chart library | Hand-built SVG from real numbers |
| Storybook | Deferred; the lab page and Playwright snapshots cover the use case in v1 |
| Radar sweeps, terminal effects, particle "networks" | Banned by 1.3 |

### 14.4 Scoring parity

The gate explorer and the landing results compute in the browser with `src/lib/scoring/gate.ts`, a direct port of `evaluate_integrity_gate`, `compute_composite_signal_integrity` and `compute_visual_liveness`. A script (`frontend/scripts/export-golden.py`) runs the Python implementation on 200 random vectors plus the threshold edges and writes `tests/fixtures/gate_golden.json`; a Vitest test asserts the TypeScript port matches to 4 decimals. If the backend thresholds change, the golden file is regenerated and the test fails until the port is updated.

### 14.5 Sources checked 2026-10-13

[Next.js 16 overview](https://makerkit.dev/blog/tutorials/nextjs-16), [Next.js 16.4](https://nextjs.org/blog/next-16-4), [Next.js 16 upgrade guide](https://nextjs.org/docs/app/guides/upgrading/version-16), [Protomaps basemaps](https://github.com/protomaps/basemaps), [Protomaps downloads](https://docs.protomaps.com/basemaps/downloads), [MapLibre globe and PMTiles issue 5242](https://github.com/maplibre/maplibre-gl-js/issues/5242), [deck.gl and MapLibre](https://deck.gl/docs/api-reference/mapbox/mapbox-overlay), [deck.gl release notes](https://deck.gl/docs/whats-new), [Anime.js v4 release](https://github.com/juliangarnier/anime/releases/tag/v4.0.0), [Anime.js v3 to v4 migration](https://github.com/juliangarnier/anime/wiki/Migrating-from-v3-to-v4), [Three.js in 2026](https://www.utsubo.com/blog/threejs-2026-what-changed), [openapi-typescript](https://github.com/openapi-ts/openapi-typescript), [openapi-fetch](https://openapi-ts.dev/openapi-fetch/). Web-sourced version claims are secondary sources; exact versions and API names are confirmed against the installed packages at scaffold time and wrapped so call sites never import vendor APIs directly.

---

## 15. Data layer and contracts

### 15.1 Layers

- `src/lib/api/schema.d.ts`: generated by `openapi-typescript` from `backend` `/openapi.json` (script `npm run gen:api`; the snapshot `openapi.snapshot.json` is committed).
- `src/lib/api/client.ts`: `openapi-fetch` client, base URL `NEXT_PUBLIC_COBRA_API_URL` (default `http://localhost:8000`), timeouts, typed errors, an `ApiError` carrying status and the backend `detail`.
- `src/lib/api/normalize.ts`: zod-validated flattening of GeoJSON features into `Device` records, and prettifying of factor strings.
- `src/lib/api/socket.ts`: one WebSocket per tab to `/api/ws/alerts`, exponential backoff (1 s to 30 s), message parsing by `type`, heartbeat check.
- `src/lib/api/sse.ts`: brief stream reader (`text`, `chunk`, `done`, `error`); a thrown `ApiError` must escape the parse loop (a bug in the previous integration).
- `src/lib/state/console-store.ts`: Zustand store for alerts (ring buffer of 1,000), connection state, selected device and filters. Server data lives in TanStack Query, not Zustand.

### 15.2 Endpoint contract (real backend, verified against the router files 2026-10-13)

| Used for | Method and path | Notes |
|---|---|---|
| Health | `GET /health` | Includes `ws_clients` |
| Devices | `GET /api/devices?city=` | GeoJSON; properties include `trust_score`, `action_tier`, `integrity_gate_tripped`, `trust_score_basis`, `cves`, `city`, `geo_source`. `All India` is served from cache only |
| Trust score | `GET /api/devices/{id}/trust-score` | The authoritative on-demand score |
| Integrity | `GET /api/integrity/{id}`, `GET /api/integrity/stats` | Channel B state |
| Thresholds | `GET /api/config/thresholds` | `{tiers:{high_min,medium_min}, gate:{theta_low,theta_high,floor_multiplier,hard_cap}}` |
| Alerts | `GET /api/alerts`, `POST /api/alerts/{id}/verdict` | Verdict needs `X-API-Key` when one is configured |
| Detection event | `POST /api/detection-event` | Body `{camera_id, event_type, detected_at, idempotency_key}`; 409 duplicate, 429 rate limit |
| Live | `WS /api/ws/alerts` | `ALERT` (payload includes `demo`) and `INTEGRITY_GATE_TRIPPED` |
| Analytics | `GET /api/analytics/trust-distribution`, `/alert-timeline`, `/score-comparison`, `/summary`, `GET /api/stats`, `GET /api/heatmap` | |
| Ledger | `GET /api/audit/ledger`, `/ledger/{alert_id}`, `/verify`, `/stats`, `/chain-proof`, `/anchor`, `/velocity`, `/integrity-trips`, `/collusion`, `/collusion/gnn`; `GET /api/devices/{id}/audit-trail` | |
| Decay | `GET /api/decay-curve`, `/api/decay-preview` | |
| Brief, news | `POST /api/brief`, `POST /api/brief/stream` (SSE), `GET /api/news` | Language-model key required |
| NL query | `POST /api/nl-query` | Falls back to text search without a key |
| Live accuracy | `GET /api/eval/live` | |
| Demo | `POST /api/scenarios/run`, `POST /api/simulate/replay-attack`, `/timestamp-skew`, `/rate-flood`, `/collusion-ring`, `/reset` | Alerts flagged `demo: true` |
| Not wired | `GET /api/devices/{id}/heartbeat`, `/api/heartbeat/status` | Opens connections to device addresses; see B2 |

### 15.3 Types and messages

OpenAPI types for every REST response. Hand-written zod schemas only for: `WsMessage` (`ALERT | INTEGRITY_GATE_TRIPPED`), `BriefStreamMessage` (`text | chunk | done | error`), and the GeoJSON flattening. All three are covered by contract tests against recorded fixtures.

### 15.4 IP masking

A single `maskIp()` helper is the only way an address reaches the DOM. Default output `a.b.c.•`. `NEXT_PUBLIC_REVEAL_IP=true` shows the full address for local sessions and adds a persistent `Unmasked` banner. A lint rule forbids rendering `ip` fields directly.

---

## 16. Backend touchpoints (need separate approval; not frontend work)

| # | Change | Why |
|---|---|---|
| B1 | Mask IPs server-side on public read routes behind `EXPOSE_FULL_IP` (default false) | Client-side masking still ships the full address in the JSON; the ethics policy says data minimisation |
| B2 | Decide the fate of `heartbeat_service.py` and `/api/heartbeat/*`: remove, or gate behind an explicit authorized-device allowlist | It opens TCP connections to device IPs, which contradicts the passive-only boundary (claim C15). The UI does not wire it |
| B3 | `generate_unique_id_function` on the FastAPI app and tags on every router | Clean operation ids and grouped docs for the generated client |
| B4 | Export `openapi.json` in CI; document the WebSocket and SSE message schemas in `docs/` | OpenAPI does not cover them |
| B5 | `GET /api/demo/scenarios` (names and descriptions) | The Lab lists scenarios from the backend instead of mirroring them |
| B6 | Make tests use a temporary database, and clear or archive the dev DB's `audit_ledger` (32 chain starts from past test runs make `/api/audit/verify` report tampering at entry 1) | The ledger tab should be able to show a clean chain |
| B7 | A `geo_precision` field (`city` / `region`) on devices | The map legend states the precision instead of assuming it |
| B8 | Serve `paper/data/results.json` at `GET /api/results` (optional) | Lets the live site show current results without a rebuild; the build-time sync remains the default |
| B9 | `LICENSE` file | The README states MIT; the file is missing |

---

## 17. Performance plan

### 17.1 Budgets

| Metric | Target |
|---|---|
| LCP (landing, mid-tier mobile, 4G) | < 2.5 s (headline is the LCP element) |
| CLS | < 0.05 (canvas slots have fixed aspect boxes; fonts via `next/font`) |
| INP | < 200 ms (background shader off the main thread where possible) |
| Initial JS, landing (excluding three and maplibre) | < 180 kB gzip |
| `three` + scene chunk | loaded after hydration via `next/dynamic` (`ssr: false`) |
| `maplibre-gl` + style chunk | loaded only when `/console` or the landing map band is near the viewport |
| Basemap | self-hosted PMTiles, range requests only, cached; size recorded at Phase 1 |
| GPU frame time | < 8 ms high tier, < 16 ms low tier |

### 17.2 Quality tiers (`src/lib/three/quality.ts`)

| Tier | Selected when | DPR cap | Frames | Shader octaves | Extras |
|---|---|---:|---:|---:|---|
| high | fine pointer, >= 8 cores or `deviceMemory >= 8`, viewport >= 1280 | 2.0 | 400 | 4 | MSAA, raycast hover |
| medium | tablet or mid laptop | 1.5 | 160 | 3 | no raycast |
| low | coarse pointer or small viewport | 1.0 | 48 | 2 | background at 24 fps |
| static | reduced motion or WebGL unavailable | n/a | 0 | n/a | one rendered frame or the SVG mark |

**Runtime governor:** if the average frame time exceeds 22 ms over 90 frames, step down one tier (never up within a session). The map has its own governor: above 20,000 points it disables clustering animation.

### 17.3 Loop discipline

At most two canvases animating on a page (background field and hood), plus the map on `/console` (the background field is off there). Pause offscreen (`IntersectionObserver`) and when `document.hidden`. Shared geometries and materials; no per-frame allocation. No `window.addEventListener('scroll')`: scroll work uses Anime.js `onScroll`, `IntersectionObserver` or CSS scroll timelines.

---

## 18. Animation architecture (Anime.js v4)

### 18.1 Library usage

Exports used: `animate`, `createTimeline`, `stagger`, `onScroll`, `createScope`, `spring`, `splitText`, `createDrawable`, `utils`. Names are confirmed against the installed version at scaffold time and wrapped in `src/lib/animations/` so call sites never import Anime.js directly. Three.js targets are plain objects: `camera.position`, `mesh.rotation` and `material.uniforms.uX.value` are animated directly; any adapter lives in `src/lib/animations/three.ts` only.

### 18.2 Utilities (`src/lib/animations/`)

| Function | Notes |
|---|---|
| `animateIn` / `animateOut` | opacity, translateY, optional blur, `ease.out` |
| `revealText` | `splitText`; the original string stays in `aria-label`, split spans are `aria-hidden` |
| `staggerReveal` | lists and result rows |
| `createMagneticInteraction`, `createParallaxInteraction`, `createTiltInteraction` | disabled on coarse pointers and reduced motion |
| `createSectionTimeline` | `onScroll`-driven timeline for one section; plays once or syncs to progress |
| `animateUniform` | Three.js uniform helper |
| `drawPath` | `createDrawable` stroke draw |
| `animateHood` | tweens `uSpread` (WebGL) and the SVG gauge with one signature, used by the hero, the CTA, the explorer and the inspector |

### 18.3 React integration

`useAnime(scopeRef, setup, deps)` wraps `createScope({ root })`; everything created in `setup` reverts on unmount (safe under StrictMode double mounting). `usePrefersReducedMotion()` is one shared `matchMedia` subscription; every utility degrades to instant or opacity-only. Components declare intent (`<RevealText by="word">`, `<ScrollReveal>`, `<HoodGauge animate>`) and never contain raw animation blocks.

### 18.4 Motion components

`RevealText`, `ScrollReveal`, `ParallaxElement`, `MagneticButton`, `TiltCard`, `SpotlightCard`, `AnimatedCounter`, `AnimatedBorder`. Each exposes duration, distance, stagger, `once` and `disabled` with defaults from the tokens. **No custom cursor** (accessibility and performance cost); spotlight and magnetic effects give the same sense of response.

---

## 19. Project structure

```
frontend/
├── package.json
├── next.config.ts              # Turbopack GLSL rules (no webpack config), headers, standalone output switch
├── tsconfig.json               # strict, noUncheckedIndexedAccess
├── postcss.config.mjs
├── components.json             # shadcn/ui
├── openapi.snapshot.json       # committed FastAPI schema
├── .env.example                # NEXT_PUBLIC_COBRA_API_URL, NEXT_PUBLIC_REVEAL_IP, NEXT_PUBLIC_REPO_URL, NEXT_PUBLIC_SITE_URL
├── Dockerfile  .dockerignore
├── scripts/
│   ├── sync-facts.mjs          # paper/data/results.json -> src/lib/content/facts.generated.ts
│   ├── export-golden.py        # Python gate implementation -> tests/fixtures/gate_golden.json
│   └── sync-brand.mjs          # assets/logo/cobra-mark.geometry.json -> src/lib/three/hood-geometry.json
├── public/
│   ├── favicon.svg  og fallback
│   └── tiles/india.pmtiles     # self-hosted basemap (git-ignored, built by scripts/build-basemap.sh)
├── tests/                      # vitest + playwright, fixtures
└── src/
    ├── app/                    # layout, page, research, lab, console, console/devices/[id], verify/[alertId], ethics, not-found, opengraph-image
    ├── components/
    │   ├── ui/  animation/  brand/  three/  map/
    │   ├── sections/           # Hero, TwinCameras, WalkTheGate, GateExplorer, Results, Pipeline, MapBand, Ethics, Process, CtaBand, Footer
    │   ├── console/            # TopBar, AlertStream, Inspector, AnalyticsDrawer, ZoneBrief, CommandPalette, ScenarioMenu
    │   ├── lab/  research/
    ├── hooks/                  # useAnime, usePrefersReducedMotion, usePointer, useInView, useQualityTier, useApiHealth
    ├── lib/
    │   ├── animations/  three/  shaders/  api/  state/  scoring/  map/
    │   ├── content/            # facts.generated.ts, facts.manual.ts, copy.ts
    │   └── constants/          # z.ts, routes.ts
    ├── shaders/                # feed.vert/.frag, ribs.vert/.frag, frames.vert/.frag, glow.frag
    └── styles/                 # tokens.css, globals.css, map-style.ts (Protomaps flavour in palette)
```

`facts.generated.ts` is the only place marketing numbers live.

---

## 20. Accessibility

- Semantic landmarks, one `h1` per page, ordered headings, skip link to `#main` visible on focus.
- Focus ring: 2 px amber outline with a 2 px ink offset on every interactive element, never removed.
- Keyboard: Radix tabs, menus and dialogs; the alert stream with roving focus; map devices reachable through the stream and the palette (the map itself is not the only way to select a device); sliders in the explorer with arrow keys and `aria-valuetext` giving the computed outcome.
- Canvases and the map container are `aria-hidden` or labelled regions with an adjacent visually hidden description; every number drawn in a canvas is also in the DOM.
- Split text keeps the full string in `aria-label`; split spans are hidden from assistive tech.
- Reduced motion: no parallax, tilt, magnetic effects, camera moves or hood animation; frames frozen; reveals become 200 ms opacity fades; counters show final values; shaders render one frame.
- Contrast verified for every token pair in 5.1; `bone-3` is used only at 18 px or larger or for non-essential text. No information by colour alone: tier is shape plus label plus gauge.
- Forms: label above input, helper and error text below, `aria-describedby`, errors announced.

## 21. Responsiveness

| Breakpoint | Landing | Console |
|---|---|---|
| >= 1280 | full layout, high tier | three panes |
| 1024-1279 | full layout, medium tier | three panes, narrower inspector |
| 768-1023 | hero stacks (text above canvas), sticky stage becomes inline per panel | two panes and a segmented control |
| < 768 | single column, low tier, canvas 60vh blocks, nav overlay | tabs: Map / Stream / Detail |

Every multi-column component declares its `< 768px` layout in the same file. Nothing is hidden on mobile; heavy effects are reduced, not removed.

---

## 22. Build order

Each phase ends with its acceptance check before the next begins.

| # | Phase | Done when |
|---|---|---|
| 1 | Scaffold, contracts, basemap | `frontend/` runs with `npm install && npm run dev`; `gen:api` produces types from the live backend; `sync-facts` and `sync-brand` run; the India PMTiles file is built and its size recorded; strict TS passes |
| 2 | Design system | tokens, fonts, grain, z-scale, primitives, `HoodGauge`, `TierTag`, `SourceNote`; contrast table re-verified |
| 3 | Responsive structure | every section and console pane laid out at four breakpoints, no content, no motion |
| 4 | Core UI and live data | all copy from facts; the console renders the real devices, alerts, inspector, analytics and ledger; offline states work; masking enforced |
| 5 | Scoring port and Lab | `gate.ts` passes the golden test; gate explorer, simulators and scenario replay work against the backend |
| 6 | Anime.js system | utilities, motion components, hero timeline, section reveals, reduced-motion paths |
| 7 | Three.js scene | `Stage`, `HoodRibs`, `EyeLens`, `FrameParticles`, hero and Walk the gate |
| 8 | Shader effects | feed field with documented uniforms, feed panes, glow; hood animation shared with the SVG gauge |
| 9 | Interactions and map polish | magnetic, tilt, spotlight, parallax, command palette with NL query, zone brief, View Transition, CTA hood; **WebGPU spike and deck.gl decision gates** |
| 10 | Performance | tiers, governor, lazy loading, offscreen pausing, OffscreenCanvas worker, disposal assertions, bundle analysis |
| 11 | Accessibility and QA | section 23 passes; Lighthouse and axe runs recorded |
| 12 | Phase 2 features | `/verify`, deck.gl arcs and H3 density |

---

## 23. Final QA checklist

**Truth**
- [ ] Every number on `/` and `/research` is imported from `facts.generated.ts` and matches `paper/results.md`.
- [ ] Every accuracy figure carries the `Synthetic corpus, n = 120` chip and the limits block is on the page.
- [ ] No live view shows data when the backend is offline.
- [ ] Demo traffic is labelled everywhere it appears and excluded from fleet statistics unless stated.
- [ ] Map copy says "Estimated position"; scores show their basis.
- [ ] No full IP address is reachable in the DOM with default settings.

**Visual (taste pre-flight)**
- [ ] One accent (amber), one radius system, one theme, sentence case; none of the 1.3 banned items appear.
- [ ] Zero em-dashes or en-dash separators in visible UI copy.
- [ ] Hero: headline <= 2 lines, subtext <= 20 words, CTAs visible without scrolling at 1366 x 768, top padding <= `pt-24`.
- [ ] <= 3 eyebrows on the landing page; no section numbering; no scroll cue; no version strings.
- [ ] No two sections share a layout family.
- [ ] One CTA label per intent ("Open console").
- [ ] The logo, favicon and OG image all use the section 5.1 colours.

**Motion**
- [ ] Every animation has a written purpose in this file.
- [ ] Hero entrance is one timeline; no orphan animations.
- [ ] All animations revert on unmount (StrictMode double-mount shows no duplicates).
- [ ] Reduced-motion mode verified on every page.

**WebGL and map**
- [ ] No WebGL errors or warnings; context loss recovers or falls back to the SVG mark.
- [ ] `renderer.info.memory` returns to baseline after mount and unmount.
- [ ] Loops pause offscreen and in hidden tabs; the governor steps down on a throttled CPU.
- [ ] A pan or zoom makes zero requests to a third-party host.

**Contracts**
- [ ] `openapi.snapshot.json` matches the running backend; the golden gate fixture matches the TypeScript port.
- [ ] WebSocket, SSE and GeoJSON flattening tests pass against recorded fixtures.

**Platform**
- [ ] No hydration warnings; no layout shift from the canvas or fonts.
- [ ] Lighthouse (mobile): Performance >= 85, Accessibility >= 95, Best Practices >= 95.
- [ ] axe: zero serious or critical issues.
- [ ] Keyboard-only walkthrough of every page.
- [ ] `npm run build` passes with no type or lint errors; no unused dependencies.

---

## 24. Commands

```bash
# backend
pip install -r backend/requirements.txt
python backend/main.py                      # API, WebSocket and docs on :8000

# frontend
cd frontend
cp .env.example .env.local                  # NEXT_PUBLIC_COBRA_API_URL=http://localhost:8000
npm install
npm run gen:api                             # types from the running backend's /openapi.json
npm run sync                                # facts from paper/data/results.json, hood geometry from assets/logo
npm run dev                                 # http://localhost:3000
npm run build && npm run start              # production
npm run lint && npm run test                # eslint, vitest (facts, parity, contracts)
npm run e2e                                 # playwright, axe

# brand and basemap
python assets/logo/build_logo.py            # regenerate logo assets and hood geometry
bash scripts/build-basemap.sh               # pmtiles extract for the India bounding box
```

---

## 25. Open decisions for the owner

1. **Palette:** approve sodium amber on green-black ink as the identity (the logo already uses it). The alternatives considered and rejected are in 1.3.
2. **Hero line:** confirm "A secure camera can still lie." Fallbacks: "Trust the feed, not just the firmware." and "Clean on paper, fake on screen."
3. **IP masking:** confirm that public views mask to the /24 by default and that the backend does the same (B1).
4. **Heartbeat:** decide B2 (remove or allowlist). Until then the UI does not expose it.
5. **Basemap hosting:** decide where the PMTiles file lives (repo-adjacent static host, object storage, or a local build only) after its size is measured in Phase 1.
6. **Scope of v1:** confirm that deck.gl, `/verify`, WebGPU and React Compiler are Phase 2 or spikes, and that v1 is MapLibre native layers plus the landing, console, lab, research and ethics pages.
7. **Credits and licence:** confirm the footer credit line and the names to show, add the missing `LICENSE` file (B9), and set `NEXT_PUBLIC_REPO_URL`.
8. **Restore or restart:** the previous Next.js integration is not on disk. This spec assumes a clean rebuild with the new design; its API-client lessons are folded into section 15.
