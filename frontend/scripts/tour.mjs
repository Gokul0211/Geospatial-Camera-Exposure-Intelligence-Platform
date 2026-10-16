// Screenshot every landing section: node scripts/tour.mjs <outDir> <w> <h>
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
const [out, w = "1366", h = "768"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const page = await (await browser.newContext({ viewport: { width: +w, height: +h } })).newPage();
const logs = [];
page.on("console", (m) => ["error", "warning"].includes(m.type()) && logs.push(`${m.type()}: ${m.text().slice(0, 240)}`));
page.on("pageerror", (e) => logs.push(`pageerror: ${e.message.slice(0, 240)}`));
page.on("response", (r) => r.status() >= 400 && logs.push(`HTTP ${r.status()} ${r.url()}`));
await page.goto("http://localhost:3000/");
await page.waitForTimeout(3000);
const ids = await page.$$eval("main section[aria-labelledby]", (els) => els.map((e) => e.getAttribute("aria-labelledby")));
for (const id of ids) {
  await page.evaluate((i) => document.getElementById(i)?.scrollIntoView({ block: "start" }), id);
  await page.waitForTimeout(2200);
  await page.screenshot({ path: `${out}/${id}-${w}.png` });
  console.log("shot", id);
}
// the walk-the-gate panels
const panels = await page.$$("#method article");
for (let i = 0; i < panels.length; i++) {
  await panels[i].scrollIntoViewIfNeeded();
  await page.evaluate((idx) => document.querySelectorAll("#method article")[idx]?.scrollIntoView({ block: "center" }), i);
  await page.waitForTimeout(2600);
  await page.screenshot({ path: `${out}/walk-${i + 1}-${w}.png` });
}
console.log(JSON.stringify(logs, null, 1));
await browser.close();
