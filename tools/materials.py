# SPDX-License-Identifier: AGPL-3.0-or-later
"""Texturas tileables para el cliente 3D (LIFE INC). Se pintan con la misma paleta/técnica que el resto del arte (originales)."""
import random
from pixel import new, up, px
WOOD = [(70,44,24),(98,62,34),(128,84,46),(158,110,62)]
S = 32   # media resolución; se escala x2 => 64x64 tileable

def _dk(c, k): return tuple(max(0, min(255, int(v * k))) for v in c[:3])

def stone(pal, seed, bw=8, bh=4):
    img = new(S, S); rnd = random.Random(seed); cache = {}
    for y in range(S):
        r = y // bh; off = bw // 2 if r % 2 else 0
        for x in range(S):
            lx, ly = (x + off) % bw, y % bh
            if lx == bw - 1 or ly == bh - 1: c = pal[3]
            else:
                k = (((x + off) % S) // bw, r)
                if k not in cache: cache[k] = rnd.randrange(3)
                c = pal[cache[k]]
                if ly == 0: c = _dk(c, 1.1)
            px(img, x, y, c)
    return up(img, 2)

def plaster(seed=1):
    img = new(S, S); rnd = random.Random(seed)
    for y in range(S):
        for x in range(S):
            px(img, x, y, (232,214,170) if rnd.random() > 0.12 else (218,198,152))
    return up(img, 2)

def timber(seed=2):
    img = plaster(seed); img = img.copy()
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    for x in (0, 62): d.rectangle((x, 0, x + 1, 63), fill=WOOD[1])
    d.rectangle((0, 0, 63, 3), fill=WOOD[0]); d.rectangle((0, 30, 63, 33), fill=WOOD[1])
    return img

def roof(pal, seed):
    img = new(S, S); rnd = random.Random(seed); cache = {}
    for y in range(S):
        row = y // 4; off = 3 if row % 2 else 0
        for x in range(S):
            k = (((x + off) % S) // 6 if S % 6 == 0 else ((x + off) % 30) // 6, row)
            if k not in cache: cache[k] = rnd.random()
            c = pal[1] if cache[k] > 0.25 else pal[2]
            if y % 4 == 3: c = pal[0]
            elif (x + off) % 8 == 7: c = _dk(c, 0.82)
            px(img, x, y, c)
    return up(img, 2)

def planks(seed=3):
    img = new(S, S); rnd = random.Random(seed)
    for y in range(S):
        for x in range(S):
            b = x // 8
            c = WOOD[2] if b % 2 else WOOD[1]
            if x % 8 == 7: c = WOOD[0]
            if (y + b * 11) % 32 == 0: c = WOOD[0]
            if rnd.random() < 0.06: c = WOOD[3]
            px(img, x, y, c)
    return up(img, 2)

def rock(seed=4):
    img = new(S, S); rnd = random.Random(seed)
    pal = [(78,78,80),(104,104,104),(128,126,122),(156,152,144)]
    for y in range(S):
        for x in range(S):
            v = (x * 3 + y * 5 + rnd.randrange(4)) % 13
            c = pal[1 if v < 5 else 2 if v < 10 else 3 if v < 12 else 0]
            if rnd.random() < 0.08: c = (72,118,52)   # musgo
            px(img, x, y, c)
    return up(img, 2)

def sand(seed=5):
    img = new(S, S); rnd = random.Random(seed)
    for y in range(S):
        for x in range(S):
            r = rnd.random()
            px(img, x, y, (214,190,140) if r > 0.3 else (196,170,122) if r > 0.08 else (232,212,168))
    return up(img, 2)

def awning():
    img = new(S, S)
    for y in range(S):
        for x in range(S):
            px(img, x, y, (196,44,40) if (x // 8) % 2 else (236,226,200))
    return up(img, 2)

def build_all():
    return {
        'muro_yeso_vigas': timber(),
        'muro_piedra_clara': stone(((146,132,108),(172,156,126),(194,178,146),(104,92,76)), 7),
        'zocalo_piedra': stone(((120,112,100),(146,138,122),(166,158,142),(92,84,74)), 2),
        'techo_tejas_rojas': roof([(84,36,24),(140,66,40),(170,92,58)], 3),
        'techo_pizarra_azul': roof([(46,52,68),(80,90,110),(108,120,140)], 9),
        'madera_tablas': planks(),
        'roca_acantilado': rock(),
        'arena_orilla': sand(),
        'piedra_fuente': stone(((150,146,138),(178,174,164),(204,200,190),(120,116,110)), 11, 16, 8),
        'toldo_rayas': awning(),
    }
