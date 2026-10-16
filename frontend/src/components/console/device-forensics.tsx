"use client";
import Link from "next/link";
import { ArrowLeft } from "@phosphor-icons/react/dist/ssr";
import { Inspector } from "@/components/console/inspector";
import { Logo } from "@/components/brand/logo";
import { ROUTES } from "@/lib/constants/routes";

/** The inspector at full width in a two-column reading layout (spec 11). */
export function DeviceForensics({ id }: { id: string }) {
  return (
    <div data-console className="min-h-dvh bg-ink-0">
      <header className="flex items-center justify-between border-b border-line px-4 py-3 md:px-8"><Logo size={34} /><Link href={ROUTES.console} className="inline-flex items-center gap-2 text-sm text-bone-2 no-underline hover:text-bone"><ArrowLeft size={16} aria-hidden="true" />Back to the console</Link></header>
      <main id="main" className="mx-auto max-w-[1100px] px-2 py-6 md:px-6">
        <h1 className="px-4 text-2xl font-semibold tracking-tight">Device forensics</h1>
        {/* The device list for "All India" is the one cache that always contains the device. */}
        <Inspector deviceId={id} city="All India" wide />
      </main>
    </div>
  );
}
