import { layers, namedFlavor, type Flavor } from "@protomaps/basemaps";
import type { StyleSpecification } from "maplibre-gl";

/**
 * Protomaps flavour in the COBRA-WATCH palette (spec 10.2): land ink-1, water ink-0, roads and
 * boundaries as bone hairlines at 6 to 14%, labels bone-3, no POI icons. Every colour below is a
 * token from tokens.css; no other hue is used.
 */
const INK_0 = "#0a0c0b";
const INK_0_WATER = "#070908";
const LAND = "#151917"; // between ink-1 and ink-2: coastlines need more contrast than ink-1 on ink-0 gives
const BONE_3 = "#6e746c";
const bone = (a: number) => `rgba(231,234,227,${a})`;
const NONE = "rgba(0,0,0,0)";

function recolour(key: string): string {
  if (key === "water") return INK_0_WATER;
  if (key === "background") return INK_0;
  if (/casing/.test(key)) return NONE;
  if (/label.*halo|halo/.test(key)) return INK_0;
  if (/label/.test(key)) return BONE_3;
  if (key === "boundaries") return bone(0.14);
  if (key === "buildings") return bone(0.04);
  if (key === "railway") return bone(0.1);
  if (/highway|major/.test(key)) return bone(0.14);
  if (/link/.test(key)) return bone(0.1);
  if (/minor|other|service|pedestrian|pier|runway/.test(key)) return bone(0.07);
  return LAND; // earth, parks, woods, industrial, sand ... all land is one tone
}

export function cobraFlavor(): Flavor {
  const base = namedFlavor("dark");
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(base)) {
    if (typeof v === "string") out[k] = recolour(k);
    else if (k === "pois" && v) out[k] = Object.fromEntries(Object.keys(v).map((p) => [p, BONE_3]));
    else if (k === "landcover" && v) out[k] = Object.fromEntries(Object.keys(v).map((p) => [p, LAND]));
  }
  return out as unknown as Flavor;
}

/**
 * Build the MapLibre style. `origin` makes glyph URLs absolute (workers cannot resolve relative
 * ones). All requests go to our own origin: tiles via pmtiles://, fonts from /map/fonts, so a pan or
 * zoom makes zero third-party requests (QA checklist, WebGL and map).
 */
export function buildMapStyle(opts: { origin: string; basemapUrl: string }): StyleSpecification {
  const tilesUrl = opts.basemapUrl.startsWith("http") ? opts.basemapUrl : `${opts.origin}${opts.basemapUrl}`;
  const all = layers("protomaps", cobraFlavor(), { lang: "en" });
  // No POI icons and no sprite sheet: drop every layer that needs one.
  const noIcons = all.filter((l) => {
    const layout = "layout" in l ? (l.layout as Record<string, unknown> | undefined) : undefined;
    const sourceLayer = "source-layer" in l ? l["source-layer"] : undefined;
    return !(layout && "icon-image" in layout) && sourceLayer !== "pois";
  });
  return {
    version: 8,
    glyphs: `${opts.origin}/map/fonts/{fontstack}/{range}.pbf`,
    sources: {
      protomaps: {
        type: "vector",
        url: `pmtiles://${tilesUrl}`,
        attribution: "Basemap data © OpenStreetMap contributors, Protomaps",
      },
    },
    layers: noIcons as StyleSpecification["layers"],
  };
}
