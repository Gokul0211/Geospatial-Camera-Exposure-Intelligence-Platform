import Link from "next/link";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { Button } from "@/components/ui/button";

/** Branded 404: the hood, closed at the floor (spec 4). */
export default function NotFound() {
  return (
    <main id="main" className="mx-auto flex min-h-dvh max-w-[1360px] flex-col items-start justify-center gap-6 px-5 md:px-8">
      <HoodGauge gate={0.3} score={30} size={120} label="Hood closed" />
      <h1 className="t-h2">This page does not exist.</h1>
      <p className="t-body text-bone-2">The address may be wrong, or the page has not been built yet.</p>
      <Button asChild variant="secondary">
        <Link href="/">Back to the start</Link>
      </Button>
    </main>
  );
}
