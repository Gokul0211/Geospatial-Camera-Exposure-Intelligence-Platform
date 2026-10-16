precision highp float;
uniform vec3 uBone;
uniform vec3 uAmber;
varying float vAlpha;
varying float vFlare;
void main() {
  vec2 q = gl_PointCoord - 0.5;
  vec2 half_size = vec2(0.46, 0.26);
  vec2 d = abs(q) - half_size;
  float outside = max(d.x, d.y);
  float line = smoothstep(0.045, 0.0, abs(outside));
  if (line < 0.01) discard;
  vec3 col = mix(uBone, uAmber, clamp(vFlare, 0.0, 1.0));
  gl_FragColor = vec4(col, line * vAlpha * (0.5 + vFlare));
}
