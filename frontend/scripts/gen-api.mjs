// Fetch the FastAPI schema, snapshot it and generate TypeScript types (spec 14.2, 15.1).
//   npm run gen:api            fetch, write openapi.snapshot.json, write src/lib/api/schema.d.ts
//   npm run gen:api -- --check fail when the running backend differs from the committed snapshot
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = (p) => fileURLToPath(new URL(p, import.meta.url));
const base = process.env.NEXT_PUBLIC_COBRA_API_URL || "http://localhost:8000";
const check = process.argv.includes("--check");

let live;
try {
  const res = await fetch(`${base}/openapi.json`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  live = await res.json();
} catch (e) {
  console.error(`gen-api: backend not reachable at ${base} (${e.message}). Start it with: python backend/main.py`);
  process.exit(2);
}
const text = JSON.stringify(live, null, 2) + "\n";
const snap = root("../openapi.snapshot.json");
if (check) {
  const same = existsSync(snap) && readFileSync(snap, "utf8") === text;
  console.log(same ? "gen-api: snapshot matches the running backend" : "gen-api: SNAPSHOT IS STALE, run npm run gen:api");
  process.exit(same ? 0 : 1);
}
writeFileSync(snap, text);
execFileSync("npx", ["openapi-typescript", snap, "-o", root("../src/lib/api/schema.d.ts")], { stdio: "inherit" });
console.log(`gen-api: ${Object.keys(live.paths).length} paths from ${base}`);
