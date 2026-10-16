"use client";
import * as React from "react";
import Link from "next/link";
import { ChartBar, Command as CommandIcon } from "@phosphor-icons/react/dist/ssr";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { CITIES, useThresholds } from "@/lib/api/hooks";
import { gateCurve } from "@/lib/scoring/gate";
import { useStats, useSummary } from "@/lib/api/console-hooks";
import { useConsoleStore } from "@/lib/state/console-store";
import { cn } from "@/lib/utils";

const STATUS: Record<string, string> = { connecting: "Connecting", live: "Live", disconnected: "Disconnected" };

export function TopBar({ onRun, running, onAnalytics, onPalette, runMessage }: { onRun: () => void; running: boolean; onAnalytics: () => void; onPalette: () => void; runMessage: string | null }) {
  const city = useConsoleStore((s) => s.city);
  const setCity = useConsoleStore((s) => s.setCity);
  const connection = useConsoleStore((s) => s.connection);
  const retryInMs = useConsoleStore((s) => s.retryInMs);
  const alerts = useConsoleStore((s) => s.alerts);
  const stats = useStats(city);
  const summary = useSummary();
  const [left, setLeft] = React.useState<number | null>(null);

  React.useEffect(() => {
    if (connection !== "disconnected" || retryInMs === null) { const t = setTimeout(() => setLeft(null), 0); return () => clearTimeout(t); }
    const end = Date.now() + retryInMs;
    const tick = () => setLeft(Math.max(0, Math.ceil((end - Date.now()) / 1000)));
    const t0 = setTimeout(tick, 0);
    const id = setInterval(tick, 500);
    return () => { clearTimeout(t0); clearInterval(id); };
  }, [connection, retryInMs]);

  const { thresholds } = useThresholds();
  const latest = alerts[0];
  // The gauge shows the latest alert's gate multiplier, computed from its signal integrity with the live thresholds.
  const gate = !latest ? 1
    : latest.signal_integrity_score != null ? gateCurve(latest.signal_integrity_score, thresholds.gate.theta_high, thresholds.gate.theta_low)
    : latest.integrity_gate_tripped ? thresholds.gate.floor_multiplier : 1;

  return (
    <header className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line bg-ink-0 px-3 py-2 md:px-4">
      <Link href="/" aria-label="COBRA-WATCH home" className="flex items-center gap-2 no-underline">
        <HoodGauge gate={gate} score={latest?.trust_score ?? 100} size={40} animate label="Latest gate state" />
        <span className="hidden text-sm font-semibold tracking-[0.18em] text-bone sm:inline">COBRA-WATCH</span>
      </Link>
      <label className="sr-only" htmlFor="city">City</label>
      <select id="city" value={city} onChange={(e) => setCity(e.target.value)} className="h-9 rounded-full border border-line-strong bg-ink-2 px-3 text-sm text-bone">
        {CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
      <div role="status" aria-live="polite" className="flex items-center gap-2 text-sm text-bone-2">
        <span aria-hidden="true" className={cn("size-2 rounded-full", connection === "live" ? "bg-signal" : "border border-bone-3")} />
        {STATUS[connection]}{connection === "disconnected" && left !== null ? <span className="num">, retry in {left}s</span> : null}
      </div>
      <dl className="num hidden items-center gap-5 text-sm md:flex">
        <div className="flex items-baseline gap-1.5"><dt className="text-xs text-bone-2">Devices</dt><dd>{stats.data?.total_devices ?? "—"}</dd></div>
        <div className="flex items-baseline gap-1.5"><dt className="text-xs text-bone-2">Alerts 24 h</dt><dd>{summary.data?.total_alerts_24h ?? "—"}</dd></div>
      </dl>
      <div className="ml-auto flex items-center gap-2">
        {runMessage && <span role="status" className="hidden max-w-[28ch] truncate text-xs text-bone-2 lg:inline">{runMessage}</span>}
        <Button size="sm" onClick={onRun} disabled={running}>{running ? "Starting" : "Run scenario"}</Button>
        <Button size="sm" variant="secondary" onClick={onAnalytics} aria-label="Analytics"><ChartBar size={16} aria-hidden="true" /><span className="hidden sm:inline">Analytics</span></Button>
        <Button size="sm" variant="ghost" onClick={onPalette} aria-label="Open command palette"><CommandIcon size={16} aria-hidden="true" /><span className="hidden items-center gap-1 lg:inline-flex"><Kbd>Ctrl</Kbd><Kbd>K</Kbd></span></Button>
      </div>
    </header>
  );
}
