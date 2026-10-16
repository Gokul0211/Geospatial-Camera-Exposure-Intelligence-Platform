"use client";
import * as React from "react";
import maplibregl, { type GeoJSONSource, type Map as MLMap, type StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { createRoot, type Root } from "react-dom/client";
import { BASEMAP_URL } from "@/lib/api/config";
import { maskIp } from "@/lib/api/mask-ip";
import type { Device } from "@/lib/api/normalize";
import { geoProvenance, tierLabel } from "@/lib/api/normalize";
import { buildMapStyle } from "@/styles/map-style";
import { registerPmtiles } from "@/lib/map/pmtiles";
import { MARKER_KINDS, circlePolygon, drawMarker, haversine, markerKind } from "@/lib/map/icons";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { cn } from "@/lib/utils";

export interface Zone {
  center: [number, number];
  radiusM: number;
  ids: string[];
}

export interface MapViewProps {
  devices: Device[];
  selectedId?: string | null;
  onSelect?: (id: string | null) => void;
  view: { center: [number, number]; zoom: number };
  /** Changing this value flies (or jumps, under reduced motion) to `view`. */
  flyKey?: string | number;
  projection?: "globe" | "mercator";
  interactive?: boolean;
  heat?: [number, number, number][] | null;
  zoneMode?: boolean;
  zone?: Zone | null;
  onZone?: (z: Zone | null) => void;
  onBasemap?: (kind: "pmtiles" | "fallback") => void;
  className?: string;
  label?: string;
}

const INK_0 = "#0a0c0b";
const INK_1 = "#101311";
const INK_3 = "#202522";
const BONE = "#e7eae3";

/** Basemap used when public/tiles/india.pmtiles has not been built: public-domain Natural Earth outlines, self-hosted. */
function fallbackStyle(origin: string): StyleSpecification {
  return {
    version: 8,
    glyphs: `${origin}/map/fonts/{fontstack}/{range}.pbf`,
    sources: {
      countries: { type: "geojson", data: `${origin}/map/south-asia-countries.geojson`, attribution: "Natural Earth (public domain)" },
      states: { type: "geojson", data: `${origin}/map/india-states.geojson` },
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": INK_0 } },
      { id: "land", type: "fill", source: "countries", paint: { "fill-color": INK_1 } },
      { id: "states", type: "line", source: "states", paint: { "line-color": "rgba(231,234,227,0.07)", "line-width": 0.6 } },
      { id: "borders", type: "line", source: "countries", paint: { "line-color": "rgba(231,234,227,0.16)", "line-width": 0.8 } },
    ],
  };
}

/** public/tiles/basemap.json is committed as {"available": false} and rewritten by scripts/build-basemap.sh, so no probe request ever 404s. */
async function basemapExists(): Promise<boolean> {
  try {
    const r = await fetch("/tiles/basemap.json", { cache: "no-store" });
    if (!r.ok) return false;
    const m = (await r.json()) as { available?: boolean };
    return m.available === true;
  } catch {
    return false;
  }
}

function toCollection(devices: Device[]) {
  return {
    type: "FeatureCollection" as const,
    features: devices.map((d) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [d.lon, d.lat] },
      properties: { id: d.id, kind: markerKind(d), score: d.trust_score ?? -1 },
    })),
  };
}

/** MapLibre GL JS v5 map with clustering, the severity encoding, popups with masked IPs, and zone drawing (spec 10.2). */
export default function MapView(props: MapViewProps) {
  const { devices, selectedId, onSelect, view, flyKey, projection = "mercator", interactive = true, heat, zoneMode, zone, onZone, onBasemap, className, label } = props;
  const reduced = usePrefersReducedMotion();
  const reducedRef = React.useRef(reduced);
  const host = React.useRef<HTMLDivElement | null>(null);
  const mapRef = React.useRef<MLMap | null>(null);
  const readyRef = React.useRef(false);
  const popupRoot = React.useRef<Root | null>(null);
  const popupRef = React.useRef<maplibregl.Popup | null>(null);
  const cb = React.useRef({ onSelect, onZone, devices, zoneMode, onBasemap });
  React.useEffect(() => {
    cb.current = { onSelect, onZone, devices, zoneMode, onBasemap };
    reducedRef.current = reduced;
  });
  const [basemap, setBasemap] = React.useState<"pmtiles" | "fallback" | null>(null);
  const [ready, setReady] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // create the map once
  React.useEffect(() => {
    let disposed = false;
    let map: MLMap | null = null;
    (async () => {
      const origin = window.location.origin;
      const hasTiles = await basemapExists();
      if (disposed || !host.current) return;
      if (hasTiles) registerPmtiles(maplibregl);
      const kind = hasTiles ? "pmtiles" : "fallback";
      setBasemap(kind);
      cb.current.onBasemap?.(kind);
      try {
        map = new maplibregl.Map({
          container: host.current,
          style: hasTiles ? buildMapStyle({ origin, basemapUrl: BASEMAP_URL }) : fallbackStyle(origin),
          center: view.center,
          zoom: view.zoom,
          attributionControl: { compact: true },
          interactive,
          maxPitch: 0,
          dragRotate: false,
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : "Map failed to start");
        return;
      }
      mapRef.current = map;
      map.touchZoomRotate.disableRotation();
      map.on("error", (ev) => {
        if (ev.error && /WebGL|context/i.test(String(ev.error.message))) setError("WebGL is not available, so the map cannot draw.");
      });
      map.on("load", () => {
        if (!map) return;
        for (const k of MARKER_KINDS) map.addImage(`m-${k}`, drawMarker(k), { pixelRatio: 2 });
        map.addSource("devices", { type: "geojson", data: toCollection(cb.current.devices), cluster: true, clusterRadius: 46, clusterMaxZoom: 11 });
        map.addLayer({ id: "clusters", type: "circle", source: "devices", filter: ["has", "point_count"], paint: { "circle-color": INK_3, "circle-stroke-color": "rgba(231,234,227,0.22)", "circle-stroke-width": 1, "circle-radius": ["step", ["get", "point_count"], 14, 25, 18, 100, 24, 500, 30] } });
        map.addLayer({ id: "cluster-count", type: "symbol", source: "devices", filter: ["has", "point_count"], layout: { "text-field": ["get", "point_count_abbreviated"], "text-font": ["Noto Sans Medium"], "text-size": 12, "text-allow-overlap": true }, paint: { "text-color": BONE } });
        map.addLayer({ id: "selected", type: "circle", source: "devices", filter: ["==", ["get", "id"], ""], paint: { "circle-radius": 13, "circle-color": "rgba(0,0,0,0)", "circle-stroke-color": "#f3a33a", "circle-stroke-width": 2 } });
        map.addLayer({ id: "device", type: "symbol", source: "devices", filter: ["!", ["has", "point_count"]], layout: { "icon-image": ["concat", "m-", ["get", "kind"]], "icon-allow-overlap": true, "icon-size": 1 } });
        map.addSource("zone", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
        map.addLayer({ id: "zone-fill", type: "fill", source: "zone", paint: { "fill-color": "rgba(243,163,58,0.08)" } });
        map.addLayer({ id: "zone-line", type: "line", source: "zone", paint: { "line-color": "#f3a33a", "line-width": 1.5, "line-dasharray": [2, 2] } });
        map.addSource("heat", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
        map.addLayer({
          id: "heat", type: "heatmap", source: "heat", layout: { visibility: "none" },
          paint: {
            "heatmap-weight": ["get", "w"], "heatmap-radius": 28, "heatmap-opacity": 0.85,
            "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"], 0, "rgba(243,163,58,0)", 0.3, "rgba(243,163,58,0.18)", 0.7, "rgba(243,163,58,0.45)", 1, "rgba(231,234,227,0.8)"],
          },
        }, "device");
        if (projection === "globe") map.setProjection({ type: "globe" });
        readyRef.current = true;
        setReady(true);
      });

      map.on("click", "clusters", async (e) => {
        const f = e.features?.[0];
        if (!f || !map) return;
        const src = map.getSource("devices") as GeoJSONSource;
        const zoom = await src.getClusterExpansionZoom(f.properties?.cluster_id as number);
        const g = f.geometry as unknown as { coordinates: [number, number] };
        map.easeTo({ center: g.coordinates, zoom: zoom + 0.5, duration: reducedRef.current ? 0 : 500 });
      });
      map.on("click", "device", (e) => {
        const f = e.features?.[0];
        if (f) cb.current.onSelect?.(String(f.properties?.id));
      });
      for (const layer of ["device", "clusters"]) {
        map.on("mouseenter", layer, () => map && (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", layer, () => map && (map.getCanvas().style.cursor = cb.current.zoneMode ? "crosshair" : ""));
      }

      let start: [number, number] | null = null;
      map.on("mousedown", (e) => {
        if (!cb.current.zoneMode || !map) return;
        start = [e.lngLat.lng, e.lngLat.lat];
        map.dragPan.disable();
      });
      map.on("mousemove", (e) => {
        if (!start || !map) return;
        const r = haversine(start, [e.lngLat.lng, e.lngLat.lat]);
        (map.getSource("zone") as GeoJSONSource).setData({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [circlePolygon(start, r)] } });
      });
      map.on("mouseup", (e) => {
        if (!start || !map) return;
        const c = start;
        start = null;
        map.dragPan.enable();
        const r = haversine(c, [e.lngLat.lng, e.lngLat.lat]);
        if (r < 200) {
          cb.current.onZone?.(null);
          return;
        }
        const ids = cb.current.devices.filter((d) => haversine(c, [d.lon, d.lat]) <= r).map((d) => d.id);
        cb.current.onZone?.({ center: c, radiusM: r, ids });
      });
    })();
    return () => {
      disposed = true;
      readyRef.current = false;
      setReady(false);
      popupRef.current?.remove();
      const root = popupRoot.current;
      if (root) queueMicrotask(() => root.unmount());
      map?.remove();
      mapRef.current = null;
    };
    // created once; later changes are applied by the effects below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (map.getSource("devices") as GeoJSONSource | undefined)?.setData(toCollection(devices));
  }, [devices, ready]);

  React.useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    map.setFilter("selected", ["==", ["get", "id"], selectedId ?? ""]);
    popupRef.current?.remove();
    popupRef.current = null;
    const oldRoot = popupRoot.current;
    popupRoot.current = null;
    if (oldRoot) queueMicrotask(() => oldRoot.unmount());
    const d = selectedId ? devices.find((x) => x.id === selectedId) : undefined;
    if (!d) return;
    const el = document.createElement("div");
    const root = createRoot(el);
    root.render(
      <div className="flex min-w-[210px] flex-col gap-2 text-[0.8125rem]">
        <div className="flex items-center justify-between gap-3">
          <span className="num text-bone">{maskIp(d.ip)}</span>
          <HoodGauge gate={d.integrity_gate_tripped ? 0.3 : 1} score={d.trust_score ?? 100} size={44} />
        </div>
        <div className="text-bone-2">{d.manufacturer ?? "Unknown manufacturer"} · {d.owner_type ?? "unknown owner"}</div>
        <div className="text-bone-2">{d.integrity_gate_tripped ? "Gate tripped" : `${tierLabel(d.action_tier)} trust`}{d.trust_score !== undefined ? ` · ${d.trust_score}` : ""}</div>
        <div className="text-xs text-bone-2">{geoProvenance(d.geo_source).note}</div>
      </div>,
    );
    popupRoot.current = root;
    popupRef.current = new maplibregl.Popup({ closeButton: false, offset: 14, className: "cw-popup", maxWidth: "260px" })
      .setLngLat([d.lon, d.lat])
      .setDOMContent(el)
      .addTo(map);
  }, [selectedId, devices, ready]);

  React.useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    if (reducedRef.current) map.jumpTo({ center: view.center, zoom: view.zoom });
    else map.flyTo({ center: view.center, zoom: view.zoom, duration: 1800 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flyKey, ready]);

  React.useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    map.setLayoutProperty("heat", "visibility", heat ? "visible" : "none");
    if (heat) {
      (map.getSource("heat") as GeoJSONSource).setData({
        type: "FeatureCollection",
        features: heat.map(([lon, lat, w]) => ({ type: "Feature" as const, properties: { w }, geometry: { type: "Point" as const, coordinates: [lon, lat] } })),
      });
    }
  }, [heat, ready]);

  React.useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (map.getSource("zone") as GeoJSONSource).setData(
      zone ? { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [circlePolygon(zone.center, zone.radiusM)] } } : { type: "FeatureCollection", features: [] },
    );
  }, [zone, ready]);

  React.useEffect(() => {
    const map = mapRef.current;
    if (map && ready) map.getCanvas().style.cursor = zoneMode ? "crosshair" : "";
  }, [zoneMode, ready]);

  return (
    <div className={cn("relative size-full bg-ink-0", className)}>
      <div ref={host} role="application" aria-label={label ?? "Map of exposed devices"} className="size-full" />
      {basemap === "fallback" && (
        <p className="pointer-events-none absolute bottom-28 left-3 max-w-[30ch] rounded-chip border border-line bg-ink-0/80 px-2 py-1 text-[0.6875rem] leading-snug text-bone-2">
          Outline basemap. Build the detailed one with scripts/build-basemap.sh.
        </p>
      )}
      {error && <p role="alert" className="absolute inset-x-3 top-3 rounded-input border border-signal/40 bg-ink-1 p-3 text-sm text-bone">{error}</p>}
    </div>
  );
}
