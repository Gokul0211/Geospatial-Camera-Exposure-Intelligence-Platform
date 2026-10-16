import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { computeBannerDrift, fuse, gateCurve, evaluateGate, pyRound } from "@/lib/scoring/gate";

interface Case { t_cve: number; drift: number; freeze: boolean | null; quality: number; spec: boolean; liveness: number | null; s: number; multiplier: number; status: string; tripped: boolean; hard_cap: number | null; t_final: number }
interface Banner { baseline: Record<string, unknown>; current: Record<string, unknown>; drift: number; distances: Record<string, number> }
const golden = JSON.parse(readFileSync(new URL("./fixtures/gate_golden.json", import.meta.url), "utf8")) as { cases: Case[]; banner: Banner[] };

describe("scoring parity with the Python implementation (spec 14.4)", () => {
  it("has the golden vectors", () => expect(golden.cases.length).toBeGreaterThanOrEqual(200));

  it("matches liveness, signal integrity, multiplier, status and T_final on every vector", () => {
    for (const c of golden.cases) {
      const r = fuse({ tCve: c.t_cve, drift: c.drift, freeze: c.freeze, qualityDrift: c.quality, specMismatch: c.spec });
      const label = JSON.stringify(c);
      expect(r.liveness, label).toBe(c.liveness);
      expect(r.signalIntegrity, label).toBeCloseTo(c.s, 4);
      expect(r.gate.multiplier, label).toBeCloseTo(c.multiplier, 4);
      expect(r.gate.status, label).toBe(c.status);
      expect(r.gate.tripped, label).toBe(c.tripped);
      expect(r.gate.hardCap, label).toBe(c.hard_cap);
      expect(r.tFinal, label).toBe(c.t_final);
    }
  });

  it("matches Tier 1 banner drift on the recorded fingerprints", () => {
    for (const b of golden.banner) {
      const r = computeBannerDrift(b.baseline as never, b.current as never);
      expect(r.drift).toBeCloseTo(b.drift, 4);
      for (const [k, v] of Object.entries(b.distances)) expect(r.distances[k] ?? 0, k).toBeCloseTo(v, 6);
    }
  });

  it("rounds half to even like Python", () => {
    expect([0.5, 1.5, 2.5, 3.5].map((x) => pyRound(x))).toEqual([0, 2, 2, 4]);
  });

  it("gate edges: 0.85 passes, 0.5 tapers to 0.3 floor, below 0.5 trips", () => {
    expect(evaluateGate(0.85).status).toBe("nominal");
    expect(evaluateGate(0.5).multiplier).toBeCloseTo(0.3, 6);
    expect(evaluateGate(0.5).status).toBe("tapered");
    expect(evaluateGate(0.4999).status).toBe("hard_gated");
    expect(gateCurve(0.675)).toBeCloseTo(0.65, 6);
  });
});
