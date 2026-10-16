import { factSource, type FactKey } from "@/lib/content/facts";
import { REPO_URL } from "@/lib/api/config";
import { cn } from "@/lib/utils";

/**
 * Footnote marker that links a number to its section in paper/results.md (ground rule 3).
 * The title and accessible name carry the exact source path.
 */
export function SourceNote({ fact, className }: { fact: FactKey; className?: string }) {
  const { source, section } = factSource(fact);
  return (
    <a
      href={`${REPO_URL}/blob/main/paper/results.md`}
      target="_blank"
      rel="noreferrer noopener"
      title={`${section}. Source: ${source}`}
      aria-label={`Source: ${section}`}
      className={cn(
        "num inline-flex h-4 min-w-4 items-center justify-center rounded-chip border border-line-strong px-1 text-[0.625rem] leading-none text-bone-2 no-underline transition-colors duration-[160ms] hover:border-signal hover:text-signal",
        className,
      )}
    >
      src
    </a>
  );
}
