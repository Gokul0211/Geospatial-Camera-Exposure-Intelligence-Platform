import * as React from "react";
import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return <div aria-hidden="true" className={cn("skeleton rounded-input bg-ink-2", className)} {...props} />;
}
