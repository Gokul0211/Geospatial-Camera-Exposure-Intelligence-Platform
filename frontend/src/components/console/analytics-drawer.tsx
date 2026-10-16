"use client";
import * as React from "react";
import { Dialog } from "radix-ui";
import { X } from "@phosphor-icons/react/dist/ssr";
import { scaleBand, scaleLinear } from "d3-scale";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { InlineError } from "@/components/ui/inline-error";
import { OfflineState } from "@/components/ui/offline-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SyntheticChip } from "@/components/ui/synthetic-chip";
import { ApiError } from "@/lib/api/errors";
import { useAuditStats, useEvalLive, useIntegrity, useLedger, useStats, useTimeline, useTrustDist, useVerifyChain } from "@/lib/api/console-hooks";
import { useConsoleStore } from "@/lib/state/console-store";
import { fact, fmt3 } from "@/lib/content/facts";
import { resultsBars } from "@/lib/content/copy";
import { cn } from "@/lib/utils";

function State({ q, children }: { q: { isPending: boolean; error: unknown }; children: React.ReactNode }) {
  if (q.isPending) return <div className="flex flex-col gap-2" aria-hidden="true"><Skeleton className="h-5 w-1/3" /><Skeleton className="h-24 w-full" /></div>;
  if (q.error instanceof ApiError && q.error.offline) return <OfflineState />;
  if (q.error) return <InlineError>{q.error instanceof ApiError ? q.error.detail : "Unexpected error"}</InlineError>;
  return <>{children}</>;
}

function Bars({ rows }: { rows: [string, number][] }) {
  const max = Math.max(...rows.map((r) => r[1]), 1);
  return (
    <ul className="flex flex-col gap-2">
      {rows.map(([k, v]) => (
        <li key={k} className="grid grid-cols-[8rem_1fr_auto] items-center gap-3 text-sm text-bone-2">
          <span>{k}</span>
          <span className="h-2 overflow-hidden rounded-full bg-ink-3" aria-hidden="true"><span className="block h-full rounded-full bg-bone-3" style={{ width: `${(v / max) * 100}%` }} /></span>
          <span className="num text-bone">{v}</span>
        </li>
      ))}
    </ul>
  );
}

function Fleet() {
  const dist = useTrustDist();
  const stats = useStats("All India");
  return (
    <div className="flex flex-col gap-6">
      <div><h4 className="mb-2 text-sm font-medium">Alert tiers, last 24 hours</h4>
        <State q={dist}>{dist.data && <Bars rows={[["High", dist.data.tiers.high_trust ?? 0], ["Medium", dist.data.tiers.medium_trust ?? 0], ["Low", dist.data.tiers.low_trust ?? 0]]} />}</State></div>
      <div><h4 className="mb-2 text-sm font-medium">Devices by owner type</h4>
        <State q={stats}>{stats.data?.by_owner && <Bars rows={Object.entries(stats.data.by_owner)} />}</State></div>
    </div>
  );
}

function AlertsTab() {
  const tl = useTimeline();
  const alerts = useConsoleStore((s) => s.alerts);
  const demo = alerts.filter((a) => a.demo).length;
  return (
    <div className="flex flex-col gap-4">
      <State q={tl}>
        {tl.data && (() => {
          const W = 480, H = 200, m = { l: 30, r: 8, t: 10, b: 28 };
          const data = tl.data.timeline;
          const x = scaleBand().domain(data.map((d) => d.hour)).range([m.l, W - m.r]).padding(0.22);
          const max = Math.max(1, ...data.map((d) => d.count));
          const y = scaleLinear().domain([0, max]).range([H - m.b, m.t]).nice(4);
          const ticks = y.ticks(4).filter((t) => Number.isInteger(t));
          const total = data.reduce((n, d) => n + d.count, 0);
          return (
            <>
              <div className="flex items-baseline justify-between"><h4 className="text-sm font-medium">Alerts per hour</h4><span className="num text-xs text-bone-2">{total} in the last {data.length} hours</span></div>
              <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Alerts per hour for the last ${data.length} hours, ${total} in total`} className="w-full">
                {ticks.map((t) => (
                  <g key={t}>
                    <line x1={m.l} x2={W - m.r} y1={y(t)} y2={y(t)} stroke="var(--line)" />
                    <text x={m.l - 6} y={y(t) + 3} textAnchor="end" fontSize="9" className="num" fill="var(--bone-2)">{t}</text>
                  </g>
                ))}
                {data.map((d) => {
                  const bx = x(d.hour) ?? 0;
                  const full = H - m.b - y(d.count);
                  const low = (d.low_trust / Math.max(d.count, 1)) * full;
                  return (
                    <g key={d.hour}>
                      <title>{`${d.hour} UTC: ${d.count} alerts (${d.low_trust} low, ${d.medium_trust} medium, ${d.high_trust} high)`}</title>
                      <rect x={bx} width={x.bandwidth()} y={y(d.count)} height={Math.max(full - low, 0)} fill="var(--bone-3)" rx="1.5" />
                      <rect x={bx} width={x.bandwidth()} y={H - m.b - low} height={Math.max(low, 0)} fill="var(--signal)" rx="1.5" />
                    </g>
                  );
                })}
                <line x1={m.l} x2={W - m.r} y1={H - m.b} y2={H - m.b} stroke="var(--line-strong)" />
                {data.filter((_, i) => i % 4 === 3 || i === data.length - 1).map((d) => (
                  <text key={d.hour} x={(x(d.hour) ?? 0) + x.bandwidth() / 2} y={H - 10} textAnchor="middle" fontSize="9" className="num" fill="var(--bone-2)">{d.hour}</text>
                ))}
              </svg>
              <ul className="flex items-center gap-4 text-xs text-bone-2">
                <li className="flex items-center gap-1.5"><span aria-hidden="true" className="size-2.5 rounded-[3px] bg-signal" />Low trust</li>
                <li className="flex items-center gap-1.5"><span aria-hidden="true" className="size-2.5 rounded-[3px] bg-bone-3" />Medium and high</li>
                <li className="ml-auto">Hours are UTC</li>
              </ul>
            </>
          );
        })()}
      </State>
      <p className="text-xs text-bone-2">The API series includes demo traffic. In this tab&apos;s live buffer, <span className="num text-bone">{demo}</span> of <span className="num text-bone">{alerts.length}</span> alerts are demo.</p>
    </div>
  );
}

function Integrity() {
  const q = useIntegrity();
  return (
    <State q={q}>
      {q.data && !q.data.gate_distribution && <p className="text-sm text-bone-2">No devices in the database yet, so there is no integrity state to show.</p>}
      {q.data?.gate_distribution && (
        <div className="flex flex-col gap-5">
          <Bars rows={[["Nominal", q.data.gate_distribution.nominal ?? 0], ["Tapered", q.data.gate_distribution.tapered ?? 0], ["Hard gated", q.data.gate_distribution.hard_gated ?? 0]]} />
          {q.data.drift_stats && (
            <dl className="num grid grid-cols-2 gap-3 text-sm">
              <div><dt className="text-xs text-bone-2">Mean drift</dt><dd>{q.data.drift_stats.mean_drift_score.toFixed(3)}</dd></div>
              <div><dt className="text-xs text-bone-2">Devices with anomalous drift</dt><dd>{q.data.drift_stats.anomalous_count}</dd></div>
            </dl>
          )}
        </div>
      )}
    </State>
  );
}

function Ledger() {
  const stats = useAuditStats();
  const ledger = useLedger();
  const verify = useVerifyChain();
  return (
    <div className="flex flex-col gap-5">
      <State q={stats}>
        {stats.data && (
          <dl className="num grid gap-2 text-sm">
            <div className="flex justify-between gap-4 border-b border-line py-1"><dt className="text-bone-2">Chain length</dt><dd>{stats.data.chain_length}</dd></div>
            <div className="flex justify-between gap-4 border-b border-line py-1"><dt className="text-bone-2">Head hash</dt><dd className="truncate">{stats.data.head_hash.slice(0, 20)}</dd></div>
          </dl>
        )}
      </State>
      <div className="flex flex-col gap-2">
        <Button size="sm" variant="secondary" className="self-start" disabled={verify.isPending} onClick={() => verify.mutate()}>{verify.isPending ? "Verifying" : "Verify full chain"}</Button>
        <div role="status" aria-live="polite">
          {verify.data && <p className={cn("rounded-input border p-3 text-sm", verify.data.valid ? "border-line bg-ink-1 text-bone-2" : "border-signal/50 bg-signal-dim text-bone")}>{verify.data.valid ? "Valid" : "Verification failed"}: {verify.data.message} <span className="num">({verify.data.chain_length} entries)</span></p>}
          {verify.error instanceof ApiError && <InlineError title="Could not verify">{verify.error.detail}</InlineError>}
        </div>
      </div>
      <State q={ledger}>
        {ledger.data && <ul className="flex flex-col gap-1.5">{ledger.data.entries.map((e) => <li key={e.hash} className="num truncate rounded-input border border-line bg-ink-1 px-3 py-2 text-xs text-bone-2">#{e.sequence_id} · {e.hash.slice(0, 18)}</li>)}</ul>}
      </State>
    </div>
  );
}

function Accuracy() {
  const live = useEvalLive();
  const bars = resultsBars();
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-3"><h4 className="text-sm font-medium">Evaluation corpus</h4><SyntheticChip /></div>
      <ul className="flex flex-col gap-1.5 text-sm">{bars.map((b) => <li key={b.key} className="flex justify-between gap-4 border-b border-line py-1 text-bone-2"><span>{b.label}</span><span className="num text-bone">F1 {fmt3(b.f1)}</span></li>)}</ul>
      <p className="text-xs text-bone-2">From paper/results.md, corpus of {fact("res.corpus").n} synthetic scenarios.</p>
      <div><h4 className="mb-2 text-sm font-medium">Live operator labels</h4>
        <p className="mb-2 text-xs text-bone-2">Backend definition: an alert in the high-trust tier counts as the positive class. The paper&apos;s convention is the opposite (positive = fabricated), so these two sets of numbers are not comparable.</p>
        <State q={live}>{live.data && (live.data.total_labelled === 0 ? <p className="text-sm text-bone-2">{live.data.message ?? "No operator verdicts recorded yet."}</p> : <dl className="num grid grid-cols-2 gap-2 text-sm"><div>Precision {fmt3(live.data.precision ?? 0)}</div><div>Recall {fmt3(live.data.recall ?? 0)}</div></dl>)}</State></div>
    </div>
  );
}

export function AnalyticsDrawer({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-modal bg-ink-0/70" />
        <Dialog.Content aria-describedby={undefined} className="fixed inset-y-0 right-0 z-modal flex w-full max-w-[560px] flex-col border-l border-line-strong bg-ink-1 shadow-[var(--inner-highlight)]">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <Dialog.Title className="text-lg font-semibold tracking-tight">Analytics</Dialog.Title>
            <Dialog.Close className="inline-flex size-9 items-center justify-center rounded-full text-bone-2 hover:bg-ink-3 hover:text-bone" aria-label="Close analytics"><X size={18} /></Dialog.Close>
          </div>
          <Tabs defaultValue="fleet" className="flex min-h-0 flex-1 flex-col gap-5 p-5">
            <TabsList aria-label="Analytics views" className="self-start">
              {(["fleet", "alerts", "integrity", "ledger", "accuracy"] as const).map((t) => <TabsTrigger key={t} value={t} className="capitalize">{t}</TabsTrigger>)}
            </TabsList>
            <div className="min-h-0 flex-1 overflow-y-auto pr-1">
              <TabsContent value="fleet"><Fleet /></TabsContent>
              <TabsContent value="alerts"><AlertsTab /></TabsContent>
              <TabsContent value="integrity"><Integrity /></TabsContent>
              <TabsContent value="ledger"><Ledger /></TabsContent>
              <TabsContent value="accuracy"><Accuracy /></TabsContent>
            </div>
          </Tabs>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
