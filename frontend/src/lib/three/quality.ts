/** Quality tiers and the runtime governor (spec 17.2). */
export type Tier = "high" | "medium" | "low";

export interface QualityConfig {
  tier: Tier;
  dprCap: number;
  antialias: boolean;
  octaves: number;
  frames: number;
  feedFps: number;
}

const CONFIG: Record<Tier, QualityConfig> = {
  high: { tier: "high", dprCap: 2, antialias: true, octaves: 4, frames: 240, feedFps: 30 },
  medium: { tier: "medium", dprCap: 1.5, antialias: false, octaves: 3, frames: 120, feedFps: 30 },
  low: { tier: "low", dprCap: 1, antialias: false, octaves: 2, frames: 60, feedFps: 24 },
};

export function pickTier(): Tier {
  if (typeof navigator === "undefined") return "medium";
  const nav = navigator as Navigator & { deviceMemory?: number };
  const cores = nav.hardwareConcurrency ?? 4;
  const memory = nav.deviceMemory ?? 4;
  const coarse = typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;
  if (coarse || cores <= 4 || memory <= 2) return coarse && cores >= 8 ? "medium" : "low";
  if (cores >= 8 && memory >= 8) return "high";
  return "medium";
}

export function configFor(tier: Tier): QualityConfig {
  return CONFIG[tier];
}

export const lowerTier = (t: Tier): Tier => (t === "high" ? "medium" : "low");

/**
 * Measures frame time over a window. If the average stays above the budget it asks for one step
 * down, at most once per window. Never steps back up within a page view.
 */
export class QualityGovernor {
  private samples: number[] = [];
  constructor(private readonly onDegrade: () => void, private readonly budgetMs = 26, private readonly window = 90) {}
  sample(dtMs: number) {
    this.samples.push(dtMs);
    if (this.samples.length < this.window) return;
    const avg = this.samples.reduce((a, b) => a + b, 0) / this.samples.length;
    this.samples = [];
    if (avg > this.budgetMs) this.onDegrade();
  }
}

let webglProbe: boolean | undefined;

/**
 * Whether WebGL can be created. Probed once and the probe context is released at once: browsers cap
 * live contexts (about 16), and every un-released probe would count against the real canvases.
 */
export function webglAvailable(): boolean {
  if (typeof document === "undefined") return false;
  if (webglProbe !== undefined) return webglProbe;
  try {
    const c = document.createElement("canvas");
    const gl = (c.getContext("webgl2") || c.getContext("webgl")) as WebGLRenderingContext | WebGL2RenderingContext | null;
    webglProbe = !!gl;
    gl?.getExtension("WEBGL_lose_context")?.loseContext();
  } catch {
    webglProbe = false;
  }
  return webglProbe;
}
