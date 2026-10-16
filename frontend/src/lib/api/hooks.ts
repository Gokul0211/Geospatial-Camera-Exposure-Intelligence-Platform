"use client";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { fetchJson } from "./client";
import { flattenDevices } from "./normalize";
import { HealthSchema, STATIC_THRESHOLDS, ThresholdsSchema, TrustScoreSchema, type Thresholds } from "./schemas";

export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: () => fetchJson("/health", HealthSchema), refetchInterval: 15_000, retry: false });
}

/** Live thresholds, or the labelled static constants when the backend is unreachable (spec 3.1). */
export function useThresholds(): { thresholds: Thresholds; source: "live" | "static"; loading: boolean } {
  const q = useQuery({ queryKey: ["thresholds"], queryFn: () => fetchJson("/api/config/thresholds", ThresholdsSchema), retry: false, staleTime: 5 * 60_000 });
  if (q.data) return { thresholds: q.data, source: "live", loading: false };
  return { thresholds: STATIC_THRESHOLDS, source: "static", loading: q.isPending };
}

export function useDevices(city: string, enabled = true) {
  return useQuery({
    queryKey: ["devices", city],
    enabled,
    retry: false,
    staleTime: 60_000,
    queryFn: async () => {
      const json = await fetchJson(`/api/devices?city=${encodeURIComponent(city)}`, z.unknown());
      return flattenDevices(json);
    },
  });
}

export function useTrustScore(id: string | null) {
  return useQuery({
    queryKey: ["trust-score", id],
    enabled: !!id,
    retry: false,
    queryFn: () => fetchJson(`/api/devices/${encodeURIComponent(id ?? "")}/trust-score`, TrustScoreSchema),
  });
}

export const CITIES = ["All India", "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad"] as const;
