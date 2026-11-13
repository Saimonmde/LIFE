# SPDX-License-Identifier: AGPL-3.0-or-later
"""Arte original de caballo, establo y profesora de la cadena. No usa fotos ni marcas."""
import os
from pixel import new, up, px, outline, ellipse_shadow
import objects as O
import village as V

OUT = (40, 28, 20, 255)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def horse(frame=0):
    """Caballo de perfil, arte original. frame 0/1 = paso."""
    img = new(56, 40)
    ellipse_shadow(img, 28, 37, 18, 3)
    coat = [(110, 70, 40), (150, 98, 55), (186, 128, 74), (70, 42, 24)]
    mane = [(50, 32, 18), (90, 55, 28)]
    for y in range(14, 28):
        for x in range(12, 40):
            if ((x - 26) / 15) ** 2 + ((y - 20) / 8) ** 2 <= 1:
                c = coat[1]
                if y < 17:
                    c = coat[2]
                if y > 24:
                    c = coat[0]
                px(img, x, y, c)
    for y in range(6, 18):
        for x in range(34, 44):
            if ((x - 38) / 5.5) ** 2 + ((y - 12) / 7) ** 2 <= 1:
                px(img, x, y, coat[1] if y > 9 else coat[2])
    for y in range(7, 14):
        for x in range(42, 52):
            if ((x - 46) / 5) ** 2 + ((y - 10) / 3.2) ** 2 <= 1:
                px(img, x, y, coat[2] if x < 48 else coat[1])
    px(img, 50, 9, (20, 16, 14))
    px(img, 44, 5, coat[0]); px(img, 45, 4, coat[3]); px(img, 47, 5, coat[0]); px(img, 48, 4, coat[3])
    for (x, y) in ((36, 7), (37, 8), (35, 9), (36, 11), (34, 13), (35, 15)):
        px(img, x, y, mane[0]); px(img, x + 1, y + 1, mane[1])
    for (x, y) in ((10, 16), (9, 18), (8, 20), (9, 22), (8, 24), (10, 23)):
        px(img, x, y, mane[0]); px(img, x + 1, y, mane[1])
    for y in range(15, 20):
        for x in range(20, 32):
            px(img, x, y, (86, 44, 28) if y in (15, 19) else (120, 62, 38))
    leg_shift = 2 if frame else 0
    legs = [(16, 27, 16 + leg_shift), (24, 27, 24 - leg_shift), (30, 27, 30 + leg_shift), (36, 27, 36 - leg_shift)]
    for _x0, y0, x1 in legs:
        for y in range(y0, 36):
            px(img, x1, y, coat[0]); px(img, x1 + 1, y, coat[3])
        px(img, x1, 36, (40, 28, 18)); px(img, x1 + 1, 36, (40, 28, 18))
    return up(outline(img, OUT), 2)


def establo():
    """Establo de madera y teja, dos puestos abiertos. Arte original."""
    img = new(96, 88)
    ellipse_shadow(img, 48, 84, 42, 4)
    wood = [(90, 56, 30), (120, 78, 42), (150, 100, 56), (70, 42, 22)]
    tile = [(140, 48, 36), (168, 64, 44), (196, 86, 58), (110, 36, 28)]
    for y in range(70, 84):
        for x in range(6, 90):
            px(img, x, y, (150, 118, 70) if (x + y) % 3 else (132, 100, 58))
    V.stone_wall(img, 10, 34, 86, 72, pal=((150, 100, 70), (170, 118, 80), (190, 136, 92), (120, 78, 50)), seed=21)
    V.roof(img, 48, 48, 4, 92, 8, 40, tile)
    for ox in (18, 50):
        for y in range(48, 72):
            for x in range(ox, ox + 24):
                if y == 48 or x in (ox, ox + 23):
                    px(img, x, y, wood[3])
                else:
                    px(img, x, y, (50, 34, 22) if y < 66 else (80, 58, 32))
        for (x, y) in ((ox + 6, 66), (ox + 10, 65), (ox + 14, 66), (ox + 8, 67)):
            px(img, x, y, (210, 180, 70)); px(img, x + 1, y, (190, 160, 50))
        for y in range(46, 76):
            px(img, ox + 11, y, wood[0]); px(img, ox + 12, y, wood[1])
    for y in range(26, 34):
        for x in range(44, 52):
            px(img, x, y, (80, 160, 190) if not (x in (44, 51) or y in (26, 33)) else wood[3])
    return up(outline(img, OUT), 2)


def profesora_sheet():
    """Personaje original. No representa ni se llama Satoshi Nakamoto."""
    saved = (O.TUNIC, O.HAT, O.FEATHER, O.CAPE_ON, O.HAIR)
    O.TUNIC = [(28, 72, 88), (44, 108, 124), (80, 150, 164)]
    O.HAT = [(62, 42, 30), (96, 66, 44)]
    O.FEATHER = None
    O.CAPE_ON = False
    O.HAIR = [(42, 28, 22), (86, 56, 38)]
    sheet = O.player_sheet()
    O.TUNIC, O.HAT, O.FEATHER, O.CAPE_ON, O.HAIR = saved
    for y in range(46, 54):
        for x in range(30, 38):
            c = (180, 48, 48) if y in (46, 53) or x in (30, 37) else (240, 228, 200)
            if 0 <= x < sheet.width and 0 <= y < sheet.height:
                sheet.putpixel((x, y), c + (255,))
    return sheet


def save_all():
    os.makedirs(os.path.join(ROOT, 'graphics', 'objects'), exist_ok=True)
    os.makedirs(os.path.join(ROOT, 'graphics', 'characters'), exist_ok=True)
    horse(0).save(os.path.join(ROOT, 'graphics', 'objects', 'caballo_0.png'))
    horse(1).save(os.path.join(ROOT, 'graphics', 'objects', 'caballo_1.png'))
    establo().save(os.path.join(ROOT, 'graphics', 'objects', 'establo.png'))
    profesora_sheet().save(os.path.join(ROOT, 'graphics', 'characters', 'profesora_cadena.png'))


if __name__ == '__main__':
    save_all()
    print('sprites de caballo, establo y profesora escritos')
