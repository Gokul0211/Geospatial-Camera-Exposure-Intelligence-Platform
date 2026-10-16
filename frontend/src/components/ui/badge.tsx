import * as React from "react";
import { cn } from "@/lib/utils";

/** Square badge (chip radius 6). Text is always present; colour is never the only carrier. */
export function Badge({
  className,
  tone = "neutral",
  dashed = false,
  ...props
}: React.ComponentProps<"span"> & { tone?: "neutral" | "signal"; dashed?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-chip border px-2 py-0.5 text-xs font-medium leading-5",
        tone === "signal" ? "border-signal/45 bg-signal-dim text-signal" : "border-line-strong bg-ink-2 text-bone-2",
        dashed && "border-dashed",
        className,
      )}
      {...props}
    />
  );
}
