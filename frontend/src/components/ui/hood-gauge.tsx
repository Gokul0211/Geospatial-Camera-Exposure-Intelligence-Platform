"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { dur } from "@/lib/animations/tokens";
import { animateNumbers, type TweenHandle } from "@/lib/animations";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { HOOD, HOOD_ASPECT, HOOD_VIEWBOX, eyeOpacity, eyePath, ribPath, ribsForSpread, spreadForGate } from "@/lib/brand/hood";

export interface HoodGaugeProps {
  /** Gate multiplier G(s) in [0.3, 1]. 1 = the full mark. */
  gate?: number;
  /** T_final in [0, 100]. Drives eye intensity. */
  score?: number;
  /** Rendered width in px (16 to 160 in tables, popups and the inspector). */
  size?: number;
  /** Tween on change (ease.spring over dur.short). Snaps under reduced motion. */
  animate?: boolean;
  /** Visible to assistive tech. Defaults to a computed description. */
  label?: string;
  className?: string;
}

/**
 * The hood is a gauge (spec 6.3): spread = 236 degrees * G(s), eye intensity = T_final / 100.
 * Uses the same geometry module as the WebGL hood, so the two cannot disagree. React renders the
 * first state; later changes are applied imperatively so a tween never fights a re-render.
 */
export function HoodGauge({ gate = 1, score = 100, size = 64, animate = false, label, className }: HoodGaugeProps) {
  const reduced = usePrefersReducedMotion();
  const spread = spreadForGate(gate);
  const eye = eyeOpacity(score);

  const [initial] = React.useState(() => ({ ribs: ribsForSpread(spread).map(ribPath), eye }));
  const ribRefs = React.useRef<(SVGPathElement | null)[]>([]);
  const eyeRef = React.useRef<SVGPathElement | null>(null);
  const current = React.useRef({ spread, eye });
  const tween = React.useRef<TweenHandle | null>(null);

  React.useEffect(() => {
    const paint = (s: { spread: number; eye: number }) => {
      const ribs = ribsForSpread(s.spread);
      ribs.forEach((r, i) => ribRefs.current[i]?.setAttribute("d", ribPath(r)));
      eyeRef.current?.setAttribute("fill-opacity", s.eye.toFixed(3));
    };
    tween.current?.cancel();
    if (!animate || reduced) {
      current.current = { spread, eye };
      paint(current.current);
      return;
    }
    tween.current = animateNumbers(current.current, { spread, eye }, { duration: dur.short, ease: "spring", onFrame: paint });
    return () => tween.current?.cancel();
  }, [spread, eye, animate, reduced]);

  const description =
    label ?? `Gate multiplier ${gate.toFixed(2)}, hood open ${spread.toFixed(0)} degrees, score ${Math.round(score)}`;

  return (
    <svg
      role="img"
      aria-label={description}
      width={size}
      height={size / HOOD_ASPECT}
      viewBox={HOOD_VIEWBOX}
      className={cn("shrink-0", className)}
    >
      <title>{description}</title>
      {initial.ribs.map((d, i) => (
        <path key={i} ref={(el) => void (ribRefs.current[i] = el)} d={d} fill={HOOD.colors.bone} />
      ))}
      <path ref={eyeRef} d={eyePath()} fill={HOOD.colors.signal} fillOpacity={initial.eye} />
    </svg>
  );
}
