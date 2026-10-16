"use client";
import * as React from "react";
import { Check, Copy } from "@phosphor-icons/react/dist/ssr";
import { cn } from "@/lib/utils";

/** Mono code panel with a copy button that confirms success (spec 7.10). */
export function CodeBlock({ code, label, className }: { code: string; label?: string; className?: string }) {
  const [copied, setCopied] = React.useState(false);
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  React.useEffect(() => () => void (timer.current && clearTimeout(timer.current)), []);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className={cn("relative rounded-card border border-line bg-ink-1 shadow-[var(--inner-highlight)]", className)}>
      {label ? <div className="border-b border-line px-4 py-2 text-xs text-bone-2">{label}</div> : null}
      <pre tabIndex={0} aria-label={label ? `${label}, code` : "Code"} className="num overflow-x-auto p-4 pr-24 text-[0.8125rem] leading-6 text-bone">
        <code>{code}</code>
      </pre>
      <button
        type="button"
        onClick={copy}
        className="absolute right-3 top-3 inline-flex h-8 items-center gap-1.5 rounded-full border border-line-strong bg-ink-2 px-3 text-xs text-bone-2 transition-colors duration-[160ms] hover:bg-ink-3 hover:text-bone"
      >
        {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
        <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
      </button>
    </div>
  );
}
