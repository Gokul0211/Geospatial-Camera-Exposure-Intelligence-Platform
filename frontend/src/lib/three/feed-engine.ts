import * as THREE from "three";
import feedVert from "@/shaders/feed.vert";
import feedFrag from "@/shaders/feed.frag";
import { configFor, lowerTier, type Tier } from "./quality";
import { RenderLoop } from "./loop";

export type FeedState = {
  intro: number;
  scroll: number;
  drift: number;
  freeze: number;
  blur: number;
  spec: number;
  accentX: number;
  accentY: number;
  accent: number;
  pointerX: number;
  pointerY: number;
}

export const defaultFeedState = (): FeedState => ({
  intro: 1, scroll: 0, drift: 0, freeze: 0, blur: 0, spec: 0,
  accentX: 0.7, accentY: 0.5, accent: 0.12, pointerX: 0.5, pointerY: 0.5,
});

const col = (hex: string) => new THREE.Color().setStyle(hex, THREE.LinearSRGBColorSpace);

/**
 * The feed shader on a fullscreen triangle. Used for the fixed background field and, with bounded
 * uniforms, for the labelled feed panes in the blind-spot section and the gate explorer.
 */
export class FeedEngine {
  readonly S: FeedState = defaultFeedState();
  readonly canvas: HTMLCanvasElement;
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private material: THREE.ShaderMaterial;
  private geometry: THREE.BufferGeometry;
  private loop: RenderLoop;
  private ro: ResizeObserver;
  private tier: Tier;
  private frozenAt = 0;
  private wasFrozen = false;
  private started = performance.now() / 1000;
  /** Seconds of simulated feed time that have advanced (stops while frozen). */
  feedTime = 0;
  lost = false;
  /** Set by dispose(). Tweens and observers can outlive an engine; they must not draw into a freed renderer. */
  disposed = false;

  constructor(canvas: HTMLCanvasElement, opts: { tier: Tier; reduced: boolean; onDegrade?: (t: Tier) => void; onLost?: () => void }) {
    this.canvas = canvas;
    this.tier = opts.tier;
    const cfg = configFor(this.tier);
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: "low-power" });
    this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, cfg.dprCap));

    this.geometry = new THREE.BufferGeometry();
    this.geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array([-1, -1, 0, 3, -1, 0, -1, 3, 0]), 3));
    this.material = new THREE.ShaderMaterial({
      vertexShader: feedVert,
      fragmentShader: feedFrag,
      defines: { OCTAVES: cfg.octaves },
      depthTest: false,
      depthWrite: false,
      uniforms: {
        uTime: { value: 0 }, uFrozenTime: { value: 0 }, uResolution: { value: new THREE.Vector2(1, 1) },
        uPointer: { value: new THREE.Vector2(0.5, 0.5) }, uIntro: { value: 1 }, uScroll: { value: 0 },
        uDrift: { value: 0 }, uFreeze: { value: 0 }, uBlur: { value: 0 }, uSpec: { value: 0 },
        uAccentPos: { value: new THREE.Vector2(0.7, 0.5) }, uAccentStrength: { value: 0.12 }, uGrain: { value: 2.2 },
        uBone: { value: col("#e7eae3") }, uAmber: { value: col("#f3a33a") },
      },
    });
    const mesh = new THREE.Mesh(this.geometry, this.material);
    mesh.frustumCulled = false;
    this.scene.add(mesh);

    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(canvas);
    this.resize();

    canvas.addEventListener("webglcontextlost", (e) => {
      e.preventDefault();
      this.lost = true;
      opts.onLost?.();
    });

    this.loop = new RenderLoop(canvas, (t) => this.draw(t), {
      fps: cfg.feedFps,
      manual: opts.reduced,
      onDegrade: () => {
        this.tier = lowerTier(this.tier);
        const c = configFor(this.tier);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, c.dprCap));
        this.material.defines.OCTAVES = c.octaves;
        this.material.needsUpdate = true;
        this.loop.setFps(c.feedFps);
        this.resize();
        opts.onDegrade?.(this.tier);
      },
    });
    if (opts.reduced) this.loop.renderOnce();
    else this.loop.start();
  }

  private resize() {
    const w = Math.max(1, this.canvas.clientWidth);
    const h = Math.max(1, this.canvas.clientHeight);
    this.renderer.setSize(w, h, false);
    const px = this.renderer.getPixelRatio();
    (this.material.uniforms.uResolution!.value as THREE.Vector2).set(w * px, h * px);
  }

  private draw(timeSec: number) {
    if (this.lost || this.disposed) return;
    const u = this.material.uniforms;
    const t = timeSec - this.started;
    const frozen = this.S.freeze > 0.5;
    if (frozen && !this.wasFrozen) this.frozenAt = this.feedTime;
    if (!frozen) this.feedTime = t - 0; // simulated time follows wall time while live
    this.wasFrozen = frozen;
    u.uTime!.value = t;
    u.uFrozenTime!.value = frozen ? this.frozenAt : t;
    u.uIntro!.value = this.S.intro;
    u.uScroll!.value = this.S.scroll;
    u.uDrift!.value = this.S.drift;
    u.uFreeze!.value = this.S.freeze;
    u.uBlur!.value = this.S.blur;
    u.uSpec!.value = this.S.spec;
    (u.uAccentPos!.value as THREE.Vector2).set(this.S.accentX, this.S.accentY);
    u.uAccentStrength!.value = this.S.accent;
    (u.uPointer!.value as THREE.Vector2).set(this.S.pointerX, this.S.pointerY);
    this.renderer.render(this.scene, this.camera);
  }

  /** Stop animating (one last frame is drawn) or resume. Used to keep at most two canvases moving. */
  setPaused(paused: boolean) {
    this.loop.setManual(paused);
  }

  /** Redraw one frame (used when the loop is off for reduced motion). */
  invalidate() {
    if (this.disposed) return;
    if (!this.loop.isRunning) this.loop.renderOnce();
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.loop.dispose();
    this.ro.disconnect();
    this.geometry.dispose();
    this.material.dispose();
    this.renderer.dispose();
    // Release the GPU context only when the canvas has really left the document. React StrictMode
    // (dev) runs mount -> cleanup -> mount on the SAME element; a lost context there makes the
    // second WebGLRenderer throw "Cannot read properties of null (reading 'precision')".
    if (!this.canvas.isConnected) this.renderer.forceContextLoss();
  }
}
