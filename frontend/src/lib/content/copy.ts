import { fact, fmt3 } from "./facts";

/** Visible copy that is not a measured number. Numbers inside strings come from facts (ground rule 1). */

export const HERO = {
  headline: "A secure camera can still lie.",
  sub: "COBRA-WATCH scores exposed cameras on how vulnerable they are and whether their feed is still real.",
};

export const NAV_LINKS = [
  { label: "Method", href: "/#method" },
  { label: "Research", href: "/research" },
  { label: "Lab", href: "/lab" },
  { label: "Ethics", href: "/ethics" },
] as const;

/** Illustrative banner shown identically on both twin cameras (spec 7.3). Not a real device. */
export const TWIN_BANNER = [
  "product: ip-camera (illustrative)",
  "server: dnvrs-webs",
  "firmware: v5.4.1",
  "ports: 80, 554, 8000",
  "known CVEs: none",
];

export const WALK_PANELS = [
  { id: "posture", title: "Posture", body: "Channel A reads public CVEs, authentication, owner type and patch age into one vulnerability score." },
  { id: "integrity", title: "Integrity", body: "Channel B asks whether the feed is still real: passive banner drift in Tier 1, frame liveness in Tier 2." },
  { id: "both", title: "Trusted only where both hold", body: "Trust is the overlap: the device is secure and its signal is authentic." },
  { id: "gate", title: "The gate", body: "The score is multiplied by G(s). The hood opens in proportion to it." },
  { id: "states", title: "Trips, tapers, passes", body: "A single-field banner change tapers the score but never trips the gate." },
] as const;

export function limitLines() {
  const c = fact("res.corpus");
  const t1 = fact("res.tier1");
  const sw = fact("res.sweep");
  return [
    { id: "C1", text: `The corpus is synthetic and hand-authored. Labels for the ${c.n - c.withChannelB} attribute-only scenarios follow the intended tier.` },
    { id: "C4, C5", text: `All of the gain comes from the ${c.withChannelB} scenarios that carry Channel B fields. On the other ${c.n - c.withChannelB}, IG-DCTF equals the CVE-only model.` },
    { id: "C7", text: `The corpus cannot choose the gate thresholds: all ${sw.total} grid points in the sweep sit within 0.01 of the best F1.` },
    { id: "C8, C10", text: `Tier 1 was benchmarked on ${t1.distinctCases} distinct cases. Tier 2 used synthetic frames, with weights revised after seeing the benchmark.` },
    { id: "C14", text: "A loop of real footage has natural motion and is not caught by the frozen-frame rule." },
    { id: "C17", text: "There is no field data. Real-world effectiveness is unverified." },
  ];
}

export const ETHICS_COLUMNS = [
  { title: "Passive only", lines: ["It reads public banner metadata, vulnerability catalogs and registration data.", "It never exploits, brute forces or probes a third-party system."] },
  { title: "No live video", lines: ["Video analysis runs only on pre-authorized recorded footage and benchmark datasets.", "Live stream addresses of public devices are rejected by design."] },
  { title: "No personal data", lines: ["No facial recognition, no plate recognition, no identity tracking.", "It stores only address, manufacturer, port and security posture."] },
];

export const RUN_STEPS = [
  { title: "Clone", code: "git clone https://github.com/Gokul0211/Geospatial-Camera-Exposure-Intelligence-Platform.git\ncd Geospatial-Camera-Exposure-Intelligence-Platform\ncp .env.example .env" },
  { title: "Install the backend", code: "pip install -r backend/requirements.txt" },
  { title: "Start the API", code: "python backend/main.py\n# API and docs on http://localhost:8000/docs" },
  { title: "Start the web app", code: "cd frontend\nnpm install\nnpm run dev\n# http://localhost:3000" },
  { title: "Or use Docker", code: "docker compose up --build" },
];

export const PIPELINE = [
  { id: "event", label: "Detection event", note: "Idempotent, 60 s freshness window" },
  { id: "corroboration", label: "Corroboration", note: "Nearby devices and sources" },
  { id: "a", label: "Channel A", note: "CVE posture" },
  { id: "b", label: "Channel B", note: "Banner drift and liveness" },
  { id: "gate", label: "The gate", note: "T_final = T_cve * G(s)" },
  { id: "ledger", label: "Alert and ledger", note: "Merkle-chained audit entry" },
];

export const PIPELINE_FACTS = [
  "Writes are idempotent and rejected outside a 60 s freshness window.",
  "Every decision is hashed into a Merkle-chained audit ledger with an external anchor.",
  "Sources are passive only: public metadata, never a probe of a device.",
];

export const resultsBars = () =>
  [
    { key: "wa" as const, label: "Weighted average" },
    { key: "advanced" as const, label: "CVE-only" },
    { key: "bayesian" as const, label: "Bayesian log-odds" },
    { key: "igdctf" as const, label: "IG-DCTF" },
  ].map((m) => ({ ...m, f1: fact(`res.model.${m.key}` as const).f1, model: fact(`res.model.${m.key}` as const) }));

export const fmtP = (p: number) => p.toExponential(1).replace("e-", "e-").replace("e-0", "e-");
export { fmt3 };
