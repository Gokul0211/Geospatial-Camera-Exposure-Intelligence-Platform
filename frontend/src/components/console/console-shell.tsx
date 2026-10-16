"use client";
import * as React from "react";
import dynamic from "next/dynamic";
import { AlertStream } from "@/components/console/alert-stream";
import { AnalyticsDrawer } from "@/components/console/analytics-drawer";
import { CommandPalette } from "@/components/console/command-palette";
import { Inspector } from "@/components/console/inspector";
import { LiveConnection } from "@/components/console/live-connection";
import { TopBar } from "@/components/console/top-bar";
import { ZoneBrief } from "@/components/console/zone-brief";
import { EmptyState } from "@/components/ui/empty-state";
import { InlineError } from "@/components/ui/inline-error";
import { OfflineState } from "@/components/ui/offline-state";
import { Skeleton } from "@/components/ui/skeleton";
import { TierShape } from "@/components/ui/tier-tag";
import { geoProvenance } from "@/lib/api/normalize";
import type { Zone } from "@/components/map/map-view";
import { useDevices } from "@/lib/api/hooks";
import { useHeat, useRunScenario } from "@/lib/api/console-hooks";
import { ApiError } from "@/lib/api/errors";
import { useConsoleStore } from "@/lib/state/console-store";
import { CITY_VIEW } from "@/lib/constants/cities";
import { cn } from "@/lib/utils";

const MapView = dynamic(() => import("@/components/map/map-view"), { ssr: false, loading: () => <Skeleton className="size-full rounded-none" /> });

type Pane = "map" | "stream" | "detail";

function Legend() {
  return (
    <ul aria-label="Marker legend" className="pointer-events-none absolute bottom-7 right-3 flex flex-col gap-1.5 rounded-input border border-line bg-ink-0/85 px-3 py-2 text-xs text-bone-2">
      <li className="flex items-center gap-2"><TierShape tier="high_trust" size={14} /> High</li>
      <li className="flex items-center gap-2"><TierShape tier="medium_trust" size={14} /> Medium</li>
      <li className="flex items-center gap-2"><TierShape tier="low_trust" size={14} /> Low</li>
      <li className="flex items-center gap-2"><TierShape gateTripped size={14} /> Gate tripped</li>
    </ul>
  );
}

/** What the loaded positions and records actually are, from each device's `geo_source` (ground rule 7). */
function Provenance({ devices }: { devices: { geo_source?: string | null }[] }) {
  if (devices.length === 0) return null;
  const counts = new Map<string, number>();
  for (const d of devices) counts.set(geoProvenance(d.geo_source).label, (counts.get(geoProvenance(d.geo_source).label) ?? 0) + 1);
  const seeded = devices.filter((d) => geoProvenance(d.geo_source).seeded).length;
  return (
    <p className="pointer-events-none absolute bottom-14 left-3 max-w-[34ch] rounded-chip border border-line bg-ink-0/85 px-2.5 py-1.5 text-[0.6875rem] leading-snug text-bone-2">
      Positions: {[...counts].map(([k, n]) => `${n} ${k}`).join(", ")}.{seeded > 0 ? " Seeded records, not scan results." : ""}
    </p>
  );
}

function Announcer() {
  const t = useConsoleStore((s) => s.lastGateTripAt);
  const alerts = useConsoleStore((s) => s.alerts);
  const [msg, setMsg] = React.useState("");
  const last = React.useRef(0);
  React.useEffect(() => {
    if (!t || Date.now() - last.current < 5000) return;
    last.current = Date.now();
    const a = alerts.find((x) => x.integrity_gate_tripped);
    const id = setTimeout(() => setMsg(`Gate tripped${a?.city ? ` in ${a.city}` : ""}`), 0);
    return () => clearTimeout(id);
  }, [t, alerts]);
  return <div role="status" aria-live="polite" className="sr-only">{msg}</div>;
}

export function ConsoleShell() {
  const city = useConsoleStore((s) => s.city);
  const selectedId = useConsoleStore((s) => s.selectedDeviceId);
  const select = useConsoleStore((s) => s.selectDevice);
  const query = useConsoleStore((s) => s.query);
  const devicesQ = useDevices(city);
  const selectedInCity = !!selectedId && !!devicesQ.data?.devices.some((d) => d.id === selectedId);
  const allQ = useDevices("All India", !!selectedId && devicesQ.isSuccess && !selectedInCity);
  const [pane, setPane] = React.useState<Pane>("map");
  const [palette, setPalette] = React.useState(false);
  const [analytics, setAnalytics] = React.useState(false);
  const [heatOn, setHeatOn] = React.useState(false);
  const [zoneMode, setZoneMode] = React.useState(false);
  const [zone, setZone] = React.useState<Zone | null>(null);
  const [focus, setFocus] = React.useState<{ center: [number, number]; zoom: number; key: number }>({ ...CITY_VIEW["Mumbai"]!, key: 0 });
  const [runMsg, setRunMsg] = React.useState<string | null>(null);
  const run = useRunScenario();
  const heat = useHeat(city, heatOn);

  const devices = React.useMemo(() => {
    const all = devicesQ.data?.devices ?? [];
    if (!query) return all;
    const text = query.text?.toLowerCase();
    return all.filter((d) =>
      (!query.ownerType || d.owner_type === query.ownerType) &&
      (query.authRequired === null || !!d.auth_required === query.authRequired) &&
      (query.hasCve === null || ((d.known_cve_count ?? 0) > 0) === query.hasCve) &&
      (!text || `${d.manufacturer ?? ""} ${d.device_type ?? ""} ${d.owner_type ?? ""} ${d.id}`.toLowerCase().includes(text)));
  }, [devicesQ.data, query]);

  // fly to the city when it changes
  React.useEffect(() => {
    const v = CITY_VIEW[city] ?? CITY_VIEW["All India"]!;
    const id = setTimeout(() => setFocus((f) => ({ ...v, key: f.key + 1 })), 0);
    return () => clearTimeout(id);
  }, [city]);

  // fly to a selected device and show its details
  React.useEffect(() => {
    if (!selectedId) return;
    const d = devicesQ.data?.devices.find((x) => x.id === selectedId) ?? allQ.data?.devices.find((x) => x.id === selectedId);
    const id = setTimeout(() => {
      setPane((p) => (p === "map" || p === "stream" ? "detail" : p));
      if (d) setFocus((f) => ({ center: [d.lon, d.lat], zoom: Math.max(13, city === "All India" ? 13 : 13), key: f.key + 1 }));
    }, 0);
    return () => clearTimeout(id);
  }, [selectedId, devicesQ.data, allQ.data, city]);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((o) => !o); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function runScenario() {
    setRunMsg(null);
    try {
      const r = await run.mutateAsync();
      setRunMsg(r.message ?? `${r.events} demo events started`);
    } catch (e) {
      setRunMsg(e instanceof ApiError ? `${e.status === 0 ? "Offline" : e.status}: ${e.detail}` : "Could not start the scenario");
    }
  }

  const offline = devicesQ.error instanceof ApiError && devicesQ.error.offline;
  const segs: [Pane, string][] = [["map", "Map"], ["stream", "Stream"], ["detail", "Detail"]];

  return (
    <div data-console className="flex h-dvh flex-col bg-ink-0">
      <LiveConnection />
      <Announcer />
      <TopBar onRun={runScenario} running={run.isPending} onAnalytics={() => setAnalytics(true)} onPalette={() => setPalette(true)} runMessage={runMsg} />
      {runMsg && <p role="status" className="border-b border-line bg-ink-1 px-3 py-1.5 text-xs text-bone-2 lg:hidden">{runMsg}</p>}

      <div role="tablist" aria-label="Console panes" className="flex gap-1 border-b border-line p-2 xl:hidden">
        {segs.map(([k, label]) => (
          <button key={k} role="tab" type="button" aria-selected={pane === k} onClick={() => setPane(k)} className={cn("h-9 flex-1 rounded-full text-sm text-bone-2 transition-colors duration-[160ms]", pane === k && "bg-ink-3 text-bone")}>{label}</button>
        ))}
      </div>

      <main id="main" className="grid min-h-0 flex-1 xl:grid-cols-[minmax(300px,3fr)_minmax(0,6fr)_minmax(320px,3fr)]">
        <div className={cn("min-h-0 border-r border-line xl:flex xl:flex-col", pane === "stream" ? "flex flex-col" : "hidden")}>
          <AlertStream className="min-h-0 flex-1" />
        </div>

        <div className={cn("relative min-h-0 xl:block", pane === "map" ? "block" : "hidden")}>
          {offline ? (
            <div className="grid size-full place-items-center p-5"><OfflineState className="max-w-xl" /></div>
          ) : devicesQ.error ? (
            <div className="p-5"><InlineError title="Devices could not be loaded">{devicesQ.error instanceof ApiError ? devicesQ.error.detail : "Unexpected error"}</InlineError></div>
          ) : (
            <MapView devices={devices} selectedId={selectedId} onSelect={select} view={focus} flyKey={focus.key} heat={heatOn ? heat.data ?? null : null}
              zoneMode={zoneMode} zone={zone} onZone={(z) => { setZone(z); setZoneMode(false); if (z) setPane("detail"); }} label="Map of exposed devices" />
          )}
          {!offline && (
            <div className="absolute left-3 top-3 flex flex-wrap items-center gap-2">
              <button type="button" aria-pressed={heatOn} onClick={() => setHeatOn((h) => !h)} className={cn("h-8 rounded-full border border-line bg-ink-1/90 px-3 text-xs text-bone-2 hover:text-bone", heatOn && "border-signal/60 bg-signal-dim text-bone")}>Heat</button>
              <button type="button" aria-pressed={zoneMode} onClick={() => setZoneMode((z) => !z)} className={cn("h-8 rounded-full border border-line bg-ink-1/90 px-3 text-xs text-bone-2 hover:text-bone", zoneMode && "border-signal/60 bg-signal-dim text-bone")}>{zoneMode ? "Drag on the map" : "Draw zone"}</button>
              {query && <button type="button" onClick={() => useConsoleStore.getState().setQuery(null)} className="h-8 rounded-full border border-signal/50 bg-signal-dim px-3 text-xs text-bone" title={query.explanation}>Filtered: {query.parsedByAi ? "parsed query" : "text"} (clear)</button>}
              {devicesQ.isPending && <span className="text-xs text-bone-2">Loading devices</span>}
              {devicesQ.isSuccess && devices.length === 0 && <span className="rounded-input border border-line bg-ink-1/90 px-3 py-1.5 text-xs text-bone-2">No devices match.</span>}
            </div>
          )}
          <Legend />
          {!offline && <Provenance devices={devices} />}
        </div>

        <aside aria-label="Detail" className={cn("min-h-0 overflow-y-auto border-l border-line xl:block", pane === "detail" ? "block" : "hidden")}>
          {zone ? (
            <ZoneBrief zone={zone} devices={devicesQ.data?.devices ?? []} city={city} onClear={() => setZone(null)} />
          ) : selectedId ? (
            <Inspector deviceId={selectedId} city={city} />
          ) : (
            <div className="p-4"><EmptyState title="Nothing selected.">Select a device on the map or in the stream to inspect its score, gate and audit trail.</EmptyState></div>
          )}
        </aside>
      </main>

      <AnalyticsDrawer open={analytics} onOpenChange={setAnalytics} />
      <CommandPalette open={palette} onOpenChange={setPalette} devices={devicesQ.data?.devices ?? []}
        actions={{ runScenario, openAnalytics: () => setAnalytics(true), toggleHeat: () => setHeatOn((h) => !h), toggleZone: () => setZoneMode((z) => !z) }} />
    </div>
  );
}
