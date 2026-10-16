"use client";
import * as React from "react";
import { animate, dur, easings } from "@/lib/animations";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";

/** Counts once from 0 to `value` when it enters the viewport, in Geist Mono. The final value is in the HTML and aria-label. */
export function AnimatedCounter({
  value,
  decimals = 0,
  format,
  className,
}: {
  value: number;
  decimals?: number;
  format?: (n: number) => string;
  className?: string;
}) {
  const ref = React.useRef<HTMLSpanElement | null>(null);
  const reduced = usePrefersReducedMotion();
  const fmt = React.useCallback((n: number) => (format ? format(n) : n.toFixed(decimals)), [format, decimals]);
  const final = fmt(value);

  React.useEffect(() => {
    const el = ref.current;
    if (!el || reduced) return;
    const io = new IntersectionObserver((entries) => {
      if (!entries.some((e) => e.isIntersecting)) return;
      io.disconnect();
      const state = { v: 0 };
      el.textContent = fmt(0);
      animate(state, {
        v: value,
        duration: dur.long + 300,
        ease: easings.out,
        onUpdate: () => void (el.textContent = fmt(state.v)),
        onComplete: () => void (el.textContent = fmt(value)),
      });
    }, { threshold: 0.6 });
    io.observe(el);
    return () => io.disconnect();
  }, [value, fmt, reduced]);

  return (
    <span ref={ref} className={`num ${className ?? ""}`} aria-label={final}>
      {final}
    </span>
  );
}
