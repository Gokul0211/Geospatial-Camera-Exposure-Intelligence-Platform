// Proof screenshots for a phase: node scripts/screenshots.mjs <outDir> <path> [path...]
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";

const [out, ...paths] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const sizes = [["1366x768", 1366, 768], ["768", 768, 1024], ["375", 375, 667]];
const browser = await chromium.launch();
for (const [label, width, height] of sizes) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  for (const p of paths) {
    await page.goto(`http://localhost:3000${p}`);
    await page.waitForLoadState("networkidle");
    const name = (p === "/" ? "home" : p.replace(/\W+/g, "-").replace(/^-|-$/g, "")) + `-${label}.png`;
    await page.screenshot({ path: `${out}/${name}`, fullPage: p !== "/" });
    console.log("wrote", `${out}/${name}`);
  }
  await ctx.close();
}
await browser.close();
