import * as React from "react";
import { cn } from "@/lib/utils";

/** A figure with its label. Values are Geist Mono with tabular numerals. Not a card (spec 7.6). */
export function Stat({
  value,
  label,
  note,
  className,
}: {
  value: React.ReactNode;
  label: React.ReactNode;
  /** Typically a <SourceNote />. */
  note?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="num text-[2rem] font-medium leading-none tracking-tight text-bone md:text-[2.5rem]">
        {value}
        {note ? <span className="ml-1 align-super text-xs">{note}</span> : null}
      </div>
      <div className="max-w-[26ch] text-sm leading-snug text-bone-2">{label}</div>
    </div>
  );
}
