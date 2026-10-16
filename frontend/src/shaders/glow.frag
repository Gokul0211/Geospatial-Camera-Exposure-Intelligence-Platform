// Radial falloff for the eye: additive, depth-write off. The only bloom in the project (spec 9.4).
precision highp float;
uniform vec3 uAmber;
uniform float uStrength;
varying vec2 vUv;
void main() {
  float d = length(vUv - 0.5) * 2.0;
  float a = pow(clamp(1.0 - d, 0.0, 1.0), 2.4) * uStrength;
  gl_FragColor = vec4(uAmber * a, a);
}
