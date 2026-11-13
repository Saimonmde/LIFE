#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Arma el Valle de Aburrá: 10 parques, río sur–norte, relieve SRTM y un solo offset.

El Parque de Envigado y el Jardín tutorial pegado a su quebrada se copian tal cual
y se asientan con VALLE_OFFSET. Ese mismo número queda en play/casa.js: la puerta,
la llegada, el oro, el establo y la Profesora salen de las coordenadas viejas más
el offset. No redibuja las teselas del parque.

Uso: python3 tools/valle_aburra.py
Requiere data/relieve-aburra.json (python3 tools/relieve_aburra.py).
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data' / 'el-jardin.json'
RELIEVE = ROOT / 'data' / 'relieve-aburra.json'
OFFSET_PATH = ROOT / 'data' / 'valle-offset.json'
BLOCK_PATH = ROOT / 'data' / 'parque-envigado-bloque.json'
CASA = ROOT / 'play' / 'casa.js'

# Rectángulo pedido, inclusive. Cada tesela se copia sin redibujarla.
CORE = (214, 52, 240, 72)
# La iglesia llega a x=243, el empedrado a x=253 y el oro de la quebrada a y=81.
PARK = (214, 50, 256, 82)
# Jardín tutorial + quebrada + parque: un solo desplazamiento conserva el camino.
STAMP = (165, 42, 258, 88)
ANCHOR_OLD = (239, 59)  # centro de Santa Gertrudis (origen 234,55, huella 10×7)
CHURCH_LAT, CHURCH_LON = 6.1698424, -75.5869528
TPSK = 7.2
ORDER = ('N', 'E', 'S', 'W', 'NE', 'SE', 'SW', 'NW')
DIRS = {'N': (0, -1), 'E': (1, 0), 'S': (0, 1), 'W': (-1, 0),
        'NE': (1, -1), 'SE': (1, 1), 'SW': (-1, 1), 'NW': (-1, -1)}

PARKS = [
    {'id': 'caldas', 'name': 'Parque de Caldas', 'lat': 6.0918607, 'lon': -75.6356652,
     'slot': (58, 362),
     'kind': 'torre_unica', 'color': '#f4f1e8', 'roof': '#a86448', 'w': 8, 'h': 6,
     'note': 'OSM Parque Principal, Caldas'},
    {'id': 'sabaneta', 'name': 'Parque de Sabaneta', 'lat': 6.15140, 'lon': -75.61660,
     'kind': 'santa_ana', 'color': '#f0eadc', 'roof': '#ad775a', 'w': 10, 'h': 8,
     'note': 'Plaza de Santa Ana, centro de Sabaneta, al surponiente de Envigado'},
    {'id': 'la_estrella', 'name': 'Parque de La Estrella', 'lat': 6.1578078, 'lon': -75.6439799,
     'slot': (78, 330),
     'kind': 'capilla', 'color': '#f7f3e6', 'roof': '#b8734e', 'w': 7, 'h': 6,
     'note': 'OSM Iglesia Nuestra Señora del Rosario, La Estrella'},
    {'id': 'itagui', 'name': 'Parque de Itagüí', 'lat': 6.1723858, 'lon': -75.6094160,
     'slot': (96, 230),
     'kind': 'torres_bajas', 'color': '#c4a48a', 'roof': '#8d5a42', 'w': 9, 'h': 6,
     'note': 'OSM Parque Principal Itagüí'},
    {'id': 'envigado', 'name': 'Parque de Envigado', 'lat': CHURCH_LAT, 'lon': CHURCH_LON,
     'kind': 'santa_gertrudis', 'color': '#f3f1e9', 'keep': True, 'w': 10, 'h': 7,
     'note': 'OSM Parroquia Santa Gertrudis. Teselas copiadas, no redibujadas.'},
    {'id': 'medellin', 'name': 'Medellín', 'lat': 6.25260, 'lon': -75.56380,
     'kind': 'catedral', 'color': '#c98962', 'roof': '#8f5b42', 'w': 10, 'h': 7,
     'note': 'Centro de Medellín, sobre el río, entre Bello e Itagüí. El parque es el de Bolívar.'},
    {'id': 'bello', 'name': 'Parque de Bello', 'lat': 6.3349881, 'lon': -75.5582772,
     'kind': 'nave_larga', 'color': '#e7e1d4', 'roof': '#a86b48', 'w': 8, 'h': 10,
     'note': 'OSM Parque Principal de Bello'},
    {'id': 'copacabana', 'name': 'Parque de Copacabana', 'lat': 6.3460614, 'lon': -75.5080978,
     'kind': 'fronton', 'color': '#e6d3a8', 'roof': '#9a6244', 'w': 8, 'h': 6,
     'note': 'OSM Parque principal de Copacabana'},
    {'id': 'girardota', 'name': 'Parque de Girardota', 'lat': 6.3775101, 'lon': -75.4461183,
     'kind': 'capilla', 'color': '#f3f6f1', 'roof': '#8d6a4a', 'w': 6, 'h': 5,
     'note': 'OSM Parque Principal Girardota'},
    {'id': 'barbosa', 'name': 'Parque de Barbosa', 'lat': 6.4370056, 'lon': -75.3313466,
     'kind': 'aguja', 'color': '#efe6d6', 'roof': '#6e5344', 'w': 7, 'h': 6,
     'note': 'OSM Parque Principal Simón Bolívar, Barbosa'},
]


def load_json(path):
    with path.open(encoding='utf-8') as handle:
        return json.load(handle)


def kind_of(tiles, tile_id):
    return tiles[str(tile_id)]['kind']


def logic_of(kind):
    return {'grass': 'G', 'grass_flowers': 'G', 'grass_worn': 'G', 'mountain': 'M', 'rocky': 'R',
            'path': 'P', 'cobble': 'C', 'water': 'W', 'bridge': 'B', 'asphalt': 'A'}.get(kind, 'G')


def inside_rect(x, y, rect):
    x0, y0, x1, y1 = rect
    return x0 <= x <= x1 and y0 <= y <= y1


def main():
    old = load_json(SRC)
    if old.get('build') == 'valle-aburra-r1' or old.get('width') != 352:
        raise SystemExit('Parte de data/el-jardin.json original (352×176). Este generador no se aplica dos veces.')
    dem = load_json(RELIEVE)
    tiles = old['tiles']
    by_key = {spec['key']: int(index) for index, spec in tiles.items()}
    lat_n, lat_s = dem['latN'], dem['latS']
    lon_w, lon_e = dem['lonW'], dem['lonE']
    km_lat = 110.574
    km_lon = 111.320 * math.cos(math.radians(6.25))
    height = int(round((lat_n - lat_s) * km_lat * TPSK))
    width = int(round((lon_e - lon_w) * km_lon * TPSK))

    def project(lat, lon):
        return ((lon - lon_w) / (lon_e - lon_w) * (width - 1),
                (lat_n - lat) / (lat_n - lat_s) * (height - 1))

    def latlon(x, y):
        return (lat_n - (y / (height - 1)) * (lat_n - lat_s),
                lon_w + (x / (width - 1)) * (lon_e - lon_w))

    def meters(lat, lon):
        rows, cols = dem['rows'], dem['cols']
        fr = (lat_n - lat) / (lat_n - lat_s) * (rows - 1)
        fc = (lon - lon_w) / (lon_e - lon_w) * (cols - 1)
        r0 = max(0, min(rows - 2, int(math.floor(fr))))
        c0 = max(0, min(cols - 2, int(math.floor(fc))))
        tr, tc = fr - r0, fc - c0
        grid = dem['elev']
        a, b = grid[r0][c0], grid[r0][c0 + 1]
        c, d = grid[r0 + 1][c0], grid[r0 + 1][c0 + 1]
        return (a * (1 - tc) + b * tc) * (1 - tr) + (c * (1 - tc) + d * tc) * tr

    meter_grid = [[meters(*latlon(x, y)) for x in range(width)] for y in range(height)]
    flat = sorted(v for row in meter_grid[::4] for v in row[::4])
    river_m = flat[max(0, len(flat) // 12)]

    def game_h(value):
        return round(max(0.0, (value - river_m) * 0.045), 2)

    ax, ay = project(CHURCH_LAT, CHURCH_LON)
    dx, dy = int(round(ax)) - ANCHOR_OLD[0], int(round(ay)) - ANCHOR_OLD[1]
    sx0, sy0, sx1, sy1 = (STAMP[0] + dx, STAMP[1] + dy, STAMP[2] + dx, STAMP[3] + dy)
    if sx0 < 2 or sy0 < 2 or sx1 >= width - 2 or sy1 >= height - 2:
        raise SystemExit(f'El bloque no cabe: offset {(dx, dy)} sello {(sx0, sy0, sx1, sy1)} mapa {width}×{height}')

    logic = [['G'] * width for _ in range(height)]
    locked = [[False] * width for _ in range(height)]
    ground = [[0] * width for _ in range(height)]
    coll = [[0] * width for _ in range(height)]
    elev = [[0.0] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            h = game_h(meter_grid[y][x])
            elev[y][x] = h
            if h > 28:
                logic[y][x] = 'R'
            elif h > 14:
                logic[y][x] = 'M'

    # Río por el fondo del valle, de sur (y grande) a norte (y chico).
    raw_x = []
    for y in range(height):
        lo, hi = int(width * 0.08), int(width * 0.92)
        best = min(range(lo, hi), key=lambda x: meter_grid[y][x])
        raw_x.append(best)
    smooth = raw_x[:]
    for _ in range(4):
        nxt = smooth[:]
        for y in range(1, height - 1):
            nxt[y] = int(round((smooth[y - 1] + smooth[y] + smooth[y + 1]) / 3))
        smooth = nxt
    for y, rx in enumerate(smooth):
        for x in range(rx - 1, rx + 2):
            if 0 <= x < width and not (sx0 <= x <= sx1 and sy0 <= y <= sy1):
                logic[y][x] = 'W'
                elev[y][x] = -0.45
                coll[y][x] = 1
    # Si el thalweg cae dentro del sello, el cauce sigue por el occidente del bloque.
    for y in range(sy0, sy1 + 1):
        x = sx0 - 3
        for xx in range(x - 1, x + 2):
            if 0 <= xx < width:
                logic[y][xx] = 'W'
                elev[y][xx] = -0.45
                coll[y][xx] = 1

    # Copia intacta del sello (parque + jardín + quebrada).
    old_anchor = old['elevation'][ANCHOR_OLD[1]][ANCHOR_OLD[0]]
    base = game_h(meters(CHURCH_LAT, CHURCH_LON))
    for y in range(STAMP[1], STAMP[3] + 1):
        for x in range(STAMP[0], STAMP[2] + 1):
            nx, ny = x + dx, y + dy
            ground[ny][nx] = old['ground'][y][x]
            coll[ny][nx] = old['collision'][y][x]
            logic[ny][nx] = logic_of(kind_of(tiles, old['ground'][y][x]))
            elev[ny][nx] = round(base + (old['elevation'][y][x] - old_anchor), 2)
            locked[ny][nx] = True

    def free(x, y):
        return 0 <= x < width and 0 <= y < height and not locked[y][x]

    def plaza_ok(cx, cy):
        if not (10 < cx < width - 10 and 10 < cy < height - 10):
            return False
        for y in range(cy - 8, cy + 9):
            for x in range(cx - 9, cx + 10):
                if not free(x, y) or logic[y][x] == 'W':
                    return False
        return elev[cy][cx] < 22

    def separated(cx, cy):
        return all(max(abs(cx - other['x']), abs(cy - other['y'])) >= 30 for other in placed)

    def find_spot(ideal_x, ideal_y, bearing_x, bearing_y):
        ix, iy = bearing_x - ax, bearing_y - ay
        best = None
        best_score = 1e18
        for radius in (4, 36, 80, 150, 240):
            for y in range(int(ideal_y) - radius, int(ideal_y) + radius + 1, 3):
                for x in range(int(ideal_x) - radius, int(ideal_x) + radius + 1, 3):
                    if (x - ideal_x) ** 2 + (y - ideal_y) ** 2 > radius * radius:
                        continue
                    if not plaza_ok(x, y) or not separated(x, y):
                        continue
                    vx, vy = x - ax, y - ay
                    if vx * ix + vy * iy < 0 and radius < 200:
                        continue
                    # y crece hacia el sur: no cruzar Envigado al lado contrario del rumbo.
                    if abs(iy) > 8 and (y - ay) * iy < 0:
                        continue
                    score = abs(x - ideal_x) + abs(y - ideal_y) * 2 + elev[y][x] * 4
                    if score < best_score:
                        best_score = score
                        best = (x, y)
            if best:
                return best
        return None

    placed = []
    for park in PARKS:
        if park.get('keep'):
            park = dict(park)
            # Plaza abierta (239,69), no el cuerpo sólido de la iglesia.
            park['x'], park['y'] = 239 + dx, 69 + dy
            placed.append(park)
            continue
        real = project(park['lat'], park['lon'])
        target = park.get('slot', real)
        direct = (int(round(target[0])), int(round(target[1])))
        found = direct if plaza_ok(*direct) and separated(*direct) else find_spot(target[0], target[1], real[0], real[1])
        if not found:
            raise SystemExit('No hubo sitio para ' + park['name'])
        park = dict(park)
        park['x'], park['y'] = found
        # Plaza empedrada y plana. La cruz del centro queda libre para el camino.
        shelf = elev[found[1]][found[0]]
        for y in range(found[1] - 6, found[1] + 8):
            for x in range(found[0] - 7, found[0] + 8):
                logic[y][x] = 'C'
                coll[y][x] = 0
                elev[y][x] = shelf
        park['w'] = min(park['w'], 6)
        park['h'] = min(park['h'], 5)
        church_x, church_y = found[0] + 1, found[1] - park['h'] // 2
        for y in range(church_y, church_y + park['h']):
            for x in range(church_x, church_x + park['w']):
                if x == found[0] or y == found[1]:
                    continue
                coll[y][x] = 1
        park['church'] = (church_x, church_y)
        placed.append(park)

    road_cells = []

    def paint(x, y):
        if not free(x, y):
            return False
        if logic[y][x] == 'W':
            logic[y][x] = 'B'
            coll[y][x] = 0
            elev[y][x] = 0.15
        elif logic[y][x] in ('G', 'M', 'R', 'A'):
            logic[y][x] = 'P'
            coll[y][x] = 0
        road_cells.append((x, y))
        return True

    def line(a, b):
        x0, y0 = a
        x1, y1 = b
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            x = int(round(x0 + (x1 - x0) * i / steps))
            y = int(round(y0 + (y1 - y0) * i / steps))
            paint(x, y)
            paint(x + 1, y)

    ordered = sorted(placed, key=lambda p: -p['y'])
    for a, b in zip(ordered, ordered[1:]):
        line((a['x'], a['y']), (b['x'], b['y']))

    # Entrada al sello por una tesela de camino ya existente, sin pisar el parque.
    spawn = (old['spawn']['x'] + dx, old['spawn']['y'] + dy)

    def walkable_cell(x, y):
        return 0 <= x < width and 0 <= y < height and coll[y][x] == 0 and logic[y][x] != 'W'

    def bfs(start, goal):
        if not walkable_cell(*start):
            return None
        seen = {start}
        queue = [start]
        prev = {start: None}
        for x, y in queue:
            if goal(x, y):
                path = []
                cur = (x, y)
                while cur is not None:
                    path.append(cur)
                    cur = prev[cur]
                path.reverse()
                return path
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (x + ox, y + oy)
                if nxt in seen or not walkable_cell(*nxt):
                    continue
                seen.add(nxt)
                prev[nxt] = (x, y)
                queue.append(nxt)
        return None

    stamp_goal = lambda x, y: locked[y][x] and walkable_cell(x, y) and logic[y][x] in ('P', 'C', 'B', 'G')
    # Conecta el camino del valle con el borde exterior del sello.
    border = []
    for y in range(sy0, sy1 + 1):
        for x in (sx0, sx1):
            if walkable_cell(x, y):
                border.append((x, y))
    for x in range(sx0, sx1 + 1):
        for y in (sy0, sy1):
            if walkable_cell(x, y):
                border.append((x, y))
    gate = None
    for cell in border:
        if bfs(spawn, lambda x, y, cell=cell: (x, y) == cell):
            outside = None
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (cell[0] + ox, cell[1] + oy)
                if free(*nxt) and logic[nxt[1]][nxt[0]] != 'W':
                    outside = nxt
                    break
            if outside:
                gate = (cell, outside)
                break
    if not gate:
        raise SystemExit('El sello no tiene una salida caminable')
    line(gate[1], (ordered[0]['x'], ordered[0]['y']))
    # Une también el extremo norte por si el sello partió la polilínea.
    line(gate[1], (ordered[-1]['x'], ordered[-1]['y']))

    # Las Palmas: subida al oriente de Medellín, sobre la ladera.
    med = next(p for p in placed if p['id'] == 'medellin')
    mirador = None
    best_h = -1
    for x in range(med['x'] + 8, min(width - 2, med['x'] + 48)):
        y = med['y']
        if locked[y][x] or logic[y][x] == 'W':
            continue
        if elev[y][x] > best_h:
            best_h = elev[y][x]
            mirador = (x, y)
    if mirador:
        line((med['x'], med['y']), mirador)

    def mask(x, y, group):
        bits = {}
        for name, (ox, oy) in DIRS.items():
            nx, ny = x + ox, y + oy
            if 0 <= nx < width and 0 <= ny < height:
                bits[name] = logic[ny][nx] in group
            else:
                bits[name] = logic[y][x] in group
        for corner, a, b in (('NE', 'N', 'E'), ('SE', 'S', 'E'), ('SW', 'S', 'W'), ('NW', 'N', 'W')):
            if not (bits[a] and bits[b]):
                bits[corner] = False
        return ''.join('1' if bits[name] else '0' for name in ORDER)

    mountain_id = next(int(i) for i, spec in tiles.items() if spec['kind'] == 'mountain')
    rocky_id = next(int(i) for i, spec in tiles.items() if spec['kind'] == 'rocky')
    grass_ids = [by_key[f'grass_{i}'] for i in range(4)]
    flower_ids = [by_key[f'grass_flores_{i}'] for i in range(2)]
    worn_ids = [by_key[f'grass_gastado_{i}'] for i in range(4)]
    for y in range(height):
        for x in range(width):
            if locked[y][x]:
                continue
            code = logic[y][x]
            if code == 'G':
                n = (x * 17 + y * 31) % 20
                ground[y][x] = flower_ids[n % 2] if n == 0 else worn_ids[n % 4] if n < 3 else grass_ids[(x + y) % 4]
            elif code == 'M':
                ground[y][x] = mountain_id
            elif code == 'R':
                ground[y][x] = rocky_id
            elif code == 'P':
                ground[y][x] = by_key['path_' + mask(x, y, 'PCBA')]
            elif code == 'C':
                ground[y][x] = by_key['cobble_' + mask(x, y, 'C')]
            elif code == 'W':
                ground[y][x] = by_key['water_' + mask(x, y, 'WB')]
            elif code == 'B':
                ground[y][x] = 151
            coll[y][x] = 1 if code == 'W' else coll[y][x]

    # El autotile de la montaña usó grass_0 un instante: ya quedó en la id de montaña.
    world = {k: old[k] for k in old if k not in {
        'ground', 'collision', 'elevation', 'width', 'height', 'spawn', 'areas', 'npcs', 'doors',
        'nodes', 'decorations', 'waterBodies', 'landmarks', 'memories', 'waypoints', 'roads3d',
        'bridges', 'riverLayouts', 'parkDetails', 'surfaceZones', 'signs3d', 'scenery3d',
        'regions', 'mapLabels', 'layoutNote', 'referenceSources', 'expansion'}}
    world['version'] = 5
    world['width'] = width
    world['height'] = height
    world['build'] = 'valle-aburra-r1'
    world['ground'] = ground
    world['collision'] = coll
    world['elevation'] = elev
    world['name'] = 'SaimonCity · Valle de Aburrá'

    def moved(items):
        out = []
        for item in items:
            if inside_rect(item.get('x', -1), item.get('y', -1), STAMP):
                copy = json.loads(json.dumps(item))
                copy['x'] += dx
                copy['y'] += dy
                if 'approach' in copy:
                    copy['approach']['x'] += dx
                    copy['approach']['y'] += dy
                out.append(copy)
        return out

    world['nodes'] = moved(old['nodes'])
    world['decorations'] = moved(old['decorations'])
    world['npcs'] = moved(old['npcs'])
    world['doors'] = moved(old['doors'])
    world['spawn'] = {'x': old['spawn']['x'] + dx, 'y': old['spawn']['y'] + dy, 'facing': old['spawn']['facing']}
    world['areas'] = []
    for area in old['areas']:
        if area['id'] == 'rio':
            continue
        if inside_rect(area['x'], area['y'], STAMP) and inside_rect(area['x'] + area['w'] - 1, area['y'] + area['h'] - 1, STAMP):
            copy = dict(area)
            copy['x'] += dx
            copy['y'] += dy
            world['areas'].append(copy)

    def shift_water(body_id):
        tiles_xy = []
        for x, y in old['waterBodies'][body_id]['tiles']:
            if inside_rect(x, y, STAMP):
                tiles_xy.append([x + dx, y + dy])
        return tiles_xy

    rio_claro = json.loads(json.dumps(old['waterBodies']['rio_claro']))
    rio_claro['tiles'] = shift_water('rio_claro')
    estanque = json.loads(json.dumps(old['waterBodies']['estanque']))
    estanque['tiles'] = shift_water('estanque')
    medellin_tiles = [[x, y] for y in range(height) for x in range(width) if logic[y][x] == 'W']
    world['waterBodies'] = {
        'rio_claro': rio_claro,
        'estanque': estanque,
        'rio_medellin': {
            'name': 'Río Medellín (Aburrá)',
            'kind': 'river',
            'waterLevel': -0.35,
            'bedLevel': -0.9,
            'tiles': medellin_tiles,
        },
    }
    world['bridges'] = []
    for bridge in old.get('bridges', []):
        if inside_rect(bridge['x'], bridge['y'], STAMP):
            copy = dict(bridge)
            copy['x'] += dx
            copy['y'] += dy
            world['bridges'].append(copy)
    for y in range(height):
        for x in range(width):
            if locked[y][x] or logic[y][x] != 'B':
                continue
            if any(b['x'] <= x < b['x'] + b['w'] and b['y'] <= y < b['y'] + b['h'] for b in world['bridges']):
                continue
            world['bridges'].append({'x': x, 'y': y, 'w': 2, 'h': 1, 'axis': 'y'})

    claro = old['riverLayouts'][0]
    world['riverLayouts'] = [{
        'id': 'rio_claro', 'name': claro['name'], 'x': claro['x'] + dx, 'y': claro['y'] + dy,
        'w': claro['w'], 'h': STAMP[3] - claro['y'] + 1, 'axis': 'y',
        'waterLevel': claro.get('waterLevel', -0.18), 'bedLevel': claro.get('bedLevel', -0.5),
    }]
    run_x, run_y0 = None, None
    for y, rx in enumerate(smooth):
        if sy0 <= y <= sy1:
            rx = sx0 - 3
        if run_x is None:
            run_x, run_y0 = rx, y
        if abs(rx - run_x) > 4 or y == height - 1:
            world['riverLayouts'].append({
                'id': 'rio_medellin', 'name': 'Río Medellín', 'x': max(0, run_x - 1), 'y': run_y0,
                'w': 3, 'h': max(1, y - run_y0), 'axis': 'y', 'waterLevel': -0.35, 'bedLevel': -0.9,
            })
            run_x, run_y0 = rx, y

    world['landmarks'] = []
    for mark in old.get('landmarks', []):
        if mark.get('kind') == 'santa_gertrudis' and inside_rect(mark['x'], mark['y'], STAMP):
            copy = dict(mark)
            copy['x'] += dx
            copy['y'] += dy
            world['landmarks'].append(copy)
    for park in placed:
        if park.get('keep'):
            continue
        world['landmarks'].append({
            'id': park['id'], 'name': park['name'], 'kind': park['kind'],
            'x': park['church'][0], 'y': park['church'][1], 'w': park['w'], 'h': park['h'],
            'height': 8, 'color': park['color'], 'roof': park.get('roof', '#a86b48'),
        })

    world['parkDetails'] = []
    for detail in old.get('parkDetails', []):
        if detail.get('id') == 'envigado':
            copy = dict(detail)
            copy['x'] += dx
            copy['y'] += dy
            world['parkDetails'].append(copy)
    for park in placed:
        if park.get('keep'):
            continue
        world['parkDetails'].append({'id': park['id'], 'x': park['x'], 'y': park['y']})

    world['surfaceZones'] = []
    for zone in old.get('surfaceZones', []):
        if inside_rect(zone['x'], zone['y'], STAMP):
            copy = dict(zone)
            copy['x'] += dx
            copy['y'] += dy
            world['surfaceZones'].append(copy)
    world['signs3d'] = []
    keep_signs = ('PARQUE DE ENVIGADO', 'SANTA GERTRUDIS', 'QUEBRADA')
    for sign in old.get('signs3d', []):
        if inside_rect(sign['x'], sign['y'], STAMP) and any(sign['text'].startswith(prefix) for prefix in keep_signs):
            copy = dict(sign)
            copy['x'] += dx
            copy['y'] += dy
            world['signs3d'].append(copy)
    for park in placed:
        if park.get('keep'):
            continue
        world['signs3d'].append({'text': park['name'].upper(), 'x': park['x'], 'y': park['y'] + 5})
    world['scenery3d'] = []
    for prop in old.get('scenery3d', []):
        if inside_rect(prop['x'], prop['y'], STAMP):
            copy = dict(prop)
            copy['x'] += dx
            copy['y'] += dy
            world['scenery3d'].append(copy)
    for park in placed:
        if park['id'] == 'girardota':
            for ox, oy in ((-5, -2), (5, 1), (-3, 4), (4, -4), (0, 5)):
                world['scenery3d'].append({'kind': 'tree', 'x': park['x'] + ox, 'y': park['y'] + oy})
    step = 0
    for x, y in road_cells:
        step += 1
        if step % 14 == 0 and walkable_cell(x, y):
            world['scenery3d'].append({'kind': 'lamp', 'x': x, 'y': y})

    world['regions'] = []
    for park in placed:
        world['regions'].append({'id': park['id'], 'name': park['name'], 'x': park['x'] - 9, 'y': park['y'] - 8, 'w': 18, 'h': 16})
    world['regions'].append({'id': 'jardin', 'name': 'El Jardín', 'x': sx0, 'y': sy0, 'w': sx1 - sx0 + 1, 'h': sy1 - sy0 + 1})
    if mirador:
        world['regions'].append({'id': 'las_palmas', 'name': 'Las Palmas · ladera', 'x': mirador[0] - 6, 'y': mirador[1] - 6, 'w': 14, 'h': 12})
    world['regions'].append({'id': 'valle', 'name': 'Valle de Aburrá', 'x': 0, 'y': 0, 'w': width, 'h': height})
    world['waypoints'] = [{'id': park['id'], 'name': park['name'], 'x': park['x'], 'y': park['y']} for park in placed]
    if mirador:
        world['waypoints'].append({'id': 'las_palmas', 'name': 'Las Palmas · mirador', 'x': mirador[0], 'y': mirador[1]})
    # Los nombres visibles salen de tools/mapa_etiquetas.py (Medellín, no «Bolívar»).
    world['mapLabels'] = [{'id': park['id'], 'name': park['name'], 'x': park['x'], 'y': park['y'], 'kind': 'municipio'} for park in placed]
    if mirador:
        world['mapLabels'].append({'id': 'las_palmas', 'name': 'Las Palmas', 'x': mirador[0], 'y': mirador[1], 'kind': 'poi'})

    road_points = []
    for park in ordered:
        if park['id'] == 'envigado':
            # La carretera del valle rodea la plaza: no la cruza con guardarraíl.
            px, py = park['x'], park['y']
            east = min(width - 2, px + 16)
            south = min(height - 2, py + 24)
            north = max(1, py - 26)
            road_points.append({'x': east, 'y': south, 'height': elev[south][east]})
            road_points.append({'x': east, 'y': north, 'height': elev[north][east]})
            continue
        road_points.append({'x': park['x'], 'y': park['y'], 'height': elev[park['y']][park['x']]})
    world['roads3d'] = [{'id': 'valle', 'name': 'Camino del Valle de Aburrá', 'points': road_points}]
    if mirador:
        world['roads3d'].append({'id': 'las_palmas', 'name': 'Subida a Las Palmas', 'points': [
            {'x': med['x'], 'y': med['y'], 'height': elev[med['y']][med['x']]},
            {'x': mirador[0], 'y': mirador[1], 'height': elev[mirador[1]][mirador[0]]},
        ]})

    memories = []
    for memory in old['memories']:
        copy = dict(memory)
        if inside_rect(copy['x'], copy['y'], STAMP):
            copy['x'] += dx
            copy['y'] += dy
            memories.append(copy)
        elif copy['id'] == 'villa':
            copy['x'], copy['y'] = med['x'] + 2, med['y'] + 2
            if not walkable_cell(copy['x'], copy['y']):
                copy['x'], copy['y'] = med['x'], med['y']
            memories.append(copy)
        elif copy['id'] == 'rio':
            spot = next((cell for cell in road_cells if walkable_cell(*cell)), spawn)
            copy['x'], copy['y'] = spot
            memories.append(copy)
    world['memories'] = memories

    quests = json.loads(json.dumps(old['quests']))
    def shift_quest(node):
        if isinstance(node, dict):
            if 'x' in node and 'y' in node and isinstance(node['x'], (int, float)):
                node['x'] += dx
                node['y'] += dy
            for value in node.values():
                shift_quest(value)
        elif isinstance(node, list):
            for value in node:
                shift_quest(value)
    shift_quest(quests)
    world['quests'] = quests

    world['layoutNote'] = (
        f'Valle de Aburrá a {TPSK} casillas por kilómetro, norte hacia y menor. '
        f'El Parque de Envigado y El Jardín se trasladaron intactos con VALLE_OFFSET ({dx}, {dy}). '
        'El río sigue el fondo del valle (SRTM) y rodea ese bloque por el occidente. '
        'Los parques que caían encima del bloque se empujan en su rumbo real hasta quedar libres.'
    )
    sources = list(old.get('referenceSources') or [])
    sources.append({
        'title': 'NASA SRTM GL1, dominio público',
        'url': dem['attribution']['url'],
        'note': dem['attribution']['note'],
    })
    sources.append({
        'title': 'Plazas de referencia (OpenStreetMap / Nominatim)',
        'url': 'https://www.openstreetmap.org/copyright',
        'note': 'Sólo coordenadas de centros de plaza. El arte es original.',
    })
    world['referenceSources'] = sources
    world['expansion'] = {'revision': 2, 'offsetX': dx, 'offsetY': dy, 'stamp': list(STAMP), 'anchor': list(ANCHOR_OLD)}
    world['valle'] = {
        'chunked': True, 'chunkSize': 32, 'chunkRadius': 3,
        'tilesPerKm': TPSK, 'riverMeters': river_m,
        'offset': {'x': dx, 'y': dy},
        'municipios': [p['id'] for p in placed],
        'width': width, 'height': height,
        'relief': {
            'source': dem['attribution']['title'],
            'license': dem['attribution']['license'],
            'mirror': dem['attribution']['mirror'],
            'min': round(min(v for row in elev for v in row), 2),
            'max': round(max(v for row in elev for v in row), 2),
        },
    }
    for park in placed:
        world['areas'].append({'id': 'parque_' + park['id'], 'name': park['name'], 'x': park['x'] - 8, 'y': park['y'] - 7, 'w': 16, 'h': 14})

    def connected(a, b):
        return bfs(a, lambda x, y, b=b: (x, y) == b) is not None

    caldas = next(p for p in placed if p['id'] == 'caldas')
    estrella = next(p for p in placed if p['id'] == 'la_estrella')
    barbosa = next(p for p in placed if p['id'] == 'barbosa')
    if not connected((caldas['x'], caldas['y']), (barbosa['x'], barbosa['y'])):
        raise SystemExit('El camino no une Caldas con Barbosa')
    if not connected((estrella['x'], estrella['y']), (barbosa['x'], barbosa['y'])):
        raise SystemExit('El camino no une La Estrella con Barbosa')
    for park in placed:
        if not connected((caldas['x'], caldas['y']), (park['x'], park['y'])):
            raise SystemExit('Sin camino a ' + park['name'])
    for node in world['nodes']:
        if not bfs(spawn, lambda x, y, node=node: max(abs(x - node['x']), abs(y - node['y'])) == 1):
            raise SystemExit('Nodo inalcanzable ' + node['id'])
    for memory in memories:
        if not connected(spawn, (memory['x'], memory['y'])):
            raise SystemExit('Memoria inalcanzable ' + memory['id'])
    for gold in world['nodes']:
        if gold['type'] != 'nodo_oro_fluvial':
            continue
        if [gold['x'], gold['y']] not in rio_claro['tiles']:
            raise SystemExit('Oro fuera de rio_claro ' + gold['id'])

    # Manifiesto celda por celda del parque, antes y después del offset.
    core_rows = []
    cells = []
    x0, y0, x1, y1 = CORE
    for y in range(y0, y1 + 1):
        row = []
        for x in range(x0, x1 + 1):
            spec = tiles[str(old['ground'][y][x])]
            row.append(spec['key'])
            cells.append({'x': x, 'y': y, 'nx': x + dx, 'ny': y + dy, 'id': old['ground'][y][x], 'key': spec['key'], 'kind': spec['kind']})
        core_rows.append({'y': y, 'keys': row})
    extended = []
    ex0, ey0, ex1, ey1 = PARK
    for y in range(ey0, ey1 + 1):
        for x in range(ex0, ex1 + 1):
            spec = tiles[str(old['ground'][y][x])]
            extended.append({'x': x, 'y': y, 'nx': x + dx, 'ny': y + dy, 'key': spec['key'], 'kind': spec['kind']})
    manifest = {
        'offset': {'x': dx, 'y': dy},
        'core': {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1, 'note': 'Rectángulo reservado. Teselas idénticas al mapa anterior.'},
        'extended': {'x0': ex0, 'y0': ey0, 'x1': ex1, 'y1': ey1,
                     'note': 'Ampliado para no partir la iglesia (hasta x=243), el empedrado (hasta x=253) ni el oro (y=81).'},
        'stamp': {'x0': STAMP[0], 'y0': STAMP[1], 'x1': STAMP[2], 'y1': STAMP[3],
                  'note': 'Incluye El Jardín tutorial para conservar el camino, la quebrada y el oro.'},
        'rows': core_rows,
        'cells': cells,
        'extendedCells': extended,
    }
    BLOCK_PATH.write_text(json.dumps(manifest, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    OFFSET_PATH.write_text(json.dumps({
        'x': dx, 'y': dy,
        'anchor': {'from': list(ANCHOR_OLD), 'lat': CHURCH_LAT, 'lon': CHURCH_LON, 'to': [ANCHOR_OLD[0] + dx, ANCHOR_OLD[1] + dy]},
        'parkDoor': {'from': [226, 64], 'to': [226 + dx, 64 + dy]},
        'parkStand': {'from': [227, 64], 'to': [227 + dx, 64 + dy]},
        'stable': {'from': [224, 62], 'to': [224 + dx, 62 + dy]},
        'profesora': {'from': [230, 66], 'to': [230 + dx, 66 + dy]},
        'gold': {node['id']: {'from': [node['x'] - dx, node['y'] - dy], 'to': [node['x'], node['y']]}
                 for node in world['nodes'] if node['type'] == 'nodo_oro_fluvial'},
        'note': 'Único desplazamiento del Parque de Envigado. casa.js suma este valor a 226,64 y 227,64.',
    }, ensure_ascii=False, indent=2), encoding='utf-8')

    text = json.dumps(world, ensure_ascii=False, separators=(',', ':'))
    (ROOT / 'data' / 'el-jardin.json').write_text(text, encoding='utf-8')
    (ROOT / 'data' / 'el-jardin.js').write_text('window.EL_JARDIN=' + text + ';\n', encoding='utf-8')
    casa = CASA.read_text(encoding='utf-8')
    updated, count = re.subn(
        r'const VALLE_OFFSET = \{ x: -?\d+, y: -?\d+ \};',
        f'const VALLE_OFFSET = {{ x: {dx}, y: {dy} }};',
        casa,
        count=1,
    )
    if count != 1:
        raise SystemExit('No encontré VALLE_OFFSET en play/casa.js')
    CASA.write_text(updated, encoding='utf-8')
    print(f'mapa {width}×{height} offset {dx},{dy} río {river_m:.0f} m')
    for park in ordered:
        print(f"  {park['id']:12} {park['x']:4} {park['y']:4}  {park['note']}")
    print('puerta', 226 + dx, 64 + dy, 'sello', sx0, sy0, sx1, sy1)


if __name__ == '__main__':
    main()
