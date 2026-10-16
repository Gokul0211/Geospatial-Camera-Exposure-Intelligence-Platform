"use client";
import * as React from "react";
import Link from "next/link";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { MagneticButton } from "@/components/motion/magnetic-button";
import { CONSOLE_CTA, ROUTES } from "@/lib/constants/routes";
import { ScrollReveal } from "@/components/motion/scroll-reveal";

/** Closing band: the hood rests nearly closed and opens when the button is hovered or focused. */
export function CtaBand() {
  const [open, setOpen] = React.useState(false);
  return (
    <section aria-labelledby="cta-title" className="relative z-content py-24 md:py-40">
      <div className="mx-auto grid max-w-[1360px] items-center gap-10 px-5 md:grid-cols-2 md:px-8">
        <ScrollReveal className="flex flex-col items-start gap-8">
          <h2 id="cta-title" className="t-h2 max-w-[16ch]">See the gate on live data.</h2>
          <div onPointerEnter={() => setOpen(true)} onPointerLeave={() => setOpen(false)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>
            <MagneticButton asChild size="lg"><Link href={ROUTES.console}>{CONSOLE_CTA}</Link></MagneticButton>
          </div>
        </ScrollReveal>
        <div className="flex justify-center md:justify-end" aria-hidden="true">
          <HoodGauge gate={open ? 1 : 0.34} score={open ? 100 : 40} size={360} animate className="h-auto w-[min(80%,360px)]" />
        </div>
      </div>
    </section>
  );
}
