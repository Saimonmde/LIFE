# SPDX-License-Identifier: AGPL-3.0-or-later
"""Recompone el Parque de Envigado con el tamaño real que cabe en el plano.

OpenStreetMap (vía 154893173) dibuja el parque como un cuadrado de 73.1 m de lado,
girado 32° respecto al norte verdadero porque sigue el damero (calles 37 y 38 Sur,
carreras 42 y 43). Aquí el norte del juego es -y y la casilla mide 2 m, así que el
prado es un cuadrado alineado de 36×36 casillas (72 m).

La iglesia (vía 552362722, y 71×33 varas ≈ 59×28 m) va al oriente. La fachada usa
los 28 m. La nave queda en 12 m: el plano está plano solo hasta x=125 y la loma
empieza en x=126. No se mueve la puerta, el caballo, el oro del arroyo ni el skate.

La escala del valle (7.2 casillas/km) no se toca. Son dos escalas y se dejan escritas.
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

# Prado de 72 m. El cuadrado OSM mide 73.1 m; la casilla de juego mide 2 m.
LAWN = (83, 118, 249, 284)  # x0, x1, y0, y1 inclusive
CHURCH = (120, 259, 6, 14)  # x, y, w, h → 12 m de fondo por 28 m de fachada
ROAD_BOX = (83, 249, 125, 284)
PLAY_M_PER_TILE = 2
VALLEY_TILES_PER_KM = 7.2


def main():
    world = json.loads(WORLD.read_text(encoding='utf-8'))
    tiles = world['tiles']
    ground = world['ground']
    collision = world['collision']
    x0, x1, y0, y1 = LAWN
    cx, cy, cw, ch = CHURCH

    def kind(x, y):
        return tiles[str(ground[y][x])]['kind']

    def church_cell(x, y):
        return cx <= x < cx + cw and cy <= y < cy + ch

    def lawn_cell(x, y):
        return x0 <= x <= x1 and y0 <= y <= y1

    def ring_cell(x, y):
        return (x0 - 2) <= x <= (x1 + 2) and (y0 - 2) <= y <= (y1 + 2) and not lawn_cell(x, y) and not church_cell(x, y)

    changed = {}
    for y in range(y0 - 4, y1 + 6):
        for x in range(x0 - 4, cx + cw + 2):
            if (x, y) in KEEP or kind(x, y) in ('water', 'creek', 'bridge'):
                continue
            if church_cell(x, y):
                tile, blocked = COBBLE, 1
            elif lawn_cell(x, y):
                on_cross = x in (97, 98) or y == 266
                on_edge = x in (x0, x1) or y in (y0, y1)
                tile, blocked = (PATH if on_cross or on_edge else GRASS), 0
            elif ring_cell(x, y) and x <= cx + cw:
                tile, blocked = COBBLE, 0
            else:
                continue
            ground[y][x] = int(tile)
            collision[y][x] = blocked
            changed[(x, y)] = tile

    for x, y in PROTECTED:
        ground[y][x] = int(COBBLE)
        collision[y][x] = 0
        changed[(x, y)] = COBBLE

    church = None
    for mark in world['landmarks']:
        if mark.get('kind') == 'santa_gertrudis':
            mark['x'], mark['y'], mark['w'], mark['h'] = CHURCH
            mark['note'] = (
                'Al oriente del parque, fachada al occidente. Arte original: '
                'dos torres, cúpulas y pórtico. Fachada de 28 m; la nave del juego mide 12 m '
                'porque la loma empieza en la casilla 126.'
            )
            church = mark

    trees = [
        (88, 255), (94, 258), (90, 263),
        (104, 255), (110, 258), (114, 263),
        (88, 270), (94, 276), (90, 280),
        (104, 270), (110, 276), (114, 280),
    ]
    world['decorations'] = [d for d in world['decorations'] if not str(d.get('id', '')).startswith('plaza_')]
    kept_trees = []
    for i, (x, y) in enumerate(trees):
        if (x, y) in KEEP or kind(x, y) in ('path', 'water', 'creek', 'bridge'):
            continue
        collision[y][x] = 1
        world['decorations'].append({
            'id': f'plaza_arbol_{i}', 'type': 'canopy', 'x': x, 'y': y, 'solid': True,
        })
        kept_trees.append((x, y))
    for i, (x, y, w, h, floors) in enumerate(((90, 247, 4, 2, 2), (108, 247, 4, 2, 2), (96, 285, 4, 2, 2))):
        world['decorations'].append({
            'id': f'plaza_casa_{i}', 'type': 'casa_envigado', 'x': x, 'y': y, 'w': w, 'h': h,
            'floors': floors, 'solid': True,
        })
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if (xx, yy) in KEEP or kind(xx, yy) in ('water', 'creek', 'bridge'):
                    continue
                collision[yy][xx] = 1

    elev = world.get('elevation') or []

    def road_height(x, y):
        try:
            return elev[y][x]
        except (IndexError, TypeError):
            return 0

    def crosses(a, b):
        steps = max(abs(b[0] - a[0]), abs(b[1] - a[1]), 1)
        bx0, by0, bx1, by1 = ROAD_BOX
        for i in range(steps + 1):
            x = int(round(a[0] + (b[0] - a[0]) * i / steps))
            y = int(round(a[1] + (b[1] - a[1]) * i / steps))
            if bx0 <= x <= bx1 and by0 <= y <= by1:
                return True
        return False

    for road in world.get('roads3d') or []:
        if road.get('id') != 'valle':
            continue
        raw = [(int(p['x']), int(p['y']), p) for p in road.get('points') or []]
        if not raw:
            continue
        points = [raw[0][2]]
        skirted = False
        for _, _, point in raw[1:]:
            prev = points[-1]
            a, b = (int(prev['x']), int(prev['y'])), (int(point['x']), int(point['y']))
            if crosses(a, b):
                if not skirted:
                    points.append({'x': 140, 'y': 296, 'height': road_height(140, 296)})
                    points.append({'x': 140, 'y': 240, 'height': road_height(140, 240)})
                    skirted = True
                if not (ROAD_BOX[0] <= b[0] <= ROAD_BOX[2] and ROAD_BOX[1] <= b[1] <= ROAD_BOX[3]):
                    points.append(point)
                continue
            if ROAD_BOX[0] <= b[0] <= ROAD_BOX[2] and ROAD_BOX[1] <= b[1] <= ROAD_BOX[3]:
                continue
            points.append(point)
        road['points'] = points

    scale = {
        'playMetersPerTile': PLAY_M_PER_TILE,
        'valleyTilesPerKm': VALLEY_TILES_PER_KM,
        'valleyMetersPerTile': round(1000 / VALLEY_TILES_PER_KM, 2),
        'note': (
            'Dos escalas, a propósito. El interior del parque y la iglesia usan 2 m por casilla, '
            'la misma de render.metersPerTile. El valle coloca los municipios a 7.2 casillas por km '
            '(unos 139 m por casilla) y no se reescala. Las distancias entre municipios no son todavía las de la Tierra.'
        ),
        'osm': {
            'parkWay': 154893173,
            'parkName': 'Parque de Envigado',
            'squareSide_m': 73.1,
            'rotationFromTrueNorth_deg': 32.4,
            'streets': ['Calle 37 Sur', 'Calle 38 Sur', 'Carrera 43', 'Carrera 42'],
            'churchWay': 552362722,
            'churchName': 'Parroquia Santa Gertrudis',
            'churchBBox_m': [55.6, 57.4],
            'churchVaras': '71 x 33 varas. 1 vara castellana = 0.8359 m, o sea 59.3 m por 27.6 m. La nave citada mide 54 varas (45.1 m).',
            'fetched': '2026-11-13',
            'source': 'OpenStreetMap, ODbL, api.openstreetmap.org. Las varas, de la ficha de la Iglesia de Santa Gertrudis en Wikipedia.',
        },
        'play': {
            'lawnTiles': {'x0': x0, 'x1': x1, 'y0': y0, 'y1': y1},
            'lawnMeters': [(x1 - x0 + 1) * PLAY_M_PER_TILE, (y1 - y0 + 1) * PLAY_M_PER_TILE],
            'churchTiles': {'x': cx, 'y': cy, 'w': cw, 'h': ch},
            'churchMeters': [cw * PLAY_M_PER_TILE, ch * PLAY_M_PER_TILE],
            'facadeFaces': 'west',
            'whyTheNaveIsShorter': (
                'El suelo de juego sigue plano hasta la casilla x=125. En x=126 empieza la loma. '
                'Una nave de 46 m se saldría de ese plano. La fachada conserva los 28 m y mira al parque.'
            ),
        },
    }
    world.setdefault('valle', {})['escalaParque'] = {
        'playMetersPerTile': scale['playMetersPerTile'],
        'valleyTilesPerKm': scale['valleyTilesPerKm'],
        'valleyMetersPerTile': scale['valleyMetersPerTile'],
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
    origin = (81, 255)
    benches = [
        ('banca_norte', 13, 9), ('banca_oriente', 20, 9), ('banca_sur', 13, 13), ('banca_esquina', 20, 13),
        ('banca_sendero_oeste', 9, 10), ('banca_sendero_este', 31, 10), ('banca_sendero_sur', 27, 12),
        ('banca_cruce_oeste', 15, 5), ('banca_cruce_este', 18, 17), ('banca_cruce_suroeste', 15, 21),
        ('banca_atrio_1', 36, 7), ('banca_atrio_2', 36, 15),
    ]
    block['layout'] = {
        'note': 'Prado de 72 m con la cruz de senderos, bancas hacia el prado e iglesia al oriente. La escala del valle no cambia.',
        'church': {'id': 'santa_gertrudis', 'x': church['x'], 'y': church['y'], 'w': church['w'], 'h': church['h']},
        'trees': kept_trees,
        'protected': [list(p) for p in sorted(PROTECTED)],
        'scale': scale,
    }
    props = block.setdefault('props', {})
    props['benches'] = [
        {'id': name, 'dx': dx, 'dy': dy, 'x': origin[0] + dx, 'y': origin[1] + dy}
        for name, dx, dy in benches
    ]
    props['sculptures'] = [
        {'id': 'anillo', 'dx': 14, 'dy': 7, 'x': 95, 'y': 262, 'name': 'Anillo'},
        {'id': 'columna', 'dx': 19, 'dy': 7, 'x': 100, 'y': 262, 'name': 'Columna'},
        {'id': 'ovalo', 'dx': 15, 'dy': 15, 'x': 96, 'y': 270, 'name': 'Óvalo'},
    ]
    BLOCK.write_text(json.dumps(block, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('changed', len(changed), 'church', church['x'], church['y'], 'trees', len(kept_trees))


if __name__ == '__main__':
    main()
