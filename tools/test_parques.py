#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Los diez parques del Valle de Aburrá, el relieve y el bloque intacto de Envigado."""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = ['caldas', 'la_estrella', 'sabaneta', 'envigado', 'itagui', 'medellin', 'bello', 'copacabana', 'girardota', 'barbosa']


def load(name):
    with open(os.path.join(ROOT, 'data', name), encoding='utf-8') as handle:
        return json.load(handle)


class ParquesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = load('el-jardin.json')
        cls.block = load('parque-envigado-bloque.json')
        cls.offset = load('valle-offset.json')

    def test_ten_parks_and_relief_credit(self):
        world = self.world
        self.assertEqual(set(world['valle']['municipios']), set(ORDER))
        ids = {park['id'] for park in world['waypoints']}
        self.assertTrue(set(ORDER) <= ids)
        relief = world['valle']['relief']
        self.assertIn('SRTM', relief['source'])
        self.assertIn('Public domain', relief['license'])
        self.assertGreater(relief['max'], relief['min'] + 20)

    def test_south_to_north_and_banks(self):
        by_id = {park['id']: park for park in self.world['waypoints']}
        ys = [by_id[name]['y'] for name in ('caldas', 'la_estrella', 'sabaneta', 'envigado', 'medellin', 'barbosa')]
        self.assertEqual(ys, sorted(ys, reverse=True))
        self.assertLess(by_id['itagui']['y'], by_id['envigado']['y'])
        self.assertGreater(by_id['itagui']['y'], by_id['medellin']['y'])
        self.assertLess(by_id['bello']['x'], by_id['copacabana']['x'])
        self.assertLess(by_id['medellin']['x'], by_id['girardota']['x'])
        self.assertLess(by_id['girardota']['y'], by_id['medellin']['y'])
        self.assertGreater(by_id['girardota']['y'], by_id['barbosa']['y'])
        self.assertLess(by_id['girardota']['x'], by_id['barbosa']['x'])

    def test_door_horse_and_exit_stay_clear(self):
        world = self.world
        tiles = world['tiles']
        clear = {'caballo_2': (92, 268), 'casa': (93, 267), 'salida': (94, 267)}
        for name, (x, y) in clear.items():
            self.assertEqual(tiles[str(world['ground'][y][x])]['kind'], 'cobble', name)
            self.assertEqual(world['collision'][y][x], 0, name)
        dx, dy = self.offset['x'], self.offset['y']
        origin = (214 + dx, 52 + dy)
        blocked = [(origin[0] + dx_, origin[1] + dy_) for dx_, dy_ in ((18, 8), (15, 11), (22, 18))]
        blocked += [(origin[0] + 3 + dx_, origin[1] + 18 + dy_) for dx_, dy_ in ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (2, 1))]
        self.assertTrue(set(clear.values()).isdisjoint(blocked))
        for group in ('decorations', 'nodes', 'landmarks'):
            for obj in world[group]:
                ox, oy = obj.get('x'), obj.get('y')
                ww, hh = obj.get('w', 1), obj.get('h', 1)
                for x, y in clear.values():
                    self.assertFalse(ox <= x < ox + ww and oy <= y < oy + hh, obj.get('id') or obj.get('name'))

    def test_church_returns_and_bronze_head_stays_out(self):
        src = open(os.path.join(ROOT, 'play', 'unified3d.js'), encoding='utf-8').read()
        self.assertIn('102+offChurch.x', src)
        self.assertIn('12+offChurch.y', src)
        self.assertNotIn('Bronze head', src)
        self.assertNotIn("id==='poblado'", src)

    def test_sara_origin_uses_the_same_offset(self):
        src = open(os.path.join(ROOT, 'play', 'envigado-park.js'), encoding='utf-8').read()
        self.assertIn('const PARK_ORIGIN = { x: 214 + off.x, y: 52 + off.y }', src)
        dx, dy = self.offset['x'], self.offset['y']
        origin = (214 + dx, 52 + dy)
        self.assertEqual(tuple(self.offset['parkOrigin']['to']), origin)
        canecas = [(232 + dx, 60 + dy), (229 + dx, 63 + dy), (236 + dx, 70 + dy)]
        core = self.block['core']
        for x, y in canecas:
            self.assertTrue(core['x0'] + dx <= x <= core['x1'] + dx)
            self.assertTrue(core['y0'] + dy <= y <= core['y1'] + dy)
        for x in range(217 + dx, 220 + dx):
            for y in (70 + dy, 71 + dy):
                self.assertTrue(core['x0'] + dx <= x <= core['x1'] + dx)
                self.assertTrue(core['y0'] + dy <= y <= core['y1'] + dy)

    def test_envigado_block_is_unchanged(self):
        world = self.world
        dx, dy = self.offset['x'], self.offset['y']
        self.assertEqual((dx, dy), (self.block['offset']['x'], self.block['offset']['y']))
        for cell in self.block['cells']:
            self.assertEqual(world['ground'][cell['ny']][cell['nx']], cell['id'])
            self.assertEqual((cell['nx'], cell['ny']), (cell['x'] + dx, cell['y'] + dy))
        for cell in self.block['extendedCells']:
            kind = world['tiles'][str(world['ground'][cell['ny']][cell['nx']])]['key']
            self.assertEqual(kind, cell['key'])

    def test_gold_stays_on_the_creek_and_off_the_door(self):
        dx, dy = self.offset['x'], self.offset['y']
        creek = {tuple(tile) for tile in self.world['waterBodies']['rio_claro']['tiles']}
        gold = [node for node in self.world['nodes'] if node['type'] == 'nodo_oro_fluvial']
        self.assertGreaterEqual(len(gold), 4)
        for node in gold:
            self.assertIn((node['x'], node['y']), creek)
            self.assertEqual(node['x'] - dx, self.offset['gold'][node['id']]['from'][0])
        door = (226 + dx, 64 + dy)
        self.assertNotIn(door, {(node['x'], node['y']) for node in gold})

    def test_envigado_props_spare_the_doors_and_the_path(self):
        text = open(os.path.join(ROOT, 'play', 'envigado-park.js'), encoding='utf-8').read()
        import re
        spots = [(int(x), int(y)) for x, y in re.findall(r"dx: (\d+), dy: (\d+), id: '(?:banca_|anillo|columna|ovalo)", text)]
        origin = (81, 255)
        world = [(origin[0] + dx, origin[1] + dy) for dx, dy in spots]
        forbidden = {(92, 268), (93, 267), (94, 267), (99, 263), (96, 266), (103, 273)}
        forbidden |= {(x, y) for x in range(84, 87) for y in (273, 274)}
        forbidden |= {(x, y) for x in range(83, 92) for y in (271, 272)}
        self.assertTrue(forbidden.isdisjoint(world), sorted(set(world) & forbidden))
        self.assertGreaterEqual(text.count("id: 'banca_"), 4)
        self.assertGreaterEqual(text.count("id: 'anillo'"), 1)
        self.assertIn('Columna', text)
        self.assertIn('Óvalo', text)
        block = json.load(open(os.path.join(ROOT, 'data', 'parque-envigado-bloque.json'), encoding='utf-8'))
        self.assertEqual(len(block['props']['canecas']), 3)
        self.assertEqual(len(block['props']['benches']), 12)
        bench_spots = [(int(x), int(y)) for x, y in re.findall(r"dx: (\d+), dy: (\d+), id: 'banca_", text)]
        self.assertEqual([(b['dx'], b['dy']) for b in block['props']['benches']], bench_spots)
        self.assertEqual([s['id'] for s in block['props']['sculptures']], ['anillo', 'columna', 'ovalo'])
        layout = block['layout']
        church = layout['church']
        self.assertGreater(church['x'], 100)
        self.assertLessEqual(church['y'], 266)
        self.assertGreater(church['y'] + church['h'], 266)
        self.assertGreaterEqual(len(layout['trees']), 8)

    def test_envigado_plaza_is_symmetric_and_the_road_skirts_it(self):
        world = self.world
        tiles = world['tiles']
        box = (83, 249, 125, 284)

        def hits(a, b):
            steps = max(abs(b[0] - a[0]), abs(b[1] - a[1]), 1)
            for i in range(steps + 1):
                x = int(round(a[0] + (b[0] - a[0]) * i / steps))
                y = int(round(a[1] + (b[1] - a[1]) * i / steps))
                if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
                    return True
            return False

        road = next(item for item in world['roads3d'] if item['id'] == 'valle')
        points = [(p['x'], p['y']) for p in road['points']]
        self.assertFalse(any(hits(a, b) for a, b in zip(points, points[1:])))
        for x, y in ((97, 266), (98, 260), (91, 266), (104, 266)):
            self.assertEqual(tiles[str(world['ground'][y][x])]['kind'], 'path', (x, y))
        for x, y in ((93, 262), (102, 262), (93, 270), (102, 270)):
            self.assertEqual(tiles[str(world['ground'][y][x])]['kind'], 'grass', (x, y))
        self.assertNotEqual(tiles[str(world['ground'][262][95])]['kind'], 'path')

    def test_park_uses_real_meters_without_rescaling_the_valley(self):
        layout = self.block['layout']
        scale = layout['scale']
        self.assertEqual(scale['playMetersPerTile'], 2)
        self.assertEqual(scale['valleyTilesPerKm'], 7.2)
        self.assertAlmostEqual(scale['valleyMetersPerTile'], 1000 / 7.2, places=2)
        self.assertEqual(self.world['valle']['tilesPerKm'], 7.2)
        self.assertEqual(self.world['render']['metersPerTile'], 2)
        lawn = scale['play']['lawnTiles']
        wide = (lawn['x1'] - lawn['x0'] + 1) * 2
        deep = (lawn['y1'] - lawn['y0'] + 1) * 2
        self.assertEqual([wide, deep], scale['play']['lawnMeters'])
        self.assertAlmostEqual(wide, scale['osm']['squareSide_m'], delta=2)
        church = layout['church']
        self.assertEqual(church['h'] * 2, 28)
        self.assertLess(church['w'] * 2, 59)
        self.assertEqual(scale['play']['churchMeters'], [church['w'] * 2, church['h'] * 2])
        self.assertEqual(scale['play']['facadeFaces'], 'west')
        self.assertGreater(church['x'], lawn['x1'])
        spec = json.load(open(os.path.join(ROOT, 'graphics', 'models', 'banca_envigado.json'), encoding='utf-8'))
        self.assertEqual(spec['length_m'], 1.63)
        self.assertEqual(spec['width_m'], 0.51)
        self.assertEqual(spec['seat_height_m'], 0.48)
        self.assertEqual(spec['top_slant_m'], 0.01)
        self.assertEqual(spec['up'], 'Y')
        self.assertEqual(spec['front'], '+Z')
        self.assertIn('CC-BY-SA-4.0', spec['source']['license'])

    def test_horse_road_reaches_every_park(self):
        world = self.world
        width, height = world['width'], world['height']
        blocked = world['collision']

        def walkable(x, y):
            return 0 <= x < width and 0 <= y < height and blocked[y][x] == 0

        def reaches(start, goal):
            seen = {start}
            queue = [start]
            while queue:
                x, y = queue.pop()
                if (x, y) == goal:
                    return True
                for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nxt = (x + ox, y + oy)
                    if nxt not in seen and walkable(*nxt):
                        seen.add(nxt)
                        queue.append(nxt)
            return False

        parks = {park['id']: (park['x'], park['y']) for park in world['waypoints']}
        for name in ORDER:
            self.assertTrue(reaches(parks['caldas'], parks[name]), name)
        self.assertTrue(reaches(parks['la_estrella'], parks['barbosa']))

    def test_valley_is_lower_than_the_ridges(self):
        elev = self.world['elevation']
        height, width = len(elev), len(elev[0])
        west = east = 0
        samples = 0
        for y in range(12, height - 12, 3):
            low = min(elev[y][x] for x in range(width // 5, 4 * width // 5))
            west += max(elev[y][x] for x in range(0, width // 5)) - low
            east += max(elev[y][x] for x in range(4 * width // 5, width)) - low
            samples += 1
        self.assertGreater(west / samples, 8)
        self.assertGreater(east / samples, 8)


if __name__ == '__main__':
    unittest.main()
