/**
 * Direct port of backend/services/signal_integrity_service.py and the fusion step of
 * trust_score_service.compute_ig_dctf_trust_score (spec 14.4). Parity is asserted against
 * tests/fixtures/gate_golden.json, which scripts/export-golden.py generates from the Python code.
 */

export const DEFAULT_THETA_HIGH = 0.85;
export const DEFAULT_THETA_LOW = 0.5;
export const FLOOR_MULTIPLIER = 0.3;
export const HARD_CAP = 30;
export const TIER2_WEIGHTS = [1.0, 0.6, 0.5] as const;

export const DRIFT_WEIGHTS = {
  resolution: 0.2,
  firmware_version: 0.25,
  http_server: 0.2,
  open_ports: 0.2,
  product_string: 0.1,
  codec: 0.05,
} as const;

export type GateStatus = "nominal" | "tapered" | "hard_gated";

/**
 * Python's round(): correctly rounded from the exact binary value, ties to even. toFixed rounds from
 * the exact value too, so only exact binary ties (x * 10^digits is exactly k + 0.5) need the even rule.
 */
export function pyRound(x: number, digits = 0): number {
  if (!Number.isFinite(x)) return x;
  // toFixed expands the exact binary value, so "5 then only zeros" is an exact tie.
  const expanded = Math.abs(x).toFixed(Math.min(100, digits + 40));
  const dot = expanded.indexOf(".");
  const tail = expanded.slice(dot + 1 + digits);
  if (/^50*$/.test(tail)) {
    const m = 10 ** digits;
    const f = Math.floor(Math.abs(x) * m);
    const even = (f % 2 === 0 ? f : f + 1) / m;
    return x < 0 ? -even : even;
  }
  return digits === 0 ? Math.round(x) : Number(x.toFixed(digits));
}

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

export interface Liveness {
  liveness: number;
}

/** compute_visual_liveness */
export function computeVisualLiveness(
  freeze: boolean,
  qualityDrift: number,
  specMismatch: boolean,
  weights: readonly [number, number, number] = TIER2_WEIGHTS,
): number {
  const [w1, w2, w3] = weights;
  const f = (freeze ? 1 : 0) * w1;
  const q = clamp01(qualityDrift) * w2;
  const s = (specMismatch ? 1 : 0) * w3;
  const penalty = Math.max(f, q, s);
  return pyRound(Math.max(0, Math.min(1, 1 - penalty)), 4);
}

/** compute_composite_signal_integrity; `liveness` null means Tier 2 is unavailable. */
export function computeSignalIntegrity(drift: number, liveness: number | null): number {
  const tier1 = Math.max(0, Math.min(1, 1 - drift));
  const composite = liveness !== null ? tier1 * Math.max(0, Math.min(1, liveness)) : tier1;
  return pyRound(composite, 4);
}

export interface GateResult {
  multiplier: number;
  hardCap: number | null;
  tripped: boolean;
  status: GateStatus;
}

/** evaluate_integrity_gate */
export function evaluateGate(
  signalIntegrity: number,
  thetaHigh: number = DEFAULT_THETA_HIGH,
  thetaLow: number = DEFAULT_THETA_LOW,
): GateResult {
  const s = Math.max(0, Math.min(1, signalIntegrity));
  if (s >= thetaHigh) return { multiplier: 1, hardCap: null, tripped: false, status: "nominal" };
  if (s >= thetaLow) {
    const slope = (1 - FLOOR_MULTIPLIER) / (thetaHigh - thetaLow);
    return { multiplier: pyRound(FLOOR_MULTIPLIER + slope * (s - thetaLow), 4), hardCap: null, tripped: false, status: "tapered" };
  }
  return { multiplier: FLOOR_MULTIPLIER, hardCap: HARD_CAP, tripped: true, status: "hard_gated" };
}

/** The continuous G(s) for drawing the curve (no rounding). */
export function gateCurve(s: number, thetaHigh = DEFAULT_THETA_HIGH, thetaLow = DEFAULT_THETA_LOW): number {
  if (s >= thetaHigh) return 1;
  if (s >= thetaLow) return FLOOR_MULTIPLIER + ((1 - FLOOR_MULTIPLIER) / (thetaHigh - thetaLow)) * (s - thetaLow);
  return FLOOR_MULTIPLIER;
}

export type Tier = "high_trust" | "medium_trust" | "low_trust";
export function tierFor(score: number): Tier {
  if (score >= 80) return "high_trust";
  if (score >= 50) return "medium_trust";
  return "low_trust";
}

export interface FusionInput {
  tCve: number;
  drift: number;
  /** null = Tier 2 unavailable */
  freeze: boolean | null;
  qualityDrift: number;
  specMismatch: boolean;
  thetaHigh?: number;
  thetaLow?: number;
  weights?: readonly [number, number, number];
}

export interface FusionResult {
  liveness: number | null;
  signalIntegrity: number;
  gate: GateResult;
  tFinal: number;
  tier: Tier;
}

/** compute_ig_dctf_trust_score, fusion part: T_final = T_cve * G(s), capped at 30 when tripped. */
export function fuse(input: FusionInput): FusionResult {
  const tier2 = input.freeze !== null;
  const liveness = tier2 ? computeVisualLiveness(input.freeze === true, input.qualityDrift, input.specMismatch, input.weights) : null;
  const s = computeSignalIntegrity(input.drift, liveness);
  const gate = evaluateGate(s, input.thetaHigh, input.thetaLow);
  let tFinal = Math.trunc(pyRound(input.tCve * gate.multiplier));
  if (gate.hardCap !== null) tFinal = Math.min(gate.hardCap, tFinal);
  tFinal = Math.max(0, Math.min(100, tFinal));
  return { liveness, signalIntegrity: s, gate, tFinal, tier: tierFor(tFinal) };
}

export interface Fingerprint {
  resolution?: string;
  codec?: string;
  firmware_version?: string;
  http_server?: string;
  product_string?: string;
  open_ports?: number[];
}

/** compute_banner_drift (Tier 1). Returns the weighted, normalised drift and per-field distances. */
export function computeBannerDrift(baseline: Fingerprint, current: Fingerprint, weights: Record<string, number> = DRIFT_WEIGHTS) {
  const dist: Record<string, number> = {};
  let acc = 0;
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  for (const field of ["product_string", "http_server", "firmware_version", "codec"] as const) {
    const b = String(baseline[field] ?? "unknown").toLowerCase();
    const c = String(current[field] ?? "unknown").toLowerCase();
    let d = 0;
    if (b === "unknown" && c === "unknown") d = 0;
    else if (b !== "unknown" && c !== "unknown" && b !== c) d = 1;
    else if ((b === "unknown") !== (c === "unknown")) d = 0.5;
    dist[field] = d;
    acc += (weights[field] ?? 0) * d;
  }
  const bRes = String(baseline.resolution ?? "unknown").toLowerCase();
  const cRes = String(current.resolution ?? "unknown").toLowerCase();
  let resDist = 0;
  if (bRes !== "unknown" && cRes !== "unknown" && bRes !== cRes) {
    const rank: Record<string, number> = { "480p": 1, "720p": 2, "1080p": 3, "1440p": 4, "4k": 5 };
    resDist = (rank[cRes] ?? 3) < (rank[bRes] ?? 3) ? 1 : 0.6;
  }
  dist.resolution = resDist;
  acc += (weights.resolution ?? 0) * resDist;
  const bp = new Set(baseline.open_ports ?? []);
  const cp = new Set(current.open_ports ?? []);
  let jac = 0;
  if (bp.size || cp.size) {
    const inter = [...bp].filter((p) => cp.has(p)).length;
    const union = new Set([...bp, ...cp]).size;
    jac = 1 - (union > 0 ? inter / union : 1);
  }
  dist.open_ports = jac;
  acc += (weights.open_ports ?? 0) * jac;
  const drift = Math.min(1, Math.max(0, total > 0 ? acc / total : 0));
  return { drift: pyRound(drift, 4), distances: dist };
}
