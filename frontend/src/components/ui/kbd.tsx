import * as React from "react";
import { cn } from "@/lib/utils";

export function Kbd({ className, ...props }: React.ComponentProps<"kbd">) {
  return (
    <kbd
      className={cn(
        "inline-flex h-5 min-w-5 items-center justify-center rounded-chip border border-line-strong bg-ink-2 px-1.5 font-mono text-[0.6875rem] text-bone-2",
        className,
      )}
      {...props}
    />
  );
}
