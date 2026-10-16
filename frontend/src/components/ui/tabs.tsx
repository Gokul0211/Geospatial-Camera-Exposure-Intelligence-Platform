"use client";
import * as React from "react";
import { Tabs as TabsPrimitive } from "radix-ui";
import { cn } from "@/lib/utils";

export const Tabs = TabsPrimitive.Root;

export function TabsList({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn("inline-flex items-center gap-1 rounded-full border border-line bg-ink-1 p-1", className)}
      {...props}
    />
  );
}

export function TabsTrigger({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "inline-flex h-9 items-center rounded-full px-4 text-sm text-bone-2 transition-[background-color,color] duration-[260ms] ease-(--ease-out) hover:text-bone data-[state=active]:bg-ink-3 data-[state=active]:text-bone data-[state=active]:shadow-[inset_0_0_0_1px_var(--line-strong)]",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return <TabsPrimitive.Content className={cn("outline-offset-4", className)} {...props} />;
}
