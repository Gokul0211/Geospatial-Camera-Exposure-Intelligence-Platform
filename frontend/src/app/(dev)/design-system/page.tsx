import { readFileSync } from "node:fs";
import { join } from "node:path";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { Logo } from "@/components/brand/logo";
import { HoodLab } from "@/components/dev/hood-lab";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CodeBlock } from "@/components/ui/code-block";
import { DemoTag } from "@/components/ui/demo-tag";
import { EmptyState } from "@/components/ui/empty-state";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { InlineError } from "@/components/ui/inline-error";
import { Kbd } from "@/components/ui/kbd";
import { OfflineState } from "@/components/ui/offline-state";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { SourceNote } from "@/components/ui/source-note";
import { Stat } from "@/components/ui/stat";
import { SyntheticChip } from "@/components/ui/synthetic-chip";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TierTag } from "@/components/ui/tier-tag";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { CONTRAST_PAIRS, contrast, readHexTokens } from "@/lib/a11y/contrast";
import { fact, fmt3 } from "@/lib/content/facts";
import { maskIp } from "@/lib/api/mask-ip";

export const metadata: Metadata = { title: "Design system", robots: { index: false } };
export const dynamic = "force-dynamic";

/** Dev-only route (not in spec section 4). 404 in production unless ENABLE_DESIGN_PAGE=true. */
function guard() {
  if (process.env.NODE_ENV === "production" && process.env.ENABLE_DESIGN_PAGE !== "true") notFound();
}

const SWATCHES = ["ink-0", "ink-1", "ink-2", "ink-3", "bone", "bone-2", "bone-3", "signal"] as const;

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-6 py-12 md:py-16">
      <h2 id={id} className="text-xl font-semibold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

export default function DesignSystemPage() {
  guard();
  const css = readFileSync(join(process.cwd(), "src/styles/tokens.css"), "utf8");
  const tokens = readHexTokens(css);
  const ig = fact("res.model.igdctf");

  return (
    <main id="main" className="mx-auto max-w-[1360px] px-5 pb-24 pt-8 md:px-8">
      <header className="flex flex-col gap-6 border-b border-line pb-10">
        <Logo />
        <h1 className="t-display max-w-[14ch]">Design system</h1>
        <p className="t-body text-bone-2">
          Tokens, primitives and the hood gauge, rendered from the same source the app uses. Development route, not part of the site.
        </p>
      </header>

      <Section id="colour" title="Colour tokens">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
          {SWATCHES.map((name) => (
            <div key={name} className="flex flex-col gap-2">
              <div className="h-20 rounded-card border border-line-strong" style={{ background: `var(--${name})` }} />
              <div className="text-sm text-bone">{name}</div>
              <div className="num text-xs text-bone-2">{tokens[name]}</div>
            </div>
          ))}
        </div>
        <div role="region" aria-label="Contrast ratios, scrollable" tabIndex={0} className="overflow-x-auto rounded-card border border-line">
          <table className="w-full min-w-[560px] text-left text-sm">
            <caption className="sr-only">WCAG contrast ratios of token pairs</caption>
            <thead className="bg-ink-1 text-bone-2">
              <tr><th className="p-3 font-medium">Pair</th><th className="p-3 font-medium">Use</th><th className="p-3 text-right font-medium">Ratio</th><th className="p-3 text-right font-medium">Minimum</th></tr>
            </thead>
            <tbody>
              {CONTRAST_PAIRS.map((p) => {
                const ratio = contrast(tokens[p.fg]!, tokens[p.bg]!);
                return (
                  <tr key={`${p.fg}-${p.bg}`} className="border-t border-line">
                    <td className="p-3 num">{p.fg} on {p.bg}</td>
                    <td className="p-3 text-bone-2">{p.use}</td>
                    <td className="p-3 text-right num">{ratio.toFixed(2)}:1</td>
                    <td className="p-3 text-right num text-bone-2">{p.min}:1</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Section>

      <Separator />
      <Section id="type" title="Typography">
        <div className="flex flex-col gap-6">
          <p className="t-display max-w-[18ch]">A secure camera can still lie.</p>
          <p className="t-h2 max-w-[24ch]">Trusted only where both hold.</p>
          <p className="t-body text-bone-2">Body text is Geist at 17 px with a 1.6 leading and a 62 character measure. Numbers use Geist Mono with tabular figures so columns line up.</p>
          <p className="num text-2xl">0.9756 · 4.69 · 1.53e-5 · 203.0.113.•</p>
        </div>
      </Section>

      <Separator />
      <Section id="controls" title="Buttons, chips and keys">
        <div className="flex flex-wrap items-center gap-3">
          <Button>Open console</Button>
          <Button variant="secondary">Read the research</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Method</Button>
          <Button disabled>Disabled</Button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button size="sm">Small</Button><Button size="md">Medium</Button><Button size="lg">Large</Button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge>Neutral</Badge><Badge tone="signal">Signal</Badge><DemoTag /><SyntheticChip />
          <span className="inline-flex items-center gap-1.5 text-sm text-bone-2">Search <Kbd>Ctrl</Kbd><Kbd>K</Kbd></span>
        </div>
        <Tooltip>
          <TooltipTrigger asChild><Button variant="secondary" size="sm" className="self-start">Hover or focus for a tooltip</Button></TooltipTrigger>
          <TooltipContent>Tooltips are solid ink-2, never glass.</TooltipContent>
        </Tooltip>
      </Section>

      <Separator />
      <Section id="severity" title="Severity: shape, one-hue ramp, label">
        <div className="grid gap-x-10 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
          <TierTag tier="high_trust" score={86} />
          <TierTag tier="medium_trust" score={62} />
          <TierTag tier="low_trust" score={41} />
          <TierTag gateTripped score={30} />
          <TierTag tier="medium_trust" demo score={62} />
          <TierTag tier="low_trust" demo score={41} />
          <TierTag gateTripped demo score={30} />
          <TierTag />
        </div>
      </Section>

      <Separator />
      <Section id="hood" title="The hood is a gauge">
        <HoodLab />
        <div className="flex flex-wrap items-end gap-6">
          {[16, 24, 32, 48, 64, 96, 160].map((s) => (
            <figure key={s} className="flex flex-col items-center gap-2">
              <HoodGauge size={s} gate={1} score={100} />
              <figcaption className="num text-xs text-bone-2">{s}px</figcaption>
            </figure>
          ))}
          {[1, 0.65, 0.3].map((g) => (
            <figure key={g} className="flex flex-col items-center gap-2">
              <HoodGauge size={96} gate={g} score={Math.round(g * 100)} />
              <figcaption className="num text-xs text-bone-2">G {g.toFixed(2)}</figcaption>
            </figure>
          ))}
        </div>
      </Section>

      <Separator />
      <Section id="stats" title="Figures with their source">
        <div className="flex flex-wrap gap-x-14 gap-y-8">
          <Stat value={fmt3(ig.f1)} label="IG-DCTF F1 on the synthetic corpus" note={<SourceNote fact="res.model.igdctf" />} />
          <Stat value={`${fact("res.mcnemar").igOnly} vs ${fact("res.mcnemar").advOnly}`} label="Scenarios where only one model is right" note={<SourceNote fact="res.mcnemar" />} />
          <Stat value={fmt3(ig.accuracy)} label="Accuracy" />
        </div>
        <SyntheticChip className="self-start" />
      </Section>

      <Separator />
      <Section id="states" title="Loading, empty, error, offline">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex flex-col gap-3 rounded-card border border-line bg-ink-1 p-5" role="group" aria-label="Loading example">
            <Skeleton className="h-4 w-1/3" /><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-5/6" />
          </div>
          <EmptyState title="No alerts yet." action={<Button size="sm" variant="secondary">Run scenario</Button>}>Run a scenario or send an event.</EmptyState>
          <InlineError title="Verdict not accepted">The backend answered 403. A detection API key is configured and this browser has none.</InlineError>
          <OfflineState />
        </div>
      </Section>

      <Separator />
      <Section id="code" title="Code and tabs">
        <Tabs defaultValue="api" className="flex flex-col gap-4">
          <TabsList aria-label="Run steps">
            <TabsTrigger value="api">API</TabsTrigger>
            <TabsTrigger value="web">Web</TabsTrigger>
          </TabsList>
          <TabsContent value="api"><CodeBlock label="Terminal" code={"pip install -r backend/requirements.txt\npython backend/main.py"} /></TabsContent>
          <TabsContent value="web"><CodeBlock label="Terminal" code={"cd frontend\nnpm install\nnpm run dev"} /></TabsContent>
        </Tabs>
        <p className="text-sm text-bone-2">
          Masked by default: <span className="num text-bone">{maskIp("203.0.113.42")}</span>. The example address is from the RFC 5737 documentation range.
        </p>
      </Section>
    </main>
  );
}
