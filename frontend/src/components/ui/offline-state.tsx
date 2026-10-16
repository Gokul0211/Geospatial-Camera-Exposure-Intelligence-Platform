import { API_BASE } from "@/lib/api/config";
import { cn } from "@/lib/utils";

/** The honest offline state (ground rule 2). Never replaced by sample data. */
export function OfflineState({ className, detail }: { className?: string; detail?: string }) {
  const host = API_BASE.replace(/^https?:\/\//, "");
  return (
    <div role="status" className={cn("flex flex-col gap-2 rounded-card border border-line-strong bg-ink-1 p-5", className)}>
      <p className="font-medium text-bone">Backend not reachable</p>
      <p className="max-w-[56ch] text-sm text-bone-2">
        Nothing is shown here because there is no data to show. The API is not responding at{" "}
        <code className="num text-bone">{host}</code>. Start it with{" "}
        <code className="num text-bone">python backend/main.py</code>.
      </p>
      {detail ? <p className="num text-xs text-bone-2">{detail}</p> : null}
    </div>
  );
}
