"use client";
import * as React from "react";
import Link from "next/link";
import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import { RevealText } from "@/components/motion/reveal-text";
import { MagneticButton } from "@/components/motion/magnetic-button";
import { HoodCanvas } from "@/components/three/hood-canvas";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { HERO } from "@/lib/content/copy";
import { CONSOLE_CTA, ROUTES } from "@/lib/constants/routes";
import { animateIn, animateNumbers } from "@/lib/animations";
import { feedBus } from "@/lib/three/feed-bus";
import type { HoodEngine } from "@/lib/three/hood-engine";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";

/**
 * Hero: asymmetric split. The headline is server-rendered text; the canvas lazy-loads after
 * hydration and cross-fades over the static mark at the same position (spec 7.2).
 */
export function Hero() {
  const reduced = usePrefersReducedMotion();
  const rootRef = React.useRef<HTMLElement | null>(null);
  const subRef = React.useRef<HTMLParagraphElement | null>(null);
  const ctaRef = React.useRef<HTMLDivElement | null>(null);
  const [live, setLive] = React.useState(false);

  React.useEffect(() => {
    if (reduced) {
      subRef.current?.classList.remove("pending-reveal");
      ctaRef.current?.classList.remove("pending-reveal");
      return;
    }
    const a = animateIn(subRef.current as Element, { y: 12, delay: 800, duration: 700 });
    const b = animateIn(ctaRef.current as Element, { y: 0, delay: 1100, duration: 520 });
    subRef.current?.classList.remove("pending-reveal");
    ctaRef.current?.classList.remove("pending-reveal");
    return () => {
      a.cancel();
      b.cancel();
    };
  }, [reduced]);

  const onReady = React.useCallback(
    (engine: HoodEngine) => {
      setLive(true);
      engine.S.dolly = 9.4;
      engine.S.shiftX = 0;
      if (reduced) {
        Object.assign(engine.S, { eye: 1, prog: 1, stagger: 0, frames: 0.5 });
        engine.invalidate();
      } else {
        Object.assign(engine.S, { eye: 0, prog: 0, stagger: 1, frames: 0, dolly: 9.9 });
        const frame = () => engine.invalidate();
        animateNumbers(engine.S, { eye: 1 }, { delay: 200, duration: 520, ease: "out", onFrame: frame });
        animateNumbers(engine.S, { prog: 1 }, { delay: 700, duration: 1500, ease: "spring", onFrame: frame });
        animateNumbers(engine.S, { dolly: 9.4 }, { delay: 700, duration: 1500, ease: "inOut", onFrame: frame });
        animateNumbers(engine.S, { frames: 0.75 }, { delay: 1300, duration: 900, ease: "out", onFrame: frame });
      }
      feedBus.with((feed) => {
        feed.S.accentX = 0.74;
        feed.S.accentY = 0.5;
        feed.S.accent = 0.14;
        if (reduced) feed.S.intro = 1;
        else animateNumbers(feed.S, { intro: 1 }, { duration: 1200, ease: "out", onFrame: () => feed.invalidate() });
        feed.invalidate();
      });
    },
    [reduced],
  );

  return (
    <section ref={rootRef} aria-labelledby="hero-title" className="relative z-content min-h-dvh overflow-x-clip">
      <div className="mx-auto grid min-h-dvh max-w-[1360px] items-center px-5 pb-12 pt-24 md:px-8 lg:grid-cols-12">
        <div className="relative z-overlay flex flex-col gap-7 lg:col-span-5">
          <RevealText as="h1" text={HERO.headline} delay={360} className="t-display" />
          <p ref={subRef} className="pending-reveal t-body text-bone-2">{HERO.sub}</p>
          <div ref={ctaRef} className="pending-reveal flex flex-wrap items-center gap-x-8 gap-y-4">
            <MagneticButton asChild size="lg">
              <Link href={ROUTES.console}>{CONSOLE_CTA}</Link>
            </MagneticButton>
            <Link href={ROUTES.research} className="group inline-flex items-center gap-2 text-bone no-underline">
              <span className="underline decoration-line-strong underline-offset-[6px] group-hover:decoration-signal">Read the research</span>
              <ArrowRight size={18} className="transition-transform duration-[260ms] ease-(--ease-out) group-hover:translate-x-1" aria-hidden="true" />
            </Link>
          </div>
        </div>

        <div className="relative mt-10 h-[48vh] lg:absolute lg:inset-y-0 lg:right-[-5vw] lg:mt-0 lg:h-auto lg:w-[62%]">
          <div className={`absolute inset-0 grid place-items-center transition-opacity duration-500 ${live ? "opacity-0" : "opacity-100"}`} aria-hidden="true">
            <HoodGauge gate={1} score={100} size={520} className="h-auto w-[72%] max-w-[560px]" label="COBRA-WATCH hood" />
          </div>
          <HoodCanvas onReady={onReady} parallaxRoot={rootRef} />
        </div>
      </div>
    </section>
  );
}
