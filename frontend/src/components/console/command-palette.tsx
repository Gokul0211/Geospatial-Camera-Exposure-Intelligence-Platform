"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { Dialog } from "radix-ui";
import { Kbd } from "@/components/ui/kbd";
import { maskIp } from "@/lib/api/mask-ip";
import type { Device } from "@/lib/api/normalize";
import { CITIES } from "@/lib/api/hooks";
import { useNlQuery } from "@/lib/api/console-hooks";
import { useConsoleStore } from "@/lib/state/console-store";
import { ROUTES } from "@/lib/constants/routes";
import { ApiError } from "@/lib/api/errors";

export interface PaletteActions {
  runScenario: () => void;
  openAnalytics: () => void;
  toggleHeat: () => void;
  toggleZone: () => void;
}

/** Ctrl or Cmd K (spec 10.6). Glass is allowed here. The NL query shows the filters the model returned. */
export function CommandPalette({ open, onOpenChange, devices, actions }: { open: boolean; onOpenChange: (o: boolean) => void; devices: Device[]; actions: PaletteActions }) {
  const router = useRouter();
  const [value, setValue] = React.useState("");
  const city = useConsoleStore((s) => s.city);
  const setCity = useConsoleStore((s) => s.setCity);
  const select = useConsoleStore((s) => s.selectDevice);
  const setQuery = useConsoleStore((s) => s.setQuery);
  const query = useConsoleStore((s) => s.query);
  const nl = useNlQuery();
  const close = () => { onOpenChange(false); setValue(""); };

  async function ask() {
    const res = await nl.mutateAsync({ query: value, city }).catch(() => null);
    if (!res) return;
    if (res.city && (CITIES as readonly string[]).includes(res.city)) setCity(res.city);
    setQuery({ ownerType: res.owner_type ?? null, authRequired: res.auth_required ?? null, hasCve: res.has_cve ?? null, text: res.parsed_by_ai ? res.search_text ?? null : value, explanation: res.explanation ?? "", parsedByAi: !!res.parsed_by_ai });
    close();
  }

  const shown = value.trim().length >= 2 ? devices.slice(0, 400) : [];

  return (
    <Command.Dialog open={open} onOpenChange={onOpenChange} label="Command palette" overlayClassName="fixed inset-0 z-modal bg-ink-0/70" contentClassName="glass fixed left-1/2 top-[14vh] z-modal w-[min(640px,92vw)] -translate-x-1/2 overflow-hidden rounded-card border border-line-strong">
      <Dialog.Title className="sr-only">Command palette</Dialog.Title>
      <Command.Input value={value} onValueChange={setValue} placeholder="Jump to a city, find a device, or ask in plain language" className="h-14 w-full border-b border-line bg-transparent px-5 text-base text-bone outline-none placeholder:text-bone-3" />
      <Command.List className="max-h-[52vh] overflow-y-auto p-2">
        <Command.Empty className="px-4 py-6 text-sm text-bone-2">No match. Press Enter on &ldquo;Ask&rdquo; to run it as a query.</Command.Empty>
        {value.trim().length > 3 && (
          <Command.Group heading="Ask">
            <Item value={`ask ${value}`} onSelect={ask}>{nl.isPending ? "Asking" : `Ask: ${value}`}</Item>
          </Command.Group>
        )}
        <Command.Group heading="Go to">
          {([["Home", ROUTES.home], ["Research", ROUTES.research], ["Lab", ROUTES.lab], ["Ethics", ROUTES.ethics]] as const).map(([l, href]) => <Item key={l} value={`go ${l}`} onSelect={() => { router.push(href); close(); }}>{l}</Item>)}
        </Command.Group>
        <Command.Group heading="City">
          {CITIES.map((c) => <Item key={c} value={`city ${c}`} onSelect={() => { setCity(c); close(); }}>{c}</Item>)}
        </Command.Group>
        <Command.Group heading="Actions">
          <Item value="run scenario" onSelect={() => { actions.runScenario(); close(); }}>Run scenario (demo traffic)</Item>
          <Item value="open analytics" onSelect={() => { actions.openAnalytics(); close(); }}>Open analytics</Item>
          <Item value="toggle heat layer" onSelect={() => { actions.toggleHeat(); close(); }}>Toggle heat layer</Item>
          <Item value="draw zone" onSelect={() => { actions.toggleZone(); close(); }}>Draw a zone</Item>
          {query && <Item value="clear query filter" onSelect={() => { setQuery(null); close(); }}>Clear query filter</Item>}
        </Command.Group>
        {shown.length > 0 && (
          <Command.Group heading="Devices">
            {shown.map((d) => (
              <Item key={d.id} value={`device ${maskIp(d.ip)} ${d.manufacturer ?? ""} ${d.owner_type ?? ""} ${d.id}`} onSelect={() => { select(d.id); close(); }}>
                <span className="num">{maskIp(d.ip)}</span> <span className="text-bone-2">{d.manufacturer ?? "unknown"} · {d.owner_type ?? "unknown"}</span>
              </Item>
            ))}
          </Command.Group>
        )}
      </Command.List>
      {nl.error instanceof ApiError && <p role="alert" className="border-t border-line px-5 py-3 text-sm text-bone-2">{nl.error.detail}</p>}
      <div className="flex items-center gap-3 border-t border-line px-5 py-2.5 text-xs text-bone-2"><Kbd>Enter</Kbd> select <Kbd>Esc</Kbd> close</div>
    </Command.Dialog>
  );
}

function Item({ children, value, onSelect }: { children: React.ReactNode; value: string; onSelect: () => void }) {
  return <Command.Item value={value} onSelect={onSelect} className="flex cursor-pointer items-center gap-2 rounded-input px-3 py-2.5 text-sm text-bone data-[selected=true]:bg-ink-3">{children}</Command.Item>;
}
