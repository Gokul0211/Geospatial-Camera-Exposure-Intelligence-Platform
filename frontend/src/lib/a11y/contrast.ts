/** WCAG 2.x relative luminance and contrast ratio. Used by tests and the design-system page. */
export function parseHex(hex: string): [number, number, number] {
  const m = /^#([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m || !m[1]) throw new Error(`Not a 6-digit hex colour: ${hex}`);
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function channel(c: number): number {
  const s = c / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

export function luminance(hex: string): number {
  const [r, g, b] = parseHex(hex);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

export function contrast(fg: string, bg: string): number {
  const a = luminance(fg);
  const b = luminance(bg);
  const [hi, lo] = a >= b ? [a, b] : [b, a];
  return (hi + 0.05) / (lo + 0.05);
}

/** Read `--token: #hex;` declarations out of tokens.css text. */
export function readHexTokens(css: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const m of css.matchAll(/--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) {
    if (m[1] && m[2]) out[m[1]] = m[2];
  }
  return out;
}

/** Token pairs from spec 5.1 with the minimum ratio each must meet. */
export const CONTRAST_PAIRS: readonly { fg: string; bg: string; min: number; use: string }[] = [
  { fg: "bone", bg: "ink-0", min: 7, use: "Primary text on page" },
  { fg: "bone", bg: "ink-2", min: 7, use: "Primary text on elevated surface" },
  { fg: "bone-2", bg: "ink-0", min: 7, use: "Secondary text on page" },
  { fg: "bone-2", bg: "ink-2", min: 7, use: "Secondary text on elevated surface" },
  { fg: "bone-3", bg: "ink-0", min: 3, use: "Tertiary text, 18px or larger or non-essential only" },
  { fg: "bone-3", bg: "ink-2", min: 3, use: "Tertiary text on elevated surface, non-essential only" },
  { fg: "signal", bg: "ink-0", min: 7, use: "Accent on page, focus ring" },
  { fg: "signal", bg: "ink-2", min: 7, use: "Accent on elevated surface" },
  { fg: "ink-0", bg: "signal", min: 7, use: "Primary button label" },
];
