import geometry from "@/lib/three/hood-geometry.json";

/**
 * Hood geometry, shared by the SVG gauge and (Phase 7) the WebGL hood so the two cannot disagree.
 * Source of truth: assets/logo/cobra-mark.geometry.json, copied by `npm run sync`.
 * Angles in degrees, 0 = up, clockwise. Units are the 200x200 mark viewBox.
 */
export const HOOD = {
  cx: geometry.center[0] as number,
  cy: geometry.center[1] as number,
  rIn: geometry.rIn,
  rOut: geometry.rOut,
  eye: geometry.eye,
  ribCount: geometry.ribs.length,
  fullSpreadDeg: 236,
  gapDeg: 4.5,
  colors: geometry.colors,
  ribs: geometry.ribs as readonly { a0: number; a1: number }[],
} as const;

/** Gate floor: `G` never goes below this, so a tripped hood is nearly closed but never invisible. */
export const GATE_FLOOR = 0.3;

export interface Rib {
  a0: number;
  a1: number;
}

/** Opening angle of the hood for gate multiplier G (spec 6.3): 236 degrees * G. */
export function spreadForGate(g: number): number {
  return HOOD.fullSpreadDeg * clamp(g, GATE_FLOOR, 1);
}

/**
 * Nine ribs centred on 0 degrees for a given spread. The gap stays 4.5 degrees and the rib width is
 * (spread - 4.5 * 8) / 9, so G = 1 reproduces the mark exactly and G = 0.3 gives 70.8 / 3.9 degrees.
 */
export function ribsForSpread(spreadDeg: number): Rib[] {
  const n = HOOD.ribCount;
  const width = (spreadDeg - HOOD.gapDeg * (n - 1)) / n;
  const start = -spreadDeg / 2;
  return Array.from({ length: n }, (_, i) => {
    const a0 = start + i * (width + HOOD.gapDeg);
    return { a0, a1: a0 + width };
  });
}

function point(r: number, angleDeg: number): [number, number] {
  const a = (angleDeg * Math.PI) / 180;
  return [HOOD.cx + r * Math.sin(a), HOOD.cy - r * Math.cos(a)];
}
const f = (n: number) => n.toFixed(3);

/** SVG path of one annular sector. */
export function ribPath(rib: Rib): string {
  const [x0, y0] = point(HOOD.rOut, rib.a0);
  const [x1, y1] = point(HOOD.rOut, rib.a1);
  const [x2, y2] = point(HOOD.rIn, rib.a1);
  const [x3, y3] = point(HOOD.rIn, rib.a0);
  return `M${f(x0)} ${f(y0)}A${HOOD.rOut} ${HOOD.rOut} 0 0 1 ${f(x1)} ${f(y1)}L${f(x2)} ${f(y2)}A${HOOD.rIn} ${HOOD.rIn} 0 0 0 ${f(x3)} ${f(y3)}Z`;
}

/** SVG path of the lens-shaped eye: the overlap of two circles of radius eye.r, d apart from the centre. */
export function eyePath(): string {
  const { r, half_height: h } = HOOD.eye;
  const top = `${f(HOOD.cx)} ${f(HOOD.cy - h)}`;
  const bottom = `${f(HOOD.cx)} ${f(HOOD.cy + h)}`;
  return `M${top}A${r} ${r} 0 0 1 ${bottom}A${r} ${r} 0 0 1 ${top}Z`;
}

/** Eye opacity: T_final / 100 with a visible floor so a capped device still shows a dim eye. */
export function eyeOpacity(tFinal: number): number {
  return clamp(tFinal / 100, 0.12, 1);
}

/** Tight viewBox around the fully open hood (the 200x200 mark has padding). */
export const HOOD_VIEWBOX = "16 28 168 144";
export const HOOD_ASPECT = 168 / 144;

export function clamp(x: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, x));
}
