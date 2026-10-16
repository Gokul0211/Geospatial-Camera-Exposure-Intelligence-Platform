import Link from "next/link";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { cn } from "@/lib/utils";

/** Mark plus wordmark. The mark is the HoodGauge at G = 1, so it can never drift from the geometry. */
export function Logo({ className, size = 36 }: { className?: string; size?: number }) {
  return (
    <Link href="/" aria-label="COBRA-WATCH home" className={cn("inline-flex items-center gap-2.5 no-underline", className)}>
      <HoodGauge gate={1} score={100} size={size} label="COBRA-WATCH mark" />
      <span className="text-[0.9375rem] font-semibold tracking-[0.18em] text-bone">COBRA-WATCH</span>
    </Link>
  );
}
