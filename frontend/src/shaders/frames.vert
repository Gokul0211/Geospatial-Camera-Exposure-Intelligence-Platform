// Frame particles (spec 9.3): 16:9 outlines drift toward the eye. Illustrative only.
uniform float uTime;
uniform float uBlock;   // 0..1: attack-tagged frames stop at the ribs
uniform float uFrames;  // overall visibility
uniform float uPixel;   // pixel ratio * viewport height factor
attribute vec4 aSeed;   // angle, speed, phase, attack
varying float vAlpha;
varying float vFlare;
void main() {
  float ph = fract(uTime * (0.35 + aSeed.y * 0.5) * 0.12 + aSeed.z);
  float stopAt = mix(1.0, 0.6, uBlock * aSeed.w);
  float p = min(ph, stopAt);
  vec3 start = vec3(sin(aSeed.x) * 5.2, cos(aSeed.x) * 2.6 + 0.4, 1.6 + aSeed.z * 1.5);
  vec3 pos = mix(start, vec3(0.0), pow(p, 1.3));
  vFlare = uBlock * aSeed.w * smoothstep(stopAt - 0.02, stopAt + 0.04, ph) * (1.0 - smoothstep(stopAt + 0.04, stopAt + 0.2, ph));
  vAlpha = smoothstep(0.0, 0.18, p) * (1.0 - smoothstep(0.86, 1.0, p)) * uFrames;
  vec4 mv = modelViewMatrix * vec4(pos, 1.0);
  gl_PointSize = uPixel * (0.9 + aSeed.y * 0.5) / max(0.2, -mv.z);
  gl_Position = projectionMatrix * mv;
}
