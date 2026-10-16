import type { Metadata } from "next";
import { ConsoleShell } from "@/components/console/console-shell";

export const metadata: Metadata = { title: "Console" };

export default function ConsolePage() {
  return <ConsoleShell />;
}
