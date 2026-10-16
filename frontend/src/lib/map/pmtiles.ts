import { Protocol } from "pmtiles";

type MapLibreModule = { addProtocol: (name: string, fn: Protocol["tile"]) => void; removeProtocol: (name: string) => void };

let protocol: Protocol | null = null;

/** Register the `pmtiles://` protocol once. Pass the dynamically imported `maplibre-gl` module. */
export function registerPmtiles(maplibre: MapLibreModule): void {
  if (protocol) return;
  protocol = new Protocol();
  maplibre.addProtocol("pmtiles", protocol.tile);
}

export function unregisterPmtiles(maplibre: MapLibreModule): void {
  if (!protocol) return;
  maplibre.removeProtocol("pmtiles");
  protocol = null;
}
