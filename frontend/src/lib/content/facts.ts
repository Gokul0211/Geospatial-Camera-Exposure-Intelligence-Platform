import { generatedFacts, type GeneratedFactKey } from "./facts.generated";
import { manualFacts, type ManualFactKey } from "./facts.manual";

const all = { ...generatedFacts, ...manualFacts } as const;
export type FactKey = GeneratedFactKey | ManualFactKey;
type Value<K extends FactKey> = (typeof all)[K]["value"];

/** The only way a number reaches the UI. Returns the value; `factSource` returns its source key. */
export function fact<K extends FactKey>(key: K): Value<K> {
  return all[key].value;
}
export function factSource(key: FactKey): { source: string; section: string } {
  const f = all[key];
  return { source: f.source, section: f.section };
}
export const FACT_KEYS = Object.keys(all) as FactKey[];

/** Format a 0..1 metric to three decimals, as printed in paper/results.md. */
export function fmt3(x: number): string {
  return x.toFixed(3);
}
