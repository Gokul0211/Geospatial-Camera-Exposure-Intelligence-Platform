import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { maskIp } from "@/lib/api/mask-ip";
import { flattenDevices, prettifyFactor, tierLabel } from "@/lib/api/normalize";
import { AlertMessageSchema, GateTrippedMessageSchema, ThresholdsSchema, TrustScoreSchema, STATIC_THRESHOLDS } from "@/lib/api/schemas";
import { backoffDelay, parseWsFrame } from "@/lib/api/socket";
import { pushRing } from "@/lib/state/console-store";

const fx = (name: string) => JSON.parse(readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8")) as unknown;

describe("maskIp (ground rule 8)", () => {
  it("masks IPv4 to the /24 by default", () => {
    expect(maskIp("203.0.113.42")).toBe("203.0.113.•");
  });
  it("masks IPv6 to the first three groups", () => {
    expect(maskIp("2001:db8:85a3:0:0:8a2e:370:7334")).toBe("2001:db8:85a3:•");
  });
  it("reveals only when asked", () => {
    expect(maskIp("203.0.113.42", true)).toBe("203.0.113.42");
  });
  it("never echoes unparseable input", () => {
    expect(maskIp("not-an-ip")).toBe("masked");
    expect(maskIp(null)).toBe("unknown");
  });
});

describe("GeoJSON flattening (recorded from GET /api/devices)", () => {
  it("flattens every feature and keeps the enrichment fields", () => {
    const { devices, skipped } = flattenDevices(fx("devices.sample.json"));
    expect(skipped).toBe(0);
    expect(devices).toHaveLength(6);
    const d = devices[0]!;
    expect(d.trust_score_basis).toBe("static_posture_no_corroboration");
    expect(d.geo_source).toBe("synthetic_demo");
    expect(typeof d.lon).toBe("number");
    expect(["high_trust", "medium_trust", "low_trust"]).toContain(d.action_tier);
  });
  it("reports malformed features instead of dropping them silently", () => {
    const good = (fx("devices.sample.json") as { features: unknown[] }).features[0];
    const bad = { type: "Feature", geometry: { type: "Point", coordinates: [1, 2] }, properties: { id: 5 } };
    const { devices, skipped } = flattenDevices({ type: "FeatureCollection", features: [good, bad] });
    expect(devices).toHaveLength(1);
    expect(skipped).toBe(1);
  });
});

describe("response contracts", () => {
  it("thresholds fixture matches the schema and the static fallback", () => {
    expect(ThresholdsSchema.parse(fx("thresholds.json"))).toEqual(STATIC_THRESHOLDS);
  });
  it("trust-score fixture matches the schema", () => {
    const parsed = TrustScoreSchema.parse(fx("trust-score.sample.json"));
    expect(parsed.trust_score).toBe(parsed.trust_score_ig_dctf);
  });
});

describe("WebSocket contract (recorded from /api/ws/alerts)", () => {
  const messages = fx("ws-messages.json") as unknown[];
  it("parses every recorded ALERT and keeps the demo flag", () => {
    expect(messages.length).toBeGreaterThan(0);
    for (const m of messages) {
      const parsed = parseWsFrame(JSON.stringify(m));
      expect(parsed?.type).toBe("ALERT");
      expect(AlertMessageSchema.parse(m).demo).toBe(true);
    }
  });
  it("parses INTEGRITY_GATE_TRIPPED as built in backend/routes/alerts.py (not recorded: no live trip in the fixture run)", () => {
    const msg = {
      type: "INTEGRITY_GATE_TRIPPED", camera_id: "cam-1", city: "Mumbai", drift_score: 0.4, signal_integrity: 0.6,
      gate_status: "hard_gated", detected_at: "2026-10-14T00:00:00+00:00", action: "dispatch_technician_for_physical_inspection",
    };
    expect(GateTrippedMessageSchema.parse(msg).type).toBe("INTEGRITY_GATE_TRIPPED");
    expect(parseWsFrame(JSON.stringify(msg))?.type).toBe("INTEGRITY_GATE_TRIPPED");
  });
  it("ignores unknown and malformed frames", () => {
    expect(parseWsFrame("not json")).toBeNull();
    expect(parseWsFrame(JSON.stringify({ type: "SOMETHING_ELSE" }))).toBeNull();
    expect(parseWsFrame(new ArrayBuffer(2))).toBeNull();
  });
  it("backs off exponentially from 1 s to 30 s", () => {
    expect([0, 1, 2, 3, 4, 5, 6, 10].map(backoffDelay)).toEqual([1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000]);
  });
});

describe("helpers", () => {
  it("prettifies factor strings", () => {
    expect(prettifyFactor("ig_dctf_hard_gate_cap_30")).toBe("IG-DCTF hard gate cap 30");
    expect(prettifyFactor("visual_tamper:declared_spec_mismatch")).toBe("Visual tamper: declared spec mismatch");
    expect(prettifyFactor("unauthenticated_stream")).toBe("Unauthenticated stream");
  });
  it("labels tiers", () => {
    expect(tierLabel("low_trust")).toBe("Low");
    expect(tierLabel(undefined)).toBe("Unscored");
  });
  it("caps the alert ring buffer, newest first", () => {
    let buf: number[] = [];
    for (let i = 0; i < 1100; i++) buf = pushRing(buf, i, 1000);
    expect(buf).toHaveLength(1000);
    expect(buf[0]).toBe(1099);
  });
});
