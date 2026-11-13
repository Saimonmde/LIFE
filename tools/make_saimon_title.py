# SPDX-License-Identifier: AGPL-3.0-or-later
"""Recorta el logo rojo de Simón, lo deja con fondo transparente y deriva el wordmark dorado.

El PNG rojo es la referencia de las letras. El título usa el derivado en oro, con el
mismo degradado que la palabra City y las gotas cerradas en punta. No hace falta Pillow.
"""
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_png(path):
    data = Path(path).read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise SystemExit('no es un PNG')
    pos = 8
    width = height = color = None
    idat = []
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if tag == b'IHDR':
            width, height, bit, color, _comp, _flt, inter = struct.unpack('>IIBBBBB', chunk)
            if bit != 8 or color not in (2, 6) or inter:
                raise SystemExit('PNG no RGB de 8 bits')
        elif tag == b'IDAT':
            idat.append(chunk)
        elif tag == b'IEND':
            break
        pos += 12 + length
    channels = 4 if color == 6 else 3
    raw = zlib.decompress(b''.join(idat))
    stride = width * channels
    rows = []
    i = 0
    prev = bytearray(stride)
    for _y in range(height):
        filt = raw[i]
        i += 1
        row = bytearray(raw[i:i + stride])
        i += stride
        if filt == 1:
            for x in range(stride):
                left = row[x - channels] if x >= channels else 0
                row[x] = (row[x] + left) & 255
        elif filt == 2:
            for x in range(stride):
                row[x] = (row[x] + prev[x]) & 255
        elif filt == 3:
            for x in range(stride):
                left = row[x - channels] if x >= channels else 0
                row[x] = (row[x] + ((left + prev[x]) // 2)) & 255
        elif filt == 4:
            for x in range(stride):
                left = row[x - channels] if x >= channels else 0
                up = prev[x]
                ul = prev[x - channels] if x >= channels else 0
                p = left + up - ul
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - ul)
                pred = left if pa <= pb and pa <= pc else up if pb <= pc else ul
                row[x] = (row[x] + pred) & 255
        elif filt != 0:
            raise SystemExit('filtro PNG desconocido')
        prev = row
        rows.append(row)
    return width, height, channels, rows


def _write_png(path, width, height, rgba):
    def chunk(tag, payload):
        return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload) & 0xFFFFFFFF)
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]
    blob = b'\x89PNG\r\n\x1a\n'
    blob += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    blob += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    blob += chunk(b'IEND', b'')
    Path(path).write_bytes(blob)


def _ink(r, g, b, a=255):
    if a < 16:
        return 0
    if r > 246 and g > 246 and b > 246:
        return 0
    darkness = 1 - ((r + g + b) / (3 * 255))
    chroma = max(r, g, b) - min(r, g, b)
    if chroma < 12 and darkness < 0.04:
        return 0
    return max(darkness, chroma / 255)


# Mismo degradado que .simoncity-city en play/style.css, de arriba a abajo.
_GOLD_STOPS = (
    (0.00, (255, 246, 210)),  # #fff6d2
    (0.28, (240, 212, 138)),  # #f0d48a
    (0.62, (196, 150, 58)),   # #c4963a
    (1.00, (122, 84, 24)),    # #7a5418
)


def _gradient(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    for (a, ca), (b, cb) in zip(_GOLD_STOPS, _GOLD_STOPS[1:]):
        if t <= b or b == _GOLD_STOPS[-1][0]:
            span = b - a
            u = 0 if span <= 0 else (t - a) / span
            return tuple(int(ca[i] + (cb[i] - ca[i]) * u) for i in range(3))
    return _GOLD_STOPS[-1][1]


def _mix(a, b, u):
    return tuple(int(a[i] * (1 - u) + b[i] * u) for i in range(3))


def _taper_drips(alpha, w, h, body):
    """Las gotas bajo el cuerpo de las letras se cierran en punta.

    El logo de origen las deja como barras verticales, a veces cortadas.
    Aquí el ancho baja de forma continua hasta un punto fino, sin bola
    y sin un corte plano. El lienzo ya trae filas vacías debajo.
    """
    seen = bytearray(w * h)
    drips = []
    for y in range(body + 1, h):
        for x in range(w):
            i = y * w + x
            if alpha[i] < 16 or seen[i]:
                continue
            stack = [(x, y)]
            seen[i] = 1
            pts = []
            while stack:
                cx, cy = stack.pop()
                pts.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and body < ny < h:
                        j = ny * w + nx
                        if alpha[j] >= 16 and not seen[j]:
                            seen[j] = 1
                            stack.append((nx, ny))
            ys = [p[1] for p in pts]
            if max(ys) - min(ys) < 8:
                continue
            drips.append(pts)
    for pts in drips:
        rows = {}
        for x, y in pts:
            rows.setdefault(y, []).append(x)
        first = min(rows)
        bot = max(rows)
        sample = [rows[y] for y in range(first, min(bot, first + 14) + 1) if y in rows]
        width0 = max(max(r) - min(r) + 1 for r in sample)
        centers = {y: (min(xs) + max(xs)) / 2 for y, xs in rows.items()}
        last_c = centers[max(centers)]
        start_half = width0 / 2
        tip = min(h - 1, bot + max(int(width0 * 3.2), 40))
        for x, y in pts:
            alpha[y * w + x] = 0
        span = max(1, tip - first)
        for y in range(first, tip + 1):
            t = (y - first) / span
            # El ancho baja a lo largo de toda la gota. El último tramo es un
            # solo píxel que se apaga: punta fina, sin corte plano ni bola.
            half = start_half * ((1 - t) ** 1.05)
            cx = centers.get(y, last_c)
            if half < 1.35:
                fade = max(0.0, min(1.0, half / 1.35))
                x = int(round(cx))
                if 0 <= x < w and fade > 0.04:
                    alpha[y * w + x] = max(alpha[y * w + x], int(255 * fade))
                continue
            for x in range(int(round(cx - half)), int(round(cx + half)) + 1):
                if x < 0 or x >= w:
                    continue
                dist = abs(x - cx)
                if dist > half:
                    continue
                edge = half - dist
                coverage = 1.0 if edge >= 0.75 else max(0.0, edge / 0.75)
                alpha[y * w + x] = max(alpha[y * w + x], int(min(255, 255 * coverage)))
    return alpha


def build(source, original_out, gold_out, max_width=980, write_original=False):
    width, height, channels, rows = _read_png(source)
    ink = [0.0] * (width * height)
    row_score = [0] * height
    for y in range(height):
        row = rows[y]
        for x in range(width):
            i = x * channels
            a = row[i + 3] if channels == 4 else 255
            amount = _ink(row[i], row[i + 1], row[i + 2], a)
            ink[y * width + x] = amount
            if amount > 0.08:
                row_score[y] += 1
    col_score = [0] * width
    for y in range(height):
        for x in range(width):
            if ink[y * width + x] > 0.08:
                col_score[x] += 1
    ys = [y for y, n in enumerate(row_score) if n > 0]
    xs = [x for x, n in enumerate(col_score) if n > 0]
    if not ys or not xs:
        raise SystemExit('el logo no tiene tinta')
    # El recorte incluye las gotas enteras. El umbral alto sólo localiza el cuerpo.
    y0, y1 = ys[0], ys[-1]
    x0, x1 = xs[0], xs[-1]
    peak = max(row_score[y0:y1 + 1])
    body = y1
    for y in range(y1, y0, -1):
        if row_score[y] >= peak * 0.18:
            body = y
            break
    # Margen vacío bajo la punta más larga, para que ninguna gota llegue al borde.
    pad_bottom = 160
    crop_w = x1 - x0 + 1
    crop_h = (y1 - y0 + 1) + pad_bottom
    alpha = bytearray(crop_w * crop_h)
    red = bytearray(crop_w * (y1 - y0 + 1) * 4)
    ink_h = y1 - y0 + 1
    for y in range(ink_h):
        src = rows[y0 + y]
        for x in range(crop_w):
            i = (x0 + x) * channels
            r, g, b = src[i], src[i + 1], src[i + 2]
            src_a = src[i + 3] if channels == 4 else 255
            amount = ink[(y0 + y) * width + (x0 + x)]
            pix = 0 if amount <= 0.05 else min(255, int(40 + amount * 520))
            if src_a < 255:
                pix = min(pix, src_a)
            alpha[y * crop_w + x] = pix
            o = (y * crop_w + x) * 4
            red[o:o + 4] = bytes((r, g, b, pix))
    if write_original:
        _write_png(original_out, crop_w, ink_h, red)
    scale = min(1.0, max_width / crop_w)
    out_w = max(1, int(round(crop_w * scale)))
    out_h = max(1, int(round(crop_h * scale)))
    body_out = max(1, int(round((body - y0) * scale)))
    alphas = [0] * (out_w * out_h)
    for y in range(out_h):
        sy0 = int(y / scale)
        sy1 = min(crop_h, max(sy0 + 1, int((y + 1) / scale)))
        for x in range(out_w):
            sx0 = int(x / scale)
            sx1 = min(crop_w, max(sx0 + 1, int((x + 1) / scale)))
            acc = n = 0
            for yy in range(sy0, sy1):
                for xx in range(sx0, sx1):
                    acc += alpha[yy * crop_w + xx]
                    n += 1
            alphas[y * out_w + x] = 0 if n == 0 else acc // n
    # La punta se calcula en píxeles del PNG final: si se afina antes de
    # reducir, el encogido se come la punta y el corte vuelve a verse plano.
    _taper_drips(alphas, out_w, out_h, min(out_h - 2, body_out))
    gold = bytearray(out_w * out_h * 4)
    for y in range(out_h):
        # El degradado cubre el cuerpo de «Saimon», como el de la palabra City.
        # Debajo, las gotas siguen en el oro más oscuro.
        tone = _gradient(y / body_out)
        for x in range(out_w):
            pix = alphas[y * out_w + x]
            o = (y * out_w + x) * 4
            if pix < 18:
                continue
            up = alphas[(y - 1) * out_w + x] if y else 0
            left = alphas[y * out_w + (x - 1)] if x else 0
            down = alphas[(y + 1) * out_w + x] if y + 1 < out_h else 0
            right = alphas[y * out_w + (x + 1)] if x + 1 < out_w else 0
            lit = up < 36 or left < 36
            shade = down < 36 or right < 36
            if lit and not shade:
                rgb = _mix(tone, (255, 246, 210), 0.48)
            elif shade and not lit:
                rgb = _mix(tone, (74, 48, 16), 0.5)
            elif lit and shade:
                rgb = _mix(tone, (255, 236, 190), 0.22)
            else:
                rgb = tone
            gold[o:o + 4] = bytes((rgb[0], rgb[1], rgb[2], pix))
    _write_png(gold_out, out_w, out_h, gold)
    return {'original': (crop_w, ink_h), 'gold': (out_w, out_h), 'body': body_out}


if __name__ == '__main__':
    src = Path('/home/ubuntu/.cursor/projects/agent-repos-LIFE/uploads/saimon-logo_cffb.png')
    if not src.is_file():
        src = Path('/home/ubuntu/.cursor/projects/agent-repos-LIFE/assets/saimon-logo.png')
    out = build(
        src,
        ROOT / 'graphics/ui/saimon-logo.png',
        ROOT / 'graphics/ui/saimon-logo-gold.png',
    )
    print(out)
