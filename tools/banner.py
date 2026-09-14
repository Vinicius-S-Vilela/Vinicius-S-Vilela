"""Banner SVG for the GitHub profile README — text converted to outlines
so it renders identically everywhere (GitHub proxies SVGs through camo and
does not load remote fonts)."""
import os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

OUT = "/home/claude/gh/profile/assets"
os.makedirs(OUT, exist_ok=True)

F_BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
F_MED = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
F_LIGHT = "/usr/share/fonts/truetype/google-fonts/Poppins-Light.ttf"
F_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
F_MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

_cache = {}
def outline(text, font_path, size, tracking=0.0, x=0.0, y=0.0):
    if font_path not in _cache:
        f = TTFont(font_path)
        _cache[font_path] = (f.getGlyphSet(), f.getBestCmap(),
                             f["head"].unitsPerEm, f["hmtx"])
    gs, cmap, upem, hmtx = _cache[font_path]
    s = size / upem
    parts, cur = [], x
    for ch in text:
        g = cmap.get(ord(ch))
        if g is None:
            cur += size * 0.5 + tracking
            continue
        pen = SVGPathPen(gs, ntos=lambda v: f'{v:.1f}')
        gs[g].draw(TransformPen(pen, Transform(s, 0, 0, -s, cur, y)))
        c = pen.getCommands()
        if c:
            parts.append(c)
        cur += hmtx[g][0] * s + tracking
    return " ".join(parts), cur - x - (tracking if text else 0)

W, H = 1280, 340

def build(theme):
    if theme == "dark":
        bg, card, line = "#0D1117", "#161B22", "#21262D"
        name_c, sub_c, mut_c = "#F0F6FC", "#8B949E", "#484F58"
        dot1, dot2, dot3 = "#FF5F56", "#FFBD2E", "#27C93F"
    else:
        bg, card, line = "#FFFFFF", "#F6F8FA", "#D0D7DE"
        name_c, sub_c, mut_c = "#0D1117", "#57606A", "#8C959F"
        dot1, dot2, dot3 = "#FF5F56", "#FFBD2E", "#27C93F"
    GREEN, ORANGE, BLUE = "#3FB950", "#ED8B00", "#58A6FF"

    p = [f'<rect width="{W}" height="{H}" fill="{bg}"/>']

    # subtle dot grid on the left half
    for gy in range(48, H - 20, 34):
        for gx in range(56, 700, 34):
            p.append(f'<circle cx="{gx}" cy="{gy}" r="1.4" fill="{mut_c}" opacity="0.28"/>')

    # accent bar
    p.append(f'<rect x="56" y="86" width="5" height="96" rx="2.5" fill="{GREEN}"/>')

    # name
    d, _ = outline("VINICIUS", F_BOLD, 62, tracking=1.5, x=86, y=140)
    p.append(f'<path d="{d}" fill="{name_c}"/>')
    d, w2 = outline("SANTOS VILELA", F_LIGHT, 62, tracking=1.5, x=86, y=205)
    p.append(f'<path d="{d}" fill="{sub_c}"/>')

    # role
    d, wrole = outline("Software Engineer", F_MED, 25, tracking=0.4, x=88, y=255)
    p.append(f'<path d="{d}" fill="{name_c}"/>')
    d, _ = outline("  ·  Backend  ·  Java & Spring Boot", F_LIGHT, 25, tracking=0.4,
                   x=88 + wrole + 6, y=255)
    p.append(f'<path d="{d}" fill="{sub_c}"/>')

    # terminal card on the right
    tx, ty, tw, th = 752, 74, 472, 192
    p.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="10" fill="{card}" '
             f'stroke="{line}" stroke-width="1.5"/>')
    p.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="34" rx="10" fill="{card}"/>')
    p.append(f'<line x1="{tx}" y1="{ty+34}" x2="{tx+tw}" y2="{ty+34}" stroke="{line}" stroke-width="1.5"/>')
    for i, c in enumerate((dot1, dot2, dot3)):
        p.append(f'<circle cx="{tx + 22 + i*20}" cy="{ty + 17}" r="5.5" fill="{c}"/>')
    d, _ = outline("vilela@dev", F_MONO, 13, x=tx + 340, y=ty + 22)
    p.append(f'<path d="{d}" fill="{mut_c}"/>')

    lines = [
        [("$ ", GREEN), ("java", ORANGE), (" -jar ", sub_c), ("resilient-apis.jar", name_c)],
        [("  ", sub_c), ("→ Spring Boot · JPA · PostgreSQL", sub_c)],
        [("  ", sub_c), ("→ REST · OpenAPI · Docker", sub_c)],
        [("$ ", GREEN), ("status", BLUE), ("  ", sub_c), ("building, always", name_c)],
    ]
    ly = ty + 66
    for ln in lines:
        cx = tx + 22
        for txt, col in ln:
            d, adv = outline(txt, F_MONO, 15, x=cx, y=ly)
            if d:
                p.append(f'<path d="{d}" fill="{col}"/>')
            cx += adv
        ly += 30

    # cursor
    p.append(f'<rect x="{cx + 4}" y="{ly - 43}" width="9" height="17" fill="{GREEN}"/>')

    # bottom rule
    p.append(f'<rect x="0" y="{H-6}" width="{W}" height="6" fill="{GREEN}"/>')
    p.append(f'<rect x="0" y="{H-6}" width="{int(W*0.34)}" height="6" fill="{ORANGE}"/>')

    body = "\n  ".join(p)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}" role="img" '
            f'aria-label="Vinicius Santos Vilela — Software Engineer, Backend Java and Spring Boot">\n'
            f'  {body}\n</svg>\n')

for theme in ("dark", "light"):
    with open(f"{OUT}/banner-{theme}.svg", "w") as fh:
        fh.write(build(theme))
print("banner ok")
