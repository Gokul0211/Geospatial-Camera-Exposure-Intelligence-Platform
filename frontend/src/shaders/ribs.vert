// Hood ribs (spec 9.2). Geometry is parametric: each vertex carries its rib index, its position
// across the rib (aT in -1..1), its radius and depth. The vertex shader derives the angle from the
// current spread, so one uniform fans the whole hood open and shut and the rib width follows
// (spread - 4.5 * 8) / 9 exactly like the SVG gauge.
uniform float uSpread;   // opening of the open layout, degrees
uniform float uFrom;     // opening of the closed layout, degrees
uniform float uProg;     // 0..1 closed to open
uniform float uStagger;  // 0..1 how much ribs lag each other
uniform float uGap;
attribute float aRib;
attribute float aT;
attribute float aR;
attribute float aZ;
attribute float aKind;
varying vec3 vN;
varying vec3 vWorld;
varying float vRib;

float centreFor(float spread, float rib, out float width) {
  width = (spread - uGap * 8.0) / 9.0;
  return -spread * 0.5 + width * 0.5 + rib * (width + uGap);
}

void main() {
  float lag = uStagger * 0.8;
  float p = clamp(uProg * (1.0 + lag) - (aRib / 8.0) * lag, 0.0, 1.0);
  float wA; float wB;
  float cA = centreFor(uFrom, aRib, wA);
  float cB = centreFor(uSpread, aRib, wB);
  float c = mix(cA, cB, p);
  float w = mix(wA, wB, p);
  float a = radians(c + aT * w * 0.5);
  float s = sin(a); float co = cos(a);
  vec3 pos = vec3(aR * s, aR * co, aZ);
  vec3 n;
  if (aKind < 0.5) n = vec3(0.0, 0.0, 1.0);
  else if (aKind < 1.5) n = vec3(0.0, 0.0, -1.0);
  else if (aKind < 2.5) n = vec3(s, co, 0.0);
  else if (aKind < 3.5) n = vec3(-s, -co, 0.0);
  else if (aKind < 4.5) n = vec3(-co, s, 0.0);
  else n = vec3(co, -s, 0.0);
  vec4 world = modelMatrix * vec4(pos, 1.0);
  vWorld = world.xyz;
  vN = normalize(mat3(modelMatrix) * n);
  vRib = aRib;
  gl_Position = projectionMatrix * viewMatrix * world;
}
