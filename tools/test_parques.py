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
