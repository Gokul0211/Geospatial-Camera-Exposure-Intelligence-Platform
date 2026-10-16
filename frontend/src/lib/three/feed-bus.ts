import type { FeedEngine } from "./feed-engine";

/** Hand-off point so sections can drive the fixed background field without prop drilling. */
type Cb = (e: FeedEngine) => void;
let engine: FeedEngine | null = null;
const waiting = new Set<Cb>();

export const feedBus = {
  set(e: FeedEngine | null) {
    engine = e;
    if (e) {
      waiting.forEach((cb) => cb(e));
      waiting.clear();
    }
  },
  /** Run `cb` now if the field exists, or as soon as it does. */
  with(cb: Cb) {
    if (engine) cb(engine);
    else waiting.add(cb);
    return () => void waiting.delete(cb);
  },
  get current() {
    return engine;
  },
};
