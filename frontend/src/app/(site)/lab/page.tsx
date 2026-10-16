import type { Metadata } from "next";
import { LabTabs } from "@/components/lab/lab-tabs";

export const metadata: Metadata = { title: "Lab", description: "Break a feed and watch the gate. Attack simulators, scenario replay and natural-language query, all labelled demo." };

export default function LabPage() {
  return (
    <main className="relative z-content">
      <div className="mx-auto flex max-w-[1360px] flex-col gap-10 px-5 pb-28 pt-32 md:px-8">
        <header className="flex max-w-3xl flex-col gap-4">
          <h1 className="t-display">Lab.</h1>
          <p className="t-body text-bone-2">Everything here is scripted traffic and labelled demo. The explorer computes in your browser; the other tools call the running backend and show its real answers, status codes included.</p>
        </header>
        <LabTabs />
      </div>
    </main>
  );
}
