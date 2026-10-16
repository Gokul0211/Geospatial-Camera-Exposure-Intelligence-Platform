export const ROUTES = {
  home: "/",
  research: "/research",
  lab: "/lab",
  console: "/console",
  ethics: "/ethics",
  verify: (alertId: string) => `/verify/${encodeURIComponent(alertId)}`,
  device: (id: string) => `/console/devices/${encodeURIComponent(id)}`,
} as const;

/** The only CTA label for the console on the whole site (spec 4). */
export const CONSOLE_CTA = "Open console";
