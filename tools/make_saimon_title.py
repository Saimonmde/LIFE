# SPDX-License-Identifier: AGPL-3.0-or-later
"""Recorta el logo rojo de Simón, lo deja con fondo transparente y deriva el wordmark dorado.

El PNG rojo es la referencia de las letras. El título del juego usa el derivado en oro,
sin exigir las gotas. No hace falta Pillow: sólo zlib.
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


def build(source, original_out, gold_out, max_width=980):
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
    ys = [y for y, n in enumerate(row_score) if n > 12]
    xs = [x for x, n in enumerate(col_score) if n > 8]
    if not ys or not xs:
        raise SystemExit('el logo no tiene tinta')
    y0, y1 = ys[0], ys[-1]
    x0, x1 = xs[0], xs[-1]
    peak = max(row_score[y0:y1 + 1])
    # Las gotas son filas flojas debajo del cuerpo de las letras. No hacen falta.
    body = y1
    for y in range(y1, y0, -1):
        if row_score[y] >= peak * 0.18:
            body = y
            break
    y1 = min(y1, body + 2)
    crop_w, crop_h = x1 - x0 + 1, y1 - y0 + 1
    original = bytearray(crop_w * crop_h * 4)
    for y in range(crop_h):
        src = rows[y0 + y]
        for x in range(crop_w):
            i = (x0 + x) * channels
            r, g, b = src[i], src[i + 1], src[i + 2]
            a = src[i + 3] if channels == 4 else 255
            amount = ink[(y0 + y) * width + (x0 + x)]
            alpha = 0 if amount <= 0.05 else min(255, int(40 + amount * 520))
            if a < 255:
                alpha = min(alpha, a)
            o = (y * crop_w + x) * 4
            original[o:o + 4] = bytes((r, g, b, alpha))
    _write_png(original_out, crop_w, crop_h, original)
    scale = min(1.0, max_width / crop_w)
    out_w = max(1, int(round(crop_w * scale)))
    out_h = max(1, int(round(crop_h * scale)))
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
                    acc += original[(yy * crop_w + xx) * 4 + 3]
                    n += 1
            alphas[y * out_w + x] = 0 if n == 0 else acc // n
    gold = bytearray(out_w * out_h * 4)
    for y in range(out_h):
        for x in range(out_w):
            alpha = alphas[y * out_w + x]
            o = (y * out_w + x) * 4
            if alpha < 24:
                continue
            up = alphas[(y - 1) * out_w + x] if y else 0
            left = alphas[y * out_w + (x - 1)] if x else 0
            down = alphas[(y + 1) * out_w + x] if y + 1 < out_h else 0
            right = alphas[y * out_w + (x + 1)] if x + 1 < out_w else 0
            lit = (up < 40 or left < 40)
            shade = (down < 40 or right < 40)
            if lit and not shade:
                rgb = (255, 232, 176)
            elif shade and not lit:
                rgb = (74, 46, 14)
            elif lit and shade:
                rgb = (232, 196, 110)
            else:
                rgb = (196, 148, 58)
            gold[o:o + 4] = bytes((rgb[0], rgb[1], rgb[2], alpha))
    _write_png(gold_out, out_w, out_h, gold)
    return {'original': (crop_w, crop_h), 'gold': (out_w, out_h)}


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
