# SPDX-License-Identifier: AGPL-3.0-or-later
"""Recompone la plaza de Envigado: dosel, cruces, calles y la iglesia al suroriente.

No toca la puerta de la casa, la salida, el caballo, las canecas ni el skate.
No usa fotos como textura.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / 'data' / 'el-jardin.json'
JS = ROOT / 'data' / 'el-jardin.js'
BLOCK = ROOT / 'data' / 'parque-envigado-bloque.json'

PROTECTED = {(92, 268), (93, 267), (94, 267), (99, 263), (96, 266), (103, 273)}
SKATE = {(x, y) for x in range(84, 87) for y in (273, 274)}
KEEP = PROTECTED | SKATE
GRASS, PATH, COBBLE = '0', '10', '104'


def main():
    world = json.loads(WORLD.read_text(encoding='utf-8'))
    tiles = world['tiles']
    ground = world['ground']
    collision = world['collision']

    def kind(x, y):
        return tiles[str(ground[y][x])]['kind']

    plaza = {(x, y) for x in range(91, 105) for y in range(260, 273)}
    changed = {}
    for y in range(257, 277):
        for x in range(88, 113):
            if (x, y) in KEEP or kind(x, y) in ('water', 'creek', 'bridge'):
                continue
            on_cross = (x == 98 or y == 266) and (x, y) in plaza
            on_diag = (x, y) in plaza and (x - 91 == y - 260 or (104 - x) == (y - 260))
            if (x, y) in plaza and not on_cross and not on_diag:
                tile = GRASS
            elif on_cross or on_diag:
                tile = PATH
            else:
                tile = COBBLE
            if ground[y][x] != int(tile):
                ground[y][x] = int(tile)
                changed[(x, y)] = tile
            if tile == PATH or (x, y) in KEEP:
                collision[y][x] = 0

    for x, y in PROTECTED:
        ground[y][x] = int(COBBLE)
        collision[y][x] = 0
        changed[(x, y)] = COBBLE

    church = None
    for mark in world['landmarks']:
        if mark.get('kind') == 'santa_gertrudis':
            mark['x'], mark['y'], mark['w'], mark['h'] = 107, 269, 6, 5
            mark['note'] = 'Al suroriente de la plaza, al otro lado de la calle. Arte original.'
            church = mark
    for y in range(269, 274):
        for x in range(107, 113):
            if (x, y) in KEEP:
                continue
            collision[y][x] = 1

    trees = [(93, 261), (95, 263), (101, 261), (103, 263), (93, 269), (95, 271),
             (101, 269), (102, 271), (96, 264), (100, 268), (97, 270), (91, 264)]
    world['decorations'] = [d for d in world['decorations'] if not str(d.get('id', '')).startswith('plaza_')]
    for i, (x, y) in enumerate(trees):
        if (x, y) in KEEP or kind(x, y) == 'path':
            continue
        collision[y][x] = 1
        world['decorations'].append({
            'id': f'plaza_arbol_{i}', 'type': 'canopy', 'x': x, 'y': y, 'solid': True,
        })
    for i, (x, y, w, h, floors) in enumerate(((90, 256, 4, 2, 2), (100, 256, 4, 2, 3), (86, 262, 2, 4, 2))):
        world['decorations'].append({
            'id': f'plaza_casa_{i}', 'type': 'casa_envigado', 'x': x, 'y': y, 'w': w, 'h': h,
            'floors': floors, 'solid': True,
        })
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if (xx, yy) in KEEP:
                    continue
                collision[yy][xx] = 1

    world.setdefault('valle', {})['compass'] = {
        'north': [0, -1],
        'east': [1, 0],
        'note': 'y crece al sur y x al oriente, como el DEM SRTM. La brújula pone el norte arriba.',
    }
    WORLD.write_text(json.dumps(world, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    JS.write_text('window.EL_JARDIN=' + WORLD.read_text(encoding='utf-8'), encoding='utf-8')

    block = json.loads(BLOCK.read_text(encoding='utf-8'))
    id_key = {GRASS: ('grass_0', 'grass'), PATH: ('path_00000000', 'path'), COBBLE: ('cobble_00000000', 'cobble')}
    for group in ('cells', 'extendedCells'):
        for cell in block.get(group) or []:
            tile = changed.get((cell['nx'], cell['ny']))
            if not tile and (cell['nx'], cell['ny']) in PROTECTED:
                tile = COBBLE
            if not tile:
                continue
            key, kind_name = id_key[tile]
            cell['key'] = key
            cell['kind'] = kind_name
            if 'id' in cell:
                cell['id'] = int(tile)
    block['layout'] = {
        'note': 'Plaza cuadrada con dosel, cruces y la iglesia al suroriente. Referencia de trazado, no de foto.',
        'church': {'id': 'santa_gertrudis', 'x': church['x'], 'y': church['y'], 'w': church['w'], 'h': church['h']},
        'trees': trees,
        'protected': [list(p) for p in sorted(PROTECTED)],
    }
    BLOCK.write_text(json.dumps(block, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('changed', len(changed), 'church', church['x'], church['y'])


if __name__ == '__main__':
    main()
