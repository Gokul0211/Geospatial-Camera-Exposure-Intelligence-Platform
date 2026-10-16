import * as React from "react";
import { cn } from "@/lib/utils";

export type TierKey = "high_trust" | "medium_trust" | "low_trust";

const LABEL: Record<TierKey, string> = { high_trust: "High", medium_trust: "Medium", low_trust: "Low" };

/**
 * Severity is shape + one-hue ramp + text label (spec 5.1). Never traffic-light colours.
 *   High    filled circle 4px, bone-2 at 70%
 *   Medium  ring 6px, 1.5px stroke, amber at 55%
 *   Low     filled diamond 8px, amber 100%
 *   Gate    filled diamond plus one outer ring that pulses once
 *   Demo    any symbol with a dashed outline
 */
export function TierShape({
  tier,
  gateTripped = false,
  demo = false,
  pulse = false,
  size = 16,
  className,
}: {
  tier?: TierKey;
  gateTripped?: boolean;
  demo?: boolean;
  pulse?: boolean;
  size?: number;
  className?: string;
}) {
  const effective: TierKey | undefined = gateTripped ? "low_trust" : tier;
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true" focusable="false" className={cn("shrink-0", className)}>
      {effective === "high_trust" && <circle cx="8" cy="8" r="2" fill="var(--bone-2)" fillOpacity="0.7" />}
      {effective === "medium_trust" && (
        <circle cx="8" cy="8" r="2.25" fill="none" stroke="var(--signal)" strokeOpacity="0.55" strokeWidth="1.5" />
      )}
      {effective === "low_trust" && <path d="M8 4 12 8 8 12 4 8Z" fill="var(--signal)" />}
      {effective === undefined && <path d="M5 8h6" stroke="var(--bone-3)" strokeWidth="1.5" strokeLinecap="round" />}
      {gateTripped && (
        <circle
          className={pulse ? "ring-pulse-once" : undefined}
          cx="8" cy="8" r="6.4" fill="none" stroke="var(--signal)" strokeWidth="1"
        />
      )}
      {demo && (
        <circle cx="8" cy="8" r="7.3" fill="none" stroke="currentColor" strokeOpacity="0.7" strokeWidth="0.9" strokeDasharray="1.6 1.6" className="text-bone-2" />
      )}
    </svg>
  );
}

export function TierTag({
  tier,
  gateTripped = false,
  demo = false,
  pulse = false,
  score,
  className,
}: {
  tier?: TierKey;
  gateTripped?: boolean;
  demo?: boolean;
  pulse?: boolean;
  score?: number;
  className?: string;
}) {
  const text = gateTripped ? "Gate tripped" : tier ? LABEL[tier] : "Unscored";
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm text-bone", className)}>
      <TierShape tier={tier} gateTripped={gateTripped} demo={demo} pulse={pulse} />
      <span>{text}</span>
      {score !== undefined ? <span className="num text-bone-2">{score}</span> : null}
      {demo ? <span className="sr-only"> (demo scenario)</span> : null}
    </span>
  );
}
