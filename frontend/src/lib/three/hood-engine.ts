import * as THREE from "three";
import ribsVert from "@/shaders/ribs.vert";
import ribsFrag from "@/shaders/ribs.frag";
import glowVert from "@/shaders/glow.vert";
import glowFrag from "@/shaders/glow.frag";
import framesVert from "@/shaders/frames.vert";
import framesFrag from "@/shaders/frames.frag";
import { HOOD } from "@/lib/brand/hood";
import { configFor, lowerTier, type Tier } from "./quality";
import { RenderLoop } from "./loop";

/** Mark units to world units. The whole hood is 3.6 world units wide. */
const U = 0.02;

export type HoodState = {
  /** Opening of the open layout in degrees (236 * G). */
  spread: number;
  /** Opening of the closed layout in degrees. */
  from: number;
  /** 0 closed layout, 1 open layout. */
  prog: number;
  stagger: number;
  eye: number;
  ribs: number;
  ringA: number;
  ringB: number;
  arcs: number;
  overlap: number;
  frames: number;
  block: number;
  /** Camera distance. */
  dolly: number;
  /** Pointer parallax, -1..1. */
  px: number;
  py: number;
  /** Horizontal shift of the hood in world units (bleed right in the hero). */
  shiftX: number;
}

export const defaultHoodState = (): HoodState => ({
  spread: HOOD.fullSpreadDeg, from: 70.8, prog: 1, stagger: 0, eye: 1, ribs: 1, ringA: 0, ringB: 0,
  arcs: 0, overlap: 0, frames: 0.8, block: 0, dolly: 8.2, px: 0, py: 0, shiftX: 0,
});

const hex = (h: string) => new THREE.Color().setStyle(h, THREE.LinearSRGBColorSpace);

function buildRibGeometry(seg = 18): THREE.BufferGeometry {
  const rIn = HOOD.rIn * U;
  const rOut = HOOD.rOut * U;
  const zF = 0.11;
  const zB = -0.11;
  const pos: number[] = [];
  const rib: number[] = [];
  const t: number[] = [];
  const r: number[] = [];
  const z: number[] = [];
  const kind: number[] = [];
  const index: number[] = [];
  let base = 0;
  const push = (ri: number, tt: number, rr: number, zz: number, k: number) => {
    pos.push(0, 0, 0);
    rib.push(ri); t.push(tt); r.push(rr); z.push(zz); kind.push(k);
    return base++;
  };
  const quad = (a: number, b: number, c: number, d: number) => index.push(a, b, c, b, d, c);
  for (let i = 0; i < HOOD.ribCount; i++) {
    // front and back faces, outer and inner walls
    for (const [k, zz, rr0, rr1] of [[0, zF, rIn, rOut], [1, zB, rIn, rOut]] as const) {
      let prev: [number, number] | null = null;
      for (let s = 0; s <= seg; s++) {
        const tt = -1 + (2 * s) / seg;
        const a = push(i, tt, rr0, zz, k);
        const b = push(i, tt, rr1, zz, k);
        if (prev) quad(prev[0], prev[1], a, b);
        prev = [a, b];
      }
    }
    for (const [k, rr] of [[2, rOut], [3, rIn]] as const) {
      let prev: [number, number] | null = null;
      for (let s = 0; s <= seg; s++) {
        const tt = -1 + (2 * s) / seg;
        const a = push(i, tt, rr, zF, k);
        const b = push(i, tt, rr, zB, k);
        if (prev) quad(prev[0], prev[1], a, b);
        prev = [a, b];
      }
    }
    for (const [k, tt] of [[4, -1], [5, 1]] as const) {
      const a = push(i, tt, rIn, zF, k);
      const b = push(i, tt, rOut, zF, k);
      const c = push(i, tt, rIn, zB, k);
      const d = push(i, tt, rOut, zB, k);
      quad(a, b, c, d);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("aRib", new THREE.Float32BufferAttribute(rib, 1));
  g.setAttribute("aT", new THREE.Float32BufferAttribute(t, 1));
  g.setAttribute("aR", new THREE.Float32BufferAttribute(r, 1));
  g.setAttribute("aZ", new THREE.Float32BufferAttribute(z, 1));
  g.setAttribute("aKind", new THREE.Float32BufferAttribute(kind, 1));
  g.setIndex(index);
  return g;
}

/** The lens-shaped overlap of two circles: the IG-DCTF trust intersection and the eye. */
function lensShape(scale: number): THREE.Shape {
  const { r, d, half_height: h } = HOOD.eye;
  const a = Math.atan2(h, d);
  const s = new THREE.Shape();
  s.moveTo(0, -h * scale);
  s.absarc(-d * scale, 0, r * scale, -a, a, false);
  s.absarc(d * scale, 0, r * scale, Math.PI - a, Math.PI + a, false);
  return s;
}

export interface HoodEngineOpts {
  tier: Tier;
  reduced: boolean;
  onDegrade?: (t: Tier) => void;
  onLost?: () => void;
}

/**
 * Vanilla Three.js hood scene on WebGL (spec 8). One renderer, one loop. All state lives in the
 * mutable `S`, which Anime.js tweens directly; React never re-renders for animation.
 */
export class HoodEngine {
  readonly S: HoodState = defaultHoodState();
  readonly canvas: HTMLCanvasElement;
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(30, 1, 0.1, 60);
  private group = new THREE.Group();
  private ribsMat: THREE.ShaderMaterial;
  private ribsGeo: THREE.BufferGeometry;
  private eyeGeo: THREE.ExtrudeGeometry;
  private eyeMat: THREE.MeshBasicMaterial;
  private overlapGeo: THREE.ExtrudeGeometry;
  private overlapMat: THREE.MeshBasicMaterial;
  private glowMat: THREE.ShaderMaterial;
  private glowGeo: THREE.PlaneGeometry;
  private framesMat: THREE.ShaderMaterial;
  private framesGeo: THREE.BufferGeometry;
  private framesPoints: THREE.Points;
  private ringMats: THREE.MeshBasicMaterial[] = [];
  private ringGeos: THREE.BufferGeometry[] = [];
  private ringA: THREE.Mesh;
  private ringB: THREE.Mesh;
  private arcs: THREE.Mesh[] = [];
  private ribMesh: THREE.Mesh;
  private eyeMesh: THREE.Mesh;
  private glowMesh: THREE.Mesh;
  private loop: RenderLoop;
  private ro: ResizeObserver;
  private tier: Tier;
  private started = performance.now() / 1000;
  private opts: HoodEngineOpts;
  lost = false;
  /** Set by dispose(). Tweens and observers can outlive an engine; they must not draw into a freed renderer. */
  disposed = false;

  constructor(canvas: HTMLCanvasElement, opts: HoodEngineOpts) {
    this.canvas = canvas;
    this.opts = opts;
    this.tier = opts.tier;
    const cfg = configFor(this.tier);
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: cfg.antialias, alpha: true, powerPreference: "high-performance" });
    this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, cfg.dprCap));

    this.ribsGeo = buildRibGeometry();
    this.ribsMat = new THREE.ShaderMaterial({
      vertexShader: ribsVert,
      fragmentShader: ribsFrag,
      side: THREE.DoubleSide,
      transparent: true,
      uniforms: {
        uSpread: { value: 236 }, uFrom: { value: 70.8 }, uProg: { value: 1 }, uStagger: { value: 0 }, uGap: { value: HOOD.gapDeg },
        uBone: { value: hex(HOOD.colors.bone) }, uAmber: { value: hex(HOOD.colors.signal) }, uEye: { value: 1 }, uOpacity: { value: 1 },
        uLightDir: { value: new THREE.Vector3(-0.4, 0.7, 0.9) }, uHighlight: { value: new Array(9).fill(0) },
      },
    });
    this.ribMesh = new THREE.Mesh(this.ribsGeo, this.ribsMat);
    this.ribMesh.frustumCulled = false;
    this.group.add(this.ribMesh);

    this.eyeGeo = new THREE.ExtrudeGeometry(lensShape(U), { depth: 0.05, bevelEnabled: true, bevelThickness: 0.07, bevelSize: 0.04, bevelSegments: 7, curveSegments: 48 });
    this.eyeGeo.translate(0, 0, -0.025);
    this.eyeMat = new THREE.MeshBasicMaterial({ color: hex(HOOD.colors.signal) });
    this.eyeMesh = new THREE.Mesh(this.eyeGeo, this.eyeMat);
    this.group.add(this.eyeMesh);

    this.overlapGeo = new THREE.ExtrudeGeometry(lensShape(U), { depth: 0.01, bevelEnabled: false, curveSegments: 48 });
    this.overlapMat = new THREE.MeshBasicMaterial({ color: hex(HOOD.colors.signal), transparent: true, opacity: 0 });
    const overlap = new THREE.Mesh(this.overlapGeo, this.overlapMat);
    overlap.position.z = 0.19;
    overlap.name = "overlap";
    this.group.add(overlap);

    this.glowGeo = new THREE.PlaneGeometry(2.6, 2.6);
    this.glowMat = new THREE.ShaderMaterial({
      vertexShader: glowVert, fragmentShader: glowFrag, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: { uAmber: { value: hex(HOOD.colors.signal) }, uStrength: { value: 0.5 } },
    });
    this.glowMesh = new THREE.Mesh(this.glowGeo, this.glowMat);
    this.glowMesh.position.z = 0.35;
    this.group.add(this.glowMesh);

    // The two outlined circles of "Walk the gate" (drawn as thin tori)
    const ringR = HOOD.eye.r * U;
    const ringOff = HOOD.eye.d * U;
    const mkRing = (x: number, r0: number, arc: number, rot: number, opacity: number) => {
      const geo = new THREE.TorusGeometry(r0, 0.0065, 8, 160, arc);
      const mat = new THREE.MeshBasicMaterial({ color: hex(HOOD.colors.bone), transparent: true, opacity });
      const m = new THREE.Mesh(geo, mat);
      m.position.set(x, 0, 0.2);
      m.rotation.z = rot;
      this.ringGeos.push(geo);
      this.ringMats.push(mat);
      this.group.add(m);
      return m;
    };
    this.ringA = mkRing(-ringOff, ringR, Math.PI * 2, 0, 0);
    this.ringB = mkRing(ringOff, ringR, Math.PI * 2, 0, 0);
    // Tier 1 drift and Tier 2 liveness arcs on the Channel B circle
    this.arcs = [mkRing(ringOff, ringR + 0.05, Math.PI * 0.62, 0.35, 0), mkRing(ringOff, ringR + 0.05, Math.PI * 0.62, 2.6, 0)];

    // Frame particles
    const n = configFor(this.tier).frames;
    this.framesGeo = new THREE.BufferGeometry();
    const seeds = new Float32Array(n * 4);
    for (let i = 0; i < n; i++) {
      seeds[i * 4] = (Math.random() - 0.5) * Math.PI * 1.7;
      seeds[i * 4 + 1] = Math.random();
      seeds[i * 4 + 2] = Math.random();
      seeds[i * 4 + 3] = Math.random() < 0.3 ? 1 : 0;
    }
    this.framesGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    this.framesGeo.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 4));
    this.framesMat = new THREE.ShaderMaterial({
      vertexShader: framesVert, fragmentShader: framesFrag, transparent: true, depthWrite: false,
      uniforms: {
        uTime: { value: 0 }, uBlock: { value: 0 }, uFrames: { value: 0.8 }, uPixel: { value: 140 },
        uBone: { value: hex(HOOD.colors.bone) }, uAmber: { value: hex(HOOD.colors.signal) },
      },
    });
    this.framesPoints = new THREE.Points(this.framesGeo, this.framesMat);
    this.framesPoints.frustumCulled = false;
    this.group.add(this.framesPoints);

    this.group.rotation.x = -0.28;
    this.scene.add(this.group);

    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(canvas);
    this.resize();
    canvas.addEventListener("webglcontextlost", (e) => {
      e.preventDefault();
      this.lost = true;
      opts.onLost?.();
    });

    this.loop = new RenderLoop(canvas, (t) => this.draw(t), {
      manual: opts.reduced,
      onDegrade: () => {
        this.tier = lowerTier(this.tier);
        const c = configFor(this.tier);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, c.dprCap));
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
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    (this.framesMat.uniforms.uPixel as { value: number }).value = h * this.renderer.getPixelRatio() * 0.16;
    if (!this.loop?.isRunning) this.loop?.renderOnce();
  }

  private draw(timeSec: number) {
    if (this.lost || this.disposed) return;
    const S = this.S;
    const ru = this.ribsMat.uniforms;
    ru.uSpread!.value = S.spread;
    ru.uFrom!.value = S.from;
    ru.uProg!.value = S.prog;
    ru.uStagger!.value = S.stagger;
    ru.uEye!.value = S.eye;
    ru.uOpacity!.value = S.ribs;
    this.ribMesh.visible = S.ribs > 0.01;

    const k = 0.18 + 0.82 * S.eye;
    this.eyeMat.color.setRGB(0.953 * k, 0.639 * k, 0.227 * k);
    this.eyeMesh.visible = S.eye > 0.01 && S.overlap < 0.99 ? true : S.eye > 0.01;
    this.glowMat.uniforms.uStrength!.value = 0.55 * S.eye;
    this.glowMesh.visible = S.eye > 0.02;
    this.overlapMat.opacity = S.overlap;

    this.ringMats[0]!.opacity = S.ringA * 0.9;
    this.ringMats[1]!.opacity = S.ringB * 0.9;
    this.ringMats[2]!.opacity = S.arcs * 0.95;
    this.ringMats[3]!.opacity = S.arcs * 0.95;
    this.ringA.visible = S.ringA > 0.01;
    this.ringB.visible = S.ringB > 0.01;
    this.arcs.forEach((a) => (a.visible = S.arcs > 0.01));

    const fu = this.framesMat.uniforms;
    fu.uTime!.value = timeSec - this.started;
    fu.uBlock!.value = S.block;
    fu.uFrames!.value = S.frames;
    this.framesPoints.visible = S.frames > 0.01;

    // camera: dolly plus +/- 3 degrees of pointer parallax around the hood
    const yaw = (S.px * 3 * Math.PI) / 180;
    const pitch = (S.py * 3 * Math.PI) / 180;
    this.camera.position.set(Math.sin(yaw) * S.dolly, 0.25 + Math.sin(pitch) * S.dolly, Math.cos(yaw) * S.dolly);
    this.camera.lookAt(0, 0, 0);
    this.group.position.x = S.shiftX;
    this.renderer.render(this.scene, this.camera);
  }

  invalidate() {
    if (this.disposed) return;
    if (!this.loop.isRunning) this.loop.renderOnce();
  }

  get currentTier() {
    return this.tier;
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.loop.dispose();
    this.ro.disconnect();
    for (const g of [this.ribsGeo, this.eyeGeo, this.overlapGeo, this.glowGeo, this.framesGeo, ...this.ringGeos]) g.dispose();
    for (const m of [this.ribsMat, this.eyeMat, this.overlapMat, this.glowMat, this.framesMat, ...this.ringMats]) m.dispose();
    this.renderer.dispose();
    // Release the GPU context only when the canvas has really left the document. React StrictMode
    // (dev) runs mount -> cleanup -> mount on the SAME element; a lost context there makes the
    // second WebGLRenderer throw "Cannot read properties of null (reading 'precision')".
    if (!this.canvas.isConnected) this.renderer.forceContextLoss();
  }
}
