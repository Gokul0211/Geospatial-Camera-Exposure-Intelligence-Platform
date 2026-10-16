import { create } from "zustand";
import type { AlertMessage } from "@/lib/api/schemas";
import type { ConnectionState } from "@/lib/api/socket";

export const ALERT_BUFFER_SIZE = 1_000;

export interface AlertFilters {
  tier: "all" | "high_trust" | "medium_trust" | "low_trust";
  gateTrippedOnly: boolean;
  demo: "all" | "only" | "hide";
  ownerType: "all" | "government" | "corporate" | "telecom" | "unknown";
}

export interface DeviceQuery {
  ownerType: string | null;
  authRequired: boolean | null;
  hasCve: boolean | null;
  text: string | null;
  explanation: string;
  parsedByAi: boolean;
}

export const DEFAULT_FILTERS: AlertFilters = { tier: "all", gateTrippedOnly: false, demo: "all", ownerType: "all" };

/** Append to a ring buffer: newest first, capped. Pure, so it can be unit tested. */
export function pushRing<T>(buffer: readonly T[], item: T, cap: number): T[] {
  const next = [item, ...buffer];
  return next.length > cap ? next.slice(0, cap) : next;
}

interface ConsoleState {
  alerts: AlertMessage[];
  connection: ConnectionState;
  retryInMs: number | null;
  city: string;
  selectedDeviceId: string | null;
  filters: AlertFilters;
  /** Time of the latest INTEGRITY_GATE_TRIPPED message; drives the top-bar gauge flare. */
  lastGateTripAt: number | null;
  /** Parsed natural-language or text query applied to the map devices. */
  query: DeviceQuery | null;
  setQuery: (q: DeviceQuery | null) => void;
  pushAlert: (a: AlertMessage) => void;
  markGateTrip: () => void;
  setConnection: (c: ConnectionState, retryInMs: number | null) => void;
  setCity: (city: string) => void;
  selectDevice: (id: string | null) => void;
  setFilters: (f: Partial<AlertFilters>) => void;
}

/** Live event state only. Server data (devices, scores, analytics) lives in TanStack Query. */
export const useConsoleStore = create<ConsoleState>((set) => ({
  alerts: [],
  connection: "disconnected",
  retryInMs: null,
  city: "Mumbai",
  selectedDeviceId: null,
  filters: DEFAULT_FILTERS,
  lastGateTripAt: null,
  query: null,
  setQuery: (query) => set({ query }),
  pushAlert: (a) => set((s) => ({ alerts: pushRing(s.alerts, a, ALERT_BUFFER_SIZE) })),
  markGateTrip: () => set({ lastGateTripAt: Date.now() }),
  setConnection: (connection, retryInMs) => set({ connection, retryInMs }),
  setCity: (city) => set({ city }),
  selectDevice: (selectedDeviceId) => set({ selectedDeviceId }),
  setFilters: (f) => set((s) => ({ filters: { ...s.filters, ...f } })),
}));
