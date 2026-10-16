import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const PAGES = ["/", "/research", "/ethics", "/lab", "/console", "/design-system", "/this-page-does-not-exist"];
/** The browser logs the 404 of the document itself for the not-found route; that is expected. */
const EXPECTED = /Failed to load resource: the server responded with a status of 404/;

function watchConsole(page: Page) {
  const problems: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" || m.type() === "warning") problems.push(`${m.type()}: ${m.text()}`);
  });
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
  return problems;
}

for (const path of PAGES) {
  test(`no console errors, hydration warnings or serious axe issues on ${path}`, async ({ page }) => {
    test.setTimeout(90_000);
    const problems = watchConsole(page);
    // Software GL in CI sandboxes may warn about GPU stalls; these are not application errors.
    const benign = /GPU stall|preloaded using link preload|WebGL/i;
    const response = await page.goto(path);
    await page.waitForLoadState("networkidle");
    // Entrance animations (hero CTA fades in at 1.1 s for 0.5 s) must be finished: axe reads the blended colour mid-fade.
    await page.waitForTimeout(2200);
    if (path.includes("does-not-exist")) expect(response?.status()).toBe(404);
    const unexpected = problems.filter((p) => !(path.includes("does-not-exist") && EXPECTED.test(p)) && !benign.test(p));
    expect(unexpected, unexpected.join("\n")).toEqual([]);
    const results = await new AxeBuilder({ page }).analyze();
    const bad = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(bad.map((v) => `${v.id}: ${v.nodes.length} nodes`)).toEqual([]);
  });
}

test("no horizontal scroll at this viewport", async ({ page }) => {
  await page.goto("/design-system");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("keyboard: skip link is first, visible on focus, and moves focus to main", async ({ page }) => {
  await page.goto("/design-system");
  await page.keyboard.press("Tab");
  const skip = page.locator(".skip-link");
  await expect(skip).toBeFocused();
  const box = await skip.boundingBox();
  expect(box && box.y >= 0).toBeTruthy();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});

test("keyboard: Tab reaches controls and shows a 2px amber focus ring", async ({ page }) => {
  await page.goto("/design-system");
  const button = page.getByRole("button", { name: "Open console" });
  // Real keyboard focus (programmatic focus() does not trigger :focus-visible).
  for (let i = 0; i < 40 && !(await button.evaluate((el) => el === document.activeElement)); i++) {
    await page.keyboard.press("Tab");
  }
  await expect(button).toBeFocused();
  const outline = await button.evaluate((el) => {
    const s = getComputedStyle(el);
    return { width: s.outlineWidth, style: s.outlineStyle, color: s.outlineColor, offset: s.outlineOffset };
  });
  expect(outline).toEqual({ width: "2px", style: "solid", color: "rgb(243, 163, 58)", offset: "2px" });
});

test("hood gauge tweens normally", async ({ page }) => {
  await page.goto("/design-system");
  const rib = page.locator("section[aria-labelledby=hood] svg[role=img]").first().locator("path").first();
  const before = await rib.getAttribute("d");
  await page.getByRole("button", { name: "Trips" }).click();
  await page.waitForTimeout(40);
  const mid = await rib.getAttribute("d");
  await page.waitForTimeout(1500);
  const after = await rib.getAttribute("d");
  expect(mid).not.toBe(before);
  expect(after).not.toBe(before);
  expect(mid).not.toBe(after);
});

test.describe("reduced motion", () => {
  test.use({ contextOptions: { reducedMotion: "reduce" } });
  test("hood gauge snaps to its state with no transition", async ({ page }) => {
    await page.goto("/design-system");
    const rib = page.locator("section[aria-labelledby=hood] svg[role=img]").first().locator("path").first();
    const before = await rib.getAttribute("d");
    await page.getByRole("button", { name: "Trips" }).click();
    await page.waitForTimeout(40);
    const early = await rib.getAttribute("d");
    await page.waitForTimeout(800);
    const late = await rib.getAttribute("d");
    expect(early).not.toBe(before);
    expect(early).toBe(late);
  });
  test("skeleton pulse is disabled", async ({ page }) => {
    await page.goto("/design-system");
    const dur = await page.locator(".skeleton").first().evaluate((el) => getComputedStyle(el).animationDuration);
    expect(parseFloat(dur)).toBeLessThan(0.01);
  });
});
