"use client";
import * as React from "react";
import { ScrollReveal } from "@/components/motion/scroll-reveal";
import { PIPELINE, PIPELINE_FACTS } from "@/lib/content/copy";
import { animate, drawPath, easings } from "@/lib/animations";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { cn } from "@/lib/utils";

/** Six-stage pipeline. The packet travels once, pausing at the gate (spec 7.7). Vertical on narrow screens. */
export function Pipeline() {
  const reduced = usePrefersReducedMotion();
  const ref = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    const root = ref.current;
    if (!root || reduced) return;
    const line = root.querySelector<SVGPathElement>("[data-line]");
    const packet = root.querySelector<SVGCircleElement>("[data-packet]");
    if (!line || !packet) return;
    line.style.opacity = "0";
    packet.style.opacity = "0";
    const io = new IntersectionObserver(([e]) => {
      if (!e?.isIntersecting) return;
      io.disconnect();
      line.style.opacity = "1";
      drawPath(line, { duration: 1100 });
      const stops = [0, 1, 2, 3, 4, 5].map((i) => 70 + i * 156);
      packet.style.opacity = "1";
      animate(packet, {
        cx: [{ to: stops[0]! }, { to: stops[1]!, delay: 200 }, { to: stops[2]! }, { to: stops[3]! }, { to: stops[4]! }, { to: stops[4]!, duration: 550 }, { to: stops[5]! }],
        duration: 420, delay: 900, ease: easings.inOut,
      });
    }, { threshold: 0.5 });
    io.observe(root);
    return () => io.disconnect();
  }, [reduced]);

  return (
    <section aria-labelledby="pipe-title" className="relative z-content py-24 md:py-36">
      <div className="mx-auto max-w-[1360px] px-5 md:px-8">
        <ScrollReveal className="mb-12 flex max-w-3xl flex-col gap-4">
          <h2 id="pipe-title" className="t-h2">Six stages from event to audit entry.</h2>
        </ScrollReveal>

        <div ref={ref}>
          <svg viewBox="0 0 920 150" role="img" aria-label="Pipeline: detection event, corroboration, Channel A, Channel B, the gate, alert and ledger" className="hidden w-full md:block">
            <path data-line d="M70 60 H850" fill="none" stroke="var(--line-strong)" strokeWidth="1.5" />
            {PIPELINE.map((s, i) => {
              const x = 70 + i * 156;
              const gate = s.id === "gate";
              return (
                <g key={s.id}>
                  {gate ? <path d={`M${x} 40 L${x + 20} 60 L${x} 80 L${x - 20} 60Z`} fill="var(--signal)" /> : <circle cx={x} cy="60" r="9" fill="var(--ink-2)" stroke="var(--bone-2)" strokeWidth="1.5" />}
                  <text x={x} y="108" textAnchor="middle" fontSize="13" fontWeight="500" fill="var(--bone)">{s.label}</text>
                  <text x={x} y="127" textAnchor="middle" fontSize="11" fill="var(--bone-2)">{s.note.length > 26 ? s.note.slice(0, 26) : s.note}</text>
                </g>
              );
            })}
            <circle data-packet cx="70" cy="60" r="5" fill="var(--bone)" />
          </svg>
          <ol className="flex flex-col gap-0 md:hidden">
            {PIPELINE.map((s, i) => (
              <li key={s.id} className="relative flex gap-4 pb-8 last:pb-0">
                <span aria-hidden="true" className="relative flex w-6 flex-col items-center">
                  {s.id === "gate" ? <span className="mt-0.5 size-3.5 rotate-45 bg-signal" /> : <span className="mt-0.5 size-3.5 rounded-full border border-bone-2 bg-ink-2" />}
                  {i < PIPELINE.length - 1 && <span className="mt-1 w-px flex-1 bg-line-strong" />}
                </span>
                <div><p className={cn("font-medium", s.id === "gate" && "text-signal")}>{s.label}</p><p className="text-sm text-bone-2">{s.note}</p></div>
              </li>
            ))}
          </ol>
        </div>

        <ul className="mt-12 grid gap-6 md:grid-cols-3">
          {PIPELINE_FACTS.map((f) => (
            <li key={f} className="border-t border-line pt-4 text-sm leading-relaxed text-bone-2">{f}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
