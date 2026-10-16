"use client";
import * as React from "react";
import { Tooltip as TooltipPrimitive } from "radix-ui";
import { cn } from "@/lib/utils";

export const TooltipProvider = TooltipPrimitive.Provider;
export const Tooltip = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export function TooltipContent({ className, sideOffset = 8, ...props }: React.ComponentProps<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          "z-panel max-w-xs rounded-input border border-line-strong bg-ink-2 px-3 py-2 text-xs leading-snug text-bone shadow-[var(--inner-highlight)]",
          className,
        )}
        {...props}
      />
    </TooltipPrimitive.Portal>
  );
}
