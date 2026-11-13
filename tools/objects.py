# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sprites originales de El Jardín (árboles, parcelas, rocas, agua, animales, jugador, letrero, iconos)."""
import math, random
from PIL import Image, ImageDraw, ImageFont
from pixel import new, up, px, outline, shade_blob, ellipse_shadow, lerp

OUT = (44, 32, 22, 255)
BARK = [(84,54,30),(110,72,40),(136,92,52)]
def ramp(*c): return [tuple(x) for x in c]

# ---------- árboles -------------------------------------------------------
def trunk(img, x0, y0, y1, w=5, curve=0.0):
    for y in range(y0, y1):
        t = (y - y0) / max(1, (y1 - y0))
        off = int(round(curve * (1 - t) ** 2))
        ww = w + (2 if y > y1 - 3 else 0)
        for x in range(ww):
            c = BARK[0] if x == ww - 1 else (BARK[2] if x == 1 else BARK[1])
            px(img, x0 + x + off - (1 if y > y1 - 3 else 0), y, c)

def dot_fruit(img, x, y, base, hi, dark, size=2):
    for dy in range(size):
        for dx in range(size):
            px(img, x + dx, y + dy, base)
    px(img, x, y, hi)
    if size >= 2: px(img, x + size - 1, y + size - 1, dark)
    px(img, x + size // 2, y - 1, (70,50,24))   # rabito

def tree_round(kind, fruit):
    """manzano, peral, naranjo, roble (redondos)"""
    img = new(48, 64)
    ellipse_shadow(img, 24, 60, 15, 3.6)
    trunk(img, 21, 38, 61, 6)
    if kind == 'manzana':
        circles = [(24,22,13),(14,27,9),(34,27,9),(18,15,9),(31,15,9),(24,32,9)]
        rp = ramp((40,92,38),(58,120,44),(80,150,52),(112,180,64),(150,204,84))
    elif kind == 'pera':
        circles = [(24,12,9),(24,22,12),(17,30,8),(31,30,8),(24,33,9),(20,18,8),(29,18,8)]
        rp = ramp((54,104,40),(74,134,46),(100,162,56),(134,190,72),(172,214,96))
    elif kind == 'naranja':
        circles = [(24,24,13),(16,22,8),(32,22,8),(24,14,8),(24,32,9)]
        rp = ramp((24,74,40),(34,98,48),(50,124,58),(78,152,70),(118,182,90))
    else:  # roble decorativo
        circles = [(24,22,14),(12,26,9),(36,26,9),(17,13,9),(31,13,9),(24,33,10)]
        rp = ramp((36,84,44),(50,108,50),(70,134,56),(98,160,64),(130,186,80))
    shade_blob(img, circles, rp, seed=hash(kind) % 1000)
    rnd = random.Random(len(kind) * 7)
    if fruit:
        spots = []
        for _ in range(400):
            x, y = rnd.randrange(8, 40), rnd.randrange(8, 38)
            if img.getpixel((x, y))[3] and img.getpixel((x, y + 2))[3] and all(abs(x - a) + abs(y - b) > 5 for a, b in spots):
                spots.append((x, y))
            if len(spots) >= 9: break
        for (x, y) in spots:
            if kind == 'manzana': dot_fruit(img, x, y, (214,36,40), (255,140,130), (150,20,30), 3)
            elif kind == 'naranja': dot_fruit(img, x, y, (248,146,28), (255,210,120), (196,96,16), 3)
            elif kind == 'pera':
                dot_fruit(img, x, y + 1, (206,214,72), (240,246,150), (150,160,40), 3)
                px(img, x + 1, y, (206,214,72))
    return outline(img, OUT)

def tree_mango(fruit):
    img = new(48, 64)
    ellipse_shadow(img, 24, 60, 18, 3.8)
    trunk(img, 21, 34, 61, 6)
    # ramas
    for i in range(6): px(img, 18 - i // 2, 36 - i, BARK[1]); px(img, 29 + i // 2, 36 - i, BARK[1])
    circles = [(24,20,12),(11,25,9),(37,25,9),(16,16,9),(32,16,9),(6,29,6),(42,29,6),(24,28,10)]
    rp = ramp((20,62,34),(28,84,40),(40,108,46),(62,136,56),(98,166,72))
    shade_blob(img, circles, rp, seed=31)
    if fruit:
        for (x, y) in [(10,33),(19,34),(30,33),(38,32),(15,26),(33,24),(24,30),(6,31)]:
            # mango colgante: ovalado, rojo arriba -> amarillo abajo
            px(img, x + 1, y - 1, (60,90,30))
            for dy in range(4):
                for dx in range(3):
                    c = (226,64,44) if dy == 0 else ((244,140,40) if dy == 1 else (250,196,56))
                    if dy == 3 and dx == 0: continue
                    px(img, x + dx, y + dy, c)
            px(img, x, y, (255,170,140))
    return outline(img, OUT)

def leaf(img, x0, y0, ang, length, width, rp, droop=0.02):
    """hoja larga (banano) como tira curva"""
    for i in range(length):
        a = ang + droop * i
        cx = x0 + math.cos(a) * i
        cy = y0 + math.sin(a) * i + 0.012 * i * i
        w = width * math.sin(math.pi * (i + 1) / (length + 1))
        nx, ny = -math.sin(a), math.cos(a)
        for k in range(-int(w), int(w) + 1):
            c = rp[2] if k < 0 else rp[1]
            if k == 0: c = rp[3]
            if abs(k) == int(w): c = rp[0]
            px(img, round(cx + nx * k), round(cy + ny * k), c)

def tree_banano(fruit):
    img = new(48, 64)
    ellipse_shadow(img, 24, 60, 13, 3.4)
    stem = [(86,110,48),(110,138,58),(132,160,70)]
    for y in range(26, 61):
        for x in range(5):
            c = stem[0] if x == 4 else (stem[2] if x == 1 else stem[1])
            if (y + x) % 9 == 0: c = (98,90,46)
            px(img, 22 + x, y, c)
    rp = ramp((40,104,34),(80,160,48),(110,190,62),(196,220,120))
    for ang, ln in [(-2.7,22),(-0.45,22),(-2.2,18),(-0.95,18),(-1.6,15),(-3.05,16),(-0.1,17)]:
        leaf(img, 24, 26, ang, ln, 3.6, rp)
    if fruit:
        # racimo de bananos amarillos
        for row in range(4):
            for k in range(4 - row // 2):
                x = 25 + k * 2 - row // 2; y = 31 + row * 3
                for d in range(3):
                    px(img, x, y + d, (250,214,50)); px(img, x + 1, y + d, (232,184,30))
                px(img, x, y + 3, (110,90,30))
        for y in range(28, 31): px(img, 27, y, (90,110,40))
        # flor morada (bellota) bajo el racimo
        for (dx, dy) in [(0,0),(1,0),(0,1),(1,1),(0,2)]:
            px(img, 28 + dx, 44 + dy, (128,40,90))
    return outline(img, OUT)

def tree_coco(fruit):
    img = new(48, 72)
    ellipse_shadow(img, 24, 68, 14, 3.4)
    # tronco curvo anillado
    for y in range(18, 69):
        t = (y - 18) / 50
        off = int(round(7 * (1 - t) ** 1.6))
        for x in range(4):
            c = (150,112,70) if x in (1, 2) else (118,86,52)
            if y % 4 == 0: c = (98,70,42)
            px(img, 21 + off + x, y, c)
    rp = ramp((34,98,36),(60,138,46),(92,172,58),(160,212,90))
    cx, cy = 30, 17
    for ang in [-3.0, -2.45, -1.9, -1.25, -0.6, -0.05, 0.5, 2.6]:
        L = 19
        for i in range(L):
            a = ang + 0.03 * i * (1 if math.cos(ang) > 0 else -1)
            x = cx + math.cos(a) * i
            y = cy + math.sin(a) * i + 0.022 * i * i
            px(img, round(x), round(y), rp[0])
            if i > 2:
                l = 3 if i < L - 4 else 2
                nx, ny = -math.sin(a), math.cos(a)
                for s in (-1, 1):
                    for k in range(1, l + 1):
                        c = rp[2] if s < 0 else rp[1]
                        if k == l: c = rp[3] if s < 0 else rp[0]
                        px(img, round(x + nx * k * s + math.cos(a) * k * 0.6), round(y + ny * k * s + math.sin(a) * k * 0.6 + k * 0.4), c)
    if fruit:
        for (x, y) in [(26,19),(31,20),(28,23),(33,17),(23,21)]:
            for dy in range(4):
                for dx in range(4):
                    if (dx in (0,3) and dy in (0,3)): continue
                    px(img, x + dx, y + dy, (96,62,30) if (dx + dy) > 3 else ((150,104,56) if dx+dy < 2 else (122,82,42)))
    return outline(img, OUT)

def tree_pino(stump=False):
    img = new(48, 72)
    ellipse_shadow(img, 24, 68, 14, 3.4)
    if stump:
        for y in range(58, 69):
            for x in range(18, 30):
                c = BARK[1] if 19 < x < 28 else BARK[0]
                px(img, x, y, c)
        for x in range(19, 29):
            px(img, x, 57, (214,176,120)); px(img, x, 58, (196,156,100))
        for x in (21, 24, 27): px(img, x, 57, (176,136,86))
        px(img, 30, 66, (110,72,40)); px(img, 31, 67, (110,72,40))
        for (x, y) in ((14,66),(15,67),(33,64),(34,65)): px(img, x, y, (200,170,120))   # astillas
        return outline(img, OUT)
    trunk(img, 21, 50, 69, 6)
    rp = ramp((22,62,40),(30,84,48),(44,108,56),(66,134,66),(98,160,82))
    tiers = [(24, 54, 17, 12), (24, 42, 14, 11), (24, 31, 11, 10), (24, 21, 8, 9), (24, 12, 5, 8)]
    rnd = random.Random(9)
    for (cx, base, hw, h) in tiers:
        for y in range(base - h, base + 1):
            t = (y - (base - h)) / h
            w = hw * t + 1
            for x in range(int(cx - w), int(cx + w) + 1):
                side = (x - cx) / max(1, w)
                v = -side * 0.6 + (0.4 - t) * 0.5 + (rnd.random() - 0.5) * 0.35
                idx = max(0, min(4, int((v + 1) / 2 * 5)))
                if y == base and (x + y) % 3 == 0: continue
                px(img, x, y, rp[idx])
    return outline(img, OUT)

def make_tree(kind, fruit):
    if kind == 'pino': return up(tree_pino(not fruit), 2)
    if kind in ('manzana', 'pera', 'naranja', 'roble'): im = tree_round(kind, fruit)
    elif kind == 'mango': im = tree_mango(fruit)
    elif kind == 'banano': im = tree_banano(fruit)
    else: im = tree_coco(fruit)
    return up(im, 2)

# ---------- parcelas ------------------------------------------------------
CROP_COL = {
    'manzana': ((214,36,40),(255,140,130)), 'pera': ((206,214,72),(240,246,150)),
    'naranja': ((248,146,28),(255,210,120)), 'mango': ((244,140,40),(250,200,70)),
    'banano': ((250,214,50),(255,240,140)), 'coco': ((122,82,42),(170,120,66)),
}
def plot(state, crop=None):
    img = new(32, 48)
    wood = [(98,62,34),(130,86,46),(160,112,62)]
    soil = [(86,56,32),(108,72,40),(126,86,50)]
    # marco de madera + tierra arada
    for y in range(22, 46):
        for x in range(1, 31):
            edge = x in (1, 30) or y in (22, 45)
            if edge: c = wood[0]
            elif x in (2, 29) or y in (23, 44): c = wood[2] if y != 44 else wood[1]
            else:
                c = soil[2] if (y - 24) % 5 in (0, 1) else soil[0]
                if (y - 24) % 5 == 2: c = soil[1]
            px(img, x, y, c)
    rows = [26, 31, 36, 41]
    if state == 'planted':
        for ry in rows[:-1]:
            for x in (7, 15, 23):
                px(img, x, ry - 1, (90,170,60)); px(img, x - 1, ry - 2, (120,200,80)); px(img, x + 1, ry - 2, (70,150,50))
                px(img, x, ry, (60,120,40))
    elif state == 'grown':
        base, hi = CROP_COL[crop]
        rp = ramp((40,110,40),(70,150,50),(100,182,64),(140,206,90))
        spots = [(8,30),(16,35),(24,30),(12,40),(21,41)]
        for i, (x, y) in enumerate(spots):
            if crop in ('banano', 'coco'):
                for ang in (-2.6, -0.5, -1.55, -2.1, -1.0):
                    for k in range(8):
                        px(img, round(x + math.cos(ang) * k), round(y - 2 + math.sin(ang) * k + 0.05 * k * k), rp[1 + (k % 2)])
                for k in range(5): px(img, x, y - k, (110,130,50) if crop == 'banano' else (130,96,56))
            else:
                shade_blob_small(img, x, y - 4, 5, rp, i)
            # frutos
            for (dx, dy) in [(-3,-5),(2,-7),(1,-2)] if crop not in ('banano', 'coco') else [(0,-4)]:
                if crop == 'banano':
                    for d in range(3): px(img, x + 1, y - 4 + d, base); px(img, x + 2, y - 4 + d, (232,184,30))
                else:
                    px(img, x + dx, y + dy, base); px(img, x + dx + 1, y + dy, base)
                    px(img, x + dx, y + dy + 1, base); px(img, x + dx + 1, y + dy + 1, hi if crop != 'coco' else base)
                    px(img, x + dx, y + dy, hi)
    return up(outline(img, OUT), 2)

def shade_blob_small(img, cx, cy, r, rp, seed):
    tmp = new(img.width, img.height)
    shade_blob(tmp, [(cx, cy, r), (cx - 3, cy + 2, r - 2), (cx + 3, cy + 2, r - 2)], rp, seed=seed, dither=0.1)
    img.alpha_composite(tmp)

# ---------- rocas minerales ----------------------------------------------
def rock(kind, depleted=False):
    img = new(32, 32)
    ellipse_shadow(img, 16, 27, 13, 3)
    rp = ramp((92,88,96),(122,118,124),(152,148,150),(184,180,178),(212,208,204))
    if kind == 'piedra':
        rp = ramp((92,82,70),(120,108,92),(146,134,114),(172,160,136),(198,188,162))
    circles = [(16,18,10),(9,21,7),(23,21,7),(14,12,6)] if not depleted else [(11,23,5),(20,23,5),(15,20,4)]
    shade_blob(img, circles, rp, seed=5 if kind == 'cobre' else 9, dither=0.12)
    if not depleted:
        rnd = random.Random(3 if kind == 'cobre' else 4)
        for _ in range(7):
            x, y = rnd.randrange(7, 25), rnd.randrange(10, 26)
            if img.getpixel((x, y))[3] == 255 and img.getpixel((x + 1, y + 1))[3] == 255:
                if kind == 'cobre':
                    px(img, x, y, (214,118,52)); px(img, x + 1, y, (184,90,38)); px(img, x, y + 1, (240,160,90)); px(img, x+1, y+1, (64,150,120))
                elif kind == 'plata':
                    px(img, x, y, (236,240,248)); px(img, x + 1, y + 1, (196,206,222)); px(img, x + 1, y, (255,255,255))
        if kind == 'piedra':   # vetas de laja horizontales
            for y in (14, 19, 23):
                for x in range(4, 28):
                    if img.getpixel((x, y))[3] == 255 and (x + y) % 5: px(img, x, y, (104,88,70))
    return up(outline(img, OUT), 2)

# ---------- nodos de agua (overlay sobre tesela de agua) ------------------
def water_spot(kind, active=True):
    img = new(32, 32)
    if kind == 'pesca':
        if active:
            for r, a in ((12, 140), (8, 190), (4, 230)):
                for t in range(0, 360, 6):
                    x = 16 + math.cos(math.radians(t)) * r; y = 16 + math.sin(math.radians(t)) * r * 0.5
                    px(img, round(x), round(y), (225,245,255,a))
            # silueta de pez
            for dx in range(-4, 4):
                h = 1 if abs(dx) > 2 else 2
                for dy in range(-h + 1, h):
                    px(img, 16 + dx, 16 + dy, (24,60,100,200))
            px(img, 20, 15, (24,60,100,200)); px(img, 20, 17, (24,60,100,200))
        else:
            for t in range(0, 360, 10):
                px(img, round(16 + math.cos(math.radians(t)) * 6), round(16 + math.sin(math.radians(t)) * 3), (225,245,255,90))
    else:  # oro fluvial: lecho de arena con destellos dorados
        rnd = random.Random(12)
        for y in range(32):
            for x in range(32):
                d = ((x - 16) / 13) ** 2 + ((y - 17) / 8) ** 2
                if d < 1:
                    a = int(150 * (1 - d) + 40)
                    c = (206,176,104) if (x * 7 + y * 3) % 5 else (182,150,86)
                    px(img, x, y, (*c, min(210, a)))
        if active:
            for _ in range(9):
                x, y = rnd.randrange(7, 25), rnd.randrange(12, 22)
                px(img, x, y, (255,220,60)); px(img, x + 1, y, (240,180,30))
            for (x, y) in ((10, 13), (20, 16), (15, 20)):
                px(img, x, y - 1, (255,255,210)); px(img, x, y + 1, (255,255,210)); px(img, x - 1, y, (255,255,210)); px(img, x + 1, y, (255,255,210)); px(img, x, y, (255,240,120))
        # agua corriendo encima
        for k in range(3):
            y = 11 + k * 5
            for x in range(6 + k, 24 - k, 1):
                if (x + k) % 4 != 0: px(img, x, y, (220,244,255,120))
    return up(img, 2)

# ---------- animales ----------------------------------------------------
def animal(kind, frame=0):
    if kind == 'conejo':
        img = new(20, 18)
        ellipse_shadow(img, 10, 16, 7, 1.8)
        b = [(150,120,96),(178,148,120),(206,180,152)]
        hop = -1 if frame else 0
        for y in range(8, 15):
            for x in range(4, 14):
                if ((x - 9) / 5.2) ** 2 + ((y - 11.5) / 3.6) ** 2 <= 1:
                    px(img, x, y + hop, b[2] if y < 10 else (b[1] if y < 13 else b[0]))
        for y in range(5, 11):
            for x in range(12, 18):
                if ((x - 14.5) / 3) ** 2 + ((y - 8) / 2.8) ** 2 <= 1:
                    px(img, x, y + hop, b[1] if y > 7 else b[2])
        for y in range(0, 6):  # orejas
            px(img, 13, y + hop, b[1]); px(img, 15, y + 1 + hop, b[0]); px(img, 13, y + hop + 0, b[2] if y > 2 else b[1])
        px(img, 16, 7 + hop, (30,20,20)); px(img, 17, 9 + hop, (220,120,130))
        px(img, 4, 10 + hop, (250,250,250)); px(img, 3, 10 + hop, (250,250,250))  # colita
        px(img, 6, 15 + hop, b[0]); px(img, 12, 15 + hop, b[0])
        return up(outline(img, OUT), 2)
    if kind == 'venado':
        img = new(32, 32)
        ellipse_shadow(img, 15, 30, 10, 2)
        b = [(140,86,44),(176,114,60),(204,146,86)]
        for y in range(13, 22):
            for x in range(6, 24):
                if ((x - 15) / 9) ** 2 + ((y - 17.5) / 4.5) ** 2 <= 1:
                    px(img, x, y, b[2] if y < 15 else (b[1] if y < 20 else b[0]))
        for (x, y) in ((10, 15), (14, 14), (18, 15), (12, 17), (17, 17)):
            px(img, x, y, (240,226,200))  # manchas
        legs = [(8, 0), (11, 1), (19, 0), (22, 1)]
        for i, (x, ph) in enumerate(legs):
            off = (1 if (frame + ph) % 2 else -0) if frame else 0
            for y in range(21, 29): px(img, x + (off if y > 25 else 0), y, b[0] if i % 2 else b[1])
            px(img, x + (off), 29, (50,36,24))
        for y in range(7, 15):  # cuello
            px(img, 22 + (14 - y) // 3, y, b[1]); px(img, 23 + (14 - y) // 3, y, b[2])
        for y in range(4, 9):
            for x in range(24, 31):
                if ((x - 27) / 3.5) ** 2 + ((y - 6.5) / 2.4) ** 2 <= 1: px(img, x, y, b[2] if y < 6 else b[1])
        px(img, 30, 7, (40,26,20)); px(img, 27, 5, (20,14,10)); px(img, 24, 3, b[0]); px(img, 25, 3, b[1])
        for (x, y) in ((25,2),(24,1),(26,1),(27,0),(23,0),(28,2)): px(img, x, y, (120,96,70))  # astas
        px(img, 6, 14, (250,250,250)); px(img, 5, 14, (250,250,250))
        return up(outline(img, OUT), 2)
    # ave silvestre (original: cuerpo azul, pecho amarillo, cresta roja)
    img = new(18, 18)
    ellipse_shadow(img, 9, 16, 5, 1.5)
    bob = frame
    for y in range(7, 14):
        for x in range(3, 13):
            if ((x - 8) / 5) ** 2 + ((y - 10.5) / 3.5) ** 2 <= 1:
                px(img, x, y + bob, (40,92,200) if y < 11 else (250,204,48))
    for y in range(3, 8):
        for x in range(9, 15):
            if ((x - 12) / 2.8) ** 2 + ((y - 5.5) / 2.4) ** 2 <= 1: px(img, x, y + bob, (52,110,220))
    px(img, 15, 5 + bob, (250,170,40)); px(img, 16, 5 + bob, (230,140,30)); px(img, 13, 4 + bob, (20,20,30))
    px(img, 11, 2 + bob, (220,40,40)); px(img, 12, 1 + bob, (220,40,40)); px(img, 12, 2 + bob, (240,70,60))
    for y in range(8, 11): px(img, 2, y + bob, (28,70,160)); px(img, 1, y + bob - 1, (28,70,160))
    for y in range(14, 16): px(img, 7, y, (200,130,40)); px(img, 10, y, (200,130,40))
    for x in range(5, 10): px(img, x, 9 + bob, (30,74,170))  # ala
    return up(outline(img, OUT), 2)

# ---------- jugador ----------------------------------------------------
SKIN = [(214,158,112),(238,190,142)]
HAIR = [(70,44,26),(102,66,36)]
TUNIC = [(26,66,168),(40,96,212),(84,140,236)]
CAPE = [(150,24,30),(196,40,44)]
PANTS = [(92,64,40),(118,84,52)]
BOOT = (56,38,26)
BELT = (236,190,40)
HAT = [(232,184,32),(248,206,60)]
FEATHER = (220,40,40)
CAPE_ON = True
def player(direction, frame):
    """direction: down/up/left/right; frame 0 quieto, 1 y 2 pasos"""
    img = new(24, 40)
    ellipse_shadow(img, 12, 38, 7, 1.8)
    sw = [0, 2, -2][frame]
    side = direction in ('left', 'right')
    # capa (detrás si mira abajo; visible completa si mira arriba)
    if direction != 'down' and CAPE_ON:
        xr = range(6, 18) if direction == 'up' else range(5, 10)
        for y in range(14, 32):
            for x in xr:
                px(img, x - (1 if side and y > 26 else 0), y, CAPE[1] if x > 7 else CAPE[0])
    # piernas
    for y in range(28, 37):
        if side:
            px(img, 11 + (sw if y > 31 else sw // 2), y, PANTS[1]); px(img, 12 + (sw if y > 31 else sw // 2), y, PANTS[0])
            px(img, 12 - (sw if y > 31 else sw // 2), y, PANTS[0]); px(img, 13 - (sw if y > 31 else sw // 2), y, PANTS[0])
        else:
            l = -1 if (frame == 1 and y > 33) else 0; r = -1 if (frame == 2 and y > 33) else 0
            if y + l * -1 < 37 + l:
                for x in (9, 10): px(img, x, y + l, PANTS[1])
            for x in (13, 14): px(img, x, y + r, PANTS[0])
    if side:
        for x in range(10 + sw, 13 + sw): px(img, x, 36, BOOT); px(img, x, 37, BOOT)
        for x in range(11 - sw, 14 - sw): px(img, x, 36, BOOT); px(img, x, 37, BOOT)
    else:
        for x in (8, 9, 10): px(img, x, 36 - (1 if frame == 1 else 0), BOOT); px(img, x, 37 - (1 if frame == 1 else 0), BOOT)
        for x in (13, 14, 15): px(img, x, 36 - (1 if frame == 2 else 0), BOOT); px(img, x, 37 - (1 if frame == 2 else 0), BOOT)
    # túnica
    for y in range(15, 30):
        hw = 5 if y < 26 else 6
        if side: hw = 4 if y < 26 else 5
        for x in range(12 - hw, 12 + hw):
            c = TUNIC[1]
            if x == 12 - hw: c = TUNIC[0]
            if x == 12 + hw - 1: c = TUNIC[0]
            if x == 12 - hw + 1 and y < 24: c = TUNIC[2]
            px(img, x, y, c)
    for x in range(7, 17 if not side else 16): px(img, x, 24, BELT)
    if direction == 'down': px(img, 12, 24, (255,240,150))
    if direction == 'up' and CAPE_ON:
        for y in range(15, 30):
            for x in range(7, 17):
                px(img, x, y, CAPE[1] if x > 8 else CAPE[0])
    # brazos
    if side:
        ax = 12 + (2 if direction == 'right' else -3)
        for y in range(16, 25): px(img, ax + (sw // 2 if y > 20 else 0), y, TUNIC[0])
        px(img, ax + sw // 2, 25, SKIN[0])
    else:
        for y in range(16, 24):
            px(img, 6, y + (1 if frame == 2 and y > 20 else 0), TUNIC[0]); px(img, 17, y + (1 if frame == 1 and y > 20 else 0), TUNIC[0])
        px(img, 6, 24, SKIN[0]); px(img, 17, 24, SKIN[0])
    # cabeza
    for y in range(4, 15):
        for x in range(7, 17):
            if ((x - 11.5) / 5) ** 2 + ((y - 9.5) / 5.3) ** 2 <= 1:
                px(img, x, y, SKIN[1] if x < 13 else SKIN[0])
    # pelo
    for y in range(3, 9):
        for x in range(6, 18):
            if ((x - 11.5) / 5.6) ** 2 + ((y - 7.5) / 4.6) ** 2 <= 1 and (y < 7 or direction == 'up' or (side and ((direction == 'right' and x < 10) or (direction == 'left' and x > 13)))):
                px(img, x, y, HAIR[1] if (x + y) % 3 else HAIR[0])
    if direction == 'up':
        for y in range(8, 13):
            for x in range(7, 17):
                if ((x - 11.5) / 5) ** 2 + ((y - 9.5) / 5.3) ** 2 <= 1: px(img, x, y, HAIR[0] if x % 3 == 0 else HAIR[1])
    if direction == 'down':
        px(img, 9, 10, (30,30,50)); px(img, 14, 10, (30,30,50)); px(img, 11, 13, (190,110,90)); px(img, 12, 13, (190,110,90))
    elif direction == 'right':
        px(img, 14, 10, (30,30,50)); px(img, 16, 11, SKIN[0])
    elif direction == 'left':
        px(img, 9, 10, (30,30,50)); px(img, 7, 11, SKIN[0])
    # gorro amarillo con pluma (toque saturado)
    for x in range(7, 17): px(img, x, 4, HAT[0])
    for x in range(8, 16): px(img, x, 3, HAT[1])
    for x in range(9, 15): px(img, x, 2, HAT[1])
    if FEATHER: px(img, 15, 1, FEATHER); px(img, 16, 0, FEATHER)
    im = outline(img, OUT)
    if direction == 'left':
        pass
    return up(im, 2)

def player_sheet():
    """hoja 4 filas (abajo, izquierda, derecha, arriba) x 3 cuadros, 48x80 cada uno"""
    sheet = Image.new('RGBA', (48 * 3, 80 * 4), (0, 0, 0, 0))
    for r, d in enumerate(['down', 'left', 'right', 'up']):
        for f in range(3):
            if d == 'left':
                fr = player('right', f).transpose(Image.FLIP_LEFT_RIGHT)
            else:
                fr = player(d, f)
            sheet.paste(fr, (f * 48, r * 80))
    return sheet

# ---------- arbustos y letrero ----------------------------------------
def bush(variant):
    img = new(32, 32)
    ellipse_shadow(img, 16, 27, 13, 3)
    rp = ramp((40,98,40),(60,128,46),(86,156,56),(120,186,72),(158,210,96))
    if variant == 0:
        shade_blob(img, [(16,19,9),(9,22,6),(23,22,6),(16,14,6)], rp, seed=41)
    else:
        shade_blob(img, [(12,20,8),(21,19,8),(16,14,6)], rp, seed=43)
        for (x, y) in ((9,17),(14,13),(20,16),(23,21),(12,23),(17,20)):
            px(img, x, y, (250,250,244)); px(img, x+1, y, (250,250,244)); px(img, x, y+1, (240,150,190))
    return up(outline(img, OUT), 2)

FONT = "/usr/share/fonts/truetype/sand-box/google/Pixelify Sans/PixelifySans-VariableFont_wght.ttf"
def sign():
    img = new(48, 40)
    ellipse_shadow(img, 24, 37, 12, 2)
    wood = [(98,62,34),(136,90,48),(170,120,66),(198,152,92)]
    for y in range(20, 38):
        for x in (12, 13, 34, 35): px(img, x, y, wood[1] if x in (12, 34) else wood[0])
    for y in range(4, 24):
        for x in range(3, 45):
            c = wood[2]
            if y in (4, 23) or x in (3, 44): c = wood[0]
            elif (y - 4) % 6 == 0: c = wood[1]
            elif y in (5,) : c = wood[3]
            px(img, x, y, c)
    for (x, y) in ((6, 7), (41, 7), (6, 20), (41, 20)): px(img, x, y, (70,60,50))
    big = up(outline(img, OUT), 2)
    d = ImageDraw.Draw(big)
    try:
        f = ImageFont.truetype(FONT, 17); f.set_variation_by_name('Bold')
    except Exception:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    txt = "El Jardín"
    bb = d.textbbox((0, 0), txt, font=f)
    tx = (96 - (bb[2] - bb[0])) // 2 - bb[0]; ty = 27 - (bb[3] - bb[1]) // 2 - bb[1]
    d.text((tx + 1, ty + 1), txt, font=f, fill=(226,186,120))
    d.text((tx, ty), txt, font=f, fill=(58,34,16))
    # ligero redondeo a pixel: umbral alfa
    return big

# ---------- iconos 16x16 (x2 = 32, x4 = 64) ---------------------------
def _ic():
    return new(16, 16)
def icon(item):
    img = _ic()
    def disc(cx, cy, r, base, hi, dark, ry=None):
        ry = ry or r
        for y in range(16):
            for x in range(16):
                d = ((x + .5 - cx) / r) ** 2 + ((y + .5 - cy) / ry) ** 2
                if d <= 1:
                    c = base
                    if (x + .5 - cx) + (y + .5 - cy) < -r * .55: c = hi
                    elif (x + .5 - cx) + (y + .5 - cy) > r * .7: c = dark
                    px(img, x, y, c)
    if item == 'manzana':
        disc(8, 9, 5.5, (214,36,40), (255,130,120), (150,20,30)); px(img, 8, 3, (90,60,30)); px(img, 8, 2, (90,60,30)); px(img, 9, 2, (80,170,60)); px(img, 10, 2, (80,170,60))
    elif item == 'pera':
        disc(8, 11, 4.6, (206,214,72), (242,248,160), (150,160,40)); disc(8, 6, 2.8, (206,214,72), (242,248,160), (170,180,50)); px(img, 8, 2, (90,60,30)); px(img, 9, 3, (80,170,60))
    elif item == 'naranja':
        disc(8, 9, 5.5, (248,146,28), (255,210,120), (196,96,16)); px(img, 8, 3, (60,130,50)); px(img, 9, 3, (80,170,60)); px(img, 6, 8, (255,190,90)); px(img, 10, 11, (220,120,20))
    elif item == 'mango':
        for y in range(16):
            for x in range(16):
                if ((x - 8) / 6) ** 2 + ((y - 8.5) / 4.6) ** 2 <= 1 and not (x > 11 and y < 6):
                    t = x / 15
                    px(img, x, y, lerp((236,60,40), (250,206,60), t))
        px(img, 3, 6, (255,170,150)); px(img, 2, 4, (90,60,30))
    elif item == 'banano':
        for k, off in enumerate((0, 2, 4)):
            for i in range(10):
                x = 3 + i; y = 4 + off + int(0.09 * (i - 5) ** 2 * -1 + 2)
                px(img, x, y, (250,214,50)); px(img, x, y + 1, (226,180,30))
            px(img, 13, 4 + off + 1, (110,90,30))
        for y in range(3, 11): px(img, 2, y, (110,130,50))
    elif item == 'coco':
        disc(8, 9, 5.8, (124,82,42), (170,120,70), (82,52,26)); px(img, 6, 7, (50,30,16)); px(img, 9, 7, (50,30,16)); px(img, 7, 10, (50,30,16))
    elif item.endswith('_seed'):
        fruit = item[:-5]
        bag = [(150,112,66),(182,142,90),(206,170,116)]
        for y in range(5, 15):
            for x in range(3, 13):
                if ((x - 7.5) / 5.2) ** 2 + ((y - 10.5) / 4.8) ** 2 <= 1 or (5 <= x <= 10 and y < 8):
                    px(img, x, y, bag[1] if x > 4 else bag[0])
        for x in range(5, 11): px(img, x, 6, (120,80,40))
        for y in range(2, 6): px(img, 7, y, (80,170,60)); 
        px(img, 6, 2, (110,200,80)); px(img, 8, 3, (110,200,80))
        col = CROP_COL[fruit][0]
        for (dx, dy) in ((0,0),(1,0),(0,1),(1,1),(2,0),(2,1),(1,2),(1,-1)):
            px(img, 9 + dx, 10 + dy, col)
        px(img, 9, 10, CROP_COL[fruit][1])
    elif item in ('trucha', 'bocachico', 'mojarra'):
        cols = {'trucha': ((140,170,190),(226,120,140),(80,110,140)), 'bocachico': ((190,190,170),(230,220,190),(120,120,100)), 'mojarra': ((120,130,150),(170,180,200),(70,76,96))}[item]
        for y in range(16):
            for x in range(16):
                if ((x - 7) / 5.5) ** 2 + ((y - 8) / 3) ** 2 <= 1:
                    px(img, x, y, cols[0] if y < 8 else cols[1] if item != 'mojarra' else cols[0])
        for y in range(5, 12):
            if abs(y - 8) <= (13 - 12 + 3) - abs(0): px(img, 13, y, cols[2]); px(img, 14, y + (1 if y > 8 else -1), cols[2])
        px(img, 3, 7, (20,20,30)); 
        if item == 'trucha':
            for x in range(4, 11): px(img, x, 8, (226,120,140))
        if item == 'mojarra':
            for x in (5, 8, 11): px(img, x, 6, cols[2]); px(img, x, 7, cols[2])
    elif item == 'carne':
        disc(8, 9, 5.5, (196,60,60), (236,120,110), (140,30,40), 4.2)
        for y in range(7, 12): px(img, 3, y, (246,236,220))
        disc(8, 9, 2, (236,200,190), (250,230,220), (220,170,160))
    elif item == 'piel':
        for y in range(3, 14):
            for x in range(2, 14):
                if ((x - 8) / 6) ** 2 + ((y - 8.5) / 5.4) ** 2 <= 1 or (x in (2, 13) and y in (3, 13)):
                    px(img, x, y, (176,114,60) if (x + y) % 4 else (150,94,48))
        for (x, y) in ((6, 7), (10, 9), (8, 11)): px(img, x, y, (230,214,190))
    elif item == 'pluma':
        for i in range(12):
            x = 3 + i; y = 13 - i
            px(img, x, y, (240,240,240))
            if i > 1:
                for k in (1, 2): px(img, x - k, y - k + 1, (40,92,200) if i < 9 else (220,40,40)); px(img, x + k - 1, y + k, (60,120,220))
    elif item in ('mineral_cobre', 'mineral_plata', 'pepita_oro'):
        if item == 'pepita_oro':
            pts = [(8,9,4.5,3.6),(5,8,2.5,2.2),(11,8,2.4,2.5)]
            base, hi, dk = (240,190,30), (255,240,140), (180,120,10)
        else:
            pts = [(8,9,5.5,4.2)]
            base, hi, dk = ((168,98,52), (226,150,90), (110,62,30)) if item == 'mineral_cobre' else ((188,196,210), (250,252,255), (120,128,144))
        for (cx, cy, rx, ry) in pts: disc(cx, cy, rx, base, hi, dk, ry)
        if item == 'mineral_cobre': px(img, 6, 10, (64,150,120)); px(img, 10, 8, (64,150,120))
        if item != 'mineral_cobre': px(img, 6, 6, (255,255,255))
    elif item == 'red_pesca':
        for y in range(1, 14): px(img, 3 + y // 5, y, (120,80,40))  # mango
        for y in range(16):
            for x in range(16):
                d = ((x - 9.5) / 5.5) ** 2 + ((y - 5) / 4.6) ** 2
                if 0.65 <= d <= 1: px(img, x, y, (110,72,36))
                elif d < 0.65 and ((x + y) % 3 == 0 or (x - y) % 3 == 0): px(img, x, y, (236,232,210))
        for y in range(9, 15):
            for x in range(7, 13):
                if (x + y) % 2 == 0 and abs(x - 10) < (15 - y): px(img, x, y, (236,232,210))
    elif item == 'lanza':
        for i in range(11): px(img, 2 + i, 14 - i, (140,96,52)); px(img, 3 + i, 14 - i, (110,72,40))
        for (x, y) in ((12,3),(13,2),(14,1),(13,3),(12,4),(14,2),(15,0),(13,1),(11,3),(12,2)): px(img, x, y, (190,200,214))
        px(img, 14, 1, (250,252,255)); px(img, 11, 5, (220,40,40)); px(img, 10, 5, (220,40,40)); px(img, 11, 6, (250,206,40))
    elif item == 'pico':
        for i in range(11): px(img, 4 + i // 2 * 0 + i * 0 + 7 - i // 3, 4 + i, (140,96,52)); px(img, 8 - i // 3, 4 + i, (110,72,40))
        for x in range(2, 15):
            y = 4 - int(2.5 * math.sin(math.pi * (x - 2) / 12))
            px(img, x, y, (170,178,190)); px(img, x, y + 1, (120,126,140))
        px(img, 2, 5, (120,126,140)); px(img, 14, 5, (120,126,140))
    elif item == 'madera':
        for (y0, x0) in ((9, 1), (5, 3)):
            for y in range(y0, y0 + 5):
                for x in range(x0, x0 + 12):
                    px(img, x, y, (140,92,50) if y in (y0 + 1, y0 + 2) else (110,70,38))
            for y in range(y0, y0 + 5):
                for x in range(x0 + 11, x0 + 14):
                    if (x - (x0 + 12)) ** 2 + (y - (y0 + 2)) ** 2 <= 5: px(img, x, y, (214,176,120))
            px(img, x0 + 12, y0 + 2, (176,136,86))
    elif item == 'piedra':
        disc(8, 9, 6, (160,142,116), (210,196,168), (110,94,74), 4.5)
        for x in range(4, 12): px(img, x, 9, (124,106,84))
    elif item == 'hacha':
        for i in range(12): px(img, 4 + i // 3, 14 - i, (140,96,52)); px(img, 5 + i // 3, 14 - i, (110,72,40))
        for y in range(1, 8):
            for x in range(7, 14):
                if (x - 7) ** 2 / 36 + (y - 4) ** 2 / 9 <= 1 and x > 8: px(img, x, y, (186,196,210) if x < 12 else (230,236,244))
        px(img, 8, 3, (90,90,96)); px(img, 8, 5, (90,90,96))
    elif item == 'batea':
        for y in range(16):
            for x in range(16):
                d = ((x - 8) / 7) ** 2 + ((y - 9) / 4.4) ** 2
                if d <= 1:
                    px(img, x, y, (150,100,56) if d > 0.55 else ((120,78,42) if y > 9 else (176,124,72)))
        for (x, y) in ((7, 10), (9, 9), (8, 11)): px(img, x, y, (250,206,40))
        px(img, 9, 9, (255,245,170))
    return outline(img, OUT)

def icon_sizes(item):
    i = icon(item)
    return {16: i, 32: up(i, 2), 64: up(i, 4)}
