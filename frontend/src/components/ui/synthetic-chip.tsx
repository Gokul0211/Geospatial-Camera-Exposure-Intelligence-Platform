import Link from "next/link";
import { fact } from "@/lib/content/facts";
import { Badge } from "./badge";

/** Mandatory next to every accuracy figure (ground rule 3). Links to the limits block. */
export function SyntheticChip({ className }: { className?: string }) {
  const { n } = fact("res.corpus");
  return (
    <Badge tone="signal" className={className}>
      <Link href="/research#limits" className="no-underline hover:underline underline-offset-4">
        Synthetic corpus, n = <span className="num">{n}</span>
      </Link>
    </Badge>
  );
}
