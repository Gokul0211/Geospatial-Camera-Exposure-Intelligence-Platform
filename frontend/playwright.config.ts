import { defineConfig } from "@playwright/test";

/** Three viewports from the phase definition of done: 1366x768, 768 and 375 wide. */
export default defineConfig({
  testDir: "tests/e2e",
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  use: { baseURL: "http://localhost:3000" },
  projects: [
    { name: "desktop-1366", use: { viewport: { width: 1366, height: 768 } } },
    { name: "tablet-768", use: { viewport: { width: 768, height: 1024 } } },
    { name: "mobile-375", use: { viewport: { width: 375, height: 667 }, hasTouch: true } },
  ],
  webServer: {
    command: "npm run start",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 60_000,
    env: { ENABLE_DESIGN_PAGE: "true" },
  },
});
