"use client";
import * as React from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { TierShape } from "@/components/ui/tier-tag";
import { DemoTag } from "@/components/ui/demo-tag";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { prettifyFactor, tierLabel } from "@/lib/api/normalize";
import { useConsoleStore, DEFAULT_FILTERS, type AlertFilters } from "@/lib/state/console-store";
import type { AlertMessage } from "@/lib/api/schemas";
import { useAlertHistory } from "@/lib/api/console-hooks";
import { cn } from "@/lib/utils";

const ROW = 64;

function timeOf(iso: string) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "--:--:--" : d.toLocaleTimeString("en-GB", { hour12: false });
}

function passes(a: AlertMessage, f: AlertFilters) {
  if (f.tier !== "all" && a.action_tier !== f.tier) return false;
  if (f.gateTrippedOnly && !a.integrity_gate_tripped) return false;
  if (f.demo === "only" && !a.demo) return false;
  if (f.demo === "hide" && a.demo) return false;
  return true;
}

function Seg<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: readonly (readonly [T, string])[]; onChange: (v: T) => void }) {
  return (
    <div role="group" aria-label={label} className="inline-flex rounded-full border border-line bg-ink-1 p-0.5">
      {options.map(([v, t]) => (
        <button key={v} type="button" aria-pressed={value === v} onClick={() => onChange(v)}
          className={cn("h-7 rounded-full px-2.5 text-xs text-bone-2 transition-colors duration-[160ms] hover:text-bone", value === v && "bg-ink-3 text-bone")}>{t}</button>
      ))}
    </div>
  );
}

export function AlertStream({ className }: { className?: string }) {
  const alerts = useConsoleStore((s) => s.alerts);
  const filters = useConsoleStore((s) => s.filters);
  const setFilters = useConsoleStore((s) => s.setFilters);
  const select = useConsoleStore((s) => s.selectDevice);
  const selected = useConsoleStore((s) => s.selectedDeviceId);
  const history = useAlertHistory();
  const parent = React.useRef<HTMLDivElement | null>(null);
  const rows = React.useMemo(() => alerts.filter((a) => passes(a, filters)), [alerts, filters]);
  const seen = React.useRef(new Set<string>());
  const [fresh, setFresh] = React.useState<Set<string>>(new Set());

  React.useEffect(() => {
    const added = alerts.filter((a) => !seen.current.has(a.id)).slice(0, 5);
    if (!added.length) return;
    const first = seen.current.size === 0;
    alerts.forEach((a) => seen.current.add(a.id));
    if (first) return; // the seeded history does not animate
    const t = setTimeout(() => setFresh(new Set(added.map((a) => a.id))), 0);
    const t2 = setTimeout(() => setFresh(new Set()), 1400);
    return () => { clearTimeout(t); clearTimeout(t2); };
  }, [alerts]);

  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Virtual is used as documented
  const v = useVirtualizer({ count: rows.length, getScrollElement: () => parent.current, estimateSize: () => ROW, overscan: 8 });
  const loading = history.isPending && alerts.length === 0;
  const filtered = filters !== DEFAULT_FILTERS && JSON.stringify(filters) !== JSON.stringify(DEFAULT_FILTERS);

  return (
    <section aria-label="Alert stream" className={cn("flex min-h-0 flex-col bg-ink-0", className)}>
      <div className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2.5">
        <Seg label="Tier" value={filters.tier} onChange={(tier) => setFilters({ tier })}
          options={[["all", "All"], ["high_trust", "High"], ["medium_trust", "Med"], ["low_trust", "Low"]] as const} />
        <Seg label="Demo traffic" value={filters.demo} onChange={(demo) => setFilters({ demo })}
          options={[["all", "All"], ["only", "Demo"], ["hide", "Real"]] as const} />
        <button type="button" aria-pressed={filters.gateTrippedOnly} onClick={() => setFilters({ gateTrippedOnly: !filters.gateTrippedOnly })}
          className={cn("h-8 rounded-full border border-line px-3 text-xs text-bone-2 transition-colors duration-[160ms] hover:text-bone", filters.gateTrippedOnly && "border-signal/60 bg-signal-dim text-bone")}>Gate tripped</button>
      </div>

      {loading ? (
        <div className="flex flex-col gap-2 p-3" aria-label="Loading alerts">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-14 w-full" />)}</div>
      ) : rows.length === 0 ? (
        <div className="p-3"><EmptyState title={filtered ? "No alerts match these filters." : "No alerts yet."}>{filtered ? "Clear a filter to see more." : "Run a scenario or send an event."}</EmptyState></div>
      ) : (
        <div ref={parent} className="min-h-0 flex-1 overflow-y-auto" tabIndex={0} aria-label="Alerts, newest first">
          <ul style={{ height: v.getTotalSize() }} className="relative w-full">
            {v.getVirtualItems().map((item) => {
              const a = rows[item.index]!;
              const sel = selected === a.camera_id;
              return (
                <li key={a.id} className={cn("absolute inset-x-0 border-b border-line", fresh.has(a.id) && "row-in", fresh.has(a.id) && a.integrity_gate_tripped && "row-flash")} style={{ top: item.start, height: ROW }}>
                  <button type="button" onClick={() => select(a.camera_id)} aria-current={sel} className={cn("grid size-full grid-cols-[auto_1fr_auto] items-center gap-3 px-3 text-left transition-colors duration-[160ms] hover:bg-ink-2", sel && "bg-ink-2 shadow-[inset_2px_0_0_var(--signal)]")}>
                    <TierShape tier={a.action_tier} gateTripped={!!a.integrity_gate_tripped} demo={a.demo} size={18} />
                    <span className="min-w-0">
                      <span className="flex items-center gap-2 text-sm text-bone">
                        <span className="truncate">{a.event_type.replaceAll("_", " ")}</span>
                        {a.demo && <DemoTag className="shrink-0 !py-0 text-[0.625rem]" />}
                      </span>
                      <span className="num block truncate text-xs text-bone-2">{a.camera_id.slice(0, 10)} · {a.integrity_gate_tripped ? "Gate tripped" : tierLabel(a.action_tier)}{a.contributing_factors[0] ? ` · ${prettifyFactor(a.contributing_factors[0])}` : ""}</span>
                    </span>
                    <span className="flex flex-col items-end">
                      <span className="num text-sm text-bone">{a.trust_score}</span>
                      <span className="num text-xs text-bone-2">{timeOf(a.detected_at)}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}
