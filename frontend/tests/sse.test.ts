import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import { splitSseBuffer, streamBrief } from "@/lib/api/sse";
import { ApiError } from "@/lib/api/errors";

const body = { cluster_id: "z", city: "Mumbai", device_count: 1, device_types: [], manufacturers: [], owner_types: {}, nearby_news_headlines: [], area_description: "x" };

function streamOf(text: string, chunkSize = 7): ReadableStream<Uint8Array> {
  const enc = new TextEncoder().encode(text);
  let i = 0;
  return new ReadableStream({
    pull(c) {
      if (i >= enc.length) return c.close();
      c.enqueue(enc.slice(i, i + chunkSize));
      i += chunkSize;
    },
  });
}

async function collect(gen: AsyncGenerator<unknown>): Promise<unknown[]> {
  const out: unknown[] = [];
  for await (const m of gen) out.push(m);
  return out;
}

afterEach(() => vi.unstubAllGlobals());

describe("SSE brief stream (recorded from POST /api/brief/stream)", () => {
  it("splits events across arbitrary chunk boundaries", () => {
    const a = splitSseBuffer('data: {"type":"chunk","content":"he');
    expect(a.events).toEqual([]);
    const b = splitSseBuffer(a.rest + 'llo"}\n\ndata: {"type":"done"}\n\n');
    expect(b.events).toHaveLength(2);
  });

  it("yields text then done for the recorded no-key response", async () => {
    const recorded = readFileSync(new URL("./fixtures/brief-stream.sse.txt", import.meta.url), "utf8");
    vi.stubGlobal("fetch", vi.fn(async () => new Response(streamOf(recorded), { status: 200 })));
    const msgs = (await collect(streamBrief(body))) as { type: string }[];
    expect(msgs.map((m) => m.type)).toEqual(["text", "done"]);
  });

  it("yields chunk and error types as built in backend/services/claude_service.py (not recorded: needs an LLM key)", async () => {
    const text = 'data: {"type":"chunk","content":"a"}\n\ndata: {"type":"chunk","content":"b"}\n\ndata: {"type":"error","message":"boom"}\n\n';
    vi.stubGlobal("fetch", vi.fn(async () => new Response(streamOf(text, 5), { status: 200 })));
    const msgs = (await collect(streamBrief(body))) as { type: string }[];
    expect(msgs.map((m) => m.type)).toEqual(["chunk", "chunk", "error"]);
  });

  it("lets an HTTP error escape the parse loop as ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "No key" }), { status: 403 })));
    await expect(collect(streamBrief(body))).rejects.toMatchObject({ status: 403, detail: "No key" });
  });

  it("reports an unreachable backend as an offline ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("fetch failed"); }));
    const err = await collect(streamBrief(body)).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).offline).toBe(true);
  });

  it("skips one malformed event without ending the stream", async () => {
    const text = 'data: {oops\n\ndata: {"type":"done"}\n\n';
    vi.stubGlobal("fetch", vi.fn(async () => new Response(streamOf(text), { status: 200 })));
    const msgs = (await collect(streamBrief(body))) as { type: string }[];
    expect(msgs.map((m) => m.type)).toEqual(["done"]);
  });
});
