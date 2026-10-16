"use client";
import * as React from "react";
import { CodeBlock } from "@/components/ui/code-block";
import { ScrollReveal } from "@/components/motion/scroll-reveal";
import { RUN_STEPS } from "@/lib/content/copy";
import { cn } from "@/lib/utils";

export function RunIt() {
  const [active, setActive] = React.useState(0);
  const refs = React.useRef<(HTMLLIElement | null)[]>([]);
  React.useEffect(() => {
    const els = refs.current.filter(Boolean) as HTMLLIElement[];
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) setActive(Number((e.target as HTMLElement).dataset.i));
    }, { rootMargin: "-40% 0px -40% 0px" });
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, []);

  return (
    <section aria-labelledby="run-title" className="relative z-content py-24 md:py-36">
      <div className="mx-auto max-w-[1360px] px-5 md:px-8">
        <ScrollReveal className="mb-12 max-w-3xl"><h2 id="run-title" className="t-h2">Run it yourself.</h2></ScrollReveal>
        <div className="grid gap-10 lg:grid-cols-2">
          <ol className="flex flex-col">
            {RUN_STEPS.map((s, i) => (
              <li key={s.title} data-i={i} ref={(el) => void (refs.current[i] = el)} className="relative flex min-h-[18vh] gap-5 pb-6">
                <span aria-hidden="true" className="flex w-6 flex-col items-center">
                  <span className={cn("mt-1 size-3 rounded-full border transition-colors duration-[260ms]", i <= active ? "border-signal bg-signal" : "border-line-strong bg-ink-2")} />
                  {i < RUN_STEPS.length - 1 && <span className={cn("mt-1 w-px flex-1 transition-colors duration-[260ms]", i < active ? "bg-signal/60" : "bg-line-strong")} />}
                </span>
                <button type="button" onClick={() => setActive(i)} aria-current={i === active ? "step" : undefined} className={cn("h-fit text-left text-xl font-medium tracking-tight transition-colors duration-[160ms]", i === active ? "text-bone" : "text-bone-2 hover:text-bone")}>
                  <span className="num mr-3 text-sm text-bone-2">{String(i + 1).padStart(2, "0")}</span>{s.title}
                </button>
              </li>
            ))}
          </ol>
          <div className="lg:sticky lg:top-28 lg:self-start">
            <div key={active} className="animate-[fade-in_160ms_ease-out]">
              <CodeBlock label={RUN_STEPS[active]!.title} code={RUN_STEPS[active]!.code} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
