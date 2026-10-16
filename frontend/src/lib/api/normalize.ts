import { DeviceCollectionSchema, DevicePropsSchema } from "./schemas";
import type { z } from "zod";

export type DeviceProps = z.infer<typeof DevicePropsSchema>;

/** A flattened device. `lon`/`lat` come from the geometry, which is authoritative. */
export interface Device extends Omit<DeviceProps, "lat" | "lon"> {
  lon: number;
  lat: number;
}

export interface FlattenResult {
  devices: Device[];
  /** Features that failed validation. Reported, never silently dropped. */
  skipped: number;
}

/** Flatten the GeoJSON FeatureCollection from GET /api/devices into Device records. */
export function flattenDevices(json: unknown): FlattenResult {
  const collection = DeviceCollectionSchema.parse(json);
  const devices: Device[] = [];
  let skipped = 0;
  for (const feature of collection.features) {
    const [lon, lat] = feature.geometry.coordinates;
    const props = DevicePropsSchema.safeParse({ ...feature.properties, lat, lon });
    if (!props.success) {
      skipped += 1;
      continue;
    }
    devices.push({ ...props.data, lon, lat });
  }
  return { devices, skipped };
}

const ACRONYMS: Record<string, string> = {
  cve: "CVE", cvss: "CVSS", kev: "KEV", cisa: "CISA", ig: "IG", dctf: "DCTF", epss: "EPSS",
  ip: "IP", nvd: "NVD", rtsp: "RTSP", dvr: "DVR", nvr: "NVR", http: "HTTP", cctv: "CCTV",
};

/**
 * Make a backend factor string readable: `ig_dctf_hard_gate_cap_30` -> `IG-DCTF hard gate cap 30`,
 * `visual_tamper:quality_drift_0.55` -> `Visual tamper: quality drift 0.55`.
 */
export function prettifyFactor(factor: string): string {
  const withDctf = factor.replace(/ig_dctf/gi, "IG-DCTF");
  const [head, ...rest] = withDctf.split(":");
  const words = (s: string) =>
    s
      .split(/[_\s]+/)
      .filter(Boolean)
      .map((w) => ACRONYMS[w.toLowerCase()] ?? w)
      .join(" ");
  const phrase = rest.length ? `${words(head ?? "")}: ${words(rest.join(":"))}` : words(head ?? "");
  return phrase.charAt(0).toUpperCase() + phrase.slice(1);
}

/** Tier label for display. Shape + text carry meaning; colour never does alone (spec 5.1). */
export function tierLabel(tier: string | undefined): "High" | "Medium" | "Low" | "Unscored" {
  switch (tier) {
    case "high_trust":
      return "High";
    case "medium_trust":
      return "Medium";
    case "low_trust":
      return "Low";
    default:
      return "Unscored";
  }
}

export interface Provenance {
  /** Short name of where the position comes from. */
  label: string;
  /** One sentence for popups and the inspector. */
  note: string;
  /** True when the device record itself (CVEs, owner, authentication) is seeded rather than scanned. */
  seeded: boolean;
}

/**
 * What `geo_source` honestly says. It describes the POSITION; for the two seeded sources the rest of
 * the record is also not scan output (scripts/enrich_real_camera_locations.py, scripts/seed_demo_data.py).
 */
export function geoProvenance(source: string | null | undefined): Provenance {
  switch (source) {
    case "shodan_live":
      return { label: "IP geolocation", note: "Estimated position from scanner IP geolocation.", seeded: false };
    case "osm_verified":
      return { label: "OpenStreetMap camera node", note: "Position is a mapped camera node (OpenStreetMap). The device record is seeded from the CVE catalog, not scanned.", seeded: true };
    case "synthetic_demo":
      return { label: "Simulated", note: "Simulated position and record (demo data).", seeded: true };
    default:
      return { label: "Unknown source", note: "The backend did not say where this position comes from.", seeded: false };
  }
}
