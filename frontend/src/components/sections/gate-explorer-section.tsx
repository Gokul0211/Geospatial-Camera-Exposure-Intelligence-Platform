import Link from "next/link";
import { GateExplorer } from "@/components/lab/gate-explorer";
import { ScrollReveal } from "@/components/motion/scroll-reveal";
import { ROUTES } from "@/lib/constants/routes";

export function GateExplorerSection() {
  return (
    <section aria-labelledby="explorer-title" className="relative z-content py-24 md:py-36">
      <div className="mx-auto max-w-[1360px] px-5 md:px-8">
        <ScrollReveal className="mb-10 flex max-w-3xl flex-col gap-4">
          <h2 id="explorer-title" className="t-h2">Break a feed. Watch the gate.</h2>
          <p className="t-body text-bone-2">Move the controls and the score changes with the same formula the backend uses.</p>
        </ScrollReveal>
        <GateExplorer compact />
        <p className="mt-8"><Link href={ROUTES.lab} className="text-bone underline decoration-line-strong underline-offset-[6px] hover:decoration-signal">Open the full lab</Link></p>
      </div>
    </section>
  );
}
