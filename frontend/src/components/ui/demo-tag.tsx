import { Badge } from "./badge";

/** Marks scripted traffic wherever it appears (ground rule 5). Dashed outline = demo. */
export function DemoTag({ className }: { className?: string }) {
  return (
    <Badge dashed tone="signal" className={className} title="Scripted traffic from a demo scenario or simulator">
      Demo scenario
    </Badge>
  );
}
