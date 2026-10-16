"use client";
import * as React from "react";
import { HoodCanvas } from "@/components/three/hood-canvas";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { SourceNote } from "@/components/ui/source-note";
import { Badge } from "@/components/ui/badge";
import { WALK_PANELS } from "@/lib/content/copy";
import { fact } from "@/lib/content/facts";
import { useThresholds } from "@/lib/api/hooks";
import { animateNumbers, type TweenHandle } from "@/lib/animations";
import { spreadForGate } from "@/lib/brand/hood";
import type { HoodEngine, HoodState } from "@/lib/three/hood-engine";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { cn } from "@/lib/utils";

const STORY: Record<number, Partial<HoodState>> = {
  0: { dolly: 5.0, ringA: 1, ringB: 0, arcs: 0, overlap: 0, ribs: 0, eye: 0, frames: 0, block: 0 },
  1: { dolly: 5.0, ringA: 1, ringB: 1, arcs: 1, overlap: 0, ribs: 0, eye: 0, frames: 0, block: 0 },
  2: { dolly: 4.5, ringA: 1, ringB: 1, arcs: 0, overlap: 1, ribs: 0, eye: 0, frames: 0, block: 0 },
  3: { dolly: 10.4, ringA: 0, ringB: 0, arcs: 0, overlap: 0, ribs: 1, eye: 1, frames: 0.6, block: 0, spread: 236, prog: 1, stagger: 0 },
};
const G_STATES = [
  { id: "trips", label: "Trips", g: 0.3, block: 1 },
  { id: "tapers", label: "Tapers", g: 0.65, block: 0.3 },
  { id: "passes", label: "Passes", g: 1, block: 0 },
] as const;

export function WalkGate() {
  const reduced = usePrefersReducedMotion();
  const { thresholds, source } = useThresholds();
  const engineRef = React.useRef<HoodEngine | null>(null);
  const tweens = React.useRef<TweenHandle[]>([]);
  const [panel, setPanel] = React.useState(0);
  const [stateIdx, setStateIdx] = React.useState(0);
  const panelRefs = React.useRef<(HTMLElement | null)[]>([]);
  const ex = fact("res.model.igdctf");

  const goto = React.useCallback((to: Partial<HoodState>, duration = 900) => {
    const e = engineRef.current;
    if (!e) return;
    tweens.current.forEach((t) => t.cancel());
    tweens.current = [];
    if (reduced) {
      Object.assign(e.S, to);
      e.invalidate();
      return;
    }
    tweens.current.push(animateNumbers(e.S, to, { duration, ease: "inOut", onFrame: () => e.invalidate() }));
  }, [reduced]);

  // which panel is centred
  React.useEffect(() => {
    const els = panelRefs.current.filter(Boolean) as HTMLElement[];
    const io = new IntersectionObserver((entries) => {
      for (const en of entries) if (en.isIntersecting) setPanel(Number((en.target as HTMLElement).dataset.index));
    }, { rootMargin: "-45% 0px -45% 0px" });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  React.useEffect(() => {
    if (panel < 4) goto(STORY[panel] ?? {}, panel === 3 ? 1400 : 900);
    else {
      const s = G_STATES[stateIdx]!;
      goto({ ...STORY[3], spread: spreadForGate(s.g), block: s.block, prog: 1, eye: 0.25 + 0.75 * s.g }, 900);
    }
  }, [panel, stateIdx, goto]);

  // panel 5: walk through the three states once, then rest on "passes"
  React.useEffect(() => {
    if (panel !== 4 || reduced) return;
    const t0 = window.setTimeout(() => setStateIdx(0), 0);
    const t1 = window.setTimeout(() => setStateIdx(1), 1300);
    const t2 = window.setTimeout(() => setStateIdx(2), 2600);
    return () => {
      window.clearTimeout(t0);
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [panel, reduced]);

  const onReady = React.useCallback((e: HoodEngine) => {
    engineRef.current = e;
    Object.assign(e.S, STORY[0], { shiftX: 0, stagger: 0, prog: 1, spread: 236 });
    e.invalidate();
  }, []);

  const g = thresholds.gate;

  return (
    <section id="method" aria-labelledby="walk-title" className="relative z-content">
      <div className="mx-auto max-w-[1360px] px-5 md:px-8">
        <div className="max-w-3xl pb-10 pt-12 md:pb-16">
          <h2 id="walk-title" className="t-h2">Walk the gate.</h2>
        </div>
        <div className="grid gap-x-12 lg:grid-cols-2">
          <div className="sticky top-16 z-sticky h-[46vh] lg:top-0 lg:h-dvh">
            <div className="absolute inset-0 overflow-hidden">
              <HoodCanvas onReady={onReady} />
            </div>
            <div className="pointer-events-none absolute bottom-3 left-0 right-0 flex justify-center gap-2 lg:bottom-10" aria-hidden="true">
              {WALK_PANELS.map((p, i) => (
                <span key={p.id} className={cn("h-1 w-8 rounded-full bg-line-strong transition-colors duration-[260ms]", i === panel && "bg-signal")} />
              ))}
            </div>
          </div>

          <div className="relative flex flex-col pb-[20vh]">
            {WALK_PANELS.map((p, i) => (
              <article key={p.id} ref={(el) => void (panelRefs.current[i] = el)} data-index={i} aria-labelledby={`walk-${p.id}`}
                className="flex min-h-[78dvh] flex-col justify-center gap-5 py-10 lg:min-h-dvh">
                <h3 id={`walk-${p.id}`} className="text-3xl font-semibold tracking-tight md:text-4xl">{p.title}</h3>
                <p className="t-body text-bone-2">{p.body}</p>
                {i === 0 && <p className="num text-sm text-bone-2">T_cve, tiers from {thresholds.tiers.high_min} and {thresholds.tiers.medium_min}</p>}
                {i === 1 && <p className="num text-sm text-bone-2">drift threshold {fact("method.tier1").driftThreshold.toFixed(2)}, L = 1 - max(w1 Freeze, w2 q, w3 m)</p>}
                {i === 2 && <p className="num text-sm text-bone-2">P(secure and authentic)</p>}
                {i === 3 && (
                  <div className="flex flex-col gap-2">
                    <p className="num text-sm text-bone">G(s) = 1 above {g.theta_high.toFixed(2)}, tapers to {g.floor_multiplier.toFixed(1)} at {g.theta_low.toFixed(2)}, cap {g.hard_cap} below</p>
                    <div><Badge dashed={source === "static"}>{source === "live" ? "Live thresholds" : "Static thresholds (backend offline)"}</Badge></div>
                  </div>
                )}
                {i === 4 && (
                  <div className="flex flex-col gap-4">
                    <div className="flex flex-wrap gap-3" role="group" aria-label="Gate states">
                      {G_STATES.map((s, k) => (
                        <button key={s.id} type="button" aria-pressed={stateIdx === k} onClick={() => { setStateIdx(k); }}
                          className={cn("flex flex-col items-center gap-2 rounded-card border border-line px-4 py-3 text-sm text-bone-2 transition-colors duration-[160ms] hover:bg-ink-2", stateIdx === k && "border-signal/60 bg-signal-dim text-bone")}>
                          <HoodGauge gate={s.g} score={Math.round(s.g * 100)} size={72} />
                          {s.label}
                        </button>
                      ))}
                    </div>
                    <p className="num text-sm text-bone-2">
                      IG-DCTF F1 {ex.f1.toFixed(3)} <SourceNote fact="res.model.igdctf" /> on the synthetic corpus
                    </p>
                  </div>
                )}
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
