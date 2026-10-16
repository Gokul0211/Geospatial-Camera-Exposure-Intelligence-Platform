/** Motion tokens (spec 5.5). Mirrors tokens.css. Every animation uses these, never ad-hoc numbers. */
export const dur = { micro: 160, short: 260, base: 520, long: 900, scene: 1600 } as const;

/** Anime.js v4 accepts CSS-style cubic-bezier strings; the wrapper in ./index.ts resolves them. */
export const ease = {
  out: [0.16, 1, 0.3, 1],
  inOut: [0.65, 0, 0.35, 1],
} as const;

export const springParams = { stiffness: 170, damping: 22 } as const;

export const stagger = { textChar: 18, textWord: 45 } as const;
