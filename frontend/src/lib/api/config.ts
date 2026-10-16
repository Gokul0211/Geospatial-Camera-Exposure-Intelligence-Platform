export const API_BASE = (process.env.NEXT_PUBLIC_COBRA_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
export const REVEAL_IP = process.env.NEXT_PUBLIC_REVEAL_IP === "true";
export const REPO_URL =
  process.env.NEXT_PUBLIC_REPO_URL ?? "https://github.com/Gokul0211/Geospatial-Camera-Exposure-Intelligence-Platform";
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
export const BASEMAP_URL = process.env.NEXT_PUBLIC_BASEMAP_URL ?? "/tiles/india.pmtiles";

/** `ws://` or `wss://` URL of the alert feed, derived from the REST base. */
export const WS_ALERTS_URL = API_BASE.replace(/^http/, "ws") + "/api/ws/alerts";

export const REQUEST_TIMEOUT_MS = 12_000;
