import { QualityGovernor } from "./quality";

/**
 * One RAF loop per canvas (spec 8.1). Pauses when the canvas is offscreen or the tab is hidden, caps
 * the frame rate, and feeds the quality governor. `renderOnce` serves reduced motion and invalidation.
 */
export class RenderLoop {
  private raf = 0;
  private running = false;
  private last = 0;
  private visible = true;
  private io: IntersectionObserver | null = null;
  private governor: QualityGovernor | null;
  private readonly onVis = () => this.sync();

  constructor(
    private readonly el: Element,
    private readonly frame: (timeSec: number, dtSec: number) => void,
    private opts: { fps?: number; onDegrade?: () => void; manual?: boolean },
  ) {
    this.governor = opts.onDegrade ? new QualityGovernor(opts.onDegrade) : null;
    if (typeof IntersectionObserver !== "undefined") {
      this.io = new IntersectionObserver((e) => {
        this.visible = e.some((x) => x.isIntersecting);
        this.sync();
      });
      this.io.observe(el);
    }
    document.addEventListener("visibilitychange", this.onVis);
  }

  /** Pause (true) or resume (false) the loop without disposing it. */
  setManual(manual: boolean) {
    this.opts.manual = manual;
    this.sync();
    if (manual) this.frame(performance.now() / 1000, 0);
  }

  setFps(fps: number | undefined) {
    this.opts.fps = fps;
  }

  start() {
    this.opts.manual = false;
    this.sync();
  }

  /** Render a single frame (reduced motion, or when state changed while the loop is off). */
  renderOnce(timeSec = performance.now() / 1000) {
    this.frame(timeSec, 0);
  }

  private sync() {
    const should = !this.opts.manual && this.visible && !document.hidden;
    if (should && !this.running) {
      this.running = true;
      this.last = 0;
      const tick = (now: number) => {
        if (!this.running) return;
        this.raf = requestAnimationFrame(tick);
        const minDt = this.opts.fps ? 1000 / this.opts.fps - 1 : 0;
        if (this.last && now - this.last < minDt) return;
        const dt = this.last ? now - this.last : 16.7;
        this.last = now;
        this.governor?.sample(dt);
        this.frame(now / 1000, dt / 1000);
      };
      this.raf = requestAnimationFrame(tick);
    } else if (!should && this.running) {
      this.running = false;
      cancelAnimationFrame(this.raf);
    }
  }

  get isRunning() {
    return this.running;
  }

  dispose() {
    this.running = false;
    cancelAnimationFrame(this.raf);
    this.io?.disconnect();
    document.removeEventListener("visibilitychange", this.onVis);
  }
}
