// The feed field (spec 9.1): a dark, low-contrast procedural "camera feed". It behaves like a
// healthy feed until a section is about a feed going wrong. Abstract, unlabelled, carries no data.
precision highp float;
#ifndef OCTAVES
#define OCTAVES 4
#endif
uniform float uTime;
uniform float uFrozenTime;
uniform vec2 uResolution;
uniform vec2 uPointer;
uniform float uIntro;
uniform float uScroll;
uniform float uDrift;
uniform float uFreeze;
uniform float uBlur;
uniform float uSpec;
uniform vec2 uAccentPos;
uniform float uAccentStrength;
uniform float uGrain;
uniform vec3 uBone;
uniform vec3 uAmber;
varying vec2 vUv;

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}
float noise(vec2 p) {
  vec2 i = floor(p); vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}
float fbm(vec2 p) {
  float a = 0.5; float s = 0.0;
  for (int i = 0; i < OCTAVES; i++) { s += a * noise(p); p *= 2.03; a *= 0.5; }
  return s;
}

float field(vec2 uv, float t, float chan) {
  vec2 q = uv;
  float band = exp(-pow((fract(uv.y * 0.9 - t * 0.045 + uScroll * 0.4) - 0.5) * 6.0, 2.0));
  q.x += band * (0.012 + uDrift * 0.09) * sin(uv.y * 40.0 + t) + chan * uDrift * 0.03;
  float lum = fbm(q * vec2(2.4, 1.5) + vec2(t * 0.018, t * 0.01));
  float lines = 0.5 + 0.5 * sin(uv.y * uResolution.y * 0.9);
  float v = 0.03 + 0.085 * lum + 0.012 * lines + band * (0.02 + uDrift * 0.06);
  return v;
}

vec3 sampleScene(vec2 uv, float t) {
  float spreadAmt = uDrift * 1.0;
  return vec3(field(uv, t, -1.0), field(uv, t, 0.0), field(uv, t, 1.0)) * (uBone * 0.95 + 0.05) * (1.0 + spreadAmt * 0.0);
}

void main() {
  vec2 uv = vUv;
  float aspect = uResolution.x / max(uResolution.y, 1.0);
  vec2 p = vec2(uv.x * aspect, uv.y);
  float t = mix(uTime, uFrozenTime, uFreeze);

  // declared-spec mismatch: coarse quantisation (wrong resolution) and a letterbox
  if (uSpec > 0.001) {
    float cells = mix(900.0, 36.0, uSpec);
    p = (floor(p * cells) + 0.5) / cells;
  }

  vec3 col;
  if (uBlur > 0.001) {
    float r = uBlur * 0.045;
    vec3 acc = vec3(0.0);
    for (int i = 0; i < 9; i++) {
      float fi = float(i);
      vec2 o = vec2(cos(fi * 0.698) , sin(fi * 0.698)) * r * (0.4 + 0.6 * fract(fi * 0.37));
      acc += sampleScene(p + o, t);
    }
    col = acc / 9.0;
  } else {
    col = sampleScene(p, t);
  }

  // one dim amber pool where the hood sits
  float d = distance(vec2(uv.x * aspect, uv.y), vec2(uAccentPos.x * aspect, uAccentPos.y));
  col += uAmber * uAccentStrength * exp(-d * d * 5.0) * 0.55;

  // pointer shifts the pool a touch
  col += uAmber * 0.01 * exp(-distance(uv, uPointer) * 5.0);

  if (uSpec > 0.001) {
    float bar = smoothstep(0.0, 0.01, abs(uv.y - 0.5) - (0.5 - 0.14 * uSpec));
    col *= 1.0 - bar;
  }

  col *= uIntro;
  col += (hash(gl_FragCoord.xy + fract(uTime) * 91.0) - 0.5) * uGrain / 255.0;
  gl_FragColor = vec4(col, 1.0);
}
