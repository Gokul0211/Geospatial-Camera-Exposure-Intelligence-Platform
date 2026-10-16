"use client";
import * as React from "react";
import { FeedPane } from "@/components/three/feed-canvas";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { Badge } from "@/components/ui/badge";
import { ScrollReveal } from "@/components/motion/scroll-reveal";
import { TWIN_BANNER } from "@/lib/content/copy";
import { fact } from "@/lib/content/facts";
import { feedBus } from "@/lib/three/feed-bus";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";

/** Frame counters: the live feed keeps counting, the looped one stops at the freeze threshold. */
function useFrameCounters(active: boolean, stopAt: number, reduced: boolean) {
  const [live, setLive] = React.useState(0);
  const [frozen, setFrozen] = React.useState(reduced ? stopAt : 0);
  React.useEffect(() => {
    if (!active || reduced) return;
    const id = window.setInterval(() => {
      setLive((n) => n + 1);
      setFrozen((n) => Math.min(stopAt, n + 1));
    }, 125);
    return () => window.clearInterval(id);
  }, [active, stopAt, reduced]);
  return { live, frozen };
}

function TwinCard({ title, category, frozen, counter, cveOnly, igdctf, gate, children }: {
  title: string; category: string; frozen: boolean; counter: React.ReactNode; cveOnly: number; igdctf: number; gate: number; children?: React.ReactNode;
}) {
  return (
    <article className="flex flex-col gap-5 rounded-card border border-line bg-ink-1/80 p-5 shadow-[var(--inner-highlight)] md:p-6" aria-label={title}>
      <header className="flex items-baseline justify-between gap-3">
        <h3 className="text-lg font-semibold tracking-tight">{title}</h3>
        <span className="num text-xs text-bone-2">{category}</span>
      </header>
      <pre className="num overflow-x-auto rounded-input border border-line bg-ink-0 p-3 text-[0.8125rem] leading-6 text-bone-2" tabIndex={0} aria-label={`${title} banner`}>
        {TWIN_BANNER.join("\n")}
      </pre>
      <div className="relative aspect-video overflow-hidden rounded-input border border-line">
        <FeedPane label={frozen ? "Feed pane, frozen" : "Feed pane, moving"} freeze={frozen} />
        <div className="absolute bottom-2 left-2 flex items-center gap-2">{counter}</div>
      </div>
      {children}
      <div className="grid grid-cols-[1fr_auto] items-center gap-4 border-t border-line pt-4">
        <dl className="num grid grid-cols-2 gap-3 text-sm">
          <div><dt className="text-xs text-bone-2">CVE-only score</dt><dd className="text-2xl text-bone">{cveOnly}</dd></div>
          <div><dt className="text-xs text-bone-2">IG-DCTF score</dt><dd className="text-2xl text-bone">{igdctf}</dd></div>
        </dl>
        <HoodGauge gate={gate} score={igdctf} size={84} animate />
      </div>
    </article>
  );
}

export function BlindSpot() {
  const reduced = usePrefersReducedMotion();
  const ref = React.useRef<HTMLElement | null>(null);
  const [inView, setInView] = React.useState(false);
  const stopAt = fact("method.tier2").freezeFrames;
  const cats = fact("res.t2.end2end");
  const tcve = fact("res.t2.tcve");
  const { live, frozen } = useFrameCounters(inView, stopAt, reduced);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setInView(!!e?.isIntersecting), { threshold: 0.35 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  // the background field freezes when the right feed freezes, and resumes when the section leaves
  React.useEffect(() => {
    if (!inView) return;
    const off = feedBus.with((f) => {
      f.S.freeze = frozen >= stopAt ? 1 : 0;
      f.invalidate();
    });
    return () => off();
  }, [inView, frozen, stopAt]);
  React.useEffect(() => {
    if (inView) return;
    feedBus.with((f) => {
      f.S.freeze = 0;
      f.invalidate();
    });
  }, [inView]);

  return (
    <section ref={ref} aria-labelledby="blind-title" className="relative z-content py-24 md:py-36">
      <div className="mx-auto max-w-[1360px] px-5 md:px-8">
        <ScrollReveal className="mb-12 flex max-w-3xl flex-col gap-4">
          <h2 id="blind-title" className="t-h2">Same banner. Same clean record. One of them is a loop.</h2>
          <p className="t-body text-bone-2">A vulnerability score reads what a device says about itself. It cannot tell a live feed from a looped one.</p>
        </ScrollReveal>
        <div className="grid gap-5 md:grid-cols-2">
          <TwinCard title="Camera A" category="genuine_live" frozen={false} cveOnly={tcve} igdctf={Math.round(cats.genuine_live.mean_t_final)} gate={1}
            counter={<Badge className="num bg-ink-0/80">frame {live}</Badge>} />
          <TwinCard title="Camera B" category="freeze_loop_attack" frozen cveOnly={tcve} igdctf={Math.round(cats.freeze_loop_attack.mean_t_final)} gate={0.3}
            counter={<><Badge className="num bg-ink-0/80">frame {frozen}</Badge>{frozen >= stopAt && <Badge tone="signal" className="num bg-ink-0/80">{stopAt} identical frames</Badge>}</>} />
        </div>
        <p className="mt-6 max-w-3xl text-sm text-bone-2">
          Illustration of the <code className="num text-bone">genuine_live</code> and <code className="num text-bone">freeze_loop_attack</code> categories (results, section 5). The decoy has the same banner and a clean CVE record.
        </p>
      </div>
    </section>
  );
}
