import { API_BASE } from "./config";
import { ApiError, detailFrom } from "./errors";
import { BriefStreamMessageSchema, type BriefStreamMessage } from "./schemas";
import type { paths } from "./schema";

type BriefBody = NonNullable<paths["/api/brief/stream"]["post"]["requestBody"]>["content"]["application/json"];

/** Parse SSE text into complete `data:` payloads. Returns the unparsed remainder. */
export function splitSseBuffer(buffer: string): { events: string[]; rest: string } {
  const parts = buffer.split(/\r?\n\r?\n/);
  const rest = parts.pop() ?? "";
  const events = parts
    .map((block) =>
      block
        .split(/\r?\n/)
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trimStart())
        .join("\n"),
    )
    .filter(Boolean);
  return { events, rest };
}

/**
 * Stream a zone brief. Yields validated messages (`text | chunk | done | error`).
 * An ApiError for a non-2xx response escapes the generator: only JSON syntax errors on a single
 * event are swallowed, never transport or HTTP errors (a bug in the previous integration).
 */
export async function* streamBrief(body: BriefBody, signal?: AbortSignal): AsyncGenerator<BriefStreamMessage> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/brief/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, `Backend not reachable at ${API_BASE}.`, true);
  }
  if (!res.ok) {
    let payload: unknown;
    try {
      payload = await res.json();
    } catch {
      payload = undefined;
    }
    throw new ApiError(res.status, detailFrom(payload, res.statusText || "Request failed"));
  }
  if (!res.body) throw new ApiError(502, "The brief stream returned no body.");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { events, rest } = splitSseBuffer(buffer);
    buffer = rest;
    for (const raw of events) {
      let json: unknown;
      try {
        json = JSON.parse(raw);
      } catch {
        continue; // one malformed event does not end the stream
      }
      const parsed = BriefStreamMessageSchema.safeParse(json);
      if (parsed.success) yield parsed.data;
    }
  }
}
