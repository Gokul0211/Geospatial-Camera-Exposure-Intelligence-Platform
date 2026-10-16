/** Typed error for every non-2xx response and every transport failure. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly offline: boolean;

  constructor(status: number, detail: string, offline = false) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.offline = offline;
  }

  /** The backend refused because a detection API key is configured and the browser has none. */
  get isForbidden(): boolean {
    return this.status === 401 || this.status === 403;
  }
}

/** Pull a human-readable message out of a FastAPI error body (`{detail: string | [...]}`). */
export function detailFrom(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return d
        .map((x) => (x && typeof x === "object" && "msg" in x ? String((x as { msg: unknown }).msg) : String(x)))
        .join("; ");
    }
  }
  return fallback;
}
