import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { CONTRAST_PAIRS, contrast, readHexTokens } from "@/lib/a11y/contrast";

const tokens = readHexTokens(readFileSync(new URL("../src/styles/tokens.css", import.meta.url), "utf8"));

describe("colour tokens (spec 5.1)", () => {
  it("defines exactly the documented hex tokens", () => {
    expect(tokens).toMatchObject({
      "ink-0": "#0a0c0b",
      "ink-1": "#101311",
      "ink-2": "#171b19",
      "ink-3": "#202522",
      bone: "#e7eae3",
      "bone-2": "#a4aaa1",
      "bone-3": "#6e746c",
      signal: "#f3a33a",
    });
  });

  it("matches the brand colours in assets/logo geometry", async () => {
    const geo = (await import("@/lib/three/hood-geometry.json")).default;
    expect(geo.colors.void.toLowerCase()).toBe(tokens["ink-0"]);
    expect(geo.colors.bone.toLowerCase()).toBe(tokens.bone);
    expect(geo.colors.signal.toLowerCase()).toBe(tokens.signal);
  });

  const rows = CONTRAST_PAIRS.map((p) => ({ ...p, ratio: contrast(tokens[p.fg]!, tokens[p.bg]!) }));
  it.each(rows)("$fg on $bg meets $min:1 ($use)", ({ ratio, min }) => {
    expect(ratio).toBeGreaterThanOrEqual(min);
  });

  it("prints the table for the report", () => {
    console.table(rows.map((r) => ({ fg: r.fg, bg: r.bg, ratio: r.ratio.toFixed(2), min: r.min })));
  });
});
