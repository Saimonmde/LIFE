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

    # Plaza simétrica: cruz de senderos (sin diagonales) y empedrado alrededor.
    plaza_x0, plaza_x1, plaza_y0, plaza_y1 = 91, 104, 260, 272
    cross_x, cross_y = (97, 98), 266
    changed = {}
    for y in range(256, 277):
        for x in range(88, 116):
            if (x, y) in KEEP or kind(x, y) in ('water', 'creek', 'bridge'):
                continue
            inside = plaza_x0 <= x <= plaza_x1 and plaza_y0 <= y <= plaza_y1
            on_cross = inside and (x in cross_x or y == cross_y)
            tile = PATH if on_cross else (GRASS if inside else COBBLE)
            if ground[y][x] != int(tile):
                ground[y][x] = int(tile)
                changed[(x, y)] = tile
            else:
                changed[(x, y)] = tile
            collision[y][x] = 0

    for x, y in PROTECTED:
        ground[y][x] = int(COBBLE)
        collision[y][x] = 0
        changed[(x, y)] = COBBLE

    church = None
    church_box = (108, 264, 5, 5)
    for mark in world['landmarks']:
        if mark.get('kind') == 'santa_gertrudis':
            mark['x'], mark['y'], mark['w'], mark['h'] = church_box
            mark['note'] = 'Al oriente de la plaza, centrada con el sendero. Arte original.'
            church = mark
    cx, cy, cw, ch = church_box
    for y in range(cy, cy + ch):
        for x in range(cx, cx + cw):
            if (x, y) in KEEP:
                continue
            collision[y][x] = 1

    trees = [(93, 261), (102, 261), (95, 263), (100, 263), (93, 271), (102, 271), (95, 269), (100, 269)]
    world['decorations'] = [d for d in world['decorations'] if not str(d.get('id', '')).startswith('plaza_')]
    for i, (x, y) in enumerate(trees):
        if (x, y) in KEEP or kind(x, y) == 'path':
            continue
        collision[y][x] = 1
        world['decorations'].append({
            'id': f'plaza_arbol_{i}', 'type': 'canopy', 'x': x, 'y': y, 'solid': True,
        })
    for i, (x, y, w, h, floors) in enumerate(((90, 256, 4, 2, 2), (102, 256, 4, 2, 2))):
        world['decorations'].append({
            'id': f'plaza_casa_{i}', 'type': 'casa_envigado', 'x': x, 'y': y, 'w': w, 'h': h,
            'floors': floors, 'solid': True,
        })
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if (xx, yy) in KEEP:
                    continue
                collision[yy][xx] = 1

    elev = world.get('elevation') or []

    def road_height(x, y):
        try:
            return elev[y][x]
        except (IndexError, TypeError):
            return 0

    for road in world.get('roads3d') or []:
        if road.get('id') != 'valle':
            continue
        points = []
        skirted = False
        for point in road.get('points') or []:
            px, py = int(point['x']), int(point['y'])
            if 88 <= px <= 114 and 256 <= py <= 278:
                if not skirted:
                    points.append({'x': 122, 'y': 296, 'height': road_height(122, 296)})
                    points.append({'x': 122, 'y': 246, 'height': road_height(122, 246)})
                    skirted = True
                continue
            points.append(point)
        road['points'] = points

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
        'note': 'Plaza simétrica: cruz de senderos, bancas y árboles en espejo, iglesia al oriente. Sin carretera atravesada. Referencia de trazado, no de foto.',
        'church': {'id': 'santa_gertrudis', 'x': church['x'], 'y': church['y'], 'w': church['w'], 'h': church['h']},
        'trees': trees,
        'protected': [list(p) for p in sorted(PROTECTED)],
    }
    props = block.setdefault('props', {})
    props['benches'] = [
        {'id': 'banca_norte', 'dx': 13, 'dy': 9, 'x': 94, 'y': 264},
        {'id': 'banca_oriente', 'dx': 20, 'dy': 9, 'x': 101, 'y': 264},
        {'id': 'banca_sur', 'dx': 13, 'dy': 13, 'x': 94, 'y': 268},
        {'id': 'banca_esquina', 'dx': 20, 'dy': 13, 'x': 101, 'y': 268},
    ]
    props['sculptures'] = [
        {'id': 'anillo', 'dx': 14, 'dy': 7, 'x': 95, 'y': 262, 'name': 'Anillo'},
        {'id': 'columna', 'dx': 19, 'dy': 7, 'x': 100, 'y': 262, 'name': 'Columna'},
        {'id': 'ovalo', 'dx': 15, 'dy': 15, 'x': 96, 'y': 270, 'name': 'Óvalo'},
    ]
    BLOCK.write_text(json.dumps(block, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('changed', len(changed), 'church', church['x'], church['y'])


if __name__ == '__main__':
    main()
