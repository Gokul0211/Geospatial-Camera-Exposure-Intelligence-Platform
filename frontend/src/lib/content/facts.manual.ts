import type { Fact } from "./facts.generated";

/**
 * Hand-written constants (spec 3.4). Every entry MUST carry a `source`; a test fails otherwise.
 * Anything measured lives in facts.generated.ts, never here.
 */
export const manualFacts = {
  "method.tiers": {
    value: { highMin: 80, mediumMin: 50 },
    source: "backend/routes/config_router.py",
    section: "spec 3.1",
  },
  "method.gate": {
    value: { thetaLow: 0.5, thetaHigh: 0.85, floorMultiplier: 0.3, hardCap: 30 },
    source: "backend/services/signal_integrity_service.py (THETA_LOW, THETA_HIGH), backend/routes/config_router.py",
    section: "spec 3.1",
  },
  "method.tier1": {
    value: {
      driftThreshold: 0.15,
      weights: { firmware: 0.25, server: 0.2, ports: 0.2, resolution: 0.2, product: 0.1, codec: 0.05 },
    },
    source: "backend/services/signal_integrity_service.py (DEFAULT_DRIFT_WEIGHTS)",
    section: "spec 3.1",
  },
  "method.tier2": {
    value: { weights: { freeze: 1.0, quality: 0.6, spec: 0.5 }, freezeFrames: 25, hammingMax: 1, ewmaAlpha: 0.05 },
    source: "paper/results.md section 5; CLAUDE.md (weights since 2026-10-09)",
    section: "spec 3.1",
  },
  "res.t2.tcve": {
    value: 100,
    source: "paper/results.md section 5 (end-to-end table uses T_cve = 100, banner drift = 0)",
    section: "results.md section 5",
  },
  "eval.tests": {
    value: { passed: 434, date: "2026-10-16" },
    source: "pytest backend/tests video_pipeline/tests eval/test_eval_harness.py, run 2026-10-16 on a copy of the dev DB (paper/LOG.md)",
    section: "spec 3.2",
  },
} as const satisfies Record<string, Fact<unknown>>;

export type ManualFactKey = keyof typeof manualFacts;
