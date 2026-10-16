"use client";
import * as React from "react";
import { HoodEngine } from "@/lib/three/hood-engine";
import { pickTier, webglAvailable } from "@/lib/three/quality";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { animateNumbers, type TweenHandle } from "@/lib/animations";
import { cn } from "@/lib/utils";

/**
 * Thin React layer over the vanilla HoodEngine (spec 8.1). The static SVG sits underneath at the
 * same position; the canvas cross-fades over it once the scene has drawn, so nothing shifts.
 */
export function HoodCanvas({
  onReady,
  className,
  parallaxRoot,
}: {
  onReady?: (engine: HoodEngine) => void;
  className?: string;
  /** Element whose pointer movement drives the +/- 3 degree parallax. Defaults to the canvas parent. */
  parallaxRoot?: React.RefObject<HTMLElement | null>;
}) {
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const [live, setLive] = React.useState(false);
  const reduced = usePrefersReducedMotion();
  const readyRef = React.useRef(onReady);
  React.useEffect(() => {
    readyRef.current = onReady;
  });

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !webglAvailable()) return;
    let engine: HoodEngine | null = null;
    let tween: TweenHandle | null = null;
    let root: HTMLElement | null = null;
    let move: ((e: PointerEvent) => void) | null = null;

    // Create the engine one tick later. React StrictMode (dev) mounts, unmounts and remounts an effect
    // on the same canvas; building a renderer for the throwaway first pass leaves the shared GL context
    // in a state the second renderer trips over. The first pass is cleaned up before this timer fires.
    const boot = window.setTimeout(() => {
      try {
        engine = new HoodEngine(canvas, { tier: pickTier(), reduced, onLost: () => setLive(false) });
      } catch {
        return; // WebGL refused: the static SVG underneath stays
      }
      const eng = engine;
      readyRef.current?.(eng);
      eng.invalidate();
      setLive(true);

      root = parallaxRoot?.current ?? canvas.parentElement;
      const coarse = window.matchMedia("(pointer: coarse)").matches;
      move = (e: PointerEvent) => {
        if (!root) return;
        const r = root.getBoundingClientRect();
        const nx = ((e.clientX - r.left) / r.width) * 2 - 1;
        const ny = -(((e.clientY - r.top) / r.height) * 2 - 1);
        tween?.cancel();
        tween = animateNumbers(eng.S, { px: Math.max(-1, Math.min(1, nx)), py: Math.max(-1, Math.min(1, ny)) }, {
          duration: 600, ease: "spring", onFrame: () => eng.invalidate(),
        });
      };
      if (!reduced && !coarse) root?.addEventListener("pointermove", move);
    }, 0);

    return () => {
      window.clearTimeout(boot);
      if (move) root?.removeEventListener("pointermove", move);
      tween?.cancel();
      engine?.dispose();
      setLive(false);
    };
  }, [reduced, parallaxRoot]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={cn("absolute inset-0 h-full w-full transition-opacity duration-500", live ? "opacity-100" : "opacity-0", className)}
    />
  );
}
