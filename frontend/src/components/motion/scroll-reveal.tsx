"use client";
import * as React from "react";
import { animateIn } from "@/lib/animations";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { cn } from "@/lib/utils";

/**
 * Fades its children in once when they enter the viewport. Content is visible in the server HTML;
 * the pending state is applied after mount and only to elements still below the fold, so nothing
 * flashes and a no-JS reader sees everything.
 */
export function ScrollReveal({
  children,
  className,
  y = 20,
  delay = 0,
  stagger = 0,
  selector,
  disabled = false,
}: {
  children: React.ReactNode;
  className?: string;
  y?: number;
  delay?: number;
  stagger?: number;
  /** Animate matching descendants one after another instead of the wrapper. */
  selector?: string;
  disabled?: boolean;
}) {
  const ref = React.useRef<HTMLDivElement | null>(null);
  const reduced = usePrefersReducedMotion();

  React.useEffect(() => {
    const el = ref.current;
    if (!el || disabled) return;
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight * 0.92 && rect.bottom > 0) return; // already visible: leave it
    const targets: Element[] = selector ? Array.from(el.querySelectorAll(selector)) : [el];
    targets.forEach((t) => ((t as HTMLElement).style.opacity = "0"));
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          animateIn(targets, { y, delay, stagger, reduced });
          io.disconnect();
        }
      },
      { rootMargin: "0px 0px -10% 0px" },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      targets.forEach((t) => ((t as HTMLElement).style.opacity = ""));
    };
  }, [reduced, y, delay, stagger, selector, disabled]);

  return (
    <div ref={ref} className={cn(className)}>
      {children}
    </div>
  );
}
