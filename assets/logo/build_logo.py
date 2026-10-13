"""Builds the COBRA-WATCH identity. Run: python assets/logo/build_logo.py

Mark ("hood"): nine ribs fanned over 236 degrees, like a cobra flaring its hood, around one
eye. The eye is the lens-shaped overlap of two circles: the region where the two channels
of IG-DCTF both hold (the device is secure AND its signal is authentic). The same shape
is a cobra's eye and a camera's aperture, so a camera, a hood and the trust intersection
read as one object. The ribs are annular sectors on one centre, so the mark extrudes
cleanly into 3D (see cobra-mark.geometry.json) and the hood can flare or close by
changing a single angle.

Wordmark: COBRA-WATCH drawn as monoline paths on one cap height, in the same stroke
language as the rest of the project (square caps, mitred corners, half-circle bowls).

All numbers live in this file; cobra-mark.geometry.json is written from them so the web
app and the SVGs cannot drift apart.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))

VOID = '#0A0C0B'
BONE = '#E7EAE3'
INK = '#0A0C0B'
SIGNAL = '#F3A33A'          # sodium amber: street-lamp light over a dark city; the one accent
SIGNAL_ON_LIGHT = '#A85F00'  # same hue, darkened: 4.9:1 on white

# ---- mark geometry (200 x 200 viewBox) ------------------------------------------------
CX, CY = 100, 124            # fan origin == eye centre
RIBS = 9
SPAN = 236                   # degrees, centred on "up"
GAP = 4.5                    # degrees between ribs
R_IN, R_OUT = 34, 90         # rib inner / outer radius
EYE_R = 24                   # radius of each of the two circles that make the eye
EYE_D = 13.2                 # half the distance between their centres


def sector(cx, cy, r1, r2, a0, a1):
    """Annular sector between radii r1 < r2, angles in degrees (0 = up, clockwise)."""
    def pt(r, a):
        t = math.radians(a)
        return cx + r * math.sin(t), cy - r * math.cos(t)
    x0, y0 = pt(r2, a0)
    x1, y1 = pt(r2, a1)
    x2, y2 = pt(r1, a1)
    x3, y3 = pt(r1, a0)
    large = 1 if abs(a1 - a0) > 180 else 0
    return (f'M{x0:.2f},{y0:.2f} A{r2},{r2} 0 {large} 1 {x1:.2f},{y1:.2f} '
            f'L{x2:.2f},{y2:.2f} A{r1},{r1} 0 {large} 0 {x3:.2f},{y3:.2f} Z')


def rib_angles(n=RIBS, span=SPAN, gap=GAP):
    w = (span - gap * (n - 1)) / n
    a = -span / 2
    out = []
    for _ in range(n):
        out.append((a, a + w))
        a += w + gap
    return out


def eye_path(cx, cy, r, d):
    """Lens-shaped overlap of two circles of radius r centred (cx-d, cy) and (cx+d, cy)."""
    h = math.sqrt(r * r - d * d)
    return (f'M{cx},{cy - h:.2f} A{r},{r} 0 0 1 {cx},{cy + h:.2f} '
            f'A{r},{r} 0 0 1 {cx},{cy - h:.2f} Z')


def mark_body(ink, accent, ribs=RIBS, span=SPAN, gap=GAP, r_in=R_IN, eye_r=EYE_R, eye_d=EYE_D):
    ps = ''.join(f'<path d="{sector(CX, CY, r_in, R_OUT, a0, a1)}"/>' for a0, a1 in rib_angles(ribs, span, gap))
    return (f'<g fill="{ink}">{ps}</g>'
            f'<path d="{eye_path(CX, CY, eye_r, eye_d)}" fill="{accent}"/>')


# ---- wordmark -------------------------------------------------------------------------
H = 48          # cap height (visual)
SW = 8          # stroke width


def wordmark(color, x, top, h=H, sw=SW):
    """COBRA-WATCH as stroked paths. Returns (svg, end_x). Glyph boxes are `h` tall."""
    t = top + sw / 2            # stroke centrelines sit half a stroke inside the cap box
    b = top + h - sw / 2
    m = (t + b) / 2
    r = (b - t) / 2
    gap = 0.36 * h
    parts = []
    cur = x + sw / 2

    def glyph_c(x0):
        a0, a1 = math.radians(48), math.radians(312)
        cx = x0 + r
        p0 = (cx + r * math.cos(-a0), m + r * math.sin(-a0))
        p1 = (cx + r * math.cos(-a1), m + r * math.sin(-a1))
        parts.append(f'<path d="M{p0[0]:.2f},{p0[1]:.2f} A{r:.2f},{r:.2f} 0 1 0 {p1[0]:.2f},{p1[1]:.2f}"/>')
        return x0 + 2 * r

    def glyph_o(x0):
        parts.append(f'<circle cx="{x0 + r:.2f}" cy="{m:.2f}" r="{r:.2f}"/>')
        return x0 + 2 * r

    def bowls(x0, w_top, w_bot):
        rt = (m - t) / 2
        rb = (b - m) / 2
        parts.append(f'<path d="M{x0:.2f},{t:.2f} H{x0 + w_top - rt:.2f} A{rt:.2f},{rt:.2f} 0 0 1 {x0 + w_top - rt:.2f},{m:.2f} H{x0:.2f}"/>')
        return rb

    def glyph_b(x0):
        w1, w2 = 0.62 * r * 2, 0.70 * r * 2
        bowls(x0, w1, w2)
        rb = (b - m) / 2
        parts.append(f'<path d="M{x0:.2f},{m:.2f} H{x0 + w2 - rb:.2f} A{rb:.2f},{rb:.2f} 0 0 1 {x0 + w2 - rb:.2f},{b:.2f} H{x0:.2f} M{x0:.2f},{t - sw / 2:.2f} V{b + sw / 2:.2f}"/>')
        return x0 + w2

    def glyph_r(x0):
        w1 = 0.70 * r * 2
        bowls(x0, w1, w1)
        parts.append(f'<path d="M{x0:.2f},{t - sw / 2:.2f} V{b + sw / 2:.2f}"/>')
        x1, y1 = x0 + w1 * 0.42, m
        k = (b + sw - y1) / (b + sw / 2 - y1)
        parts.append(f'<path d="M{x1:.2f},{y1:.2f} L{x1 + (x0 + w1 - x1) * k:.2f},{b + sw:.2f}"/>')
        return x0 + w1

    def glyph_a(x0):
        w = 1.12 * r * 2
        B = b + sw / 2
        e = sw
        dx = (w / 2) * e / (B - t)
        parts.append(f'<path d="M{x0 - dx:.2f},{B + e:.2f} L{x0 + w / 2:.2f},{t:.2f} L{x0 + w + dx:.2f},{B + e:.2f}" stroke-miterlimit="1.2"/>')
        yb = B - (B - t) * 0.36
        frac = (B - yb) / (B - t)
        parts.append(f'<path d="M{x0 + w / 2 * frac:.2f},{yb:.2f} H{x0 + w - w / 2 * frac:.2f}"/>')
        return x0 + w

    def glyph_w(x0):
        w = 1.9 * r * 2
        q = w / 4
        parts.append(f'<path d="M{x0:.2f},{t - sw / 2:.2f} L{x0 + q:.2f},{b:.2f} L{x0 + 2 * q:.2f},{t + (b - t) * 0.18:.2f} '
                     f'L{x0 + 3 * q:.2f},{b:.2f} L{x0 + w:.2f},{t - sw / 2:.2f}" stroke-miterlimit="1.2"/>')
        return x0 + w

    def glyph_t(x0):
        w = 1.05 * r * 2
        parts.append(f'<path d="M{x0:.2f},{t:.2f} H{x0 + w:.2f} M{x0 + w / 2:.2f},{t:.2f} V{b + sw / 2:.2f}"/>')
        return x0 + w

    def glyph_h(x0):
        w = 0.98 * r * 2
        parts.append(f'<path d="M{x0:.2f},{t - sw / 2:.2f} V{b + sw / 2:.2f} M{x0 + w:.2f},{t - sw / 2:.2f} V{b + sw / 2:.2f} M{x0:.2f},{m:.2f} H{x0 + w:.2f}"/>')
        return x0 + w

    def glyph_dash(x0):
        w = 0.6 * r * 2
        parts.append(f'<path d="M{x0:.2f},{m:.2f} H{x0 + w:.2f}"/>')
        return x0 + w

    seq = [glyph_c, glyph_o, glyph_b, glyph_r, glyph_a, glyph_dash, glyph_w, glyph_a, glyph_t, glyph_c, glyph_h]
    kern = {0: -5, 3: 2, 4: -2, 5: -2, 6: -7, 7: -2}   # optical spacing after glyph i (px)
    for i, g in enumerate(seq):
        cur = g(cur)
        if i < len(seq) - 1:
            cur += gap + kern.get(i, 0)
    end = cur + sw / 2
    clip = (f'<clipPath id="cw-cap"><rect x="{x - 10:.2f}" y="{top:.2f}" width="{end - x + 20:.2f}" height="{h}"/></clipPath>')
    svg = (clip + f'<g clip-path="url(#cw-cap)" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linejoin="miter" '
           f'stroke-linecap="butt">' + ''.join(parts) + '</g>')
    return svg, end


# ---- assets ---------------------------------------------------------------------------
def svg_wrap(w, h, body, label, bg=None):
    back = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{label}"><title>{label}</title>{back}{body}</svg>\n')


def mark_square():
    return svg_wrap(200, 200, mark_body(BONE, SIGNAL), 'COBRA-WATCH', VOID)


def mark_transparent(ink=BONE, accent=SIGNAL):
    return svg_wrap(200, 200, mark_body(ink, accent), 'COBRA-WATCH')


def favicon():
    # fewer, fatter ribs and a bigger eye so it survives 16 px
    body = mark_body(BONE, SIGNAL, ribs=7, span=232, gap=7, r_in=30, eye_r=28, eye_d=14.5)
    return svg_wrap(200, 200, f'<rect width="200" height="200" rx="40" fill="{VOID}"/>'
                    f'<g transform="translate(100 112) scale(1.0) translate(-100 -112)">{body}</g>', 'COBRA-WATCH')


def lockup(ink, accent, bg=None):
    word, wend = wordmark(ink, 236, 76)
    width = math.ceil(wend + 28)
    body = mark_body(ink, accent) + word
    tag = (f'<text x="238" y="162" font-family="\'Helvetica Neue\', Helvetica, Arial, sans-serif" font-size="11" '
           f'font-weight="700" letter-spacing="2.2" fill="{ink}" fill-opacity=".72">CAMERA TRUST, GATED BY SIGNAL INTEGRITY</text>')
    return svg_wrap(width, 200, body + tag, 'COBRA-WATCH: camera trust, gated by signal integrity', bg)


def banner():
    """1280 x 640 social preview. Mark right, wordmark and one line of copy left."""
    W, Hh = 1280, 640
    rings = ''.join(
        f'<circle cx="0" cy="0" r="{r}" fill="none" stroke="{BONE}" stroke-opacity="{o}" stroke-width="1"/>'
        for r, o in [(150, .10), (205, .075), (265, .055), (330, .04), (400, .03), (475, .02)])
    scale = 2.3
    mx, my = 960, 330          # where the eye sits
    mark = (f'<g transform="translate({mx} {my})">{rings}'
            f'<g transform="scale({scale}) translate({-CX} {-CY})">{mark_body(BONE, SIGNAL)}</g></g>')
    word, wend = wordmark(BONE, 0, 0, h=44, sw=7.5)
    ws = 1.0
    word_g = f'<g transform="translate(84 262) scale({ws})">{word}</g>'
    copy = (f'<g font-family="\'Segoe UI Variable Display\', \'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" fill="{BONE}">'
            f'<text x="86" y="372" font-size="36" font-weight="600" letter-spacing="-0.6">Trust scores for exposed cameras.</text>'
            f'<text x="86" y="420" font-size="22" font-weight="400" fill-opacity=".62">Vulnerability posture, gated by signal integrity.</text>'
            f'</g>')
    vignette = ('<defs><radialGradient id="g" cx="960" cy="330" r="560" gradientUnits="userSpaceOnUse">'
                f'<stop offset="0" stop-color="{SIGNAL}" stop-opacity=".07"/><stop offset="1" stop-color="{SIGNAL}" stop-opacity="0"/>'
                '</radialGradient></defs>'
                f'<rect width="{W}" height="{Hh}" fill="url(#g)"/>')
    return svg_wrap(W, Hh, vignette + mark + word_g + copy, 'COBRA-WATCH: trust scores for exposed cameras', VOID)


def geometry_json():
    ribs = [{'a0': round(a0, 3), 'a1': round(a1, 3)} for a0, a1 in rib_angles()]
    return json.dumps({
        'note': 'Written by assets/logo/build_logo.py. Angles in degrees, 0 = up, clockwise. Units are the 200x200 SVG viewBox.',
        'center': [CX, CY], 'ribs': ribs, 'rIn': R_IN, 'rOut': R_OUT,
        'eye': {'r': EYE_R, 'd': EYE_D, 'half_height': round(math.sqrt(EYE_R ** 2 - EYE_D ** 2), 3)},
        'colors': {'void': VOID, 'bone': BONE, 'signal': SIGNAL},
    }, indent=2) + '\n'


def write(name, text):
    with open(os.path.join(HERE, name), 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('wrote', name)


def render_png(svg_name, png_name, width, height, scale=1):
    from playwright.sync_api import sync_playwright
    svg = open(os.path.join(HERE, svg_name), encoding='utf-8').read()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': width, 'height': height}, device_scale_factor=scale)
        pg.set_content(f'<body style="margin:0;background:transparent">{svg}</body>')
        pg.screenshot(path=os.path.join(HERE, png_name), omit_background=True)
        b.close()
    print('wrote', png_name)


if __name__ == '__main__':
    write('cobra-mark.svg', mark_square())
    write('cobra-mark-transparent.svg', mark_transparent())
    write('cobra-favicon.svg', favicon())
    write('cobra-logo-dark.svg', lockup(BONE, SIGNAL))
    write('cobra-logo-light.svg', lockup(INK, SIGNAL_ON_LIGHT))
    write('cobra-banner.svg', banner())
    write('cobra-mark.geometry.json', geometry_json())
    try:
        render_png('cobra-banner.svg', 'cobra-banner.png', 1280, 640)
        render_png('cobra-mark.svg', 'cobra-mark.png', 200, 200, scale=5)
    except Exception as e:  # PNGs are a convenience; the SVGs are the source
        print('PNG render skipped:', e)
