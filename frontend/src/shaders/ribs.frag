// Rim lighting in bone with a soft amber bounce from the eye (spec 9.2).
precision highp float;
uniform vec3 uBone;
uniform vec3 uAmber;
uniform float uEye;
uniform float uOpacity;
uniform vec3 uLightDir;
uniform float uHighlight[9];
varying vec3 vN;
varying vec3 vWorld;
varying float vRib;

void main() {
  vec3 n = normalize(vN);
  vec3 v = normalize(cameraPosition - vWorld);
  float diff = max(dot(n, normalize(uLightDir)), 0.0);
  float hemi = 0.5 + 0.5 * n.y;
  vec3 col = uBone * (0.14 + 0.6 * diff + 0.12 * hemi);
  float fres = pow(1.0 - max(dot(n, v), 0.0), 2.6);
  col += uBone * fres * 0.5;
  vec3 toEye = vec3(0.0) - vWorld;
  float d = length(toEye);
  float bounce = exp(-d * 0.9) * uEye * 0.5;
  col += uAmber * bounce * (0.3 + 0.7 * max(dot(n, normalize(toEye)), 0.0));
  float hl = 0.0;
  for (int i = 0; i < 9; i++) { if (abs(vRib - float(i)) < 0.5) hl = uHighlight[i]; }
  col += uBone * hl * 0.25;
  gl_FragColor = vec4(col, uOpacity);
}
