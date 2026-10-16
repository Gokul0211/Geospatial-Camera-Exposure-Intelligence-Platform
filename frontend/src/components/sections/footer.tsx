import Link from "next/link";
import { Logo } from "@/components/brand/logo";
import { REPO_URL } from "@/lib/api/config";
import { ROUTES } from "@/lib/constants/routes";

export function Footer() {
  return (
    <footer className="relative z-content border-t border-line bg-ink-0/80">
      <div className="mx-auto flex max-w-[1360px] flex-col gap-8 px-5 py-12 md:flex-row md:items-start md:justify-between md:px-8">
        <div className="flex max-w-sm flex-col gap-3">
          <Logo size={34} />
          <p className="text-sm text-bone-2">Trust scores for exposed cameras: vulnerability posture, gated by signal integrity.</p>
        </div>
        <nav aria-label="Footer" className="grid grid-cols-2 gap-x-12 gap-y-2 text-sm">
          <Link href={ROUTES.research} className="text-bone-2 no-underline hover:text-bone">Research</Link>
          <Link href={ROUTES.lab} className="text-bone-2 no-underline hover:text-bone">Lab</Link>
          <Link href={ROUTES.console} className="text-bone-2 no-underline hover:text-bone">Console</Link>
          <Link href={ROUTES.ethics} className="text-bone-2 no-underline hover:text-bone">Ethics</Link>
          <a href={REPO_URL} target="_blank" rel="noreferrer noopener" className="text-bone-2 no-underline hover:text-bone">GitHub</a>
          <a href={`${REPO_URL}/blob/main/paper/results.md`} target="_blank" rel="noreferrer noopener" className="text-bone-2 no-underline hover:text-bone">results.md</a>
        </nav>
      </div>
    </footer>
  );
}
