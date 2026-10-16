import type { Metadata } from "next";
import { REPO_URL } from "@/lib/api/config";

export const metadata: Metadata = { title: "Ethics and scope", description: "What COBRA-WATCH will and will not do, and where its documentation and its code disagree." };

const IN_SCOPE = ["Public IP metadata from search engines, queried passively", "Public vulnerability catalogs (NVD, CISA KEV)", "Public registration data, used only to categorise owners broadly", "Pre-authorized recorded footage and benchmark datasets", "Synthetic and labelled evaluation data"];
const OUT_SCOPE = ["Interception of live video feeds", "Credential brute forcing or penetration testing", "Exploitation of target devices", "Personal data, facial recognition or biometrics", "Unauthorized probes of private networks"];

const LAW = [
  ["Digital Personal Data Protection Act, 2023", "Only the device address, manufacturer, port and security posture are stored. No personal data of citizens is collected."],
  ["Information Technology Act, 2000", "No unauthorized access, data extraction or damage. The platform performs no active manipulation of third-party systems."],
  ["Puttaswamy v. Union of India (2017)", "Privacy is a fundamental right, subject to legality, necessity and proportionality. The platform serves a public need: finding insecure surveillance nodes."],
];

const DUAL_USE = ["Ingestion and verdict endpoints can require an API key.", "Per-camera rate limits discourage automated reconnaissance.", "Every decision is hashed into an append-only, Merkle-chained ledger with an external anchor.", "Critical findings are reported to CERT-In and the relevant city administration before public release."];

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="flex flex-col gap-3 rounded-card border border-line bg-ink-1/70 p-6">
      <h3 className="text-lg font-semibold tracking-tight">{title}</h3>
      <ul className="flex flex-col gap-2.5 text-sm leading-relaxed text-bone-2">{items.map((i) => <li key={i} className="border-t border-line pt-2.5 first:border-0 first:pt-0">{i}</li>)}</ul>
    </div>
  );
}

export default function EthicsPage() {
  return (
    <main className="relative z-content">
      <div className="mx-auto flex max-w-[1100px] flex-col gap-14 px-5 pb-28 pt-32 md:px-8">
        <header className="flex flex-col gap-5">
          <h1 className="t-display">Built passive on purpose.</h1>
          <p className="t-body text-bone-2">COBRA-WATCH is a research and civic-transparency platform. It evaluates how much to trust an alert from an exposed camera. It does not look at what the camera sees.</p>
        </header>

        <section aria-labelledby="scope" className="flex flex-col gap-5">
          <h2 id="scope" className="text-2xl font-semibold tracking-tight">In scope and out of scope</h2>
          <div className="grid gap-5 md:grid-cols-2"><List title="In scope" items={IN_SCOPE} /><List title="Out of scope" items={OUT_SCOPE} /></div>
        </section>

        <section aria-labelledby="video" className="flex flex-col gap-3">
          <h2 id="video" className="text-2xl font-semibold tracking-tight">No live video</h2>
          <p className="t-body text-bone-2">The video analysis module runs only on local recorded files and benchmark datasets. It is decoupled from network discovery, and it rejects live stream addresses from public devices. Detections leave it as data events, never as footage.</p>
        </section>

        <section aria-labelledby="law" className="flex flex-col gap-5">
          <h2 id="law" className="text-2xl font-semibold tracking-tight">Legal framework</h2>
          <dl className="grid gap-x-10 gap-y-5 md:grid-cols-3">{LAW.map(([t, d]) => <div key={t} className="flex flex-col gap-2 border-t border-line pt-4"><dt className="font-medium">{t}</dt><dd className="text-sm leading-relaxed text-bone-2">{d}</dd></div>)}</dl>
          <p className="text-sm text-bone-2">This is a summary of the project&apos;s own policy document, not legal advice.</p>
        </section>

        <section aria-labelledby="dual" className="flex flex-col gap-4">
          <h2 id="dual" className="text-2xl font-semibold tracking-tight">Dual use</h2>
          <p className="t-body text-bone-2">A map of weak cameras helps defenders and could help attackers. The design answers that risk in four ways.</p>
          <ul className="grid gap-4 sm:grid-cols-2">{DUAL_USE.map((d) => <li key={d} className="border-t border-line pt-3 text-sm leading-relaxed text-bone-2">{d}</li>)}</ul>
        </section>

        <section aria-labelledby="gap" className="flex flex-col gap-4 rounded-card border border-signal/30 bg-signal-dim p-6">
          <h2 id="gap" className="text-2xl font-semibold tracking-tight">Where the documentation and the code disagree</h2>
          <p className="text-sm leading-relaxed text-bone">The scoring path is passive: it uses stored scan metadata and never sends a packet to a device. The backend also contains an active heartbeat module that opens TCP connections to devices. That module is outside the scoring path and this web app never calls it, but the policy&apos;s &ldquo;no active probing&rdquo; statement does not describe it. The claim ledger records this as at risk, and the fix is to remove or gate the module before any field deployment.</p>
          <p className="text-sm"><a className="text-bone underline decoration-line-strong underline-offset-4 hover:decoration-signal" href={`${REPO_URL}/blob/main/paper/CLAIMS.md`} target="_blank" rel="noreferrer noopener">Claim ledger</a> · <a className="text-bone underline decoration-line-strong underline-offset-4 hover:decoration-signal" href={`${REPO_URL}/blob/main/ETHICS_AND_SCOPE_POLICY.md`} target="_blank" rel="noreferrer noopener">Full policy</a></p>
        </section>
      </div>
    </main>
  );
}
