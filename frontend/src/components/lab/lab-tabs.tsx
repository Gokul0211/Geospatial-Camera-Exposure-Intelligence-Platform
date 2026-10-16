"use client";
import * as React from "react";
import { GateExplorer } from "@/components/lab/gate-explorer";
import { LiveConnection } from "@/components/console/live-connection";
import { Button } from "@/components/ui/button";
import { CodeBlock } from "@/components/ui/code-block";
import { DemoTag } from "@/components/ui/demo-tag";
import { InlineError } from "@/components/ui/inline-error";
import { OfflineState } from "@/components/ui/offline-state";
import { TierTag } from "@/components/ui/tier-tag";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError } from "@/lib/api/errors";
import { SIMULATORS, useNlQuery, useRunScenario, useSimulate } from "@/lib/api/console-hooks";
import { useConsoleStore } from "@/lib/state/console-store";

function Simulators() {
  const sim = useSimulate();
  const [active, setActive] = React.useState<string | null>(null);
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
      <ul className="flex flex-col gap-3">
        {SIMULATORS.map((s) => (
          <li key={s.id} className="flex items-center justify-between gap-4 rounded-card border border-line bg-ink-1 p-4">
            <div><p className="font-medium">{s.label}</p><p className="text-sm text-bone-2">{s.note}</p></div>
            <Button size="sm" variant="secondary" disabled={sim.isPending} onClick={() => { setActive(s.id); sim.mutate(s.id); }}>Run</Button>
          </li>
        ))}
      </ul>
      <div className="flex min-w-0 flex-col gap-3" aria-live="polite">
        <div className="flex items-center gap-2"><DemoTag /><span className="text-sm text-bone-2">{active ? `POST /api/simulate/${active}` : "Run a simulator to see the backend's answer."}</span></div>
        {sim.data && <CodeBlock label={`HTTP ${sim.data.status}`} code={JSON.stringify(sim.data.body, null, 2)} />}
        {sim.error instanceof ApiError && (sim.error.offline ? <OfflineState /> : <InlineError title={`HTTP ${sim.error.status}`}>{sim.error.detail}</InlineError>)}
      </div>
    </div>
  );
}

function Scenario() {
  const run = useRunScenario();
  const alerts = useConsoleStore((s) => s.alerts).filter((a) => a.demo).slice(0, 8);
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
      <div className="flex flex-col gap-3 rounded-card border border-line bg-ink-1 p-5">
        <p className="font-medium">Twelve synthetic events, two seconds apart</p>
        <p className="text-sm text-bone-2">Events stream in over the WebSocket, each flagged demo. A 409 means a replay is already running.</p>
        <Button className="self-start" disabled={run.isPending} onClick={() => run.mutate()}>Run scenario</Button>
        {run.data && <p role="status" className="text-sm text-bone-2">{run.data.message ?? `${run.data.events} events started`}</p>}
        {run.error instanceof ApiError && (run.error.offline ? <OfflineState /> : <InlineError title={`HTTP ${run.error.status}`}>{run.error.detail}</InlineError>)}
      </div>
      <ul className="flex flex-col gap-2" aria-live="polite" aria-label="Streamed demo alerts">
        {alerts.length === 0 && <li className="rounded-card border border-line bg-ink-1 p-5 text-sm text-bone-2">No demo alerts yet. Run the scenario.</li>}
        {alerts.map((a) => (
          <li key={a.id} className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-line bg-ink-1 px-4 py-3 text-sm">
            <span className="flex items-center gap-3"><TierTag tier={a.action_tier} gateTripped={!!a.integrity_gate_tripped} demo /><span className="text-bone-2">{a.event_type.replaceAll("_", " ")}</span></span>
            <span className="flex items-center gap-3"><span className="num">{a.trust_score}</span><DemoTag /></span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function NlQuery() {
  const nl = useNlQuery();
  const [q, setQ] = React.useState("");
  const filters = nl.data ? ([["Owner type", nl.data.owner_type], ["Authentication required", nl.data.auth_required], ["Has CVE", nl.data.has_cve], ["City", nl.data.city], ["Search text", nl.data.search_text]] as const) : [];
  return (
    <div className="flex max-w-3xl flex-col gap-5">
      <form onSubmit={(e) => { e.preventDefault(); if (q.trim()) nl.mutate({ query: q }); }} className="flex flex-col gap-3 sm:flex-row">
        <label htmlFor="nlq" className="sr-only">Query in plain language</label>
        <input id="nlq" value={q} onChange={(e) => setQ(e.target.value)} placeholder="government cameras with no authentication in Mumbai" className="h-12 flex-1 rounded-input border border-line-strong bg-ink-2 px-4 text-bone placeholder:text-bone-3" />
        <Button type="submit" disabled={nl.isPending || !q.trim()}>{nl.isPending ? "Asking" : "Ask"}</Button>
      </form>
      <div aria-live="polite" className="flex flex-col gap-3">
        {nl.data && (
          <>
            <p className="text-sm text-bone-2">{nl.data.parsed_by_ai ? "Parsed by a language model." : "No model key is configured, so this fell back to plain text search."} {nl.data.explanation}</p>
            <dl className="grid gap-x-8 gap-y-1 sm:grid-cols-2">{filters.map(([k, v]) => <div key={k} className="flex justify-between gap-4 border-b border-line py-1.5 text-sm"><dt className="text-bone-2">{k}</dt><dd className="num">{v === null || v === undefined ? "not set" : String(v)}</dd></div>)}</dl>
          </>
        )}
        {nl.error instanceof ApiError && (nl.error.offline ? <OfflineState /> : <InlineError title={`HTTP ${nl.error.status}`}>{nl.error.detail}</InlineError>)}
      </div>
    </div>
  );
}

export function LabTabs() {
  return (
    <Tabs defaultValue="explorer" className="flex flex-col gap-8">
      <LiveConnection />
      <TabsList aria-label="Lab tools" className="self-start">
        <TabsTrigger value="explorer">Gate explorer</TabsTrigger>
        <TabsTrigger value="attacks">Attack simulators</TabsTrigger>
        <TabsTrigger value="scenario">Scenario replay</TabsTrigger>
        <TabsTrigger value="nlq">Natural-language query</TabsTrigger>
      </TabsList>
      <TabsContent value="explorer"><GateExplorer /></TabsContent>
      <TabsContent value="attacks"><Simulators /></TabsContent>
      <TabsContent value="scenario"><Scenario /></TabsContent>
      <TabsContent value="nlq"><NlQuery /></TabsContent>
    </Tabs>
  );
}
