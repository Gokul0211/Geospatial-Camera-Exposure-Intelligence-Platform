// Screenshot with WebGL enabled (software GL): node scripts/shoot.mjs <out.png> <path> <w> <h> [scrollY|full] [waitMs]
import { chromium } from "@playwright/test";
const [out, path, w = "1366", h = "768", scroll = "0", wait = "2500"] = process.argv.slice(2);
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--enable-webgl"] });
const page = await (await browser.newContext({ viewport: { width: +w, height: +h } })).newPage();
const logs = [];
page.on("response", (r) => r.status() >= 400 && logs.push(`HTTP ${r.status()} ${r.url()}`));
page.on("console", (m) => ["error", "warning"].includes(m.type()) && logs.push(`${m.type()}: ${m.text().slice(0, 300)}`));
page.on("pageerror", (e) => logs.push(`pageerror: ${e.message.slice(0, 300)}`));
await page.goto(`http://localhost:3000${path}`);
await page.waitForTimeout(+wait);
if (scroll === "full") await page.screenshot({ path: out, fullPage: true });
else { await page.evaluate((y) => window.scrollTo(0, y), +scroll); await page.waitForTimeout(1800); await page.screenshot({ path: out }); }
console.log(JSON.stringify({ webgl: await page.evaluate(() => !!document.createElement("canvas").getContext("webgl2")), canvases: await page.evaluate(() => document.querySelectorAll("canvas").length), logs }, null, 1));
await browser.close();
