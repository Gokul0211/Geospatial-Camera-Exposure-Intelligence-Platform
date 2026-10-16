"use client";
import * as React from "react";
import { animate, easings } from "@/lib/animations";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { Button, type ButtonProps } from "@/components/ui/button";

/** Pulls toward the pointer by up to 6px. Disabled on coarse pointers and under reduced motion. */
export function MagneticButton({ strength = 6, ...props }: ButtonProps & { strength?: number }) {
  const ref = React.useRef<HTMLButtonElement | null>(null);
  const reduced = usePrefersReducedMotion();

  React.useEffect(() => {
    const el = ref.current;
    if (!el || reduced || !window.matchMedia("(pointer: fine)").matches) return;
    const move = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      const dx = ((e.clientX - (r.left + r.width / 2)) / r.width) * strength * 2;
      const dy = ((e.clientY - (r.top + r.height / 2)) / r.height) * strength * 2;
      animate(el, { translateX: dx, translateY: dy, duration: 220, ease: easings.out });
    };
    const leave = () => animate(el, { translateX: 0, translateY: 0, duration: 380, ease: easings.spring });
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", leave);
    return () => {
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerleave", leave);
    };
  }, [reduced, strength]);

  return <Button ref={ref as never} {...props} />;
}
