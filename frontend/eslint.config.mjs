import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([".next/**", "node_modules/**", "src/lib/api/schema.d.ts", "next-env.d.ts", "scripts/**", "test-results/**", "playwright-report/**"]),
  {
    rules: {
      // Ground rule 8 / spec 15.4: an IP address reaches the DOM only through maskIp().
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXExpressionContainer > MemberExpression[property.name='ip']",
          message: "Do not render `.ip` directly. Use maskIp() from @/lib/api/mask-ip.",
        },
        {
          selector: "JSXExpressionContainer > TemplateLiteral MemberExpression[property.name='ip']:not(CallExpression[callee.name='maskIp'] > MemberExpression)",
          message: "Do not render `.ip` directly. Use maskIp() from @/lib/api/mask-ip.",
        },
        {
          selector: "CallExpression[callee.name='addEventListener'][arguments.0.value='scroll'], CallExpression[callee.property.name='addEventListener'][arguments.0.value='scroll']",
          message: "No scroll listeners (spec 17.3). Use Anime.js onScroll, IntersectionObserver or CSS scroll timelines.",
        },
      ],
    },
  },
]);
