/** Severity encoding for map markers (spec 5.1): shape + one-hue ramp, never traffic-light colours. */
const BONE_2 = "#a4aaa1";
const SIGNAL = "#f3a33a";

export type MarkerKind = "high" | "medium" | "low" | "gate" | "unscored";

export function drawMarker(kind: MarkerKind, px = 32): ImageData {
  const c = document.createElement("canvas");
  c.width = px;
  c.height = px;
  const g = c.getContext("2d")!;
  const m = px / 2;
  const u = px / 16;
  g.clearRect(0, 0, px, px);
  if (kind === "high") {
    g.fillStyle = BONE_2;
    g.globalAlpha = 0.7;
    g.beginPath();
    g.arc(m, m, 2.4 * u, 0, Math.PI * 2);
    g.fill();
  } else if (kind === "medium") {
    g.strokeStyle = SIGNAL;
    g.globalAlpha = 0.6;
    g.lineWidth = 1.5 * u;
    g.beginPath();
    g.arc(m, m, 2.8 * u, 0, Math.PI * 2);
    g.stroke();
  } else if (kind === "low" || kind === "gate") {
    g.fillStyle = SIGNAL;
    g.beginPath();
    g.moveTo(m, m - 4.4 * u);
    g.lineTo(m + 4.4 * u, m);
    g.lineTo(m, m + 4.4 * u);
    g.lineTo(m - 4.4 * u, m);
    g.closePath();
    g.fill();
    if (kind === "gate") {
      g.strokeStyle = SIGNAL;
      g.lineWidth = 1 * u;
      g.beginPath();
      g.arc(m, m, 6.6 * u, 0, Math.PI * 2);
      g.stroke();
    }
  } else {
    g.strokeStyle = "#6e746c";
    g.lineWidth = 1.5 * u;
    g.beginPath();
    g.moveTo(m - 2.5 * u, m);
    g.lineTo(m + 2.5 * u, m);
    g.stroke();
  }
  return g.getImageData(0, 0, px, px);
}

export const MARKER_KINDS: MarkerKind[] = ["high", "medium", "low", "gate", "unscored"];

export function markerKind(d: { action_tier?: string; integrity_gate_tripped?: boolean }): MarkerKind {
  if (d.integrity_gate_tripped) return "gate";
  switch (d.action_tier) {
    case "high_trust": return "high";
    case "medium_trust": return "medium";
    case "low_trust": return "low";
    default: return "unscored";
  }
}

/** Great-circle distance in metres. */
export function haversine(a: [number, number], b: [number, number]): number {
  const R = 6371008.8;
  const toRad = (x: number) => (x * Math.PI) / 180;
  const dLat = toRad(b[1] - a[1]);
  const dLon = toRad(b[0] - a[0]);
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a[1])) * Math.cos(toRad(b[1])) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

/** A circle polygon (GeoJSON ring) of `radiusM` around `center`. */
export function circlePolygon(center: [number, number], radiusM: number, steps = 64): [number, number][] {
  const R = 6371008.8;
  const lat = (center[1] * Math.PI) / 180;
  const ring: [number, number][] = [];
  for (let i = 0; i <= steps; i++) {
    const a = (i / steps) * Math.PI * 2;
    const dLat = (radiusM / R) * Math.cos(a);
    const dLon = ((radiusM / R) * Math.sin(a)) / Math.cos(lat);
    ring.push([center[0] + (dLon * 180) / Math.PI, center[1] + (dLat * 180) / Math.PI]);
  }
  return ring;
}
