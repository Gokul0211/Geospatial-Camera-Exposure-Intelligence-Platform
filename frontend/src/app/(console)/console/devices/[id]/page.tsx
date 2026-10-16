import type { Metadata } from "next";
import { DeviceForensics } from "@/components/console/device-forensics";

export const metadata: Metadata = { title: "Device forensics" };

export default async function DevicePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DeviceForensics id={decodeURIComponent(id)} />;
}
