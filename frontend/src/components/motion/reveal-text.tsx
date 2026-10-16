"use client";
import * as React from "react";
import { animate, dur, easings, splitText, stagger, staggerTokens } from "@/lib/animations";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";

/**
 * Word-by-word reveal (blur 8px and y 24px to sharp, 45 ms stagger). The original string stays in
 * aria-label; split spans are aria-hidden (spec 18.2). The text is in the server HTML, so it is
 * readable without JavaScript and under reduced motion.
 */
export function RevealText({
  text,
  as: Tag = "span",
  className,
  delay = 0,
  trigger = "mount",
}: {
  text: string;
  as?: "h1" | "h2" | "h3" | "p" | "span";
  className?: string;
  delay?: number;
  /** "mount" starts immediately; "view" waits until the element enters the viewport. */
  trigger?: "mount" | "view";
}) {
  const ref = React.useRef<HTMLElement | null>(null);
  const reduced = usePrefersReducedMotion();

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (reduced) {
      el.classList.remove("pending-reveal");
      return;
    }
    const split = splitText(el, { words: true });
    const words = split.words as HTMLElement[];
    words.forEach((w) => {
      w.style.opacity = "0";
      w.style.display = "inline-block";
    });
    el.classList.remove("pending-reveal");
    let run = () => {
      animate(words, {
        opacity: [0, 1],
        translateY: [24, 0],
        filter: ["blur(8px)", "blur(0px)"],
        duration: dur.base + 200,
        delay: stagger(staggerTokens.textWord, { start: delay }),
        ease: easings.out,
      });
    };
    let io: IntersectionObserver | null = null;
    if (trigger === "view") {
      const go = run;
      run = () => undefined;
      io = new IntersectionObserver((entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          go();
          io?.disconnect();
        }
      }, { threshold: 0.4 });
      io.observe(el);
    }
    run();
    return () => {
      io?.disconnect();
      split.revert();
    };
  }, [reduced, delay, trigger, text]);

  return (
    <Tag ref={ref as never} className={`pending-reveal ${className ?? ""}`} aria-label={text}>
      {text}
    </Tag>
  );
}
