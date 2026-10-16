"use client";
import { useSyncExternalStore } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

/** One shared matchMedia subscription for the whole app (spec 18.3). */
let mql: MediaQueryList | null = null;
const listeners = new Set<() => void>();
function onChange() {
  listeners.forEach((l) => l());
}
function subscribe(cb: () => void): () => void {
  if (!mql) {
    mql = window.matchMedia(QUERY);
    mql.addEventListener("change", onChange);
  }
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
    if (listeners.size === 0 && mql) {
      mql.removeEventListener("change", onChange);
      mql = null;
    }
  };
}
const getSnapshot = () => window.matchMedia(QUERY).matches;
/** Server and first client render assume motion is OK; a reduced-motion user gets the instant path after hydration. */
const getServerSnapshot = () => false;

export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
