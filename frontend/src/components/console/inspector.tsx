"use client";
import * as React from "react";
import Link from "next/link";
import { scaleLinear } from "d3-scale";
import { line } from "d3-shape";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { TierTag } from "@/components/ui/tier-tag";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { InlineError } from "@/components/ui/inline-error";
import { OfflineState } from "@/components/ui/offline-state";
import { Skeleton } from "@/components/ui/skeleton";
import { DemoTag } from "@/components/ui/demo-tag";
import { GateCurve } from "@/components/lab/gate-explorer";
import { maskIp } from "@/lib/api/mask-ip";
import { geoProvenance, prettifyFactor } from "@/lib/api/normalize";
import { ApiError } from "@/lib/api/errors";
import { useDevices, useThresholds, useTrustScore } from "@/lib/api/hooks";
import { useAuditTrail, useDecay, useVerdict } from "@/lib/api/console-hooks";
import { useConsoleStore } from "@/lib/state/console-store";
import { fact } from "@/lib/content/facts";
import { ROUTES } from "@/lib/constants/routes";
import { cn } from "@/lib/utils";

function Sec({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section aria-label={title} className={cn("flex flex-col gap-3 border-t border-line pt-4", className)}>
      <h3 className="text-sm font-medium text-bone">{title}</h3>
      {children}
    </section>
  );
}

function Skel() {
  return <div className="flex flex-col gap-2" aria-hidden="true"><Skeleton className="h-4 w-1/2" /><Skeleton className="h-8 w-full" /></div>;
}

function QueryState({ q, children, empty }: { q: { isPending: boolean; error: unknown; data: unknown }; children: React.ReactNode; empty?: string }) {
  if (q.isPending) return <Skel />;
  if (q.error instanceof ApiError && q.error.offline) return <OfflineState detail={q.error.detail} />;
  if (q.error) return <InlineError title="Could not load this section">{q.error instanceof ApiError ? q.error.detail : "Unexpected error"}</InlineError>;
  if (!q.data && empty) return <p className="text-sm text-bone-2">{empty}</p>;
  return <>{children}</>;
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return <div className="flex items-baseline justify-between gap-4 border-b border-line py-1.5 text-sm"><dt className="text-bone-2">{k}</dt><dd className="num text-right text-bone">{v}</dd></div>;
}

function ModelBars({ rows }: { rows: [string, number][] }) {
  return (
    <ul className="flex flex-col gap-2">
      {rows.map(([k, v]) => (
        <li key={k} className="grid grid-cols-[8.5rem_1fr_auto] items-center gap-3 text-xs text-bone-2">
          <span>{k}</span>
          <span className="h-2 overflow-hidden rounded-full bg-ink-3" aria-hidden="true"><span className={cn("block h-full rounded-full", k.startsWith("IG-DCTF") ? "bg-signal" : "bg-bone-3")} style={{ width: `${Math.max(0, Math.min(100, v))}%` }} /></span>
          <span className="num text-sm text-bone">{Math.round(v)}</span>
        </li>
      ))}
    </ul>
  );
}

function DecayChart({ series }: { series: { hour: number; score: number }[] }) {
  const W = 340, H = 150, m = { l: 30, r: 8, t: 8, b: 22 };
  const x = scaleLinear().domain([0, Math.max(...series.map((s) => s.hour), 1)]).range([m.l, W - m.r]);
  const y = scaleLinear().domain([0, 100]).range([H - m.b, m.t]);
  const d = line<{ hour: number; score: number }>().x((s) => x(s.hour)).y((s) => y(s.score))(series) ?? "";
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Trust score decay over hours since the scan" className="w-full">
      {[0, 50, 100].map((v) => <g key={v}><line x1={m.l} x2={W - m.r} y1={y(v)} y2={y(v)} stroke="var(--line)" /><text x={m.l - 5} y={y(v) + 3} textAnchor="end" fontSize="9" className="num" fill="var(--bone-2)">{v}</text></g>)}
      <path d={d} fill="none" stroke="var(--signal)" strokeWidth="1.6" />
      <text x={W - m.r} y={H - 6} textAnchor="end" fontSize="9" fill="var(--bone-2)">hours since scan</text>
    </svg>
  );
}

export function Inspector({ deviceId, city, wide = false, className }: { deviceId: string; city: string; wide?: boolean; className?: string }) {
  const cityDevices = useDevices(city);
  const inCity = !!cityDevices.data?.devices.some((d) => d.id === deviceId);
  const allDevices = useDevices("All India", cityDevices.isSuccess && !inCity);
  const ts = useTrustScore(deviceId);
  const decay = useDecay(deviceId);
  const trail = useAuditTrail(deviceId);
  const { thresholds } = useThresholds();
  const alerts = useConsoleStore((s) => s.alerts);
  const verdict = useVerdict();
  const device = cityDevices.data?.devices.find((d) => d.id === deviceId) ?? allDevices.data?.devices.find((d) => d.id === deviceId);
  const latest = alerts.find((a) => a.camera_id === deviceId);
  const t1 = fact("method.tier1");

  if (ts.error instanceof ApiError && ts.error.status === 404) {
    return (
      <div className={cn("flex flex-col gap-3 p-4", className)}>
        <p className="font-medium">Device not in the database</p>
        <p className="text-sm text-bone-2">The alert refers to a device identifier that is not stored (<span className="num">{deviceId.slice(0, 14)}</span>). Simulator events use identifiers like this.</p>
      </div>
    );
  }

  const s = ts.data;
  const gateTripped = s?.integrity_gate_tripped ?? false;
  const basis = device?.trust_score_basis?.startsWith("static") ? "static posture" : s ? "on demand" : "";

  return (
    <div className={cn("flex flex-col gap-5 p-4", className)}>
      <header className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 flex-col gap-1.5">
          <p className="num truncate text-lg text-bone">{maskIp(device?.ip)}</p>
          <p className="text-sm text-bone-2">{device?.manufacturer ?? "Unknown manufacturer"} · {device?.device_type ?? "device"}</p>
          <p className="text-sm text-bone-2">{device?.owner_org ?? device?.org ?? "Unknown owner"} · {device?.owner_type ?? "unknown"}{device?.ownership_confidence ? ` (${device.ownership_confidence} confidence)` : ""}</p>
          <p className="text-xs text-bone-2">City: {device?.city ?? s?.city ?? "unknown"} · {geoProvenance(device?.geo_source).label}</p>
          {device && <p className="text-xs text-bone-2">{geoProvenance(device.geo_source).note}</p>}
          {s ? <div className="mt-1 flex flex-wrap items-center gap-3"><TierTag tier={s.action_tier} gateTripped={gateTripped} score={s.trust_score} />{basis && <Badge>{basis}</Badge>}</div> : <Skeleton className="mt-1 h-5 w-40" />}
        </div>
        {s ? <HoodGauge gate={s.gate_multiplier} score={s.trust_score} size={wide ? 140 : 92} animate /> : <Skeleton className="size-20" />}
      </header>

      <div className={cn("grid gap-5", wide && "lg:grid-cols-2")}>
        <Sec title="Channel A: vulnerability posture">
          <QueryState q={ts}>
            {s && (
              <>
                <dl>
                  <Row k="Known CVEs" v={s.known_cve_count ?? 0} />
                  <Row k="Max CVSS" v={s.max_cvss ?? "none"} />
                  <Row k="Authentication" v={s.auth_required === null || s.auth_required === undefined ? "unknown (scored as open)" : s.auth_required ? "required" : "not required"} />
                  <Row k="Posture score (T_cve)" v={s.cyber_trust_score} />
                </dl>
                <ul className="flex flex-wrap gap-1.5">
                  {s.contributing_factors.map((f) => <li key={f}><Badge>{prettifyFactor(f)}</Badge></li>)}
                  {s.contributing_factors.length === 0 && <li className="text-sm text-bone-2">No contributing factors reported.</li>}
                </ul>
              </>
            )}
          </QueryState>
        </Sec>

        <Sec title="Channel B: feed authenticity">
          <QueryState q={ts}>
            {s && (
              <>
                <p className="text-xs text-bone-2">Tier 1, banner drift. Weights and the drift threshold {t1.driftThreshold.toFixed(2)} come from the scoring code.</p>
                <ul className="flex flex-col gap-1">
                  {([["Firmware", t1.weights.firmware], ["HTTP server", t1.weights.server], ["Open ports", t1.weights.ports], ["Resolution", t1.weights.resolution], ["Product string", t1.weights.product], ["Codec", t1.weights.codec]] as const).map(([k, w]) => (
                    <li key={k} className="grid grid-cols-[6.5rem_1fr_auto] items-center gap-3 text-xs text-bone-2"><span>{k}</span><span className="h-1.5 overflow-hidden rounded-full bg-ink-3" aria-hidden="true"><span className="block h-full rounded-full bg-bone-3" style={{ width: `${(w / 0.25) * 100}%` }} /></span><span className="num text-bone">{w.toFixed(2)}</span></li>
                  ))}
                </ul>
                <dl><Row k="Drift score" v={s.drift_score.toFixed(2)} /></dl>
                <p className="text-xs text-bone-2">The API returns the aggregate drift only, so the baseline and current banner values are not shown per field.</p>
                <p className="rounded-input border border-line bg-ink-1 p-3 text-sm text-bone-2">Tier 2 unavailable: no authorized footage for this device.</p>
              </>
            )}
          </QueryState>
        </Sec>

        <Sec title="Gate">
          <QueryState q={ts}>
            {s && (
              <>
                <div className="rounded-card border border-line bg-ink-1 p-2"><GateCurve s={s.signal_integrity_score} g={s.gate_multiplier} thetaLow={thresholds.gate.theta_low} thetaHigh={thresholds.gate.theta_high} /></div>
                <dl>
                  <Row k="Signal integrity s" v={s.signal_integrity_score.toFixed(2)} />
                  <Row k="Multiplier G(s)" v={s.gate_multiplier.toFixed(2)} />
                  <Row k="Gate status" v={s.gate_status.replace("_", " ")} />
                  <Row k="Hard cap" v={gateTripped ? thresholds.gate.hard_cap : "not applied"} />
                </dl>
              </>
            )}
          </QueryState>
        </Sec>

        <Sec title="Scoring models">
          <QueryState q={ts}>
            {s && <ModelBars rows={[["Weighted average", s.trust_score_wa], ["CVE-only", s.trust_score_advanced], ["Bayesian log-odds", s.trust_score_probabilistic], ["IG-DCTF", s.trust_score_ig_dctf], ["IG-DCTF, decayed", s.trust_score_decayed]]} />}
          </QueryState>
        </Sec>

        <Sec title="Decay">
          <QueryState q={decay}>
            {decay.data && (
              <>
                <DecayChart series={decay.data.decay_series} />
                <p className="num text-xs text-bone-2">{decay.data.base_score} now {decay.data.current_decayed_score} after {decay.data.hours_since_scan ?? "?"} h, half-life {decay.data.half_life_hours} h</p>
              </>
            )}
          </QueryState>
        </Sec>

        <Sec title="Audit trail">
          <QueryState q={trail}>
            {trail.data && trail.data.entries.length === 0 ? (
              <p className="text-sm text-bone-2">No ledger entries for this device yet.</p>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {trail.data?.entries.map((e, i) => (
                  <li key={e.hash ?? i} className="num truncate rounded-input border border-line bg-ink-1 px-3 py-2 text-xs text-bone-2">#{e.sequence_id} · {(e.hash ?? "").slice(0, 16)}</li>
                ))}
              </ul>
            )}
          </QueryState>
        </Sec>
      </div>

      <Sec title="Verdict">
        {latest ? (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-bone-2">Latest alert for this device: {latest.event_type.replaceAll("_", " ")} {latest.demo && <DemoTag className="ml-1" />}</p>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="secondary" disabled={verdict.isPending} onClick={() => verdict.mutate({ alertId: latest.id, verdict: "verified" })}>Verified</Button>
              <Button size="sm" variant="secondary" disabled={verdict.isPending} onClick={() => verdict.mutate({ alertId: latest.id, verdict: "false_alarm" })}>False alarm</Button>
            </div>
            {verdict.isSuccess && <p role="status" className="text-sm text-bone-2">Verdict recorded.</p>}
            {verdict.error instanceof ApiError && (
              <InlineError title="Verdict not accepted">
                {verdict.error.isForbidden ? "The backend answered " + verdict.error.status + ". A detection API key is configured and this browser has none, so verdicts are disabled." : verdict.error.detail}
              </InlineError>
            )}
          </div>
        ) : (
          <p className="text-sm text-bone-2">No alert for this device in the stream. Verdicts attach to alerts.</p>
        )}
      </Sec>

      {!wide && (
        <Button asChild variant="secondary" size="sm" className="self-start"><Link href={ROUTES.device(deviceId)}>Open forensics</Link></Button>
      )}
    </div>
  );
}
