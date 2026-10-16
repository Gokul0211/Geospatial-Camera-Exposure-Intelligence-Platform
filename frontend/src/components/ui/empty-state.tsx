import * as React from "react";
import { cn } from "@/lib/utils";

export function EmptyState({
  title,
  children,
  action,
  className,
}: {
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-start gap-2 rounded-card border border-line bg-ink-1 p-5", className)}>
      <p className="font-medium text-bone">{title}</p>
      {children ? <p className="max-w-[52ch] text-sm text-bone-2">{children}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
