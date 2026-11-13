# SPDX-License-Identifier: AGPL-3.0-or-later
"""Teselas de suelo 64x64 originales: césped, camino (autotile 8 vecinos), agua (autotile), puente."""
import math, random
from functools import lru_cache
from PIL import Image
from pixel import new, up, px, periodic_noise, value_noise

S = 32  # se pinta a media resolución y se escala x2 -> 64px
GRASS = [(74,124,40),(94,146,46),(114,164,54),(136,182,64),(164,200,84)]
GRASS_DARK = (62,106,36)
DIRT = [(134,94,56),(158,114,68),(178,134,82),(196,154,100)]
DIRT_RIM = (118,82,48)
WATER = [(22,118,140),(30,148,166),(48,174,186),(96,206,210)]
WATER_HI = (214,246,244)
SHALLOW = (88,196,196)
SAND = (214,192,132)
SAND_D = (186,160,104)

@lru_cache(None)
def _noise_grid(seed, scale=1.0):
    n = value_noise(S, seed)
    return [[v * scale for v in row] for row in n]

def grass_half(seed=0, worn=False, flowers=0):
    img = new(S, S)
    n = _noise_grid(100 + seed)
    rnd = random.Random(seed)
    for y in range(S):
        for x in range(S):
            v = n[y][x] + (rnd.random() - 0.5) * 1.6
            i = 2 + (1 if v > 1.1 else 0) + (-1 if v < -1.1 else 0) + (-1 if v < -2.4 else 0)
            px(img, x, y, GRASS[max(0, min(4, i))])
    # matas de hierba (se envuelven en los bordes => sin costuras)
    for _ in range(26):
        x, y = rnd.randrange(S), rnd.randrange(S)
        c_hi = GRASS[4] if rnd.random() < 0.6 else GRASS[3]
        px(img, x % S, y % S, c_hi)
        px(img, (x + 1) % S, (y + 1) % S, GRASS[1])
        px(img, (x - 1) % S, (y + 1) % S, GRASS[1])
    if worn:
        # césped pisado: motas de tierra y piedritas (se envuelven => sin costuras)
        for _ in range(16):
            x, y = rnd.randrange(S), rnd.randrange(S)
            c = DIRT[3] if rnd.random() < 0.6 else DIRT[2]
            for dx, dy in ((0,0),(1,0),(0,1)) if rnd.random() < 0.7 else ((0,0),):
                px(img, (x+dx) % S, (y+dy) % S, c)
        for _ in range(5):
            x, y = rnd.randrange(S), rnd.randrange(S)
            px(img, x, y, (196,192,182)); px(img, (x+1) % S, y, (160,156,150)); px(img, x, (y+1) % S, GRASS[0])
    for k in range(flowers):
        # margaritas (pétalos blancos, centro amarillo)
        x, y = rnd.randrange(S), rnd.randrange(S)
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)):
            px(img, (x+dx) % S, (y+dy) % S, (250,250,244) if dx*dy == 0 else (226,232,214))
        px(img, x, y, (250,206,40))
        px(img, x % S, (y+2) % S, GRASS[0])
    return img

def _arm_w(t, base, amp, seed):
    return base + amp * math.sin(math.tau * t / S + seed) + 0.6 * amp * math.sin(2 * math.tau * t / S + seed * 2.3)

def blob_margin(x, y, m, r_center, w_base, w_amp, seed):
    """m = dict N,E,S,W,NE,SE,SW,NW -> bool. Devuelve margen (+ dentro)."""
    cx = cy = S / 2
    X, Y = x + 0.5, y + 0.5
    best = r_center - math.hypot(X - cx, Y - cy)
    if m['N'] and Y <= cy: best = max(best, _arm_w(Y, w_base, w_amp, seed) - abs(X - cx))
    if m['S'] and Y >= cy: best = max(best, _arm_w(Y, w_base, w_amp, seed) - abs(X - cx))
    if m['W'] and X <= cx: best = max(best, _arm_w(X, w_base, w_amp, seed + 1) - abs(Y - cy))
    if m['E'] and X >= cx: best = max(best, _arm_w(X, w_base, w_amp, seed + 1) - abs(Y - cy))
    for q, a, b, qx, qy in (('NE','N','E',1,-1),('SE','S','E',1,1),('SW','S','W',-1,1),('NW','N','W',-1,-1)):
        if m[a] and m[b] and m[q] and (X - cx) * qx >= 0 and (Y - cy) * qy >= 0:
            best = 99
    return best

def path_half(m):
    img = grass_half(0)
    n = _noise_grid(321, 0.45)
    rnd = random.Random(7)
    dn = _noise_grid(55)
    for y in range(S):
        for x in range(S):
            d = blob_margin(x, y, m, 11.0, 9.0, 1.0, 0.7) + n[y][x]
            if d > 1.4:
                v = dn[y][x] + (rnd.random() - 0.5) * 1.4
                c = DIRT[2] if -1 < v < 1.3 else (DIRT[3] if v >= 1.3 else DIRT[1])
                px(img, x, y, c)
            elif d > 0:
                px(img, x, y, DIRT_RIM)
            elif d > -1.2:
                px(img, x, y, GRASS_DARK)
    # piedritas
    for _ in range(10):
        x, y = rnd.randrange(S), rnd.randrange(S)
        if blob_margin(x, y, m, 11.0, 9.0, 1.0, 0.7) > 3:
            px(img, x, y, (206,190,160)); px(img, x, y+1, DIRT[0])
    return img

def water_half(m):
    img = grass_half(1)
    n = _noise_grid(654, 0.5)
    wn = [[periodic_noise(x * 1, y * 3, S, 77) for x in range(S)] for y in range(S)]
    rnd = random.Random(11)
    for y in range(S):
        for x in range(S):
            d = blob_margin(x, y, m, 12.5, 11.5, 0.9, 1.9) + n[y][x]
            if d > 2.2:
                e = min(x + 0.5, S - x - 0.5, y + 0.5, S - y - 0.5) / 8.0
                v = wn[y][x] + 0.6 - (1.0 - min(1.0, e)) * 2.5
                c = WATER[1]
                if v > 1.6: c = WATER[3]
                elif v > 0.6: c = WATER[2]
                elif v < -1.8: c = WATER[0]
                px(img, x, y, c)
            elif d > 0.9:
                px(img, x, y, SHALLOW)
            elif d > 0:
                px(img, x, y, SAND)
            elif d > -1.0:
                px(img, x, y, SAND_D)
            elif d > -2.0:
                px(img, x, y, GRASS_DARK)
    for _ in range(5):
        x, y = rnd.randrange(2, S - 4), rnd.randrange(S)
        if blob_margin(x, y, m, 12.5, 11.5, 0.9, 1.9) > 4:
            for k in range(3): px(img, x + k, y, WATER_HI)
    return img

def bridge_half(m):
    img = water_half(m)
    wood = [(112,72,40),(140,94,52),(166,116,66),(188,140,84)]
    for x in range(S):
        for y in range(7, 26):
            k = x % 4
            c = wood[0] if k == 3 else (wood[2] if k in (0, 1) else wood[1])
            if y in (7, 25): c = wood[0]
            if k == 0 and y % 7 == 3: c = wood[3]
            px(img, x, y, c)
        for y in (5, 6): px(img, x, y, wood[1] if y == 6 else wood[0])   # baranda
        px(img, x, 4, wood[3])
        for y in (26, 27): px(img, x, y, (30,70,120))                   # sombra en el agua
    for x in (2, 17):
        for y in range(1, 7): px(img, x, y, wood[0]); px(img, x+1, y, wood[2])
    return img

def to64(half):
    return up(half, 2)

STONE = [(118,110,98),(146,138,122),(168,160,142),(190,182,162)]
MORTAR = (92,84,74)
def cobble_half(m):
    """plaza empedrada (autotile blob de 47, como el camino). Patrón periódico de 32 => sin costuras."""
    img = grass_half(0)
    n = _noise_grid(777, 0.45)
    for y in range(S):
        for x in range(S):
            d = blob_margin(x, y, m, 13.0, 12.0, 0.6, 2.9) + n[y][x]
            if d <= -1.2: continue
            if d <= 0: px(img, x, y, GRASS_DARK); continue
            row = y // 8; off = 4 if row % 2 else 0
            col = ((x + off) // 8) % 4
            lx = (x + off) % 8; ly = y % 8
            if lx == 7 or ly == 7 or d < 1.0:
                px(img, x, y, MORTAR if d >= 1.0 else (104,96,84)); continue
            if lx in (0, 6) and ly in (0, 6):
                px(img, x, y, MORTAR); continue
            h = (row * 7 + col * 13 + (row * col) % 3) % 5
            c = [STONE[1], STONE[2], (164,148,124), STONE[1], (150,146,136)][h]
            if ly == 0 or lx == 0: c = tuple(min(255, v + 22) for v in c)
            if ly == 6 or lx == 6: c = tuple(max(0, v - 30) for v in c)
            px(img, x, y, c)
    return img
