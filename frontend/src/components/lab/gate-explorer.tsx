"use client";
import * as React from "react";
import { scaleLinear } from "d3-scale";
import { line } from "d3-shape";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { TierTag } from "@/components/ui/tier-tag";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DemoTag } from "@/components/ui/demo-tag";
import { FeedPane } from "@/components/three/feed-canvas";
import { useThresholds } from "@/lib/api/hooks";
import { fuse, gateCurve, computeVisualLiveness } from "@/lib/scoring/gate";
import { fact } from "@/lib/content/facts";
import { cn } from "@/lib/utils";

interface Controls {
  tCve: number;
  drift: number;
  freeze: boolean;
  quality: number;
  spec: boolean;
  tier2Off: boolean;
}

const START: Controls = { tCve: 100, drift: 0, freeze: false, quality: 0, spec: false, tier2Off: false };

const PRESETS: { label: string; set: Partial<Controls> }[] = [
  { label: "Genuine live feed", set: { ...START } },
  { label: "Freeze loop", set: { ...START, freeze: true } },
  { label: "Quality drift", set: { ...START, quality: 1 } },
  { label: "Spec mismatch", set: { ...START, spec: true } },
  { label: "Firmware banner change", set: { ...START, drift: 0.25, tier2Off: true } },
  { label: "Full decoy banner", set: { ...START, drift: 1, tier2Off: true } },
];

function Slider({ id, label, value, min, max, step, onChange, text, disabled }: {
  id: string; label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void; text: string; disabled?: boolean;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", disabled && "opacity-45")}>
      <label htmlFor={id} className="flex items-baseline justify-between text-sm text-bone-2">
        <span>{label}</span>
        <span className="num text-bone">{text}</span>
      </label>
      <input id={id} type="range" min={min} max={max} step={step} value={value} disabled={disabled} aria-valuetext={text}
        onChange={(e) => onChange(Number(e.target.value))} className="h-2 w-full cursor-pointer accent-(--signal) disabled:cursor-not-allowed" />
    </div>
  );
}

function Toggle({ id, label, checked, onChange, disabled }: { id: string; label: string; checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <label htmlFor={id} className={cn("flex cursor-pointer items-center justify-between gap-3 text-sm text-bone-2", disabled && "cursor-not-allowed opacity-45")}>
      <span>{label}</span>
      <input id={id} type="checkbox" role="switch" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)}
        className="h-5 w-9 cursor-pointer appearance-none rounded-full border border-line-strong bg-ink-3 transition-colors duration-[160ms] checked:border-signal checked:bg-signal-dim before:block before:size-3.5 before:translate-x-0.5 before:translate-y-[2px] before:rounded-full before:bg-bone-2 before:transition-transform before:duration-[160ms] checked:before:translate-x-[18px] checked:before:bg-signal" />
    </label>
  );
}

export function GateCurve({ s, g, thetaLow, thetaHigh }: { s: number; g: number; thetaLow: number; thetaHigh: number }) {
  const W = 340, H = 190, m = { l: 36, r: 12, t: 12, b: 30 };
  const x = scaleLinear().domain([0, 1]).range([m.l, W - m.r]);
  const y = scaleLinear().domain([0.3, 1]).range([H - m.b, m.t]);
  const pts = Array.from({ length: 101 }, (_, i) => i / 100);
  const d = line<number>().x((v) => x(v)).y((v) => y(gateCurve(v, thetaHigh, thetaLow)))(pts) ?? "";
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`G of s curve. At s ${s.toFixed(2)} the multiplier is ${g.toFixed(2)}`} className="w-full">
      {[thetaLow, thetaHigh].map((t) => (
        <g key={t}>
          <line x1={x(t)} x2={x(t)} y1={m.t} y2={H - m.b} stroke="var(--line-strong)" strokeDasharray="3 4" />
          <text x={x(t)} y={H - 10} textAnchor="middle" className="num" fontSize="10" fill="var(--bone-2)">{t.toFixed(2)}</text>
        </g>
      ))}
      <line x1={m.l} x2={W - m.r} y1={H - m.b} y2={H - m.b} stroke="var(--line-strong)" />
      <line x1={m.l} x2={m.l} y1={m.t} y2={H - m.b} stroke="var(--line-strong)" />
      {[0.3, 0.65, 1].map((v) => (
        <text key={v} x={m.l - 6} y={y(v) + 3} textAnchor="end" className="num" fontSize="10" fill="var(--bone-2)">{v.toFixed(2)}</text>
      ))}
      <path d={d} fill="none" stroke="var(--bone)" strokeWidth="1.5" />
      <line x1={x(s)} x2={x(s)} y1={y(g)} y2={H - m.b} stroke="var(--signal)" strokeOpacity="0.5" />
      <circle cx={x(s)} cy={y(g)} r="5" fill="var(--signal)" style={{ transition: "cx 160ms var(--ease-out), cy 160ms var(--ease-out)" }} />
      <text x={W - m.r} y={H - 10} textAnchor="end" fontSize="10" fill="var(--bone-2)">s</text>
      <text x={m.l + 6} y={m.t + 8} fontSize="10" fill="var(--bone-2)">G(s)</text>
    </svg>
  );
}

/** The gate explorer: computed in the browser with the parity-tested port (spec 7.5 and 12). */
export function GateExplorer({ compact = false, className }: { compact?: boolean; className?: string }) {
  const [c, setC] = React.useState<Controls>(START);
  const { thresholds, source } = useThresholds();
  const set = (p: Partial<Controls>) => setC((prev) => ({ ...prev, ...p }));
  const { theta_low: thetaLow, theta_high: thetaHigh } = thresholds.gate;

  const r = fuse({
    tCve: c.tCve, drift: c.drift, freeze: c.tier2Off ? null : c.freeze, qualityDrift: c.quality, specMismatch: c.spec, thetaHigh, thetaLow,
  });
  const cveOnlyTier = c.tCve >= thresholds.tiers.high_min ? "high_trust" : c.tCve >= thresholds.tiers.medium_min ? "medium_trust" : "low_trust";
  const L = r.liveness;
  const feedQuality = c.tier2Off ? 0 : c.quality;

  return (
    <div className={cn("flex flex-col gap-5", className)}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="signal">Computed in your browser, same formula as the backend (parity-tested)</Badge>
        {source === "static" ? <Badge dashed>Static thresholds (backend offline)</Badge> : <Badge>Live thresholds from the backend</Badge>}
        <DemoTag />
      </div>

      <Tabs defaultValue="instrument" className="flex flex-col gap-5">
        {!compact && (
          <TabsList aria-label="Explorer views" className="self-start">
            <TabsTrigger value="instrument">Instrument</TabsTrigger>
            <TabsTrigger value="formula">Formula</TabsTrigger>
          </TabsList>
        )}

        <TabsContent value="instrument" className="grid gap-6 lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
          <div className="flex flex-col gap-4 rounded-card border border-line bg-ink-1 p-5 shadow-[var(--inner-highlight)]">
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Presets">
              {PRESETS.map((p) => (
                <Button key={p.label} size="sm" variant="ghost" className="h-8 border border-line px-3 text-xs" onClick={() => setC({ ...START, ...p.set })}>
                  {p.label}
                </Button>
              ))}
            </div>
            <Slider id="x-tcve" label="Posture score T_cve" value={c.tCve} min={0} max={100} step={1} onChange={(v) => set({ tCve: v })} text={String(c.tCve)} />
            <Slider id="x-drift" label="Banner drift (Tier 1)" value={c.drift} min={0} max={1} step={0.01} onChange={(v) => set({ drift: v })} text={c.drift.toFixed(2)} />
            <Toggle id="x-t2off" label="Tier 2 unavailable" checked={c.tier2Off} onChange={(v) => set({ tier2Off: v })} />
            <Toggle id="x-freeze" label="Frozen or looped feed" checked={c.freeze} disabled={c.tier2Off} onChange={(v) => set({ freeze: v })} />
            <Slider id="x-q" label="Blur and exposure drift" value={c.quality} min={0} max={1} step={0.01} disabled={c.tier2Off} onChange={(v) => set({ quality: v })} text={c.quality.toFixed(2)} />
            <Toggle id="x-spec" label="Declared spec mismatch" checked={c.spec} disabled={c.tier2Off} onChange={(v) => set({ spec: v })} />
          </div>

          <div className="flex min-w-0 flex-col gap-5">
            <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
              <div className="flex flex-col gap-2">
                <div className="aspect-video overflow-hidden rounded-card border border-line">
                  <FeedPane label="Procedural feed pane that degrades with the controls" freeze={!c.tier2Off && c.freeze} blur={feedQuality} spec={!c.tier2Off && c.spec ? 1 : 0} drift={c.drift} />
                </div>
                <p className="text-xs text-bone-2">Illustrative feed. Blur, freeze, letterbox and tracking offset follow the controls.</p>
              </div>
              <div className="rounded-card border border-line bg-ink-1 p-3">
                <GateCurve s={r.signalIntegrity} g={r.gate.multiplier} thetaLow={thetaLow} thetaHigh={thetaHigh} />
              </div>
            </div>

            <div className="grid gap-5 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-center">
              <div className="flex items-center gap-4">
                <HoodGauge gate={r.gate.multiplier} score={r.tFinal} size={compact ? 120 : 150} animate />
              </div>
              <dl className="num grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm sm:grid-cols-3">
                {([
                  ["Drift", c.drift.toFixed(2)],
                  ["L", L === null ? "n/a" : L.toFixed(2)],
                  ["s", r.signalIntegrity.toFixed(2)],
                  ["G(s)", r.gate.multiplier.toFixed(2)],
                  ["T_final", String(r.tFinal)],
                  ["Gate", r.gate.status.replace("_", " ")],
                ] as const).map(([k, v]) => (
                  <div key={k} className="flex items-baseline justify-between gap-3 border-b border-line py-1">
                    <dt className="text-bone-2">{k}</dt>
                    <dd className="text-bone" aria-live="polite">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>

            <div className="grid gap-3 rounded-card border border-line bg-ink-1 p-4 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <span className="text-xs text-bone-2">CVE-only would say</span>
                <TierTag tier={cveOnlyTier} score={c.tCve} />
              </div>
              <div className="flex flex-col gap-1.5">
                <span className="text-xs text-bone-2">IG-DCTF says</span>
                <TierTag tier={r.tier} gateTripped={r.gate.tripped} score={r.tFinal} />
              </div>
            </div>
          </div>
        </TabsContent>

        {!compact && (
          <TabsContent value="formula" className="grid gap-4 text-sm text-bone-2 md:grid-cols-2">
            <div className="flex flex-col gap-2 rounded-card border border-line bg-ink-1 p-5">
              <p className="font-medium text-bone">Signal integrity</p>
              <p className="num">s = (1 - Drift) * L</p>
              <p>When Tier 2 is unavailable, s = 1 - Drift.</p>
              <p className="num">L = 1 - max(w1 * Freeze, w2 * q, w3 * m)</p>
              <p className="num">w = ({fact("method.tier2").weights.freeze.toFixed(1)}, {fact("method.tier2").weights.quality.toFixed(1)}, {fact("method.tier2").weights.spec.toFixed(1)})</p>
              <p className="num">
                Now: L = {computeVisualLiveness(!c.tier2Off && c.freeze, c.quality, !c.tier2Off && c.spec).toFixed(2)}{c.tier2Off ? " (not used)" : ""}
              </p>
            </div>
            <div className="flex flex-col gap-2 rounded-card border border-line bg-ink-1 p-5">
              <p className="font-medium text-bone">Gate and fusion</p>
              <p className="num">G(s) = 1 if s &gt;= {thetaHigh.toFixed(2)}</p>
              <p className="num">G(s) = {thresholds.gate.floor_multiplier.toFixed(1)} + 0.7 (s - {thetaLow.toFixed(2)}) / ({thetaHigh.toFixed(2)} - {thetaLow.toFixed(2)}) if {thetaLow.toFixed(2)} &lt;= s &lt; {thetaHigh.toFixed(2)}</p>
              <p className="num">G(s) = {thresholds.gate.floor_multiplier.toFixed(1)}, score capped at {thresholds.gate.hard_cap} if s &lt; {thetaLow.toFixed(2)}</p>
              <p className="num">T_final = T_cve * G(s)</p>
              <p>Tiers: high from {thresholds.tiers.high_min}, medium from {thresholds.tiers.medium_min}, low below.</p>
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
