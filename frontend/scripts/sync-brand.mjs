// assets/logo -> frontend. The hood geometry is NEVER redrawn by hand (spec 6.1).
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const root = (p) => fileURLToPath(new URL(p, import.meta.url));
const geo = JSON.parse(readFileSync(root("../../assets/logo/cobra-mark.geometry.json"), "utf8"));
mkdirSync(root("../src/lib/three"), { recursive: true });
writeFileSync(root("../src/lib/three/hood-geometry.json"), JSON.stringify(geo, null, 2) + "\n");

mkdirSync(root("../public/brand"), { recursive: true });
for (const f of [
  "cobra-mark.svg",
  "cobra-mark-transparent.svg",
  "cobra-logo-dark.svg",
  "cobra-logo-light.svg",
  "cobra-banner.png",
]) {
  copyFileSync(root(`../../assets/logo/${f}`), root(`../public/brand/${f}`));
}
copyFileSync(root("../../assets/logo/cobra-favicon.svg"), root("../public/favicon.svg"));
console.log("sync-brand: hood-geometry.json, public/brand/*, public/favicon.svg written");
