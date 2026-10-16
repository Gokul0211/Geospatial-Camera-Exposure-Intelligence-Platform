import { z } from "zod";

/** Runtime schemas for what OpenAPI does not describe (spec 15.3). */

export const TierSchema = z.enum(["high_trust", "medium_trust", "low_trust"]);
export type Tier = z.infer<typeof TierSchema>;

export const GateStatusSchema = z.enum(["nominal", "tapered", "hard_gated"]);
export type GateStatus = z.infer<typeof GateStatusSchema>;

export const HealthSchema = z.object({ status: z.string(), ws_clients: z.number().optional() });

export const ThresholdsSchema = z.object({
  tiers: z.object({ high_min: z.number(), medium_min: z.number() }),
  gate: z.object({
    theta_low: z.number(),
    theta_high: z.number(),
    floor_multiplier: z.number(),
    hard_cap: z.number(),
  }),
});
export type Thresholds = z.infer<typeof ThresholdsSchema>;

/** Static constants (spec 3.1). The backend is authoritative; these are the labelled fallback. */
export const STATIC_THRESHOLDS: Thresholds = {
  tiers: { high_min: 80, medium_min: 50 },
  gate: { theta_low: 0.5, theta_high: 0.85, floor_multiplier: 0.3, hard_cap: 30 },
};

/** Properties of one GeoJSON feature from GET /api/devices, as the backend really sends them. */
export const DevicePropsSchema = z.object({
  id: z.string(),
  ip: z.string().nullable().optional(),
  lat: z.number(),
  lon: z.number(),
  device_type: z.string().nullable().optional(),
  manufacturer: z.string().nullable().optional(),
  ports: z.array(z.number()).nullable().optional(),
  owner_org: z.string().nullable().optional(),
  org: z.string().nullable().optional(),
  owner_type: z.string().nullable().optional(),
  ownership_confidence: z.string().nullable().optional(),
  first_seen: z.string().nullable().optional(),
  last_seen: z.string().nullable().optional(),
  banner_snippet: z.string().nullable().optional(),
  isp: z.string().nullable().optional(),
  geo_source: z.string().nullable().optional(),
  known_cve_count: z.number().nullable().optional(),
  auth_required: z.union([z.boolean(), z.number()]).nullable().optional(),
  // added by _enrich_with_posture
  trust_score: z.number().optional(),
  action_tier: TierSchema.optional(),
  integrity_gate_tripped: z.boolean().optional(),
  trust_score_basis: z.string().optional(),
  city: z.string().nullable().optional(),
  cves: z.array(z.string()).optional(),
  firmware_version: z.string().nullable().optional(),
});

export const DeviceCollectionSchema = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(
    z.object({
      type: z.literal("Feature"),
      geometry: z.object({ type: z.literal("Point"), coordinates: z.tuple([z.number(), z.number()]) }),
      properties: z.record(z.string(), z.unknown()),
    }),
  ),
});

/** GET /api/devices/{id}/trust-score (the authoritative on-demand score). */
export const TrustScoreSchema = z.object({
  camera_id: z.string(),
  city: z.string().nullable().optional(),
  manufacturer: z.string().nullable().optional(),
  owner_type: z.string().nullable().optional(),
  auth_required: z.union([z.boolean(), z.number()]).nullable().optional(),
  known_cve_count: z.number().nullable().optional(),
  cve_categories: z.array(z.string()).optional(),
  max_cvss: z.number().nullable().optional(),
  last_patch_date: z.string().nullable().optional(),
  trust_score_wa: z.number(),
  trust_score_advanced: z.number(),
  trust_score_probabilistic: z.number(),
  trust_score_ig_dctf: z.number(),
  trust_score_decayed: z.number(),
  trust_score: z.number(),
  cyber_trust_score: z.number(),
  action_tier: TierSchema,
  contributing_factors: z.array(z.string()),
  probabilistic_factors: z.array(z.string()).optional(),
  decay_factor: z.number().optional(),
  hours_since_scan: z.number().nullable().optional(),
  corroborating_cameras: z.array(z.string()).optional(),
  signal_integrity_score: z.number(),
  drift_score: z.number(),
  integrity_gate_tripped: z.boolean(),
  gate_status: GateStatusSchema,
  gate_multiplier: z.number(),
});
export type TrustScore = z.infer<typeof TrustScoreSchema>;

/** WebSocket messages on /api/ws/alerts. Verified against backend/routes/alerts.py. */
export const AlertMessageSchema = z.object({
  type: z.literal("ALERT"),
  id: z.string(),
  camera_id: z.string(),
  city: z.string().nullable().optional(),
  event_type: z.string(),
  trust_score: z.number(),
  action_tier: TierSchema,
  contributing_factors: z.array(z.string()).default([]),
  corroborated_by: z.array(z.string()).default([]),
  detected_at: z.string(),
  probabilistic_score: z.number().nullable().optional(),
  decayed_score: z.number().nullable().optional(),
  signal_integrity_score: z.number().nullable().optional(),
  drift_score: z.number().nullable().optional(),
  integrity_gate_tripped: z.boolean().optional(),
  gate_status: z.string().nullable().optional(),
  cyber_trust_score: z.number().nullable().optional(),
  velocity_suspicious: z.boolean().optional(),
  demo: z.boolean().default(false),
});
export type AlertMessage = z.infer<typeof AlertMessageSchema>;

export const GateTrippedMessageSchema = z.object({
  type: z.literal("INTEGRITY_GATE_TRIPPED"),
  camera_id: z.string(),
  city: z.string().nullable().optional(),
  drift_score: z.number().nullable().optional(),
  signal_integrity: z.number().nullable().optional(),
  gate_status: z.string().nullable().optional(),
  detected_at: z.string(),
  action: z.string().optional(),
});
export type GateTrippedMessage = z.infer<typeof GateTrippedMessageSchema>;

export const WsMessageSchema = z.discriminatedUnion("type", [AlertMessageSchema, GateTrippedMessageSchema]);
export type WsMessage = z.infer<typeof WsMessageSchema>;

/** SSE messages on POST /api/brief/stream. */
export const BriefStreamMessageSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("text"), content: z.string() }),
  z.object({ type: z.literal("chunk"), content: z.string() }),
  z.object({ type: z.literal("done"), risk_level: z.string().optional() }),
  z.object({ type: z.literal("error"), message: z.string() }),
]);
export type BriefStreamMessage = z.infer<typeof BriefStreamMessageSchema>;
