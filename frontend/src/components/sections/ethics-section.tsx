import Link from "next/link";
import { ScrollReveal } from "@/components/motion/scroll-reveal";
import { ETHICS_COLUMNS } from "@/lib/content/copy";
import { ROUTES } from "@/lib/constants/routes";

export function EthicsSection() {
  return (
    <section aria-labelledby="ethics-title" className="relative z-content py-24 md:py-36">
      <div className="mx-auto max-w-[1360px] px-5 md:px-8">
        <ScrollReveal className="mb-12 max-w-3xl"><h2 id="ethics-title" className="t-h2">Built passive on purpose.</h2></ScrollReveal>
        <ScrollReveal selector="[data-col]" stagger={80} className="grid gap-x-10 gap-y-8 md:grid-cols-3">
          {ETHICS_COLUMNS.map((c) => (
            <div key={c.title} data-col className="flex flex-col gap-3 border-t border-line pt-5">
              <h3 className="text-lg font-semibold tracking-tight">{c.title}</h3>
              {c.lines.map((l) => <p key={l} className="text-sm leading-relaxed text-bone-2">{l}</p>)}
            </div>
          ))}
        </ScrollReveal>
        <p className="mt-10"><Link href={ROUTES.ethics} className="text-bone underline decoration-line-strong underline-offset-[6px] hover:decoration-signal">Read the policy</Link></p>
      </div>
    </section>
  );
}
