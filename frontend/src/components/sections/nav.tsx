"use client";
import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { List, X } from "@phosphor-icons/react/dist/ssr";
import { Logo } from "@/components/brand/logo";
import { MagneticButton } from "@/components/motion/magnetic-button";
import { Button } from "@/components/ui/button";
import { NAV_LINKS } from "@/lib/content/copy";
import { CONSOLE_CTA, ROUTES } from "@/lib/constants/routes";
import { REPO_URL } from "@/lib/api/config";
import { animate, dur, easings, onScroll, stagger } from "@/lib/animations";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { cn } from "@/lib/utils";

/** Floating pill, hides on scroll down and returns on scroll up (Anime.js onScroll direction). */
export function Nav() {
  const pathname = usePathname();
  const reduced = usePrefersReducedMotion();
  const [open, setOpen] = React.useState(false);
  const barRef = React.useRef<HTMLElement | null>(null);
  const linksRef = React.useRef<HTMLDivElement | null>(null);
  const underlineRef = React.useRef<HTMLSpanElement | null>(null);
  const overlayRef = React.useRef<HTMLDivElement | null>(null);
  const hidden = React.useRef(false);

  // entrance: slides down 12px and fades in
  React.useEffect(() => {
    const el = barRef.current;
    if (!el) return;
    if (reduced) return;
    animate(el, { opacity: [0, 1], translateY: [-12, 0], duration: dur.base, delay: 120, ease: easings.out });
  }, [reduced]);

  // hide on scroll down, return on scroll up
  React.useEffect(() => {
    const el = barRef.current;
    if (!el || reduced) return;
    const obs = onScroll({
      target: document.body,
      repeat: true,
      onUpdate: (self) => {
        const down = !self.backward && self.velocity > 0.4;
        const up = self.backward && self.velocity > 0.2;
        if (down && !hidden.current && window.scrollY > 120) {
          hidden.current = true;
          animate(el, { translateY: -88, duration: dur.short, ease: easings.out });
        } else if ((up || window.scrollY < 60) && hidden.current) {
          hidden.current = false;
          animate(el, { translateY: 0, duration: dur.short, ease: easings.out });
        }
      },
    });
    return () => void obs.revert();
  }, [reduced]);

  // active underline slides between links
  React.useEffect(() => {
    const wrap = linksRef.current;
    const line = underlineRef.current;
    if (!wrap || !line) return;
    const active = wrap.querySelector<HTMLElement>('[data-active="true"]');
    if (!active) {
      line.style.opacity = "0";
      return;
    }
    const wr = wrap.getBoundingClientRect();
    const ar = active.getBoundingClientRect();
    line.style.opacity = "1";
    if (reduced) {
      line.style.transform = `translateX(${ar.left - wr.left}px)`;
      line.style.width = `${ar.width}px`;
    } else {
      animate(line, { translateX: ar.left - wr.left, width: ar.width, duration: dur.short, ease: easings.out });
    }
  }, [pathname, reduced]);

  // mobile overlay: staggered links, Escape closes, body scroll locked
  React.useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    if (overlayRef.current && !reduced) {
      animate(overlayRef.current.querySelectorAll("[data-item]"), { opacity: [0, 1], translateY: [16, 0], delay: stagger(60, { start: 80 }), duration: dur.base, ease: easings.out });
    }
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, reduced]);

  const isActive = (href: string) => (href.startsWith("/#") ? false : pathname === href);

  return (
    <>
      <header className="pointer-events-none fixed inset-x-0 top-4 z-nav flex justify-center px-3">
        <nav ref={barRef} aria-label="Primary" className="glass pointer-events-auto flex h-14 w-full max-w-fit items-center gap-2 rounded-full border border-line pl-4 pr-2 md:gap-6">
          <Logo size={34} className="mr-1 md:mr-4" />
          <div ref={linksRef} className="relative hidden items-center gap-1 md:flex">
            {NAV_LINKS.map((l) => (
              <Link key={l.href} href={l.href} data-active={isActive(l.href)} className="rounded-full px-3 py-2 text-sm text-bone-2 no-underline transition-colors duration-[160ms] hover:text-bone data-[active=true]:text-bone">
                {l.label}
              </Link>
            ))}
            <a href={REPO_URL} target="_blank" rel="noreferrer noopener" className="rounded-full px-3 py-2 text-sm text-bone-2 no-underline transition-colors duration-[160ms] hover:text-bone">
              GitHub
            </a>
            <span ref={underlineRef} aria-hidden="true" className="absolute -bottom-0.5 left-0 h-px w-0 bg-signal opacity-0" />
          </div>
          <MagneticButton asChild size="sm" className="hidden md:inline-flex">
            <Link href={ROUTES.console}>{CONSOLE_CTA}</Link>
          </MagneticButton>
          <button type="button" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} aria-controls="mobile-menu" onClick={() => setOpen((o) => !o)}
            className="inline-flex size-10 items-center justify-center rounded-full text-bone hover:bg-ink-2 md:hidden">
            {open ? <X size={20} /> : <List size={20} />}
          </button>
        </nav>
      </header>

      {open && (
        <div id="mobile-menu" ref={overlayRef} role="dialog" aria-modal="true" aria-label="Menu" className="fixed inset-0 z-modal flex flex-col justify-center gap-2 bg-ink-0 px-8 md:hidden">
          <button type="button" aria-label="Close menu" onClick={() => setOpen(false)} className="absolute right-5 top-5 inline-flex size-11 items-center justify-center rounded-full text-bone hover:bg-ink-2"><X size={22} /></button>
          {NAV_LINKS.map((l) => (
            <Link key={l.href} data-item href={l.href} onClick={() => setOpen(false)} className="py-3 text-3xl font-semibold tracking-tight text-bone no-underline">{l.label}</Link>
          ))}
          <a data-item href={REPO_URL} target="_blank" rel="noreferrer noopener" className="py-3 text-3xl font-semibold tracking-tight text-bone no-underline">GitHub</a>
          <Button asChild size="lg" className={cn("mt-6 self-start")} data-item>
            <Link href={ROUTES.console} onClick={() => setOpen(false)}>{CONSOLE_CTA}</Link>
          </Button>
        </div>
      )}
    </>
  );
}
