#!/usr/bin/env python3
"""Saimon City · fichas físicas coleccionables (solo diseño).

Genera SVG en milímetros reales (anverso y reverso de Simonplata y Simonchis),
capas separadas de corte y grabado, PDF por cara, variantes de comprobación
a 30 mm y hojas de vista previa.

No publica ni toca el repositorio del juego.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import cairosvg
import numpy as np
from fontTools.misc.transform import Transform
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path("/workspace/sara-saimon/monedas-fisicas")
FONT_INTER = Path("/usr/share/fonts/truetype/sand-box/google/Inter/Inter-VariableFont_opsz,wght.ttf")
SCRIPT_PATH = ROOT / "src" / "build_monedas_fisicas.py"

# Sello S de las monedas del juego (iconos/simonplata.svg y simonchis.svg).
# Curva abierta, sin barra vertical: no es un signo de peso ni de dolar.
S_MARK_D = "M9.2-8.4c0-5.4-14.6-6.1-14.6.5 0 5.2 14.6 3.6 14.6 9.6 0 6.2-14.6 4.8-14.6 10.2"

# QR de ejemplo (version 1, ECC H, payload EJEMPLO). No es un codigo real.
QR_EJEMPLO = [
    [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1],
    [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1],
    [1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0],
    [1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0],
    [0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0],
    [0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0],
    [1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0],
    [1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1],
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1],
    [1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0],
    [1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0],
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0],
    [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0],
]
QR_N = 21

MIN_LINE = 0.20
MIN_TEXT = 1.20
CUT = "#FF0000"
ENG = "#000000"
NOTE = "#0055AA"

INK = 'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"'
LAYER = 'inkscape:groupmode="layer"'

_font_cache: dict = {}


def font_inter(weight: float = 750, opsz: float = 14) -> TTFont:
    key = (weight, opsz)
    if key not in _font_cache:
        base = TTFont(str(FONT_INTER))
        _font_cache[key] = instantiateVariableFont(
            base, {"wght": weight, "opsz": opsz}, inplace=False
        )
    return _font_cache[key]


def measure_text(font: TTFont, text: str, size: float, tracking: float = 0.0) -> float:
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    upem = font["head"].unitsPerEm
    scale = size / upem
    width = 0.0
    space = glyph_set[cmap[ord(" ")]].width * scale if ord(" ") in cmap else size * 0.33
    visible = 0
    for ch in text:
        if ch == " ":
            width += space
            continue
        name = cmap.get(ord(ch))
        width += glyph_set[name].width * scale if name else size * 0.4
        visible += 1
    if visible > 1:
        width += tracking * (visible - 1)
    return width


def _glyph_advance(font: TTFont, ch: str, size: float) -> float:
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font["head"].unitsPerEm
    if ch == " ":
        return glyph_set[cmap[ord(" ")]].width * scale if ord(" ") in cmap else size * 0.33
    name = cmap.get(ord(ch))
    return glyph_set[name].width * scale if name else size * 0.4


def text_paths(
    font: TTFont,
    text: str,
    size: float,
    x: float,
    y: float,
    anchor: str = "start",
    tracking: float = 0.0,
) -> list[str]:
    width = measure_text(font, text, size, tracking)
    if anchor == "middle":
        x -= width / 2
    elif anchor == "end":
        x -= width
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font["head"].unitsPerEm
    parts: list[str] = []
    pen_x = 0.0
    n_vis = 0
    for ch in text:
        if ch == " ":
            pen_x += _glyph_advance(font, ch, size)
            continue
        name = cmap.get(ord(ch))
        if not name:
            pen_x += size * 0.4
            continue
        if n_vis:
            pen_x += tracking
        n_vis += 1
        pen = SVGPathPen(glyph_set)
        tpen = TransformPen(pen, Transform(scale, 0, 0, -scale, x + pen_x, y))
        glyph_set[name].draw(tpen)
        d = pen.getCommands()
        if d:
            parts.append(d)
        pen_x += glyph_set[name].width * scale
    return parts


def paths_group(ds: list[str], fill: str = ENG, extra: str = "") -> str:
    inner = "\n".join(f'<path d="{d}" fill="{fill}"/>' for d in ds)
    return f"<g{(' ' + extra) if extra else ''}>\n{inner}\n</g>"


def flat_text(
    font: TTFont,
    text: str,
    size: float,
    x: float,
    y: float,
    anchor: str = "middle",
    tracking: float = 0.04,
    fill: str = ENG,
) -> str:
    return paths_group(text_paths(font, text, size, x, y, anchor, tracking), fill)


def arc_text(
    font: TTFont,
    text: str,
    size: float,
    cx: float,
    cy: float,
    radius: float,
    center_deg: float,
    *,
    heads_out: bool = True,
    clockwise: bool = True,
    tracking: float = 0.06,
    fill: str = ENG,
) -> str:
    """Texto sobre un arco. theta=0 a las 3, sentido antihorario, 90 grados arriba."""
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font["head"].unitsPerEm
    chars = []
    for ch in text:
        chars.append((ch, _glyph_advance(font, ch, size), ch == " "))
    total = sum(w for _, w, _ in chars)
    n_vis = sum(0 if sp else 1 for _, _, sp in chars)
    if n_vis > 1:
        total += tracking * (n_vis - 1)
    center = math.radians(center_deg)
    direction = -1 if clockwise else 1
    cursor = 0.0
    parts: list[str] = []
    vis = 0
    for ch, w, is_space in chars:
        if not is_space and vis:
            cursor += tracking
        mid = cursor + w / 2
        theta = center + direction * (mid - total / 2) / radius
        px = cx + radius * math.cos(theta)
        py = cy - radius * math.sin(theta)
        rot = 90.0 - math.degrees(theta)
        if not heads_out:
            rot += 180.0
        if is_space:
            cursor += w
            continue
        name = cmap.get(ord(ch))
        if not name:
            cursor += w
            continue
        t = (
            Transform()
            .translate(px, py)
            .rotate(math.radians(rot))
            .translate(-w / 2, 0)
            .scale(scale, -scale)
        )
        pen = SVGPathPen(glyph_set)
        tpen = TransformPen(pen, t)
        glyph_set[name].draw(tpen)
        d = pen.getCommands()
        if d:
            parts.append(d)
        vis += 1
        cursor += w
    return paths_group(parts, fill)

def f(n: float) -> str:
    return f"{n:.3f}".rstrip("0").rstrip(".")


def path(d: str, *, fill: str = "none", stroke: str | None = None, sw: float | None = None, extra: str = "") -> str:
    attrs = [f'd="{d}"', f'fill="{fill}"']
    if stroke:
        attrs.append(f'stroke="{stroke}"')
        attrs.append(f'stroke-width="{f(sw if sw is not None else MIN_LINE)}"')
        attrs.append('stroke-linecap="round"')
        attrs.append('stroke-linejoin="round"')
    if extra:
        attrs.append(extra)
    return f'<path {" ".join(attrs)}/>'


def circle(cx, cy, r, *, fill="none", stroke=None, sw=None, extra="") -> str:
    attrs = [f'cx="{f(cx)}"', f'cy="{f(cy)}"', f'r="{f(r)}"', f'fill="{fill}"']
    if stroke:
        attrs.append(f'stroke="{stroke}" stroke-width="{f(sw if sw is not None else MIN_LINE)}"')
    if extra:
        attrs.append(extra)
    return f'<circle {" ".join(attrs)}/>'


def rect(x, y, w, h, *, fill="none", stroke=None, sw=None, rx=0, extra="") -> str:
    attrs = [
        f'x="{f(x)}"', f'y="{f(y)}"', f'width="{f(w)}"', f'height="{f(h)}"',
        f'fill="{fill}"',
    ]
    if rx:
        attrs.append(f'rx="{f(rx)}"')
    if stroke:
        attrs.append(f'stroke="{stroke}" stroke-width="{f(sw if sw is not None else MIN_LINE)}"')
    if extra:
        attrs.append(extra)
    return f'<rect {" ".join(attrs)}/>'


def line(x1, y1, x2, y2, *, stroke=ENG, sw=MIN_LINE, extra="") -> str:
    return (
        f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" '
        f'stroke="{stroke}" stroke-width="{f(sw)}" stroke-linecap="round"{(" " + extra) if extra else ""}/>'
    )


def s_mark(cx: float, cy: float, height: float, stroke: float) -> str:
    """Sello S del juego, centrado en (cx, cy), altura aproximada height."""
    x0, x1, y0, y1 = -5.4, 9.2, -14.5, 11.9
    ph = y1 - y0
    s = height / ph
    ox, oy = (x0 + x1) / 2, (y0 + y1) / 2
    return (
        f'<g transform="translate({f(cx)} {f(cy)}) scale({f(s)}) translate({f(-ox)} {f(-oy)})" '
        f'fill="none" stroke="{ENG}" stroke-width="{f(stroke / s)}" '
        f'stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="{S_MARK_D}"/>'
        f"</g>"
    )


def coffee_bean(cx: float, cy: float, rx: float, ry: float, angle: float = 0) -> str:
    rx = max(rx, 0.45)
    ry = max(ry, 0.28)
    crease_sw = max(MIN_LINE, min(rx, ry) * 0.28)
    d = f"M{f(-rx * 0.15)} {f(-ry * 0.62)} C{f(rx * 0.25)} {f(-ry * 0.15)}, {f(-rx * 0.25)} {f(ry * 0.15)}, {f(rx * 0.15)} {f(ry * 0.62)}"
    return (
        f'<g transform="translate({f(cx)} {f(cy)}) rotate({f(angle)})">'
        f'<ellipse cx="0" cy="0" rx="{f(rx)}" ry="{f(ry)}" fill="none" stroke="{ENG}" stroke-width="{f(max(MIN_LINE, ry * 0.28))}"/>'
        f'{path(d, stroke=ENG, sw=crease_sw)}'
        f"</g>"
    )




def coffee_branch(cx: float, cy: float, scale: float = 1.0) -> str:
    """Rama de cafe simetrica: dos hojas arriba, dos cerezas abajo, sin solaparse."""
    sw = max(MIN_LINE, 0.30 * scale)
    s = scale

    def leaf(lx, ly, ang, length, w):
        return (
            f'<g transform="translate({f(lx)} {f(ly)}) rotate({f(ang)})">'
            f'<ellipse cx="{f(length/2)}" cy="0" rx="{f(length/2)}" ry="{f(w)}" fill="none" stroke="{ENG}" stroke-width="{f(sw)}"/>'
            f'{line(0.2*s, 0, length-0.2*s, 0, sw=max(MIN_LINE, sw*0.85))}'
            f"</g>"
        )

    # coordenadas locales respecto a (cx, cy)
    stem = path(
        f"M{f(cx)} {f(cy+1.15*s)} C{f(cx-0.15*s)} {f(cy+0.2*s)}, {f(cx+0.15*s)} {f(cy-0.5*s)}, {f(cx)} {f(cy-1.7*s)}",
        stroke=ENG, sw=sw,
    )
    leaves = (
        leaf(cx, cy - 0.45 * s, -58, 2.9 * s, 0.90 * s)
        + leaf(cx, cy - 0.45 * s, 58, 2.9 * s, 0.90 * s)
    )
    cherries = []
    for sx in (-1, 1):
        cxi = cx + sx * 0.95 * s
        cyi = cy + 1.65 * s
        r = 0.60 * s
        cherries.append(line(cx, cy + 0.85 * s, cxi, cyi - r, sw=max(MIN_LINE, sw * 0.9)))
        cherries.append(circle(cxi, cyi, max(r, 0.48), fill="none", stroke=ENG, sw=sw))
    return f"<g>{stem}{leaves}{''.join(cherries)}</g>"

def cacao_pod(cx: float, cy: float, scale: float = 1.0, angle: float = 12) -> str:
    """Mazorca de cacao, ovalada y con costillas, no se confunde con una hoja."""
    sw = max(MIN_LINE, 0.28 * scale)
    L, W = 4.8 * scale, 2.6 * scale
    body = (
        f"M0 {f(-L/2)} C{f(W*0.62)} {f(-L*0.32)}, {f(W*0.68)} {f(L*0.28)}, 0 {f(L/2)} "
        f"C{f(-W*0.68)} {f(L*0.28)}, {f(-W*0.62)} {f(-L*0.32)}, 0 {f(-L/2)}Z"
    )
    ribs = []
    for t in (-0.36, 0.0, 0.36):
        x = t * W * 0.52
        ribs.append(path(
            f"M{f(x*0.10)} {f(-L*0.36)} C{f(x)} {f(-L*0.08)}, {f(x)} {f(L*0.12)}, {f(x*0.10)} {f(L*0.38)}",
            stroke=ENG, sw=max(MIN_LINE, sw * 0.9),
        ))
    stem = path(
        f"M0 {f(-L/2)} L0 {f(-L/2-0.70*scale)}",
        stroke=ENG, sw=sw,
    )
    # pequena hoja en el rabillo, bien separada del cuerpo
    tip_leaf = (
        f'<ellipse cx="{f(0.55*scale)}" cy="{f(-L/2-0.55*scale)}" rx="{f(0.85*scale)}" ry="{f(0.38*scale)}" '
        f'transform="rotate(-35 {f(0.55*scale)} {f(-L/2-0.55*scale)})" fill="none" stroke="{ENG}" stroke-width="{f(max(MIN_LINE, sw*0.9))}"/>'
    )
    return (
        f'<g transform="translate({f(cx)} {f(cy)}) rotate({f(angle)})">'
        f'{path(body, fill="none", stroke=ENG, sw=sw)}'
        f'{"".join(ribs)}{stem}{tip_leaf}'
        f"</g>"
    )

def mountains(cx: float, cy: float, width: float, height: float) -> str:
    """Tres picos de Las Palmas, silueta original (no es el escudo nacional)."""
    sw = max(MIN_LINE, 0.28)
    w, h = width, height
    d = (
        f"M{f(cx-w/2)} {f(cy+h*0.42)}"
        f" L{f(cx-w*0.28)} {f(cy-h*0.22)}"
        f" L{f(cx-w*0.14)} {f(cy+h*0.02)}"
        f" L{f(cx-w*0.02)} {f(cy-h*0.50)}"
        f" L{f(cx+w*0.16)} {f(cy-h*0.04)}"
        f" L{f(cx+w*0.30)} {f(cy-h*0.28)}"
        f" L{f(cx+w/2)} {f(cy+h*0.42)}"
    )
    base = line(cx - w / 2, cy + h * 0.42, cx + w / 2, cy + h * 0.42, sw=sw)
    ridge = path(
        f"M{f(cx-w*0.28)} {f(cy-h*0.22)} L{f(cx-w*0.20)} {f(cy-h*0.02)}",
        stroke=ENG, sw=MIN_LINE,
    )
    ridge2 = path(
        f"M{f(cx-w*0.02)} {f(cy-h*0.50)} L{f(cx+w*0.04)} {f(cy-h*0.18)}",
        stroke=ENG, sw=MIN_LINE,
    )
    return f"<g>{path(d, stroke=ENG, sw=sw)}{base}{ridge}{ridge2}</g>"



def bahareque_house(cx: float, cy: float, width: float, height: float) -> str:
    """Casa antioquena de bahareque, alzado simple. Sin tramado cuando es pequena."""
    sw = max(MIN_LINE, 0.26)
    w, h = width, height
    x0, y0 = cx - w / 2, cy - h / 2
    roof_h = h * 0.40
    wall_h = h - roof_h
    eaves = w * 0.10
    roof = path(
        f"M{f(x0-eaves)} {f(y0+roof_h)} L{f(cx)} {f(y0)} L{f(x0+w+eaves)} {f(y0+roof_h)} Z",
        fill="none", stroke=ENG, sw=sw,
    )
    wall = rect(x0, y0 + roof_h, w, wall_h, stroke=ENG, sw=sw)
    # ventana a la izquierda
    vw, vh = max(0.55, w * 0.22), max(0.50, wall_h * 0.34)
    vx, vy = x0 + w * 0.14, y0 + roof_h + wall_h * 0.16
    window = rect(vx, vy, vw, vh, stroke=ENG, sw=MIN_LINE)
    win_cross = line(vx, vy + vh / 2, vx + vw, vy + vh / 2, sw=MIN_LINE) + line(
        vx + vw / 2, vy, vx + vw / 2, vy + vh, sw=MIN_LINE
    )
    # puerta a la derecha, apoyada en el piso
    dw, dh = max(0.55, w * 0.24), wall_h * 0.70
    dx, dy = x0 + w * 0.58, y0 + h - dh
    door = rect(dx, dy, dw, dh, stroke=ENG, sw=MIN_LINE)
    return f"<g>{roof}{wall}{window}{win_cross}{door}</g>"

def guadua_rim(cx: float, cy: float, r_out: float, r_in: float, n_bundles: int = 12) -> str:
    """Doce pares de cana de guadua en el borde: ornamental, no es un cordoncillo monetario."""
    parts = [circle(cx, cy, r_out, stroke=ENG, sw=0.30), circle(cx, cy, r_in, stroke=ENG, sw=0.26)]
    mid = (r_out + r_in) / 2
    half = (r_out - r_in) * 0.32
    sw = max(MIN_LINE, 0.26)
    for i in range(n_bundles):
        ang = math.radians(90 + i * (360 / n_bundles))
        for off in (-5.0, 5.0):
            a = ang + math.radians(off * 0.35)
            c, s = math.cos(a), -math.sin(a)
            x1, y1 = cx + (mid - half) * c, cy + (mid - half) * s
            x2, y2 = cx + (mid + half) * c, cy + (mid + half) * s
            parts.append(line(x1, y1, x2, y2, sw=sw))
    return "".join(parts)


def bean_rim(cx: float, cy: float, r_out: float, r_in: float, n: int = 12) -> str:
    """Doce granos de cafe en el borde, no es un cordoncillo de moneda legal."""
    parts = [circle(cx, cy, r_out, stroke=ENG, sw=0.30), circle(cx, cy, r_in, stroke=ENG, sw=0.26)]
    mid = (r_out + r_in) / 2
    rx = max(0.55, (r_out - r_in) * 0.28)
    ry = max(0.38, (r_out - r_in) * 0.20)
    for i in range(n):
        ang_deg = 90 + i * (360 / n)
        a = math.radians(ang_deg)
        px = cx + mid * math.cos(a)
        py = cy - mid * math.sin(a)
        parts.append(coffee_bean(px, py, rx, ry, angle=180 - ang_deg))
    return "".join(parts)


def qr_modules(x: float, y: float, size: float) -> str:
    m = size / QR_N
    parts = []
    for r, row in enumerate(QR_EJEMPLO):
        for c, bit in enumerate(row):
            if bit:
                parts.append(rect(x + c * m, y + r * m, m, m, fill=ENG, stroke=None))
    return f'<g id="qr-ejemplo">{"".join(parts)}</g>'


def qr_corners(x: float, y: float, size: float, leg: float = 1.2, sw: float = 0.25) -> str:
    parts = []
    for ox, oy, sx, sy in (
        (x, y, 1, 1),
        (x + size, y, -1, 1),
        (x, y + size, 1, -1),
        (x + size, y + size, -1, -1),
    ):
        parts.append(line(ox, oy, ox + sx * leg, oy, sw=sw))
        parts.append(line(ox, oy, ox, oy + sy * leg, sw=sw))
    return "".join(parts)

@dataclass
class Token:
    slug: str
    nombre: str
    unidad: str
    serie: str
    metal: str
    diameter: float
    qr: float
    rim: float
    quiet: float
    rim_style: str
    tema: str
    primary: bool


TOKENS = [
    Token("simonplata", "Simonplata", "SIMONPLATA", "SMP-000001", "plata", 39.0, 15.0, 2.2, 1.0, "guadua", "ciudad", True),
    Token("simonchis", "Simonchis", "SIMONCHIS", "SCH-000001", "cobre", 34.0, 14.0, 2.0, 0.9, "granos", "cosecha", True),
]


def variant_30(tok: Token) -> Token:
    return Token(
        slug=tok.slug, nombre=tok.nombre, unidad=tok.unidad, serie=tok.serie,
        metal=tok.metal, diameter=30.0, qr=12.0, rim=1.8, quiet=0.8,
        rim_style=tok.rim_style, tema=tok.tema, primary=False,
    )


def text_sizes(tok: Token) -> dict:
    d = tok.diameter
    rim_t = max(MIN_TEXT, 1.40 if d >= 36 else 1.30 if d >= 33 else 1.22)
    banner = max(MIN_TEXT, 1.50 if d >= 36 else 1.38 if d >= 33 else 1.24)
    legal = max(MIN_TEXT, 1.28 if d >= 36 else 1.24 if d >= 33 else 1.20)
    serial = max(MIN_TEXT, 1.45 if d >= 36 else 1.35 if d >= 33 else 1.22)
    label = max(MIN_TEXT, 1.20)
    ejemplo = max(MIN_TEXT, 1.50 if d >= 34 else 1.30)
    return dict(rim=rim_t, banner=banner, legal=legal, serial=serial, label=label, ejemplo=ejemplo)


def rings(tok: Token) -> dict:
    d = tok.diameter
    cx = cy = d / 2
    r_cut = d / 2
    r_out = d / 2 - 0.18
    r_in = d / 2 - tok.rim
    ts = text_sizes(tok)
    r_text = r_in - 0.28 - ts["rim"] * 0.55
    r_field = r_text - ts["rim"] * 0.55 - 0.30
    return dict(cx=cx, cy=cy, r_cut=r_cut, r_out=r_out, r_in=r_in, r_text=r_text, r_field=r_field, ts=ts)


def rim_art(tok: Token, R: dict) -> str:
    if tok.rim_style == "guadua":
        return guadua_rim(R["cx"], R["cy"], R["r_out"], R["r_in"])
    return bean_rim(R["cx"], R["cy"], R["r_out"], R["r_in"])


def legal_banner(cx, cy, width, font_b, font_l, ts) -> str:
    h1, h2 = ts["banner"], ts["legal"]
    pad_y, gap = 0.28, 0.18
    box_h = pad_y + h1 + gap + h2 * 0.85 + pad_y
    box_w = width
    x, y = cx - box_w / 2, cy - box_h / 2
    y1 = y + pad_y + h1 * 0.82
    y2 = y1 + gap + h2 * 0.95
    return (
        '<g id="leyenda-legal">'
        f'{rect(x, y, box_w, box_h, stroke=ENG, sw=0.26, rx=0.35)}'
        f'{flat_text(font_b, "FICHA COLECCIONABLE", h1, cx, y1, "middle", 0.05)}'
        f'{flat_text(font_l, "SIN VALOR MONETARIO", h2, cx, y2, "middle", 0.07)}'
        "</g>"
    )


def build_obverse_engrave(tok: Token) -> str:
    R = rings(tok)
    cx, cy, ts = R["cx"], R["cy"], R["ts"]
    d = tok.diameter
    font_rim = font_inter(800, 12)
    font_ban = font_inter(800, 14)
    font_leg = font_inter(700, 12)
    k = d / 39.0
    parts = [rim_art(tok, R)]
    parts.append(arc_text(
        font_rim, f"SAIMON CITY  ·  {tok.unidad}", ts["rim"],
        cx, cy, R["r_text"], 90, heads_out=True, clockwise=True, tracking=0.10,
    ))
    lower = ts["rim"] * 0.92
    if lower < MIN_TEXT:
        lower = MIN_TEXT
    parts.append(arc_text(
        font_rim, "FICHA  ·  SAIMON CITY", lower,
        cx, cy, R["r_text"], 270, heads_out=False, clockwise=False, tracking=0.10,
    ))
    s_h = (11.8 if tok.tema == "ciudad" else 10.4) * k
    s_h = min(s_h, R["r_field"] * 1.12)
    s_stroke = max(0.90, 1.35 * k)
    s_cy = cy - 1.35 * k
    if tok.tema == "ciudad":
        # montanas bajas, detras de la parte inferior de la S; plantas a los lados, en el cielo
        parts.append(mountains(cx, cy + 2.2 * k, 14.8 * k, 5.2 * k))
        parts.append(coffee_branch(cx - 9.0 * k, cy - 2.2 * k, 0.95 * k))
        parts.append(cacao_pod(cx + 9.0 * k, cy - 1.6 * k, 0.98 * k, 10))
        parts.append(s_mark(cx, s_cy, s_h, s_stroke))
    else:
        # cosecha: sin sierra ancha; loma baja, cafe y cacao mas grandes a los lados
        parts.append(mountains(cx, cy + 3.0 * k, 11.0 * k, 3.4 * k))
        parts.append(coffee_branch(cx - 8.6 * k, cy - 1.1 * k, 1.00 * k))
        parts.append(cacao_pod(cx + 8.6 * k, cy - 1.0 * k, 1.08 * k, 8))
        parts.append(s_mark(cx, s_cy, s_h, s_stroke))
    banner_cy = cy + R["r_field"] * 0.62
    banner_w = min(R["r_field"] * 1.70, d * 0.62)
    max_y = cy + R["r_field"] - 0.15
    box_h = 0.28 + ts["banner"] + 0.18 + ts["legal"] * 0.85 + 0.28
    if banner_cy + box_h / 2 > max_y:
        banner_cy = max_y - box_h / 2
    parts.append(legal_banner(cx, banner_cy, banner_w, font_ban, font_leg, ts))
    return "".join(parts)


def build_reverse_engrave(tok: Token) -> str:
    R = rings(tok)
    cx, cy, ts = R["cx"], R["cy"], R["ts"]
    d = tok.diameter
    font_rim = font_inter(800, 12)
    font_ser = font_inter(750, 14)
    font_lab = font_inter(700, 12)
    font_ej = font_inter(800, 14)
    k = d / 39.0
    parts = [rim_art(tok, R)]
    parts.append(arc_text(
        font_rim, "COLECCIONABLE  ·  NO ES MONEDA LEGAL", ts["rim"],
        cx, cy, R["r_text"], 90, heads_out=True, clockwise=True, tracking=0.07,
    ))
    lower = ts["rim"] * 0.92
    if lower < MIN_TEXT:
        lower = MIN_TEXT
    parts.append(arc_text(
        font_rim, f"SAIMON CITY  ·  {tok.unidad}", lower,
        cx, cy, R["r_text"], 270, heads_out=False, clockwise=False, tracking=0.08,
    ))
    qr = tok.qr
    quiet = tok.quiet
    qr_x, qr_y = cx - qr / 2, cy - qr / 2
    space_above = (cy - qr / 2 - quiet) - (cy - R["r_field"])
    if space_above >= 2.6:
        ey = cy - qr / 2 - quiet - space_above * 0.48
        eh = min(3.4 * k if k > 0.8 else 2.6, space_above - 0.35)
        ew = eh * 1.15
        if tok.tema == "ciudad":
            parts.append(bahareque_house(cx, ey, ew, eh))
        else:
            parts.append(coffee_bean(cx - 1.35, ey, 0.70, 0.48, -25))
            parts.append(cacao_pod(cx + 1.20, ey, 0.62, 18))
    parts.append(qr_corners(qr_x, qr_y, qr, leg=max(1.0, 1.3 * k), sw=0.25))
    parts.append(qr_modules(qr_x, qr_y, qr))
    ej_size = ts["ejemplo"]
    ej_w = measure_text(font_ej, "EJEMPLO", ej_size, 0.08) + 0.7
    ej_h = ej_size + 0.45
    parts.append(
        f'<g id="sello-ejemplo" transform="translate({f(cx)} {f(cy)}) rotate(-18)">'
        f'{rect(-ej_w/2, -ej_h/2, ej_w, ej_h, fill="#FFFFFF", stroke=ENG, sw=0.25, rx=0.2)}'
        f'{flat_text(font_ej, "EJEMPLO", ej_size, 0, ej_size * 0.36, "middle", 0.08)}'
        "</g>"
    )
    space_below = (cy + R["r_field"]) - (cy + qr / 2 + quiet)
    ser_h = ts["serial"]
    lab_h = ts["label"]
    block_h = lab_h + 0.15 + ser_h + 0.45
    by = cy + qr / 2 + quiet + min(max(0.45, space_below * 0.18), space_below - block_h - 0.1)
    if by + block_h > cy + R["r_field"] - 0.1:
        by = cy + R["r_field"] - 0.1 - block_h
    lab_y = by + lab_h * 0.85
    ser_w = measure_text(font_ser, tok.serie, ser_h, 0.10) + 1.1
    ser_box_h = ser_h + 0.50
    ser_box_y = lab_y + 0.22
    ser_base = ser_box_y + ser_box_h * 0.72
    parts.append(flat_text(font_lab, "Nº SERIE", lab_h, cx, lab_y, "middle", 0.10))
    parts.append(rect(cx - ser_w / 2, ser_box_y, ser_w, ser_box_h, stroke=ENG, sw=0.26, rx=0.25))
    parts.append(flat_text(font_ser, tok.serie, ser_h, cx, ser_base, "middle", 0.10))
    return "".join(parts)


def build_annotations(tok: Token, face: str) -> str:
    R = rings(tok)
    cx, cy = R["cx"], R["cy"]
    font = font_inter(650, 10)
    parts = []
    if face == "reverso":
        qr = tok.qr
        qx, qy = cx - qr / 2, cy - qr / 2
        midy = qy + qr / 2
        # cuadrado reservado (no se graba), con cota
        parts.append(rect(qx, qy, qr, qr, stroke=NOTE, sw=0.18))
        parts.append(line(qx + qr + 0.7, qy, qx + qr + 0.7, qy + qr, stroke=NOTE, sw=0.18))
        parts.append(line(qx + qr + 0.45, qy, qx + qr + 0.95, qy, stroke=NOTE, sw=0.18))
        parts.append(line(qx + qr + 0.45, qy + qr, qx + qr + 0.95, qy + qr, stroke=NOTE, sw=0.18))
        label = f"{tok.qr:.0f} mm"
        space_right = tok.diameter - (qx + qr + 1.2)
        if space_right >= 3.8:
            parts.append(paths_group(text_paths(font, label, 1.2, qx + qr + 0.95, midy + 0.4, "start", 0.04), NOTE))
        else:
            parts.append(paths_group(text_paths(font, label, 1.2, cx + qr / 2 + 0.4, qy - 0.45, "start", 0.04), NOTE))
    parts.append(paths_group(
        text_paths(font, f"Ø {tok.diameter:.0f} mm", 1.2, cx, 1.15, "middle", 0.04),
        NOTE,
    ))
    return "".join(parts)


def layer(name: str, content: str) -> str:
    return f'<g id="{name}" inkscape:label="{name}" {LAYER}>\n{content}\n</g>'


def cut_circle(tok: Token) -> str:
    R = rings(tok)
    return circle(R["cx"], R["cy"], R["r_cut"], fill="none", stroke=CUT, sw=0.10, extra='id="contorno-corte"')


def svg_document(width_mm: float, height_mm: float, body: str, view_w=None, view_h=None) -> str:
    vw = width_mm if view_w is None else view_w
    vh = height_mm if view_h is None else view_h
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" {INK}\n'
        f'     width="{width_mm}mm" height="{height_mm}mm"\n'
        f'     viewBox="0 0 {f(vw)} {f(vh)}"\n'
        f'     xml:space="preserve">\n'
        f"{body}\n"
        f"</svg>\n"
    )


def face_svg(tok: Token, face: str) -> str:
    d = tok.diameter
    eng = build_obverse_engrave(tok) if face == "anverso" else build_reverse_engrave(tok)
    body = "\n".join([
        layer("corte", cut_circle(tok)),
        layer("grabado", eng),
        layer("anotaciones", build_annotations(tok, face)),
    ])
    return svg_document(d, d, body)


def cut_only_svg(tok: Token) -> str:
    return svg_document(tok.diameter, tok.diameter, layer("corte", cut_circle(tok)))


def engrave_only_svg(tok: Token, face: str) -> str:
    eng = build_obverse_engrave(tok) if face == "anverso" else build_reverse_engrave(tok)
    return svg_document(tok.diameter, tok.diameter, layer("grabado", eng))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


def export_pdf(svg_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))
    print(f"  wrote {pdf_path.relative_to(ROOT)}")

PX_MM = 28.0


def raster_engrave(svg_text: str, diameter: float, px_mm: float = PX_MM) -> np.ndarray:
    px = int(round(diameter * px_mm))
    raw = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), output_width=px, output_height=px)
    im = Image.open(__import__("io").BytesIO(raw)).convert("RGBA")
    arr = np.asarray(im).astype(np.float32) / 255.0
    lum = arr[..., 0] * 0.3 + arr[..., 1] * 0.59 + arr[..., 2] * 0.11
    ink = arr[..., 3] * (1.0 - lum)
    return np.clip(ink, 0, 1)


def metal_disc(mask: np.ndarray, metal: str, diameter: float, px_mm: float = PX_MM) -> Image.Image:
    h, w = mask.shape
    yy, xx = np.indices((h, w)).astype(np.float32)
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    rad = (diameter / 2.0) * px_mm
    disc = (r <= rad - 0.4).astype(np.float32)
    edge = np.clip((rad + 0.6 - r) / 1.6, 0, 1)

    rim_w = 2.2 if diameter >= 36 else 2.0 if diameter >= 33 else 1.8
    rim_outer = (diameter / 2.0 - 0.18) * px_mm
    rim_inner = (diameter / 2.0 - rim_w) * px_mm
    rim_band = disc * np.clip((r - rim_inner) / max(rim_outer - rim_inner, 1), 0, 1)
    rim_band = rim_band * (r <= rim_outer).astype(np.float32)

    height = disc * 1.00 + rim_band * 0.18
    ink = Image.fromarray((mask * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(radius=0.9))
    ink_s = np.asarray(ink).astype(np.float32) / 255.0
    height -= ink_s * 0.55
    height = np.asarray(
        Image.fromarray((np.clip(height, 0, 2) * 120).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(radius=1.1))
    ).astype(np.float32) / 120.0

    dzdx = np.zeros_like(height)
    dzdy = np.zeros_like(height)
    dzdx[:, 1:-1] = (height[:, 2:] - height[:, :-2]) * 2.4
    dzdy[1:-1, :] = (height[2:, :] - height[:-2, :]) * 2.4
    nx, ny, nz = -dzdx, -dzdy, np.ones_like(height)
    nlen = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-8
    nx, ny, nz = nx / nlen, ny / nlen, nz / nlen

    def shade(lx, ly, lz):
        ln = math.sqrt(lx * lx + ly * ly + lz * lz)
        lx, ly, lz = lx / ln, ly / ln, lz / ln
        ndotl = np.clip(nx * lx + ny * ly + nz * lz, 0, 1)
        hx, hy, hz = lx, ly, lz + 1.0
        hl = np.sqrt(hx * hx + hy * hy + hz * hz)
        spec = np.clip((nx * hx + ny * hy + nz * hz) / hl, 0, 1)
        return ndotl, spec

    d1, s1 = shade(-0.45, -0.70, 0.55)
    d2, s2 = shade(0.55, 0.15, 0.70)
    ang = np.arctan2(yy - cy, xx - cx)
    studio = np.clip(np.cos(ang - math.radians(-40)) ** 6, 0, 1) * np.clip(1.0 - abs((r / rad) - 0.78) * 6, 0, 1)
    brush = 0.012 * np.sin((r / px_mm) * 3.2)

    if metal == "plata":
        albedo = np.array([0.78, 0.81, 0.86], np.float32)
        spec_c = np.array([0.95, 0.97, 1.00], np.float32)
        groove = np.array([0.28, 0.31, 0.36], np.float32)
    else:
        albedo = np.array([0.75, 0.42, 0.20], np.float32)
        spec_c = np.array([1.00, 0.85, 0.60], np.float32)
        groove = np.array([0.32, 0.14, 0.07], np.float32)

    amb = 0.18
    dif = 0.62 * d1 + 0.28 * d2
    spec = (s1 ** 48) * 0.55 + (s2 ** 24) * 0.18 + studio * 0.22
    color = albedo * (amb + dif + brush)[..., None] + spec_c * spec[..., None]
    color = color * (1 - 0.55 * ink_s)[..., None] + groove * (0.55 * ink_s)[..., None]
    lip = np.clip((r - (rad - 1.8)) / 1.8, 0, 1) * disc
    color = color * (1 - 0.35 * lip)[..., None]
    color = np.clip(color, 0, 1)
    rgba = np.zeros((h, w, 4), np.float32)
    rgba[..., :3] = color
    rgba[..., 3] = edge
    return Image.fromarray((rgba * 255).astype(np.uint8), "RGBA")


def drop_on_canvas(disc: Image.Image, pos, bg: Image.Image) -> None:
    x, y = pos
    sh = disc.split()[-1].filter(ImageFilter.GaussianBlur(radius=8))
    shadow = Image.new("RGBA", disc.size, (0, 0, 0, 0))
    shadow.putalpha(sh.point(lambda a: int(a * 0.45)))
    bg.alpha_composite(shadow, (x + 4, y + 7))
    bg.alpha_composite(disc, (x, y))


def load_inter_pil(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_INTER), size=size)


def stamp_vista_previa(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    font = load_inter_pil(max(48, im.size[0] // 12))
    tmp_draw = ImageDraw.Draw(im)
    bbox = tmp_draw.textbbox((0, 0), "VISTA PREVIA", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tile = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((20, 10), "VISTA PREVIA", font=font, fill=(180, 30, 30, 70))
    rot = tile.rotate(28, expand=True, resample=Image.Resampling.BICUBIC)
    step_x, step_y = rot.size[0] + 80, rot.size[1] + 60
    for y in range(-80, im.size[1] + 80, step_y):
        for x in range(-80, im.size[0] + 80, step_x):
            overlay.alpha_composite(rot, (x, y))
    return Image.alpha_composite(im, overlay)


def render_token_faces(tok: Token) -> dict[str, Image.Image]:
    out = {}
    for face in ("anverso", "reverso"):
        svg = engrave_only_svg(tok, face)
        mask = raster_engrave(svg, tok.diameter)
        out[face] = metal_disc(mask, tok.metal, tok.diameter)
    return out


def build_metallic_sheet(renders: dict) -> Image.Image:
    W, H = 2400, 1760
    bg = Image.new("RGBA", (W, H), (18, 18, 22, 255))
    arr = np.asarray(bg).astype(np.float32)
    yy, xx = np.indices((H, W))
    vign = 1 - 0.35 * (((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
    arr[..., :3] *= vign[..., None]
    bg = Image.fromarray(arr.astype(np.uint8), "RGBA")
    draw = ImageDraw.Draw(bg)
    draw.text((W // 2, 70), "SAIMON CITY  ·  Fichas coleccionables", font=load_inter_pil(42), fill=(240, 236, 228, 255), anchor="mt")
    draw.text(
        (W // 2, 125),
        "Simulacro metálico  ·  no es moneda legal  ·  sin valor monetario  ·  VISTA PREVIA",
        font=load_inter_pil(22), fill=(180, 176, 168, 255), anchor="mt",
    )
    show_ppmm = 15.6
    cells = [
        ((0, 0), "simonplata", "anverso", "Simonplata  ·  anverso  ·  39 mm  ·  plata"),
        ((1, 0), "simonplata", "reverso", "Simonplata  ·  reverso  ·  QR 15 mm  ·  SMP-000001"),
        ((0, 1), "simonchis", "anverso", "Simonchis  ·  anverso  ·  34 mm  ·  cobre"),
        ((1, 1), "simonchis", "reverso", "Simonchis  ·  reverso  ·  QR 14 mm  ·  SCH-000001"),
    ]
    top, bottom = 210, 140
    grid_w, grid_h = W, H - top - bottom
    cell_w, cell_h = grid_w // 2, grid_h // 2
    for (col, row), slug, face, label in cells:
        disc = renders[(slug, face)]
        d_mm = 39.0 if slug == "simonplata" else 34.0
        target = int(d_mm * show_ppmm)
        disc_s = disc.resize((target, target), Image.Resampling.LANCZOS)
        cx = col * cell_w + cell_w // 2
        cy = top + row * cell_h + cell_h // 2 - 16
        x, y = cx - target // 2, cy - target // 2
        drop_on_canvas(disc_s, (x, y), bg)
        ImageDraw.Draw(bg).text((cx, y + target + 28), label, font=load_inter_pil(20), fill=(220, 216, 208, 255), anchor="mt")
    ImageDraw.Draw(bg).text(
        (W // 2, H - 48),
        "Arte original de Sara · Diseñadora gráfica, para Jay Montana / Saimon City.  Ficha coleccionable, no es moneda legal, no tiene valor en pesos.",
        font=load_inter_pil(16), fill=(150, 146, 138, 255), anchor="mt",
    )
    return stamp_vista_previa(bg)


def mm_to_px(mm: float, dpi: float = 300) -> int:
    return int(round(mm * dpi / 25.4))

def build_comparison_sheet(renders: dict, renders30: dict) -> Image.Image:
    dpi = 300
    W, H = mm_to_px(297, dpi), mm_to_px(210, dpi)
    bg = Image.new("RGBA", (W, H), (244, 240, 232, 255))
    draw = ImageDraw.Draw(bg)

    def t(xy, text, size=28, fill=(30, 28, 24), anchor="lt"):
        draw.text(xy, text, font=load_inter_pil(size), fill=fill, anchor=anchor)

    t((mm_to_px(14), mm_to_px(10)), "SAIMON CITY  ·  Comparación de tamaños  ·  escala 1:1 (300 dpi)", 32)
    t((mm_to_px(14), mm_to_px(20)), "VISTA PREVIA  ·  Fichas coleccionables  ·  no es moneda legal  ·  sin valor monetario", 20, fill=(90, 70, 50))

    origin_x = mm_to_px(20)
    origin_y = mm_to_px(42)

    def ruler(x, y, length_mm=140):
        x2 = x + mm_to_px(length_mm)
        draw.line([(x, y), (x2, y)], fill=(20, 20, 20), width=3)
        for mmv in range(0, length_mm + 1):
            px = x + mm_to_px(mmv)
            if mmv % 10 == 0:
                h = mm_to_px(6)
                draw.line([(px, y), (px, y + h)], fill=(20, 20, 20), width=3)
                t((px, y + h + mm_to_px(1)), str(mmv), 16, anchor="mt")
            elif mmv % 5 == 0:
                draw.line([(px, y), (px, y + mm_to_px(4))], fill=(20, 20, 20), width=2)
            else:
                draw.line([(px, y), (px, y + mm_to_px(2.2))], fill=(20, 20, 20), width=1)
        t((x2 + mm_to_px(4), y), "mm", 16, anchor="lm")

    ruler(origin_x, origin_y, 140)

    def paste_disc(disc, d_mm, x_mm, y_mm):
        px = mm_to_px(d_mm)
        im = disc.resize((px, px), Image.Resampling.LANCZOS)
        pos = (mm_to_px(x_mm), mm_to_px(y_mm))
        drop_on_canvas(im, pos, bg)
        return pos, px

    y1 = 62
    t((mm_to_px(20), mm_to_px(y1 - 6)), "Simonplata (plata)", 24)
    paste_disc(renders30[("simonplata", "anverso")], 30, 20, y1)
    paste_disc(renders[("simonplata", "anverso")], 39, 20 + 30 + 12, y1)
    paste_disc(renders30[("simonplata", "reverso")], 30, 20 + 30 + 12 + 39 + 12, y1)
    paste_disc(renders[("simonplata", "reverso")], 39, 20 + 30 + 12 + 39 + 12 + 30 + 12, y1)
    t((mm_to_px(20 + 15), mm_to_px(y1 + 30 + 3)), "30 mm  ·  QR 12 mm", 16, anchor="mt")
    t((mm_to_px(20 + 30 + 12 + 19.5), mm_to_px(y1 + 39 + 3)), "39 mm  ·  QR 15 mm  ·  primaria", 16, anchor="mt")
    t((mm_to_px(20 + 30 + 12 + 39 + 12 + 15), mm_to_px(y1 + 30 + 3)), "30 mm reverso  ·  QR 12 mm", 16, anchor="mt")
    t((mm_to_px(20 + 30 + 12 + 39 + 12 + 30 + 12 + 19.5), mm_to_px(y1 + 39 + 3)), "39 mm reverso  ·  QR 15 mm", 16, anchor="mt")

    y2 = 62 + 39 + 16
    t((mm_to_px(20), mm_to_px(y2 - 6)), "Simonchis (cobre)", 24)
    paste_disc(renders30[("simonchis", "anverso")], 30, 20, y2)
    paste_disc(renders[("simonchis", "anverso")], 34, 20 + 30 + 12, y2)
    paste_disc(renders30[("simonchis", "reverso")], 30, 20 + 30 + 12 + 34 + 12, y2)
    paste_disc(renders[("simonchis", "reverso")], 34, 20 + 30 + 12 + 34 + 12 + 30 + 12, y2)
    t((mm_to_px(20 + 15), mm_to_px(y2 + 30 + 3)), "30 mm  ·  QR 12 mm", 16, anchor="mt")
    t((mm_to_px(20 + 30 + 12 + 17), mm_to_px(y2 + 34 + 3)), "34 mm  ·  QR 14 mm  ·  primaria", 16, anchor="mt")
    t((mm_to_px(20 + 30 + 12 + 34 + 12 + 15), mm_to_px(y2 + 30 + 3)), "30 mm reverso  ·  QR 12 mm", 16, anchor="mt")
    t((mm_to_px(20 + 30 + 12 + 34 + 12 + 30 + 12 + 17), mm_to_px(y2 + 34 + 3)), "34 mm reverso  ·  QR 14 mm", 16, anchor="mt")

    box_y = 165
    draw.rectangle(
        [mm_to_px(20), mm_to_px(box_y), mm_to_px(277), mm_to_px(box_y + 32)],
        outline=(120, 40, 30), width=2, fill=(255, 248, 240, 255),
    )
    t((mm_to_px(28), mm_to_px(box_y + 6)),
      "El QR no se reduce por debajo de 12 mm. Si la ficha se fabrica a 30 mm (minimo del rango 30-39 mm),", 18)
    t((mm_to_px(28), mm_to_px(box_y + 14)),
      "el diseno se recompone: el QR queda en 12 mm (no es un escalado uniforme). En 34 mm mide 14 mm y en 39 mm, 15 mm.", 18)
    t((mm_to_px(28), mm_to_px(box_y + 22)),
      "El codigo que se ve es un EJEMPLO y debe sustituirse por un QR unico grabado.  Ficha coleccionable · sin valor en pesos.", 18)
    return stamp_vista_previa(bg)


def dim_line_h(draw, x1, x2, y, label, font, color=(0, 80, 160)):
    draw.line([(x1, y), (x2, y)], fill=color, width=2)
    draw.line([(x1, y - 6), (x1, y + 6)], fill=color, width=2)
    draw.line([(x2, y - 6), (x2, y + 6)], fill=color, width=2)
    draw.text(((x1 + x2) // 2, y - 8), label, font=font, fill=color, anchor="mb")


def dim_line_v(draw, x, y1, y2, label, font, color=(0, 80, 160)):
    draw.line([(x, y1), (x, y2)], fill=color, width=2)
    draw.line([(x - 6, y1), (x + 6, y1)], fill=color, width=2)
    draw.line([(x - 6, y2), (x + 6, y2)], fill=color, width=2)
    draw.text((x + 10, (y1 + y2) // 2), label, font=font, fill=color, anchor="lm")


def build_mechanical_sheet(toks_primary) -> Image.Image:
    dpi = 300
    W, H = mm_to_px(297, dpi), mm_to_px(210, dpi)
    bg = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(bg)
    font_s = load_inter_pil(16)
    font_d = load_inter_pil(15)
    draw.text((mm_to_px(14), mm_to_px(8)), "SAIMON CITY  ·  Plano de cotas  ·  VISTA PREVIA", font=load_inter_pil(30), fill=(20, 20, 20))
    draw.text(
        (mm_to_px(14), mm_to_px(16)),
        "Fichas coleccionables  ·  no es moneda legal  ·  sin valor monetario  ·  no imita la moneda oficial colombiana",
        font=font_s, fill=(60, 60, 60),
    )

    scale = 2.0

    def token_line_art(tok, face):
        R = rings(tok)
        art = build_obverse_engrave(tok) if face == "anverso" else build_reverse_engrave(tok)
        body = layer("grabado", art) + circle(R["cx"], R["cy"], R["r_cut"], stroke=ENG, sw=0.15)
        return svg_document(tok.diameter, tok.diameter, body)

    items = [
        (toks_primary[0], "anverso", 10, 26),
        (toks_primary[0], "reverso", 106, 26),
        (toks_primary[1], "anverso", 16, 116),
        (toks_primary[1], "reverso", 106, 116),
    ]
    for tok, face, x_mm, y_mm in items:
        svg2 = token_line_art(tok, face)
        px = int(tok.diameter * scale * dpi / 25.4)
        raw = cairosvg.svg2png(bytestring=svg2.encode("utf-8"), output_width=px, output_height=px)
        im = Image.open(__import__("io").BytesIO(raw)).convert("RGBA")
        pos = (mm_to_px(x_mm), mm_to_px(y_mm))
        bg.alpha_composite(im, pos)
        x0, y0 = pos
        dpx = px
        color = (0, 80, 160)
        dim_line_h(draw, x0, x0 + dpx, y0 + dpx + mm_to_px(5), f"Ø {tok.diameter:.0f} mm", font_d, color)
        if face == "reverso":
            qr = tok.qr
            qr_px = px * (qr / tok.diameter)
            qx = x0 + (px - qr_px) / 2
            qy = y0 + (px - qr_px) / 2
            dim_line_v(draw, int(qx + qr_px) + mm_to_px(3), int(qy), int(qy + qr_px), f"QR {qr:.0f} x {qr:.0f} mm", font_d, color)
        title = f"{tok.nombre}  ·  {face}  ·  primaria"
        draw.text((x0, y0 - mm_to_px(5)), title, font=font_s, fill=(20, 20, 20), anchor="lt")

    tx, ty = mm_to_px(198), mm_to_px(26)
    lines = [
        ("ESPECIFICACIONES", 17, (0, 80, 160)),
        ("", 15, (20, 20, 20)),
        ("Simonplata (primaria): Ø 39 mm, QR 15 mm", 15, (20, 20, 20)),
        ("Simonchis (primaria): Ø 34 mm, QR 14 mm", 15, (20, 20, 20)),
        ("Rango de fabricacion: 30-39 mm", 15, (20, 20, 20)),
        ("Variante de comprobacion: Ø 30 mm, QR 12 mm", 15, (20, 20, 20)),
        ("  (el QR nunca baja de 12 mm)", 15, (20, 20, 20)),
        ("", 15, (20, 20, 20)),
        ("Zona de silencio del QR: 0,8-1,0 mm", 15, (20, 20, 20)),
        ("Modulos del QR de ejemplo: 21 (v1, ECC H)", 15, (20, 20, 20)),
        ("  15 mm -> modulo 0,71 mm", 15, (20, 20, 20)),
        ("  14 mm -> modulo 0,67 mm", 15, (20, 20, 20)),
        ("  12 mm -> modulo 0,57 mm", 15, (20, 20, 20)),
        ("", 15, (20, 20, 20)),
        ("Trazo minimo: 0,20 mm", 15, (20, 20, 20)),
        ("Altura de texto minima: 1,20 mm", 15, (20, 20, 20)),
        ("Tipografia: Inter Bold / ExtraBold (OFL),", 15, (20, 20, 20)),
        ("  convertida a trazos en los SVG.", 15, (20, 20, 20)),
        ("", 15, (20, 20, 20)),
        ("Espesor sugerido (no vinculante): 2,0-2,5 mm", 15, (20, 20, 20)),
        ("Profundidad de grabado laser: 0,15-0,30 mm", 15, (20, 20, 20)),
        ("Relieve de troquel (si se usa): ~0,3-0,4 mm", 15, (20, 20, 20)),
        ("", 15, (20, 20, 20)),
        ("Tolerancias sugeridas:", 15, (20, 20, 20)),
        ("  diametro  ±0,10 mm", 15, (20, 20, 20)),
        ("  posicion del QR  ±0,20 mm", 15, (20, 20, 20)),
        ("  tamano del QR  +0,3 / -0,0 mm", 15, (20, 20, 20)),
        ("    (nunca por debajo de 12 mm)", 15, (20, 20, 20)),
        ("", 15, (20, 20, 20)),
        ("Capas:  corte (rojo)  /  grabado (negro)", 15, (20, 20, 20)),
        ("El grupo qr-ejemplo y el sello EJEMPLO", 15, (20, 20, 20)),
        ("se sustituyen por el QR unico real.", 15, (20, 20, 20)),
        ("", 15, (20, 20, 20)),
        ("LEYENDA OBLIGATORIA", 16, (0, 80, 160)),
        ("FICHA COLECCIONABLE · SIN VALOR MONETARIO", 14, (20, 20, 20)),
        ("COLECCIONABLE · NO ES MONEDA LEGAL", 14, (20, 20, 20)),
        ("Sin pesos, sin signo de peso, sin escudo nacional,", 14, (20, 20, 20)),
        ("sin Banco de la Republica.", 14, (20, 20, 20)),
    ]
    y = ty
    for line, sz, fill in lines:
        draw.text((tx, y), line, font=load_inter_pil(sz), fill=fill, anchor="lt")
        y += mm_to_px(4.15 if sz <= 15 else 5.0)

    draw.text(
        (mm_to_px(14), mm_to_px(200)),
        "Escala de las vistas de las fichas: 2:1.  Arte de Sara · Diseñadora gráfica, para Jay Montana / Saimon City.",
        font=font_s, fill=(80, 80, 80),
    )
    return stamp_vista_previa(bg)

def generate_all() -> None:
    print("== Saimon City · fichas fisicas ==")
    primary = list(TOKENS)
    variants = [variant_30(t) for t in primary]

    for tok in primary:
        for face in ("anverso", "reverso"):
            svg_path = ROOT / "svg" / f"{tok.slug}_{int(tok.diameter)}mm_{face}.svg"
            write_text(svg_path, face_svg(tok, face))
            export_pdf(svg_path, ROOT / "pdf" / f"{tok.slug}_{int(tok.diameter)}mm_{face}.pdf")
        write_text(ROOT / "svg" / "capas" / f"{tok.slug}_{int(tok.diameter)}mm_corte.svg", cut_only_svg(tok))
        for face in ("anverso", "reverso"):
            write_text(
                ROOT / "svg" / "capas" / f"{tok.slug}_{int(tok.diameter)}mm_{face}_grabado.svg",
                engrave_only_svg(tok, face),
            )

    for tok in variants:
        for face in ("anverso", "reverso"):
            p = ROOT / "svg" / "variantes-30mm" / f"{tok.slug}_30mm_{face}.svg"
            write_text(p, face_svg(tok, face))
            export_pdf(p, ROOT / "pdf" / "variantes-30mm" / f"{tok.slug}_30mm_{face}.pdf")

    print("== renders metalicos ==")
    renders: dict = {}
    renders30: dict = {}
    for tok in primary:
        faces = render_token_faces(tok)
        for face, im in faces.items():
            renders[(tok.slug, face)] = im
            out = ROOT / "previews" / f"{tok.slug}_{int(tok.diameter)}mm_{face}_metal.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            canvas = Image.new("RGBA", (im.size[0] + 80, im.size[1] + 80), (18, 18, 22, 255))
            drop_on_canvas(im, (40, 36), canvas)
            stamp_vista_previa(canvas).save(out)
            print(f"  wrote {out.relative_to(ROOT)}")
    for tok in variants:
        faces = render_token_faces(tok)
        for face, im in faces.items():
            renders30[(tok.slug, face)] = im

    print("== hojas ==")
    h1 = ROOT / "hojas" / "hoja_vistas_metalicas.png"
    h1.parent.mkdir(parents=True, exist_ok=True)
    build_metallic_sheet(renders).save(h1, dpi=(150, 150))
    print(f"  wrote {h1.relative_to(ROOT)}")
    h2 = ROOT / "hojas" / "hoja_comparacion_tamanos.png"
    build_comparison_sheet(renders, renders30).save(h2, dpi=(300, 300))
    print(f"  wrote {h2.relative_to(ROOT)}")
    h3 = ROOT / "hojas" / "hoja_mecanica_cotas.png"
    build_mechanical_sheet(primary).save(h3, dpi=(300, 300))
    print(f"  wrote {h3.relative_to(ROOT)}")
    print("listo.")


if __name__ == "__main__":
    generate_all()
