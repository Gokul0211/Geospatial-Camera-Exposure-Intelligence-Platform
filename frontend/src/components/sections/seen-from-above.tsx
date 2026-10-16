"use client";
import * as React from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { ScrollReveal } from "@/components/motion/scroll-reveal";
import { Button } from "@/components/ui/button";
import { OfflineState } from "@/components/ui/offline-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useDevices } from "@/lib/api/hooks";
import { CONSOLE_CTA, ROUTES } from "@/lib/constants/routes";
import { ApiError } from "@/lib/api/errors";

const MapView = dynamic(() => import("@/components/map/map-view"), { ssr: false, loading: () => <Skeleton className="size-full rounded-none" /> });

const INDIA = { center: [79, 22] as [number, number], zoom: 4.1 };
const GLOBE = { center: [20, 18] as [number, number], zoom: 1.2 };

/** Seen from above: a globe that flies to India, with live data or an honest offline state (spec 7.8). */
export function SeenFromAbove() {
  const ref = React.useRef<HTMLElement | null>(null);
  const [near, setNear] = React.useState(false);
  const [fly, setFly] = React.useState(0);
  const q = useDevices("All India", near);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => {
      if (e?.isIntersecting) {
        setNear(true);
        setFly((n) => (n === 0 ? 1 : n));
      }
    }, { rootMargin: "300px 0px", threshold: 0.2 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const offline = q.error instanceof ApiError && q.error.offline;
  const count = q.data?.devices.length ?? 0;

  return (
    <section ref={ref} aria-labelledby="map-title" className="relative z-content py-24 md:py-36">
      <div className="mx-auto max-w-[1360px] px-5 md:px-8">
        <ScrollReveal className="mb-10 flex max-w-3xl flex-col gap-4">
          <h2 id="map-title" className="t-h2">Seen from above.</h2>
          <p className="t-body text-bone-2">Every marker is a device from public scan metadata. Position is an estimate, and addresses are masked to the network.</p>
        </ScrollReveal>

        <div className="relative h-[56vh] min-h-[360px] overflow-hidden rounded-card border border-line md:h-[64vh]">
          {offline ? (
            <div className="grid size-full place-items-center bg-ink-1 p-5"><OfflineState className="max-w-xl" /></div>
          ) : (
            <MapView devices={q.data?.devices ?? []} view={fly ? INDIA : GLOBE} flyKey={fly} projection="globe" label="Globe map of exposed devices over India" />
          )}
          {!offline && q.isSuccess && count === 0 && (
            <p className="absolute left-3 top-3 rounded-input border border-line bg-ink-0/85 px-3 py-2 text-sm text-bone-2">No devices in the database yet.</p>
          )}
        </div>
        <div className="mt-6 flex flex-wrap items-center gap-6">
          <Button asChild><Link href={ROUTES.console}>{CONSOLE_CTA}</Link></Button>
          <p className="text-sm text-bone-2">{q.isSuccess ? <span><span className="num text-bone">{count}</span> devices loaded from the API.</span> : offline ? "The API is offline." : "Loading devices."}</p>
        </div>
      </div>
    </section>
  );
}
