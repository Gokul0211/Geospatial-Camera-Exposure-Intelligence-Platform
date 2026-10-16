import type { NextConfig } from "next";

/**
 * Next.js 16, Turbopack only. Do NOT add a `webpack` key: with Turbopack as the
 * default bundler a custom webpack config makes `next build` fail (spec 1.2).
 * GLSL files are imported as strings through the Turbopack raw-loader rule.
 */
const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  turbopack: {
    rules: {
      "*.{glsl,vert,frag}": {
        loaders: ["raw-loader"],
        as: "*.js",
      },
    },
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
      {
        // Basemap tiles are fetched with HTTP range requests; allow caching.
        source: "/tiles/:file*",
        headers: [{ key: "Cache-Control", value: "public, max-age=86400" }],
      },
    ];
  },
};

export default config;
