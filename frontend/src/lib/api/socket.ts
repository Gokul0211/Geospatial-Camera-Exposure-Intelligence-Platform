import { WS_ALERTS_URL } from "./config";
import { WsMessageSchema, type WsMessage } from "./schemas";

export type ConnectionState = "connecting" | "live" | "disconnected";

export interface AlertSocketHandlers {
  onMessage: (message: WsMessage) => void;
  onState: (state: ConnectionState, info: { retryInMs: number | null; attempt: number }) => void;
}

const MIN_DELAY_MS = 1_000;
const MAX_DELAY_MS = 30_000;
const PING_EVERY_MS = 25_000;

/** Delay before reconnect attempt `attempt` (0-based): 1 s, 2 s, 4 s ... capped at 30 s. */
export function backoffDelay(attempt: number): number {
  return Math.min(MAX_DELAY_MS, MIN_DELAY_MS * 2 ** attempt);
}

/** Parse one WebSocket frame. Unknown or malformed frames return null. */
export function parseWsFrame(data: unknown): WsMessage | null {
  if (typeof data !== "string") return null;
  let json: unknown;
  try {
    json = JSON.parse(data);
  } catch {
    return null;
  }
  const parsed = WsMessageSchema.safeParse(json);
  return parsed.success ? parsed.data : null;
}

/**
 * One WebSocket per tab to /api/ws/alerts with exponential backoff.
 * The server only broadcasts and ignores client text, so the periodic "ping" only keeps
 * intermediaries from idling the connection and surfaces a dead socket through `send` errors;
 * it is not a round-trip health check (the server does not answer).
 */
export class AlertSocket {
  private ws: WebSocket | null = null;
  private attempt = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private closedByUser = false;

  constructor(private readonly handlers: AlertSocketHandlers, private readonly url: string = WS_ALERTS_URL) {}

  connect(): void {
    this.closedByUser = false;
    this.handlers.onState("connecting", { retryInMs: null, attempt: this.attempt });
    let ws: WebSocket;
    try {
      ws = new WebSocket(this.url);
    } catch {
      this.scheduleRetry();
      return;
    }
    this.ws = ws;
    ws.onopen = () => {
      this.attempt = 0;
      this.handlers.onState("live", { retryInMs: null, attempt: 0 });
      this.pingTimer = setInterval(() => {
        try {
          if (ws.readyState === WebSocket.OPEN) ws.send("ping");
        } catch {
          ws.close();
        }
      }, PING_EVERY_MS);
    };
    ws.onmessage = (ev) => {
      const msg = parseWsFrame(ev.data);
      if (msg) this.handlers.onMessage(msg);
    };
    ws.onclose = () => {
      this.clearPing();
      this.ws = null;
      if (!this.closedByUser) this.scheduleRetry();
    };
    ws.onerror = () => ws.close();
  }

  close(): void {
    this.closedByUser = true;
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.clearPing();
    this.ws?.close();
    this.ws = null;
    this.handlers.onState("disconnected", { retryInMs: null, attempt: this.attempt });
  }

  private clearPing(): void {
    if (this.pingTimer) clearInterval(this.pingTimer);
    this.pingTimer = null;
  }

  private scheduleRetry(): void {
    const delay = backoffDelay(this.attempt);
    this.attempt += 1;
    this.handlers.onState("disconnected", { retryInMs: delay, attempt: this.attempt });
    this.retryTimer = setTimeout(() => this.connect(), delay);
  }
}
