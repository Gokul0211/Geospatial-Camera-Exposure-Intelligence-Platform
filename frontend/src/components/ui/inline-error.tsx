import * as React from "react";
import { WarningDiamond } from "@phosphor-icons/react/dist/ssr";
import { cn } from "@/lib/utils";

/** Announced error. Shape (icon) and text carry the meaning, not colour. */
export function InlineError({
  title = "Something went wrong",
  children,
  className,
}: {
  title?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div role="alert" className={cn("flex gap-3 rounded-card border border-signal/40 bg-signal-dim p-4", className)}>
      <WarningDiamond weight="regular" size={20} className="mt-0.5 text-signal" aria-hidden="true" />
      <div className="flex flex-col gap-1">
        <p className="font-medium text-bone">{title}</p>
        {children ? <p className="text-sm text-bone-2">{children}</p> : null}
      </div>
    </div>
  );
}
