import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { RESULTS_JSON_SHA256 } from "@/lib/content/facts.generated";
import { manualFacts } from "@/lib/content/facts.manual";
import { FACT_KEYS, fact, fmt3 } from "@/lib/content/facts";

const resultsPath = new URL("../../paper/data/results.json", import.meta.url);

describe("facts (spec 3.4)", () => {
  it("facts.generated.ts is in sync with paper/data/results.json", () => {
    const sha = createHash("sha256").update(readFileSync(resultsPath, "utf8")).digest("hex");
    expect(RESULTS_JSON_SHA256, "results.json changed: run `npm run sync`").toBe(sha);
  });

  it("every manual fact carries a source and a section", () => {
    for (const [key, f] of Object.entries(manualFacts)) {
      expect(f.source, key).toBeTruthy();
      expect(f.section, key).toBeTruthy();
    }
  });

  it("covers every key listed in spec 3.2", () => {
    for (const key of [
      "res.model.wa", "res.model.advanced", "res.model.bayesian", "res.model.igdctf", "res.mcnemar",
      "res.strat.with_b", "res.strat.without_b", "res.ablation", "res.sweep", "res.tier1", "res.tier2",
      "res.t2.end2end", "res.overhead", "eval.tests",
    ]) {
      expect(FACT_KEYS, key).toContain(key);
    }
  });

  it("matches the numbers printed in paper/results.md (4 decimals there, 3 decimals on the site)", () => {
    const wa = fact("res.model.wa");
    const adv = fact("res.model.advanced");
    const bay = fact("res.model.bayesian");
    const ig = fact("res.model.igdctf");
    // results.md section 1: WA F1 0.7525, Advanced 0.8113, Bayesian 0.8319, IG-DCTF 0.9756
    expect(wa.f1.toFixed(4)).toBe("0.7525");
    expect(adv.f1.toFixed(4)).toBe("0.8113");
    expect(bay.f1.toFixed(4)).toBe("0.8319");
    expect(ig.f1.toFixed(4)).toBe("0.9756");
    // Rounded once from the stored value: WA F1 is 0.752, not 0.753 (0.7525 rounded twice).
    expect([wa, adv, bay, ig].map((m) => fmt3(m.f1))).toEqual(["0.752", "0.811", "0.832", "0.976"]);
    expect([ig.tp, ig.fp, ig.tn, ig.fn]).toEqual([60, 0, 57, 3]);
    expect(fact("res.corpus")).toEqual({ n: 120, fabricated: 63, genuine: 57, withChannelB: 30 });
    expect(fact("res.mcnemar").igOnly).toBe(17);
    expect(fact("res.tier1").distinctCases).toBe(13);
    expect(fact("res.overhead").igdctfUs.toFixed(2)).toBe("4.69");
  });

  it("renders no hard-coded digits in section and page components", () => {
    // Heuristic for ground rule 1: JSX text between tags must not contain decimals or multi-digit numbers
    // (result figures). Single-digit method constants such as "G(s) = 1" are allowed.
    const roots = [new URL("../src/components/sections", import.meta.url).pathname];
    const offenders: string[] = [];
    const walk = (dir: string) => {
      let entries: string[] = [];
      try {
        entries = readdirSync(dir);
      } catch {
        return;
      }
      for (const e of entries) {
        const p = join(dir, e);
        if (statSync(p).isDirectory()) walk(p);
        else if (p.endsWith(".tsx")) {
          const text = readFileSync(p, "utf8");
          for (const m of text.matchAll(/>([^<>{}]*(?:\d+\.\d+|\d{2,})[^<>{}]*)</g)) offenders.push(`${p}: ${m[1]?.trim()}`);
        }
      }
    };
    roots.forEach(walk);
    expect(offenders).toEqual([]);
  });
});
