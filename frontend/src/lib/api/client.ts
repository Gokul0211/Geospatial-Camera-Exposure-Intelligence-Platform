import createClient, { type Middleware } from "openapi-fetch";
import type { z } from "zod";
import type { paths } from "./schema";
import { API_BASE, REQUEST_TIMEOUT_MS } from "./config";
import { ApiError, detailFrom } from "./errors";

/** fetch with a timeout; transport failures become an offline ApiError (status 0). */
async function timedFetch(input: Request | string | URL, init?: RequestInit): Promise<Response> {
  try {
    const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
    if (input instanceof Request) {
      const signal = AbortSignal.any([input.signal, timeout]);
      return await fetch(new Request(input, { signal }));
    }
    const signal = init?.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
    return await fetch(input, { ...init, signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError" && init?.signal?.aborted) throw e;
    const reason = e instanceof DOMException && e.name === "TimeoutError" ? "timed out" : "not reachable";
    throw new ApiError(0, `Backend ${reason} at ${API_BASE}. Start it with: python backend/main.py`, true);
  }
}

const throwOnHttpError: Middleware = {
  async onResponse({ response }) {
    if (!response.ok) {
      let body: unknown;
      try {
        body = await response.clone().json();
      } catch {
        body = undefined;
      }
      throw new ApiError(response.status, detailFrom(body, response.statusText || "Request failed"));
    }
    return undefined;
  },
};

/** Typed client generated from the FastAPI schema (request bodies and parameters). */
export const api = createClient<paths>({ baseUrl: API_BASE, fetch: (req) => timedFetch(req) });
api.use(throwOnHttpError);

/**
 * GET/POST helper for endpoints whose responses OpenAPI does not describe (most of this backend's
 * routes return bare dicts). The zod schema is the contract; a mismatch is a loud ApiError.
 */
export async function fetchJson<S extends z.ZodType>(
  path: string,
  schema: S,
  init?: RequestInit,
): Promise<z.infer<S>> {
  const res = await timedFetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = undefined;
    }
    throw new ApiError(res.status, detailFrom(body, res.statusText || "Request failed"));
  }
  const json: unknown = await res.json();
  const parsed = schema.safeParse(json);
  if (!parsed.success) {
    throw new ApiError(502, `Unexpected response shape from ${path}: ${parsed.error.issues[0]?.message ?? "invalid"}`);
  }
  return parsed.data;
}
