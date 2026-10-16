"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { fetchJson } from "./client";
import { API_BASE } from "./config";
import { ApiError, detailFrom } from "./errors";

const loose = <T extends z.ZodRawShape>(shape: T) => z.looseObject(shape);
const num = z.number().nullable().optional();

export const StatsSchema = loose({
  city: z.string().nullable().optional(),
  total_devices: z.number(),
  by_type: z.record(z.string(), z.number()).optional(),
  by_owner: z.record(z.string(), z.number()).optional(),
  top_manufacturer: z.string().nullable().optional(),
});
export const SummarySchema = loose({
  device_count: z.number(),
  total_alerts_24h: z.number(),
  alert_tiers_24h: z.record(z.string(), z.number()).optional(),
  audit_chain_length: z.number().optional(),
  audit_chain_valid: z.boolean().optional(),
});
export const HeatSchema = loose({ points: z.array(z.tuple([z.number(), z.number(), z.number()])) });
export const AlertHistorySchema = loose({
  alerts: z.array(loose({
    id: z.string(), camera_id: z.string(), city: z.string().nullable().optional(), event_type: z.string(),
    detected_at: z.string(), trust_score: z.number(), contributing_factors: z.array(z.string()).optional(),
    corroborated_by: z.array(z.string()).optional(), action_tier: z.string(), probabilistic_score: num, decayed_score: num,
    integrity_gate_tripped: z.union([z.boolean(), z.number()]).nullable().optional(), gate_status: z.string().nullable().optional(),
    operator_verdict: z.string().nullable().optional(), signal_integrity_score: num, drift_score: num, is_demo: z.union([z.boolean(), z.number()]).nullable().optional(), demo: z.union([z.boolean(), z.number()]).nullable().optional(),
  })),
});
export const TrustDistSchema = loose({
  total_alerts: z.number(),
  tiers: z.record(z.string(), z.number()),
  averages: z.record(z.string(), z.number().nullable()).optional(),
});
export const TimelineSchema = loose({
  total_alerts: z.number(),
  timeline: z.array(loose({ hour: z.string(), count: z.number(), high_trust: z.number(), medium_trust: z.number(), low_trust: z.number() })),
});
export const IntegritySchema = loose({
  total_devices: z.number(),
  // absent when the database holds no devices (the backend returns only a message then)
  gate_distribution: z.record(z.string(), z.number()).optional(),
  drift_stats: loose({ mean_drift_score: z.number(), max_drift_score: z.number(), anomalous_count: z.number(), anomalous_fraction: z.number() }).optional(),
  top_drifting_devices: z.array(loose({})).optional(),
});
export const AuditStatsSchema = loose({ chain_length: z.number(), head_hash: z.string(), chain_valid: z.boolean(), integrity_message: z.string().optional() });
export const AuditVerifySchema = loose({ valid: z.boolean(), chain_length: z.number(), head_hash: z.string().nullable().optional(), message: z.string() });
export const LedgerSchema = loose({ entries: z.array(loose({ sequence_id: z.number(), hash: z.string(), previous_hash: z.string(), payload: loose({}) })) });
export const EvalLiveSchema = loose({ total_labelled: z.number(), message: z.string().optional(), precision: num, recall: num, f1_score: num, accuracy: num });
export const NewsSchema = loose({ articles: z.array(loose({ id: z.string(), title: z.string(), source: z.string().optional(), city: z.string().optional() })) });
export const DecaySchema = loose({
  base_score: z.number(), current_decayed_score: z.number(), hours_since_scan: z.number().nullable().optional(), half_life_hours: z.number(),
  decay_series: z.array(loose({ hour: z.number(), score: z.number() })),
});
export const AuditTrailSchema = loose({ entries: z.array(loose({ sequence_id: z.number().optional(), hash: z.string().optional(), payload: loose({}).optional() })), count: z.number() });
export const NlQuerySchema = loose({
  auth_required: z.boolean().nullable().optional(), has_cve: z.boolean().nullable().optional(), owner_type: z.string().nullable().optional(),
  city: z.string().nullable().optional(), search_text: z.string().nullable().optional(), explanation: z.string().optional(), parsed_by_ai: z.boolean().optional(),
});

/** stats, news and heatmap default to Mumbai when `city` is missing, and "All India" is a valid value for them. */
const cityParam = (city: string) => `?city=${encodeURIComponent(city || "All India")}`;
const q = <S extends z.ZodType>(key: unknown[], path: string, schema: S, opts: { refetch?: number; enabled?: boolean } = {}) =>
  ({ queryKey: key, queryFn: () => fetchJson(path, schema), retry: false, refetchInterval: opts.refetch, enabled: opts.enabled ?? true, staleTime: 15_000 });

export const useStats = (city: string) => useQuery(q(["stats", city], `/api/stats${cityParam(city)}`, StatsSchema, { refetch: 30_000 }));
export const useSummary = () => useQuery(q(["summary"], "/api/analytics/summary", SummarySchema, { refetch: 20_000 }));
export const useAlertHistory = () => useQuery(q(["alert-history"], "/api/alerts?limit=100", AlertHistorySchema));
export const useTrustDist = () => useQuery(q(["trust-dist"], "/api/analytics/trust-distribution", TrustDistSchema, { refetch: 30_000 }));
export const useTimeline = () => useQuery(q(["timeline"], "/api/analytics/alert-timeline", TimelineSchema, { refetch: 30_000 }));
export const useIntegrity = () => useQuery(q(["integrity"], "/api/integrity/stats", IntegritySchema));
export const useAuditStats = () => useQuery(q(["audit-stats"], "/api/audit/stats", AuditStatsSchema));
export const useLedger = () => useQuery(q(["ledger"], "/api/audit/ledger?limit=12", LedgerSchema));
export const useEvalLive = () => useQuery(q(["eval-live"], "/api/eval/live", EvalLiveSchema));
export const useNews = (city: string) => useQuery(q(["news", city], `/api/news${cityParam(city)}`, NewsSchema));
export const useDecay = (id: string | null) => useQuery(q(["decay", id], `/api/decay-curve?camera_id=${encodeURIComponent(id ?? "")}`, DecaySchema, { enabled: !!id }));
export const useAuditTrail = (id: string | null) => useQuery(q(["audit-trail", id], `/api/devices/${encodeURIComponent(id ?? "")}/audit-trail?limit=20`, AuditTrailSchema, { enabled: !!id }));

/** Heat points arrive as [lat, lon, weight]; MapLibre wants [lon, lat, weight]. */
export function useHeat(city: string, enabled: boolean) {
  return useQuery({
    ...q(["heat", city], `/api/heatmap${cityParam(city)}`, HeatSchema, { enabled }),
    select: (d) => d.points.map(([lat, lon, w]) => [lon, lat, w] as [number, number, number]),
  });
}

async function post<S extends z.ZodType>(path: string, body: unknown, schema: S) {
  return fetchJson(path, schema, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export const useRunScenario = () => useMutation({ mutationFn: () => post("/api/scenarios/run", { scenario: "default" }, loose({ events: z.number(), interval_seconds: z.number(), message: z.string().optional() })) });
export const useNlQuery = () => useMutation({ mutationFn: (v: { query: string; city?: string }) => post("/api/nl-query", { query: v.query, current_city: v.city && v.city !== "All India" ? v.city : null }, NlQuerySchema) });
export const useVerifyChain = () => useMutation({ mutationFn: () => fetchJson("/api/audit/verify", AuditVerifySchema) });

export const SIMULATORS = [
  { id: "replay-attack", label: "Replay attack", note: "Re-sends the same idempotency key" },
  { id: "timestamp-skew", label: "Timestamp skew", note: "Sends an event outside the freshness window" },
  { id: "rate-flood", label: "Rate flood", note: "Sends events faster than the per-camera limit" },
  { id: "collusion-ring", label: "Collusion ring", note: "A group of devices corroborating each other" },
  { id: "reset", label: "Reset", note: "Clears simulator state" },
] as const;

/** Shows the real response, status code included, for the lab (spec 12). */
export const useSimulate = () =>
  useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`${API_BASE}/api/simulate/${id}`, { method: "POST" });
      const text = await res.text();
      let body: unknown = text;
      try { body = JSON.parse(text); } catch { /* keep text */ }
      if (!res.ok) throw new ApiError(res.status, detailFrom(body, res.statusText));
      return { status: res.status, body };
    },
  });

export type VerdictInput = { alertId: string; verdict: "verified" | "false_alarm"; notes?: string };
export const useVerdict = () =>
  useMutation({
    mutationFn: async (v: VerdictInput) => {
      const res = await fetch(`${API_BASE}/api/alerts/${encodeURIComponent(v.alertId)}/verdict`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ verdict: v.verdict, notes: v.notes ?? null }),
      });
      const body: unknown = await res.json().catch(() => undefined);
      if (!res.ok) throw new ApiError(res.status, detailFrom(body, res.statusText));
      return body;
    },
  });
