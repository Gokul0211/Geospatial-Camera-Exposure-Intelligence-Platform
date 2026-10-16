import { REVEAL_IP } from "./config";

/**
 * The ONLY way an IP address may reach the DOM (spec 15.4, ground rule 8).
 * IPv4 -> `a.b.c.•` (the /24), IPv6 -> first three groups then `:•` (the /48).
 * `NEXT_PUBLIC_REVEAL_IP=true` returns the full address for a local session.
 *
 * NOTE: this is client-side masking only. The JSON still carries the full address until the
 * backend touchpoint B1 (server-side masking) is approved; see the Phase 1 report.
 */
export function maskIp(ip: string | null | undefined, reveal: boolean = REVEAL_IP): string {
  if (!ip) return "unknown";
  if (reveal) return ip;
  const v4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.\d{1,3}$/.exec(ip);
  if (v4) return `${v4[1]}.${v4[2]}.${v4[3]}.•`;
  if (ip.includes(":")) {
    const groups = ip.split(":").filter((g, i, a) => g !== "" || i === 0 || i === a.length - 1);
    return `${groups.slice(0, 3).join(":")}:•`;
  }
  return "masked";
}

export const IS_UNMASKED = REVEAL_IP;
