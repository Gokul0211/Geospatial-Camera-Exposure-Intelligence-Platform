"use client";
import * as React from "react";
import { AnimatedCounter } from "@/components/motion/animated-counter";
import { ScrollReveal } from "@/components/motion/scroll-reveal";
import { SourceNote } from "@/components/ui/source-note";
import { SyntheticChip } from "@/components/ui/synthetic-chip";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { animate, dur, easings } from "@/lib/animations";
import { resultsBars } from "@/lib/content/copy";
import { fact, fmt3 } from "@/lib/content/facts";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { cn } from "@/lib/utils";

function Bar({ label, value, tint, detail }: { label: string; value: number; tint: boolean; detail: string }) {
  const ref = React.useRef<HTMLDivElement | null>(null);
  const reduced = usePrefersReducedMotion();
  React.useEffect(() => {
    const el = ref.current;
    if (!el || reduced) return;
    el.style.width = "0%";
    const io = new IntersectionObserver(([e]) => {
      if (!e?.isIntersecting) return;
      io.disconnect();
      animate(el, { width: `${value * 100}%`, duration: dur.long, ease: easings.out });
    }, { threshold: 0.6 });
    io.observe(el);
    return () => io.disconnect();
  }, [value, reduced]);
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <li tabIndex={0} className="grid cursor-default grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-4 rounded-input py-2.5 outline-offset-4 sm:grid-cols-[12rem_1fr_auto]">
          <span className={cn("text-sm", tint ? "text-bone" : "text-bone-2")}>{label}</span>
          <span className="h-2.5 overflow-hidden rounded-full bg-ink-3" aria-hidden="true">
            <span ref={ref} className={cn("block h-full rounded-full", tint ? "bg-signal" : "bg-bone-3")} style={{ width: `${value * 100}%` }} />
          </span>
          <span className={cn("num text-lg", tint ? "text-bone" : "text-bone-2")}>
            <AnimatedCounter value={value} format={fmt3} />
          </span>
        </li>
      </TooltipTrigger>
      <TooltipContent>{detail}</TooltipContent>
    </Tooltip>
  );
}

export function Results() {
  const bars = resultsBars();
  const mc = fact("res.mcnemar");
  const abl = fact("res.ablation");
  const tier1 = fact("res.tier1");
  const tier2 = fact("res.tier2");
  const oh = fact("res.overhead");
  const withB = fact("res.strat.with_b");
  const withoutB = fact("res.strat.without_b");
  const corpus = fact("res.corpus");
  const tests = fact("eval.tests");
  const mult = abl["IG-DCTF (multiplicative)"];
  const add = abl["Additive fusion"];

  return (
    <section aria-labelledby="results-title" className="relative z-content py-24 md:py-36">
      <div className="mx-auto max-w-[1360px] px-5 md:px-8">
        <ScrollReveal className="mb-12 flex max-w-3xl flex-col gap-4">
          <h2 id="results-title" className="t-h2">It closes the blind spot.</h2>
          <div className="flex flex-wrap items-center gap-3 text-sm text-bone-2">
            F1 on {corpus.n} scenarios
            <SyntheticChip />
            <SourceNote fact="res.model.igdctf" />
          </div>
        </ScrollReveal>

        <ul className="max-w-4xl divide-y divide-line" aria-label="F1 by model">
          {bars.map((b) => (
            <Bar key={b.key} label={b.label} value={b.f1} tint={b.key === "igdctf"}
              detail={`TP ${b.model.tp}, FP ${b.model.fp}, TN ${b.model.tn}, FN ${b.model.fn}. Accuracy ${fmt3(b.model.accuracy)}, recall ${fmt3(b.model.recall)}.`} />
          ))}
        </ul>

        <div className="mt-16 grid gap-x-10 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          <Fig value={`${mc.igOnly} vs ${mc.advOnly}`} label="Scenarios only IG-DCTF gets right versus only the CVE-only model (exact McNemar)" note="res.mcnemar" />
          <Fig value={`${mult.fn} vs ${add.fn}`} label="Missed fabrications: multiplicative gate versus the additive control" note="res.ablation" />
          <Fig value={`${(oh.igdctfUs).toFixed(1)} us`} label="Per scoring call, in-process, pure Python" note="res.overhead" />
          <Fig value={`${tests.passed}`} label={`Backend tests passing on ${tests.date}`} note="eval.tests" />
        </div>

        <div className="mt-16 max-w-4xl rounded-card border border-line bg-ink-1/70 p-6">
          <h3 className="text-lg font-semibold tracking-tight">Where the gain comes from</h3>
          <p className="mt-2 text-sm text-bone-2">Accuracy split by whether a scenario carries Channel B fields.</p>
          <div className="mt-5 grid gap-6 sm:grid-cols-2">
            <Strat title={`With Channel B (n = ${withB.n})`} data={withB} />
            <Strat title={`Without (n = ${withoutB.n})`} data={withoutB} />
          </div>
          <p className="mt-5 text-sm text-bone-2">
            Tier 1 is {fmt3(tier1.recall)} recall on {tier1.distinctCases} distinct cases; Tier 2 detects {tier2.tp} of {tier2.tp + tier2.fn} attacks after a mean of {tier2.meanLatencyFrames.toFixed(1)} frames.
          </p>
        </div>
      </div>
    </section>
  );
}

function Fig({ value, label, note }: { value: string; label: string; note: "res.mcnemar" | "res.ablation" | "res.overhead" | "eval.tests" }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="num text-[2.25rem] font-medium leading-none tracking-tight">{value} <SourceNote fact={note} className="align-super" /></div>
      <p className="max-w-[28ch] text-sm leading-snug text-bone-2">{label}</p>
    </div>
  );
}

function Strat({ title, data }: { title: string; data: { WA: number; Advanced: number; Bayesian: number; "IG-DCTF": number } }) {
  const rows = [["Weighted average", data.WA], ["CVE-only", data.Advanced], ["Bayesian", data.Bayesian], ["IG-DCTF", data["IG-DCTF"]]] as const;
  return (
    <div>
      <p className="mb-2 text-sm font-medium">{title}</p>
      <ul className="flex flex-col gap-1.5">
        {rows.map(([k, v]) => (
          <li key={k} className="grid grid-cols-[7.5rem_1fr_auto] items-center gap-3 text-xs text-bone-2">
            <span>{k}</span>
            <span className="h-1.5 overflow-hidden rounded-full bg-ink-3" aria-hidden="true"><span className={cn("block h-full rounded-full", k === "IG-DCTF" ? "bg-signal" : "bg-bone-3")} style={{ width: `${v * 100}%` }} /></span>
            <span className="num text-bone">{fmt3(v)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
