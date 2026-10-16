"use client";
import * as React from "react";
import { FeedEngine, type FeedState } from "@/lib/three/feed-engine";
import { pickTier, webglAvailable } from "@/lib/three/quality";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { cn } from "@/lib/utils";

/** Fixed page background: the feed field (spec 9.1). Mounted after idle so it never competes with LCP. */
export function FeedBackground({ onReady }: { onReady?: (engine: FeedEngine) => void }) {
  const ref = React.useRef<HTMLCanvasElement | null>(null);
  const reduced = usePrefersReducedMotion();
  const readyRef = React.useRef(onReady);
  React.useEffect(() => {
    readyRef.current = onReady;
  });
  const [shown, setShown] = React.useState(false);

  React.useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !webglAvailable()) return;
    let engine: FeedEngine | null = null;
    let cancelled = false;
    const w = window as unknown as { requestIdleCallback?: (cb: () => void) => number; cancelIdleCallback?: (h: number) => void };
    const idle = w.requestIdleCallback;
    const start = () => {
      if (cancelled) return; // a cleaned-up (StrictMode) pass must not build a second renderer on this canvas
      try {
        engine = new FeedEngine(canvas, { tier: pickTier(), reduced });
      } catch {
        return;
      }
      engine.S.intro = 0;
      readyRef.current?.(engine);
      engine.invalidate();
      setShown(true);
    };
    const handle = idle ? idle(start) : window.setTimeout(start, 200);
    const onMove = (e: PointerEvent) => {
      if (!engine) return;
      engine.S.pointerX = e.clientX / window.innerWidth;
      engine.S.pointerY = 1 - e.clientY / window.innerHeight;
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      cancelled = true;
      if (idle) w.cancelIdleCallback?.(handle);
      else window.clearTimeout(handle);
      engine?.dispose();
      setShown(false);
    };
  }, [reduced]);

  return <canvas ref={ref} aria-hidden="true" className={cn("pointer-events-none fixed inset-0 z-canvas h-full w-full transition-opacity duration-700", shown ? "opacity-100" : "opacity-0")} />;
}

export interface FeedPaneProps {
  freeze?: boolean;
  blur?: number;
  spec?: number;
  drift?: number;
  className?: string;
  label: string;
}

/** A bounded, labelled feed pane (spec 9.4) driven by the twin-camera section or the gate explorer. */
export function FeedPane({ freeze = false, blur = 0, spec = 0, drift = 0, className, label }: FeedPaneProps) {
  const ref = React.useRef<HTMLCanvasElement | null>(null);
  const engineRef = React.useRef<FeedEngine | null>(null);
  const reduced = usePrefersReducedMotion();
  const props = React.useRef({ freeze, blur, spec, drift });

  const apply = React.useCallback((e: FeedEngine) => {
    const p = props.current;
    const S: FeedState = e.S;
    S.freeze = p.freeze ? 1 : 0;
    S.blur = p.blur;
    S.spec = p.spec;
    S.drift = p.drift;
    S.intro = 2.6; // bounded panes are brighter than the page background
    S.accent = 0.08;
    S.accentX = 0.5;
    S.accentY = 0.5;
    e.invalidate();
  }, []);

  React.useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !webglAvailable()) return;
    let engine: FeedEngine | null = null;
    // One tick later, so StrictMode's throwaway first mount never builds a renderer (see hood-canvas.tsx).
    const boot = window.setTimeout(() => {
      try {
        engine = new FeedEngine(canvas, { tier: "low", reduced });
      } catch {
        return;
      }
      engineRef.current = engine;
      apply(engine);
    }, 0);
    return () => {
      window.clearTimeout(boot);
      engine?.dispose();
      engineRef.current = null;
    };
  }, [reduced, apply]);

  React.useEffect(() => {
    props.current = { freeze, blur, spec, drift };
    if (engineRef.current) apply(engineRef.current);
  }, [freeze, blur, spec, drift, apply]);

  return <canvas ref={ref} role="img" aria-label={label} className={cn("block h-full w-full bg-ink-1", className)} />;
}
