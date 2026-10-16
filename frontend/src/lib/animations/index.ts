import {
  animate,
  createDrawable,
  createScope,
  createTimeline,
  cubicBezier,
  onScroll,
  splitText,
  spring,
  stagger,
  utils,
  type AnimationParams,
} from "animejs";
import { dur, ease, springParams, stagger as staggerTokens } from "./tokens";

/**
 * The only module that imports Anime.js (spec 18.1). Components call these wrappers, so a vendor
 * API change touches one file. Everything degrades to instant or opacity-only under reduced motion
 * (callers pass `reduced` from usePrefersReducedMotion).
 */
export { animate, createDrawable, createScope, createTimeline, onScroll, splitText, stagger, utils };
export { dur, ease, springParams } from "./tokens";
export { staggerTokens };

export const easings = {
  out: cubicBezier(...ease.out),
  inOut: cubicBezier(...ease.inOut),
  spring: spring(springParams),
};

export interface TweenHandle {
  cancel: () => void;
}

/** Tween numeric fields of a plain object, calling `onFrame` on every update. Drives gauges and uniforms. */
export function animateNumbers<T extends Record<string, number>>(
  state: T,
  to: Partial<T>,
  opts: { duration?: number; ease?: "out" | "inOut" | "spring"; delay?: number; onFrame: (s: T) => void; onDone?: () => void },
): TweenHandle {
  const params = {
    ...to,
    duration: opts.duration ?? dur.short,
    delay: opts.delay ?? 0,
    ease: easings[opts.ease ?? "spring"],
    onUpdate: () => opts.onFrame(state),
    onComplete: () => opts.onDone?.(),
  } as unknown as AnimationParams;
  const anim = animate(state, params);
  return { cancel: () => void anim.cancel() };
}

/** Same signature for the SVG gauge and the WebGL hood (spec 18.2). */
export function animateHood(
  state: { spread: number; eye: number },
  to: { spread?: number; eye?: number },
  onFrame: (s: { spread: number; eye: number }) => void,
  opts: { reduced?: boolean; duration?: number; delay?: number } = {},
): TweenHandle {
  if (opts.reduced) {
    Object.assign(state, to);
    onFrame(state);
    return { cancel: () => undefined };
  }
  return animateNumbers(state, to, { duration: opts.duration ?? dur.short, delay: opts.delay, ease: "spring", onFrame });
}

export interface InOpts {
  y?: number;
  blur?: number;
  duration?: number;
  delay?: number;
  stagger?: number;
  reduced?: boolean;
}

/** Fade (and optionally rise and unblur) elements in. Reduced motion is a 200 ms opacity fade. */
export function animateIn(targets: Element | Element[] | NodeListOf<Element> | string, o: InOpts = {}): TweenHandle {
  const reduced = o.reduced ?? false;
  const params: Record<string, unknown> = reduced
    ? { opacity: [0, 1], duration: 200, ease: "linear" }
    : {
        opacity: [0, 1],
        translateY: [o.y ?? 16, 0],
        ...(o.blur ? { filter: [`blur(${o.blur}px)`, "blur(0px)"] } : {}),
        duration: o.duration ?? dur.base,
        delay: stagger(o.stagger ?? 0, { start: o.delay ?? 0 }),
        ease: easings.out,
      };
  const anim = animate(targets as never, params as unknown as AnimationParams);
  return { cancel: () => void anim.cancel() };
}

/** Stroke-draw an SVG path or line. */
export function drawPath(target: string | SVGGeometryElement | SVGGeometryElement[], o: { duration?: number; delay?: number } = {}): TweenHandle {
  const anim = animate(createDrawable(target as never), { draw: ["0 0", "0 1"], duration: o.duration ?? dur.long, delay: o.delay ?? 0, ease: easings.inOut });
  return { cancel: () => void anim.cancel() };
}
