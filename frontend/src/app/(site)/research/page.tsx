import type { Metadata } from "next";
import { Tex } from "@/components/research/math";
import { SourceNote } from "@/components/ui/source-note";
import { SyntheticChip } from "@/components/ui/synthetic-chip";
import { REPO_URL } from "@/lib/api/config";
import { fact, fmt3 } from "@/lib/content/facts";
import { limitLines, resultsBars } from "@/lib/content/copy";

export const metadata: Metadata = { title: "Research", description: "The IG-DCTF method, its propositions, the results and their limits." };

const TOC = [["problem", "The problem"], ["channels", "Two channels"], ["gate", "The gate"], ["propositions", "Five propositions"], ["results", "Results"], ["ablation", "Ablation and fusion control"], ["sweep", "Threshold sweep"], ["tiers", "Tier 1 and Tier 2 benchmarks"], ["overhead", "Overhead"], ["limits", "Limits"]] as const;

function H2({ id, children }: { id: string; children: React.ReactNode }) {
  return <h2 id={id} className="scroll-mt-24 text-2xl font-semibold tracking-tight md:text-3xl">{children}</h2>;
}
const P = ({ children }: { children: React.ReactNode }) => <p className="t-body text-bone-2">{children}</p>;

function Table({ caption, head, rows, note }: { caption: string; head: string[]; rows: (string | number)[][]; note?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <div role="region" aria-label={`${caption}, scrollable`} tabIndex={0} className="overflow-x-auto rounded-card border border-line">
        <table className="w-full min-w-[520px] text-left text-sm">
          <caption className="sr-only">{caption}</caption>
          <thead className="bg-ink-1 text-bone-2"><tr>{head.map((h) => <th key={h} scope="col" className="p-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>{rows.map((r, i) => <tr key={i} className="border-t border-line">{r.map((c, j) => <td key={j} className={j === 0 ? "p-3 text-bone" : "num p-3 text-bone-2"}>{c}</td>)}</tr>)}</tbody>
        </table>
      </div>
      {note}
    </div>
  );
}

export default function ResearchPage() {
  const corpus = fact("res.corpus");
  const mc = fact("res.mcnemar");
  const abl = fact("res.ablation");
  const sw = fact("res.sweep");
  const t1 = fact("res.tier1");
  const t2 = fact("res.tier2");
  const cats = fact("res.t2.end2end");
  const single = fact("res.t2.single");
  const oh = fact("res.overhead");
  const w = fact("method.tier2").weights;
  const g = fact("method.gate");
  const tr = fact("method.tier1");
  const bars = resultsBars();

  return (
    <main className="relative z-content">
      <div className="read-progress" aria-hidden="true" />
      <div className="mx-auto grid max-w-[1360px] gap-12 px-5 pb-24 pt-32 md:px-8 lg:grid-cols-[220px_minmax(0,1fr)]">
        <nav aria-label="On this page" className="hidden lg:block">
          <ol className="sticky top-28 flex flex-col gap-2 text-sm">{TOC.map(([id, t]) => <li key={id}><a href={`#${id}`} className="text-bone-2 no-underline hover:text-bone">{t}</a></li>)}</ol>
        </nav>

        <article className="flex max-w-3xl flex-col gap-14">
          <header className="flex flex-col gap-5">
            <h1 className="t-display">Vulnerability posture, gated by signal integrity.</h1>
            <P>IG-DCTF fuses two channels with a multiplicative gate, so a device with a perfect security record cannot compensate for a feed that is no longer real. Everything below is read from the paper&apos;s saved results, never from a re-run.</P>
            <div className="flex items-center gap-3"><SyntheticChip /><a className="text-sm text-bone-2 underline decoration-line-strong underline-offset-4 hover:text-bone" href={`${REPO_URL}/blob/main/paper/results.md`} target="_blank" rel="noreferrer noopener">results.md</a></div>
          </header>

          <section className="flex flex-col gap-4"><H2 id="problem">The problem</H2>
            <P>Scoring exposed cameras by their CVEs, authentication and patch age answers how vulnerable a device is. It cannot say whether the video behind a clean record is real. Two cameras with the same banner and the same clean record look identical to any vulnerability-only scorer, including one that is replaying a loop.</P></section>

          <section className="flex flex-col gap-4"><H2 id="channels">Two channels</H2>
            <P>Channel A is the vulnerability posture <Tex tex="T_{\mathrm{cve}}\in[0,100]" />. Channel B is feed authenticity: Tier 1 passive banner drift and Tier 2 frame liveness.</P>
            <Tex block tex={`\\mathrm{Drift}=\\frac{\\sum_f w_f\\,d_f}{\\sum_f w_f},\\qquad w=(${tr.weights.firmware},${tr.weights.server},${tr.weights.ports},${tr.weights.resolution},${tr.weights.product},${tr.weights.codec})`} />
            <Tex block tex={`L=1-\\max(w_1\\,\\mathrm{Freeze},\\;w_2\\,q,\\;w_3\\,m),\\qquad (w_1,w_2,w_3)=(${w.freeze.toFixed(1)},${w.quality.toFixed(1)},${w.spec.toFixed(1)})`} />
            <P>Signal integrity is <Tex tex="s=(1-\mathrm{Drift})\cdot L" />, or <Tex tex="s=1-\mathrm{Drift}" /> when Tier 2 is unavailable.</P></section>

          <section className="flex flex-col gap-4"><H2 id="gate">The gate</H2>
            <Tex block tex={`G(s)=\\begin{cases}1 & s\\ge ${g.thetaHigh}\\\\ ${g.floorMultiplier}+\\dfrac{0.7\\,(s-${g.thetaLow})}{${g.thetaHigh}-${g.thetaLow}} & ${g.thetaLow}\\le s<${g.thetaHigh}\\\\ ${g.floorMultiplier} & s<${g.thetaLow}\\end{cases}\\qquad T_{\\mathrm{final}}=T_{\\mathrm{cve}}\\,G(s)`} />
            <P>Below the lower threshold the score is also capped at {g.hardCap}. Tiers are high from {fact("method.tiers").highMin}, medium from {fact("method.tiers").mediumMin}, low below. Try it in the <a className="text-bone underline underline-offset-4" href="/lab">lab</a>.</P></section>

          <section className="flex flex-col gap-5"><H2 id="propositions">Five propositions</H2>
            <ol className="flex flex-col gap-6">
              <li><h3 className="font-medium text-bone">1. Non-compensation</h3><P>If <Tex tex="s\le\theta_{\mathrm{low}}" /> then <Tex tex={`T_{\\mathrm{final}}\\le ${g.hardCap}`} /> whatever the device attributes, so the event is low trust.</P></li>
              <li><h3 className="font-medium text-bone">2. Blind spot of Channel-A-only scorers</h3><P>Two events with equal Channel A inputs get the same tier from any score that is a function of those inputs alone. If their labels differ, it errs on at least one.</P></li>
              <li><h3 className="font-medium text-bone">3. Tolerance of single-field updates</h3><P>With Tier 2 clean, a change in any single banner field gives <Tex tex="\mathrm{Drift}\le 0.25" />, hence <Tex tex="s\ge 0.75" /> and <Tex tex="G\ge 0.8" />. The hard region needs <Tex tex="\mathrm{Drift}>0.5" />, which takes at least three changed fields.</P></li>
              <li><h3 className="font-medium text-bone">4. Bounded sensitivity</h3><P><Tex tex="G" /> is continuous and non-decreasing with Lipschitz constant <Tex tex="0.7/(\theta_{\mathrm{high}}-\theta_{\mathrm{low}})=2" />, so <Tex tex="|\Delta T_{\mathrm{final}}|\le 2\,T_{\mathrm{cve}}\,|\Delta s|" />.</P></li>
              <li><h3 className="font-medium text-bone">5. Tier-2 reachability</h3><P>A failure of weight <Tex tex="w" /> at full strength reaches low trust for a perfect device iff <Tex tex="1-w<0.6" />, that is <Tex tex="w>0.4" />. The old weights capped at 0.5, which is why only freezes could trip the gate before the revision.</P></li>
            </ol></section>

          <section className="flex flex-col gap-5"><H2 id="results">Results</H2>
            <div className="flex flex-wrap items-center gap-3"><P>{corpus.n} scenarios, {corpus.fabricated} fabricated and {corpus.genuine} genuine.</P><SyntheticChip /></div>
            <Table caption="Four-model comparison" head={["Model", "F1", "Accuracy", "Recall", "TP", "FP", "TN", "FN"]}
              rows={bars.map((b) => [b.label, fmt3(b.model.f1), fmt3(b.model.accuracy), fmt3(b.model.recall), b.model.tp, b.model.fp, b.model.tn, b.model.fn])}
              note={<p className="text-sm text-bone-2">Exact McNemar, IG-DCTF against CVE-only: {mc.igOnly} scenarios only IG-DCTF gets right, {mc.advOnly} only the other, <span className="num">p = {mc.p.toExponential(2)}</span> <SourceNote fact="res.mcnemar" /></p>} />
          </section>

          <section className="flex flex-col gap-5"><H2 id="ablation">Ablation and fusion control</H2>
            <Table caption="Ablation" head={["Variant", "F1", "Recall", "TP", "FP", "TN", "FN"]} rows={Object.entries(abl).map(([k, m]) => [k, fmt3(m.f1), fmt3(m.recall), m.tp, m.fp, m.tn, m.fn])}
              note={<p className="text-sm text-bone-2">The additive control is <Tex tex="T=T_{\mathrm{cve}}-70(1-s)" />, chosen so a perfect device with a fully failed Channel B ends on the same score. It is one choice of control. <SourceNote fact="res.ablation" /></p>} /></section>

          <section className="flex flex-col gap-4"><H2 id="sweep">Threshold sweep</H2>
            <P>Best F1 {fmt3(sw.bestF1)}, chosen thresholds {fmt3(sw.chosenF1)}, and {sw.within001} of {sw.total} grid points within 0.01 of the best. Every labelled scenario sits far from both thresholds, so the corpus cannot select them. <SourceNote fact="res.sweep" /></P></section>

          <section className="flex flex-col gap-5"><H2 id="tiers">Tier 1 and Tier 2 benchmarks</H2>
            <P>Tier 1: n = {t1.n}, precision {fmt3(t1.precision)}, recall {fmt3(t1.recall)}, on {t1.distinctCases} distinct cases replicated to fill the benchmark. This is a weak test of generalisation. <SourceNote fact="res.tier1" /></P>
            <Table caption="Tier 2 end-to-end" head={["Category", "n", "Flagged", "Reaches low trust", "Mean min L", "Mean T_final"]}
              rows={Object.entries(cats).map(([k, c]) => [k, c.n, c.flagged, c.low_trust, c.mean_min_L.toFixed(3), c.mean_t_final.toFixed(1)])}
              note={<p className="text-sm text-bone-2">Tier 2: n = {t2.n}, precision {fmt3(t2.precision)}, recall {fmt3(t2.recall)}, mean latency {t2.meanLatencyFrames.toFixed(1)} frames after onset. The weights were revised after seeing this benchmark. <SourceNote fact="res.tier2" /></p>} />
            <Table caption="Single-factor reachability" head={["Failure", "L", "G(L)", "T_final", "Gate status"]} rows={single.map((r) => [r.failure, r.L.toFixed(2), r.G.toFixed(2), r.T_final, r.status.replace("_", " ")])} /></section>

          <section className="flex flex-col gap-4"><H2 id="overhead">Overhead</H2>
            <P>Channel A alone takes {oh.channelAOnlyUs.toFixed(1)} microseconds per call and the full IG-DCTF {oh.igdctfUs.toFixed(1)}, in-process pure Python without I/O. <SourceNote fact="res.overhead" /></P></section>

          <section className="flex flex-col gap-4 rounded-card border border-signal/30 bg-signal-dim p-6"><H2 id="limits">Limits</H2>
            <ul className="flex flex-col gap-3">{limitLines().map((l) => <li key={l.id} className="grid grid-cols-[4.5rem_1fr] gap-3 text-sm leading-relaxed text-bone"><span className="num text-bone-2">{l.id}</span><span>{l.text}</span></li>)}</ul></section>
        </article>
      </div>
    </main>
  );
}
