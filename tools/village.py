"""Sprites originales del pueblo de El Jardín (LIFE INC): casas, puesto, fuente, antorchas, vallas, cascada, mina, capataz."""
import math, random
from PIL import Image, ImageDraw
from pixel import new, up, px, outline, shade_blob, ellipse_shadow
import objects as O
from tiles import GRASS, WATER, WATER_HI, SHALLOW

OUT = (40, 28, 20, 255)
WOOD = [(70,44,24),(98,62,34),(128,84,46),(158,110,62)]
def rect(img, x0, y0, x1, y1, c):
    for y in range(y0, y1):
        for x in range(x0, x1): px(img, x, y, c)

def stone_wall(img, x0, y0, x1, y1, pal=((120,112,100),(148,140,124),(170,162,146),(96,88,78)), seed=1):
    rnd = random.Random(seed)
    for y in range(y0, y1):
        r = (y - y0) // 5; off = 3 if r % 2 else 0
        for x in range(x0, x1):
            lx = (x - x0 + off) % 8; ly = (y - y0) % 5
            if lx == 7 or ly == 4: c = pal[3]
            else:
                h = ((x - x0 + off) // 8 * 5 + r * 3) % 3
                c = pal[h]
                if ly == 0: c = tuple(min(255, v + 18) for v in c)
            px(img, x, y, c)

def roof(img, xl0, xr0, xl1, xr1, y0, y1, pal):
    """plano de techo frontal: trapecio de y0 (cumbrera) a y1 (alero) con tejas"""
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0)
        a = round(xl0 + (xl1 - xl0) * t); b = round(xr0 + (xr1 - xr0) * t)
        row = (y - y0) // 4; off = 3 if row % 2 else 0
        for x in range(a, b):
            ly = (y - y0) % 4; lx = (x + off) % 6
            c = pal[1]
            if ly == 3: c = pal[0]
            elif lx == 5: c = pal[0]
            elif ly == 0: c = pal[2]
            if x - a < 2 or b - x <= 2: c = pal[0]
            px(img, x, y, c)
    rect(img, xl0 - 1, y0 - 2, xr0 + 1, y0 + 1, pal[3])   # cumbrera
    rect(img, xl1, y1, xr1, y1 + 2, pal[0])             # alero

def window(img, x, y, w=10, h=10, lit=True):
    rect(img, x - 1, y - 1, x + w + 1, y + h + 1, WOOD[0])
    rect(img, x, y, x + w, y + h, (250,214,120) if lit else (60,70,90))
    if lit: rect(img, x, y, x + w // 2, y + h // 2, (255,236,170))
    rect(img, x + w // 2, y, x + w // 2 + 1, y + h, WOOD[1]); rect(img, x, y + h // 2, x + w, y + h // 2 + 1, WOOD[1])

def banner(img, x, y, w=12, h=30):
    rect(img, x - 2, y - 2, x + w + 2, y, WOOD[2])
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            tip = (yy - (y + h - 6)) > -abs(xx - (x + w / 2 - 0.5)) + w / 2 - 1 and yy > y + h - 6
            if tip: continue
            px(img, xx, yy, (176,30,36) if xx > x + 1 else (130,20,28))
    cx, cy = x + w // 2, y + h // 2 - 2       # emblema: árbol verde con tronco dorado
    for yy in range(cy - 5, cy + 3):
        for xx in range(cx - 5, cx + 6):
            if ((xx - cx) / 4.5) ** 2 + ((yy - cy + 1) / 3.8) ** 2 <= 1: px(img, xx, yy, (70,160,70))
    rect(img, cx, cy + 2, cx + 1, cy + 8, (226,184,60)); px(img, cx - 2, cy + 7, (226,184,60)); px(img, cx + 2, cy + 7, (226,184,60))

def lantern(img, x, y):
    rect(img, x, y, x + 4, y + 5, (40,30,24)); rect(img, x + 1, y + 1, x + 3, y + 4, (255,190,70)); px(img, x + 1, y + 1, (255,240,170))

def casa_capataz():
    W_, H_ = 104, 150
    img = new(W_, H_)
    ellipse_shadow(img, 52, 146, 50, 5, 80)
    stone_wall(img, 6, 126, 98, 148, seed=2)
    rect(img, 6, 92, 98, 126, (226,206,160))                     # yeso
    for x in (6, 28, 76, 96): rect(img, x, 92, x + 3, 126, WOOD[1])
    rect(img, 6, 92, 98, 95, WOOD[0]); rect(img, 6, 108, 98, 110, WOOD[1])
    for k in range(10): px(img, 30 + k, 110 + k, WOOD[1]); px(img, 31 + k, 110 + k, WOOD[1])   # diagonales
    for k in range(10): px(img, 74 - k, 110 + k, WOOD[1]); px(img, 73 - k, 110 + k, WOOD[1])
    window(img, 13, 97, 10, 9); window(img, 82, 97, 9, 9)
    # puerta en arco
    for y in range(110, 148):
        for x in range(44, 60):
            if y < 116 and ((x - 51.5) / 8) ** 2 + ((y - 116) / 6) ** 2 > 1: continue
            c = WOOD[1] if (x - 44) % 4 else WOOD[0]
            px(img, x, y, c)
    rect(img, 56, 128, 58, 131, (220,190,90))
    lantern(img, 37, 112); lantern(img, 63, 112)
    banner(img, 64, 96 - 14, 11, 26)
    roof(img, 14, 90, 0, 104, 34, 92, [(92,46,30),(132,70,44),(160,92,56),(70,34,22)])
    stone_wall(img, 72, 12, 84, 40, seed=5)                      # chimenea
    rect(img, 70, 10, 86, 13, (90,82,72))
    return up(outline(img, OUT), 2)

def casa_piedra():
    W_, H_ = 104, 150
    img = new(W_, H_)
    ellipse_shadow(img, 52, 146, 50, 5, 80)
    pal = ((150,136,112),(176,160,130),(196,180,148),(110,98,80))
    stone_wall(img, 6, 88, 98, 148, pal, seed=7)
    window(img, 16, 100, 11, 11); window(img, 78, 100, 11, 11)
    for y in range(116, 148):                                    # puerta
        for x in range(46, 60):
            if y < 121 and ((x - 52.5) / 7) ** 2 + ((y - 121) / 5) ** 2 > 1: continue
            px(img, x, y, (84,52,30) if (x - 46) % 4 else (60,36,20))
    # escaleras
    for i in range(3):
        rect(img, 42 - i * 2, 140 + i * 3, 64 + i * 2, 143 + i * 3, (186,176,156) if i % 2 == 0 else (160,150,132))
    roof(img, 12, 92, 0, 104, 30, 88, [(56,62,78),(84,92,110),(110,120,138),(44,48,60)])
    # buhardilla
    rect(img, 44, 46, 62, 66, (176,160,130)); window(img, 48, 50, 10, 10)
    roof(img, 52, 54, 40, 66, 36, 48, [(56,62,78),(84,92,110),(110,120,138),(44,48,60)])
    lantern(img, 38, 112)
    return up(outline(img, OUT), 2)

def puesto():
    img = new(70, 72)
    ellipse_shadow(img, 35, 68, 33, 4, 70)
    for x in (5, 62):
        rect(img, x, 22, x + 3, 68, WOOD[1]); rect(img, x, 22, x + 1, 68, WOOD[2])
    rect(img, 4, 44, 66, 56, WOOD[2]); rect(img, 4, 44, 66, 46, WOOD[3]); rect(img, 4, 56, 66, 66, WOOD[1])
    for x in range(4, 66, 6): rect(img, x, 56, x + 1, 66, WOOD[0])
    # cajas de frutas
    for i, (c1, c2) in enumerate([((240,150,30),(255,210,120)), ((214,40,40),(255,140,130)), ((244,190,50),(255,240,140)), ((120,80,40),(170,120,66))]):
        bx = 8 + i * 14
        rect(img, bx, 38, bx + 12, 45, WOOD[1])
        for k in range(5): px(img, bx + 1 + k * 2, 36 + (k % 2), c1); px(img, bx + 2 + k * 2, 37, c2 if k % 2 else c1)
    # toldo rojo con festón
    for y in range(8, 28):
        a = 2 - (y - 8) // 7; b = 68 + (y - 8) // 7
        for x in range(a, b):
            stripe = ((x + 2) // 6) % 2
            px(img, x, y, (196,44,40) if stripe else (226,70,58))
    for x in range(1, 69):
        d = abs(((x - 1) % 8) - 3.5)
        for y in range(28, 31 - int(d / 1.5)): px(img, x, y, (196,44,40) if ((x + 2) // 6) % 2 else (226,70,58))
    rect(img, 2, 7, 68, 9, (150,30,30))
    return up(outline(img, OUT), 2)

def fuente(frame=0):
    img = new(68, 84)
    ellipse_shadow(img, 34, 76, 33, 7, 70)
    st = [(120,116,110),(150,146,138),(178,174,164),(204,200,190)]
    cx, cy = 34, 60
    for y in range(84):
        for x in range(68):
            d = ((x + .5 - cx) / 31) ** 2 + ((y + .5 - cy) / 17) ** 2
            if d <= 1:
                di = ((x + .5 - cx) / 25) ** 2 + ((y + .5 - cy - 1) / 12.5) ** 2
                if di <= 1:
                    v = (x * 3 + y * 7 + frame * 5) % 11
                    px(img, x, y, WATER[3] if v == 0 else (WATER[2] if v < 5 else WATER[1]))
                else:
                    px(img, x, y, st[3] if y < cy - 6 else (st[2] if y < cy + 4 else st[1]))
    # frente del borde (grosor)
    for x in range(4, 65):
        yb = cy + 17 * math.sqrt(max(0, 1 - ((x + .5 - cx) / 31) ** 2))
        for y in range(int(yb) - 1, int(yb) + 6): px(img, x, y, st[0] if (x // 6) % 2 else st[1])
    # columna y cuenco superior
    rect(img, 31, 26, 38, 60, st[1]); rect(img, 31, 26, 33, 60, st[3]); rect(img, 36, 26, 38, 60, st[0])
    for y in range(20, 32):
        for x in range(20, 49):
            if ((x + .5 - 34.5) / 13) ** 2 + ((y + .5 - 27) / 4.5) ** 2 <= 1: px(img, x, y, st[2] if y < 27 else st[0])
    for y in range(22, 27):
        for x in range(24, 45):
            if ((x + .5 - 34.5) / 9.5) ** 2 + ((y + .5 - 25) / 2.4) ** 2 <= 1: px(img, x, y, WATER[2])
    rect(img, 33, 10, 36, 22, st[2]); rect(img, 32, 8, 37, 11, st[3])
    # chorros
    for side in (-1, 1):
        for i in range(20):
            x = 34.5 + side * (13 + i * 0.55); y = 28 + i * 1.25 + 0.02 * i * i
            if (i + frame) % 3: px(img, round(x), round(y), (220,250,250))
    for k in range(6): px(img, 34 + (k % 3) - 1, 4 + k - frame, (220,250,250))
    return up(outline(img, OUT), 2)

def antorcha(frame=0):
    img = new(16, 50)
    ellipse_shadow(img, 8, 47, 5, 1.5, 70)
    rect(img, 7, 16, 10, 48, WOOD[1]); rect(img, 7, 16, 8, 48, WOOD[2])
    rect(img, 5, 14, 12, 17, (60,56,56)); rect(img, 5, 10, 6, 15, (60,56,56)); rect(img, 11, 10, 12, 15, (60,56,56))
    fl = [(9,(236,110,30)),(6.5,(255,190,60)),(3.5,(255,246,190))]
    for i, (r, c) in enumerate(fl):
        for y in range(0, 14):
            for x in range(16):
                if ((x + .5 - 8.5 - (frame - 0.5) * 0.6 * (14 - y) / 14) / (r * 0.45)) ** 2 + ((y + .5 - 10) / r) ** 2 <= 1:
                    px(img, x, y, c)
    return up(outline(img, OUT), 2)

def valla(kind):
    img = new(32, 32)
    if kind == 'h':
        for x in (2, 28):
            rect(img, x, 10, x + 3, 30, WOOD[1]); rect(img, x, 10, x + 1, 30, WOOD[3]); rect(img, x, 9, x + 3, 10, WOOD[3])
        for y in (14, 21): rect(img, 0, y, 32, y + 2, WOOD[2]); rect(img, 0, y + 2, 32, y + 3, WOOD[0])
    else:
        rect(img, 14, 2, 18, 30, WOOD[1]); rect(img, 14, 2, 15, 30, WOOD[3])
        for y in (2, 26): rect(img, 13, y, 19, y + 4, WOOD[2])
    return up(outline(img, OUT), 2)

def baranda():
    img = new(32, 32)
    for x in (1, 17):
        rect(img, x, 18, x + 3, 30, WOOD[1]); rect(img, x, 18, x + 1, 30, WOOD[3])
    rect(img, 0, 21, 32, 23, WOOD[2]); rect(img, 0, 23, 32, 24, WOOD[0])
    return up(img, 2)

def capataz_sheet():
    saved = (O.TUNIC, O.HAT, O.FEATHER, O.CAPE_ON, O.HAIR)
    O.TUNIC = [(40,96,40),(62,130,52),(100,168,76)]; O.HAT = [(110,70,36),(140,92,50)]; O.FEATHER = None; O.CAPE_ON = False; O.HAIR = [(120,120,120),(160,160,160)]
    sheet = O.player_sheet()
    O.TUNIC, O.HAT, O.FEATHER, O.CAPE_ON, O.HAIR = saved
    return sheet

PLAYER_COLORS = {
    'azul':     ([(26,66,168),(40,96,212),(84,140,236)], [(232,184,32),(248,206,60)]),
    'rojo':     ([(150,24,30),(200,44,44),(236,96,86)], [(40,40,48),(70,70,84)]),
    'amarillo': ([(196,140,20),(236,184,40),(252,220,100)], [(150,24,30),(196,40,44)]),
    'verde':    ([(30,110,60),(46,150,80),(100,196,120)], [(232,184,32),(248,206,60)]),
    'morado':   ([(84,40,140),(118,64,184),(160,110,220)], [(40,40,48),(70,70,84)]),
}
def player_variant(color):
    saved = (O.TUNIC, O.HAT)
    O.TUNIC, O.HAT = PLAYER_COLORS[color]
    sheet = O.player_sheet()
    O.TUNIC, O.HAT = saved
    return sheet

def entrada_mina():
    img = new(68, 76)
    ellipse_shadow(img, 34, 72, 32, 4, 80)
    rp = [(84,76,70),(110,100,90),(136,126,112),(162,152,136),(186,176,160)]
    shade_blob(img, [(34,44,28),(14,54,16),(54,54,16),(34,26,18)], rp, seed=17, dither=0.14)
    for y in range(36, 72):
        for x in range(22, 47):
            if y < 46 and ((x + .5 - 34.5) / 12.5) ** 2 + ((y + .5 - 46) / 10) ** 2 > 1: continue
            px(img, x, y, (24,18,16) if y > 40 else (40,30,26))
    rect(img, 20, 38, 24, 72, WOOD[1]); rect(img, 45, 38, 49, 72, WOOD[1]); rect(img, 18, 35, 51, 39, WOOD[2])
    lantern(img, 51, 42)
    for x in range(26, 44, 3): px(img, x, 70, (90,90,96)); px(img, x + 1, 70, (90,90,96))
    return up(outline(img, OUT), 2)

def cascada(frame=0):
    """acantilado con cascada: huella 12x4 casillas; el río sale por la columna relativa 4..6"""
    import tiles as TL
    Wd, Hd = 384, 152
    img = new(Wd, Hd)
    rnd = random.Random(5)
    rock = [(78,68,62),(104,92,80),(128,114,98),(152,140,122),(178,166,146)]
    def top_y(x):
        edge = min(x, Wd - 1 - x)
        base = 40 + 6 * math.sin(x / 23) + 3 * math.sin(x / 7)
        if edge < 70: base += (70 - edge) ** 2 / 70 * 1.2
        return int(min(base, 126))
    g = TL.grass_half(0)
    for x in range(Wd):
        ty = top_y(x)
        for y in range(0, ty): px(img, x, y, g.getpixel((x % 32, y % 32)))
        for y in range(ty, 128): px(img, x, y, rock[1])
    # rocas grandes con volumen sobre la cara
    face = new(Wd, Hd)
    for i in range(150):
        x = rnd.randrange(0, Wd); ty = top_y(x)
        if ty > 120: continue
        y = rnd.randrange(ty + 6, 128); r = rnd.randrange(7, 15)
        shade_blob(face, [(x, y, r), (x + r * 0.5, y + 2, r * 0.7)], rock, seed=i, dither=0.12)
    fpx = face.load()
    for x in range(Wd):
        ty = top_y(x)
        for y in range(ty, 128):
            if fpx[x, y][3]: px(img, x, y, fpx[x, y][:3])
        for k in range(3): px(img, x, ty + k, (66,118,44) if k < 2 else (48,92,38))
        if rnd.random() < 0.25: px(img, x, ty + 3, (66,118,44))
    fall0, fall1 = 166, 250
    for x in range(Wd):
        if top_y(x) < 124:
            for y in range(128, 128 + 5): px(img, x, y, (24,44,16,int(110 - (y - 128) * 18)))
    # canal del río en la meseta
    for x in range(fall0 - 6, fall1 + 6):
        for y in range(0, top_y(x)):
            edge = x < fall0 - 3 or x > fall1 + 2
            px(img, x, y, (214,192,132) if edge else (WATER[1] if (x * 3 + y * 5) % 11 else WATER[2]))
    # caída de agua (franjas verticales que bajan)
    for x in range(fall0, fall1):
        stripe = (x * 7) % 13
        for y in range(top_y(x) - 2, 138):
            s = (stripe + (y - frame * 8) // 6) % 9
            c = (236,252,252) if s < 2 else ((168,232,234) if s < 5 else (104,206,214))
            if x in (fall0, fall0 + 1, fall1 - 1, fall1 - 2): c = (236,252,252)
            px(img, x, y, c)
    # espuma
    cx = (fall0 + fall1) / 2
    for i in range(120):
        x = cx + rnd.uniform(-1, 1) * ((fall1 - fall0) / 2 + 26); y = rnd.uniform(126, 148)
        r = rnd.uniform(3, 6.5)
        for yy in range(int(y - r), int(y + r) + 1):
            for xx in range(int(x - r), int(x + r) + 1):
                if (xx - x) ** 2 + (yy - y) ** 2 <= r * r and 0 <= yy < Hd and 0 <= xx < Wd:
                    shade = (yy - y) > r * 0.3
                    px(img, xx, yy, (190,236,238) if shade else (244,253,253))
    # árboles y arbustos en la meseta
    for (x, y, r) in [(30,20,13),(70,14,11),(262,18,12),(300,26,13),(345,14,11),(108,8,9),(244,6,9),(12,40,9),(372,40,9)]:
        tmp = new(Wd, Hd)
        shade_blob(tmp, [(x, y, r), (x - r * 0.6, y + 3, r * 0.7), (x + r * 0.6, y + 3, r * 0.7)],
                   [(36,84,40),(50,110,46),(72,138,54),(104,166,68),(140,194,90)], seed=x)
        img.alpha_composite(tmp)
    return up(outline(img, OUT), 2)

def ui_icon(kind):
    """iconos 16x16 de la interfaz LIFE INC (x2 = 32)"""
    img = new(16, 16)
    if kind == 'bolsa':
        for y in range(5, 15):
            for x in range(2, 14):
                if ((x - 7.5) / 6) ** 2 + ((y - 10) / 5) ** 2 <= 1: px(img, x, y, (150,100,52) if x > 4 else (118,76,40))
        rect(img, 5, 3, 11, 6, (176,124,70)); rect(img, 4, 6, 12, 7, (90,56,28)); px(img, 9, 10, (226,184,60))
    elif kind == 'habilidades':
        return O.icon('pico')
    elif kind == 'misiones':
        rect(img, 3, 3, 13, 13, (236,214,160)); rect(img, 2, 2, 14, 4, (190,150,90)); rect(img, 2, 12, 14, 14, (190,150,90))
        for y in (6, 8, 10): rect(img, 5, y, 11, y + 1, (120,90,60))
    elif kind == 'social':
        for (cx, col) in ((5, (60,110,200)), (11, (200,60,50))):
            for y in range(2, 7):
                for x in range(cx - 2, cx + 3):
                    if (x - cx) ** 2 + (y - 4) ** 2 <= 5: px(img, x, y, (236,190,142))
            for y in range(8, 15):
                for x in range(cx - 3, cx + 4):
                    if abs(x - cx) <= 1 + (y - 8) // 2: px(img, x, y, col)
    elif kind == 'luna':
        for y in range(16):
            for x in range(16):
                if (x - 8) ** 2 + (y - 8) ** 2 <= 36 and (x - 11) ** 2 + (y - 6) ** 2 > 22: px(img, x, y, (240,228,170))
    elif kind == 'sol':
        for y in range(16):
            for x in range(16):
                d = (x - 7.5) ** 2 + (y - 7.5) ** 2
                if d <= 14: px(img, x, y, (255,206,60))
                elif d <= 40 and (x + y) % 3 == 0: px(img, x, y, (255,170,40))
    elif kind == 'moneda':
        for y in range(16):
            for x in range(16):
                d = (x - 7.5) ** 2 + (y - 7.5) ** 2
                if d <= 42: px(img, x, y, (232,180,40) if d > 26 else (252,214,80))
        rect(img, 7, 4, 9, 12, (190,130,20))
    elif kind == 'ayuda':
        for y in range(16):
            for x in range(16):
                if (x - 7.5) ** 2 + (y - 7.5) ** 2 <= 42: px(img, x, y, (70,110,170))
        for (x, y) in ((6,4),(7,3),(8,3),(9,4),(10,5),(9,6),(8,7),(8,8),(8,11)): px(img, x, y, (255,255,255))
    return outline(img, OUT)

# ---- v3.1: fogata de la plaza y rocas musgosas de la orilla (arte original procedural) ----
def fogata(frame=0):
    img = new(40, 36)
    ellipse_shadow(img, 20, 30, 16, 4, 80)
    rng = random.Random(5)
    for i in range(10):                      # anillo de piedras
        a = i / 10 * math.tau
        cx, cy = 20 + math.cos(a) * 13, 28 + math.sin(a) * 5
        shade_blob(img, [(cx, cy, 3.2)], [(70,66,62),(96,92,86),(122,116,108),(160,152,140)], seed=i)
    for (x0, y0, x1, y1) in ((10,27,30,30),(12,30,28,26)):  # leños cruzados
        d = ImageDraw.Draw(img); d.line((x0, y0, x1, y1), fill=WOOD[1], width=3); d.line((x0, y0 - 1, x1, y1 - 1), fill=WOOD[3], width=1)
    sway = (frame - 1) * 0.9
    for r, c in ((10, (226,92,26)), (7.5, (255,170,48)), (4.5, (255,236,160))):
        for y in range(4, 28):
            for x in range(40):
                k = (27 - y) / 23
                if ((x + .5 - 20 - sway * k * 3) / (r * (1 - k * 0.75))) ** 2 + ((y + .5 - 22) / (r * 1.5)) ** 2 <= 1 and y < 27:
                    px(img, x, y, c)
    for i in range(3):                        # chispas
        sx, sy = 14 + rng.randrange(12) + frame, 2 + rng.randrange(6) + (frame * 3 + i * 2) % 5
        px(img, sx, sy, (255, 210, 90))
    return up(outline(img, OUT), 2)

def roca_orilla(v=0):
    img = new(48, 40)
    rng = random.Random(11 + v)
    ellipse_shadow(img, 24, 34, 20, 4, 90)
    blobs = [(16, 24, 11), (31, 26, 9), (24, 16, 9)] if v == 0 else [(20, 22, 12), (34, 27, 7), (11, 28, 6)]
    shade_blob(img, blobs, [(62,66,70),(84,90,92),(112,118,116),(144,150,144),(180,184,174)], seed=v)
    for cx, cy, r in blobs:                   # musgo arriba
        for y in range(int(cy - r), int(cy - r * 0.35)):
            for x in range(int(cx - r), int(cx + r)):
                if ((x - cx) / r) ** 2 + ((y - cy) / r) ** 2 <= 0.9 and rng.random() < 0.75:
                    px(img, x, y, (70,128,46) if rng.random() < 0.6 else (98,156,58))
    for i in range(14):                       # grietas
        x, y = rng.randrange(8, 40), rng.randrange(18, 34)
        if img.getpixel((x, y))[3]: px(img, x, y, (64,68,70))
    return up(outline(img, OUT), 2)

# ---- v3.1: casas con volumen 3/4 (fachada + muro lateral en fuga + techo a dos aguas con alero) ----
def _poly_mask(size, pts):
    m = Image.new('L', size, 0); ImageDraw.Draw(m).polygon(pts, fill=255); return m

def _fill(img, pts, fn):
    m = _poly_mask(img.size, pts).load()
    W_, H_ = img.size
    for y in range(H_):
        for x in range(W_):
            if m[x, y]: px(img, x, y, fn(x, y))

def _dk(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])

def _stone_tex(pal, seed):
    rnd = random.Random(seed); cache = {}
    def fn(x, y):
        r = y // 5; off = 4 if r % 2 else 0
        lx = (x + off) % 9; ly = y % 5
        if lx == 8 or ly == 4: return pal[3]
        key = ((x + off) // 9, r)
        if key not in cache: cache[key] = rnd.randrange(3)
        c = pal[cache[key]]
        if ly == 0: c = _dk(c, 1.12)
        return c
    return fn

def _plaster_tex(x, y):
    v = (x * 13 + y * 7) % 17
    return (232,214,170) if v else (218,198,152)

def _roof_tex(pal, ridge, eave, seed):
    rnd = random.Random(seed); cache = {}
    def fn(x, y):
        r0, e0 = ridge(x), eave(x)
        t = (y - r0) / max(1, e0 - r0)
        row = int(t * 11); off = 3 if row % 2 else 0
        within = t * 11 - row
        key = ((x + off) // 6, row)
        if key not in cache: cache[key] = rnd.random()
        c = pal[1] if cache[key] > 0.25 else pal[2]
        if cache[key] > 0.9: c = _dk(pal[1], 0.86)
        if within > 0.78: c = pal[0]                      # sombra bajo cada hilera
        elif (x + off) % 6 == 5: c = _dk(c, 0.82)
        if within < 0.15: c = _dk(c, 1.12)
        return c
    return fn

def casa3q(style='capataz'):
    W_, H_ = 104, 150
    img = new(W_, H_)
    X0, X1, YT, YB = 4, 78, 88, 146          # fachada
    DX, DY = 22, -10                          # vector de profundidad (fuga hacia atrás-derecha)
    RH = 46                                   # altura del techo
    ellipse_shadow(img, 54, 145, 52, 6, 90)
    if style == 'capataz':
        wall = lambda x, y: (_stone_tex(((120,112,100),(146,138,122),(166,158,142),(92,84,74)), 2)(x, y) if y >= 128 else _plaster_tex(x, y))
        rpal = [(84,36,24),(140,66,40),(170,92,58),(66,28,18)]
    else:
        st = _stone_tex(((146,132,108),(172,156,126),(194,178,146),(104,92,76)), 7)
        wall = st
        rpal = [(46,52,68),(80,90,110),(108,120,140),(36,40,52)]
    # muro lateral (más oscuro)
    _fill(img, [(X1, YT), (X1 + DX, YT + DY), (X1 + DX, YB + DY), (X1, YB)], lambda x, y: _dk(wall(x, y + (x - X1) * 10 // 22), 0.68))
    # frontón lateral (triángulo bajo el techo)
    peak = (X1 + DX // 2, YT + DY // 2 - RH)
    _fill(img, [(X1, YT), (X1 + DX, YT + DY), peak], lambda x, y: _dk(_plaster_tex(x, y) if style == 'capataz' else wall(x, y), 0.62))
    # fachada
    _fill(img, [(X0, YT), (X1, YT), (X1, YB), (X0, YB)], wall)
    # entramado de madera (capataz)
    if style == 'capataz':
        rect(img, X0, 126, X1, 129, WOOD[0])
        for x in (X0, 24, 58, X1 - 3): rect(img, x, YT, x + 3, 127, WOOD[1]); rect(img, x, YT, x + 1, 127, WOOD[2])
        rect(img, X0, 107, X1, 109, WOOD[1])
        for k in range(17):
            px(img, 27 + k, 109 + k, WOOD[1]); px(img, 28 + k, 109 + k, WOOD[0])
            px(img, 55 - k, 109 + k, WOOD[1]); px(img, 54 - k, 109 + k, WOOD[0])
        # vigas del muro lateral
        for t in (0.0, 0.5, 1.0):
            x = X1 + int(DX * t)
            for y in range(YT + int(DY * t), 127 + int(DY * t)): px(img, x, y, WOOD[0])
    # sombra del alero sobre los muros
    for x in range(X0, X1 + DX):
        top = YT if x <= X1 else YT + (x - X1) * DY // DX
        for y in range(top, top + 4):
            c = img.getpixel((x, y))
            if c[3]: px(img, x, y, _dk(c, 0.55))
    # techo: faldón frontal (trapecio con alero que sobresale)
    rl = (X0 + DX // 2 - 2, YT + DY // 2 - RH); rr = (X1 + DX // 2 + 2, YT + DY // 2 - RH)
    el, er = (X0 - 5, YT + 3), (X1 + 5, YT + 3)
    ridge = lambda x: rl[1] + (rr[1] - rl[1]) * (x - rl[0]) / max(1, rr[0] - rl[0])
    eave = lambda x: el[1]
    _fill(img, [rl, rr, er, el], _roof_tex(rpal, ridge, eave, 3 if style == 'capataz' else 9))
    # canto lateral del techo (tablas de remate sobre el frontón)
    d = ImageDraw.Draw(img)
    d.line([er, (rr[0], rr[1])], fill=rpal[3], width=3)
    d.line([(X1 + DX + 3, YT + DY + 2), (rr[0], rr[1])], fill=rpal[0], width=3)
    d.line([el, er], fill=rpal[3], width=2)
    d.line([(rl[0], rl[1] - 1), (rr[0], rr[1] - 1)], fill=_dk(rpal[2], 1.15), width=3)      # cumbrera
    # chimenea
    cx0 = 60 if style == 'capataz' else 22
    cy_top = int(ridge(cx0)) - 6
    _fill(img, [(cx0, cy_top), (cx0 + 10, cy_top), (cx0 + 10, int(ridge(cx0)) + 18), (cx0, int(ridge(cx0)) + 18)], _stone_tex(((110,100,92),(136,126,114),(150,140,126),(80,72,64)), 4))
    _fill(img, [(cx0 + 10, cy_top), (cx0 + 14, cy_top - 2), (cx0 + 14, int(ridge(cx0)) + 14), (cx0 + 10, int(ridge(cx0)) + 18)], lambda x, y: (84,76,68))
    rect(img, cx0 - 1, cy_top - 2, cx0 + 15, cy_top + 1, (70,64,58))
    # puerta (columna central de la huella) con arco, escalón y farol
    dx0 = 34
    for y in range(114, YB):
        for x in range(dx0, dx0 + 16):
            if y < 121 and ((x + .5 - dx0 - 8) / 8) ** 2 + ((y + .5 - 121) / 7) ** 2 > 1: continue
            px(img, x, y, (96,58,32) if (x - dx0) % 4 else (66,40,22))
    rect(img, dx0 + 11, 131, dx0 + 13, 134, (224,190,90))
    rect(img, dx0 - 3, YB - 2, dx0 + 19, YB + 1, (150,142,128)); rect(img, dx0 - 3, YB - 2, dx0 + 19, YB - 1, (184,176,160))
    lantern(img, dx0 - 7, 116); lantern(img, dx0 + 19, 116)
    # ventanas con dintel, alféizar y jardinera
    def win(x, y, w=11, h=11):
        window(img, x, y, w, h)
        rect(img, x - 2, y - 3, x + w + 2, y - 1, WOOD[0])
        rect(img, x - 2, y + h + 1, x + w + 2, y + h + 4, WOOD[2])
        for k in range(0, w + 2, 2): px(img, x - 1 + k, y + h, (220,60,70) if k % 4 else (250,200,60)); px(img, x + k, y + h - 1, (70,140,50))
    if style == 'capataz':
        win(9, 93); win(62, 93); win(9, 132, 9, 8); win(63, 132, 9, 8)
        banner(img, 49, 92, 9, 20)
    else:
        win(10, 100); win(58, 100)
        # buhardilla
        bx = 38
        _fill(img, [(bx, 62), (bx + 16, 62), (bx + 16, 78), (bx, 78)], wall)
        window(img, bx + 3, 65, 10, 9)
        _fill(img, [(bx - 3, 63), (bx + 8, 52), (bx + 19, 63)], lambda x, y: rpal[1] if (x + y) % 5 else rpal[0])
    # ventana lateral (sesgada)
    for k in range(7):
        for j in range(8):
            px(img, X1 + 7 + k, 100 + j + (k * DY) // DX, (250,210,110) if j < 7 and k < 6 else WOOD[0])
    # enredadera / musgo en la esquina
    rnd = random.Random(21 if style == 'capataz' else 22)
    for i in range(40):
        x = X0 + rnd.randrange(0, 6); y = YB - rnd.randrange(0, 34)
        px(img, x, y, (58,112,42) if rnd.random() < 0.6 else (90,150,56))
    for i in range(20):
        x = X1 + rnd.randrange(0, 5); y = YB - rnd.randrange(0, 22)
        px(img, x, y, (52,100,40))
    return up(outline(img, OUT), 2)
