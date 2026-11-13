# SPDX-License-Identifier: AGPL-3.0-or-later
"""Aparición en Envigado, la pista de la 4 Sur y la habilidad de patinaje."""
import json
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as handle:
        return json.load(handle)


class SkateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = load('data/el-jardin.json')
        cls.casa = open(os.path.join(ROOT, 'play', 'casa.js'), encoding='utf-8').read()
        cls.game = open(os.path.join(ROOT, 'play', 'game.js'), encoding='utf-8').read()
        cls.html = open(os.path.join(ROOT, 'play', 'index.html'), encoding='utf-8').read()

    def test_house_exit_lands_by_the_benches(self):
        self.assertIn('PARK_STAND = { x: 231 + VALLE_OFFSET.x, y: 61 + VALLE_OFFSET.y }', self.casa)
        stand = (231 - 133, 61 + 203)
        self.assertEqual(stand, (98, 264))
        tiles = self.world['tiles']
        self.assertEqual(tiles[str(self.world['ground'][stand[1]][stand[0]])]['kind'], 'path')
        self.assertEqual(self.world['collision'][stand[1]][stand[0]], 0)
        benches = [(94, 264), (101, 264), (94, 268), (101, 268)]
        self.assertNotIn(stand, benches)
        self.assertLess(abs(stand[0] - 98), 3)
        stage = self.world['quests'][0]['tutorial']['stages'][0]
        self.assertEqual(stage['id'], 'seguir_camino')
        self.assertIn('Sigue el camino', stage['box'])
        self.assertIn('El Poblado', stage['box'])
        self.assertTrue(self._reaches(stand, (50, 267)))
        self.assertTrue(self._reaches(stand, (51, 267)))

    def test_skate_park_uses_the_osm_node_and_stays_clear(self):
        cfg = json.loads(subprocess.check_output(
            ['node', '-e',
             'const fs=require("fs"),vm=require("vm"),c={window:{}};'
             'vm.runInNewContext(fs.readFileSync("data/skate-4-sur.js","utf8"),c);'
             'process.stdout.write(JSON.stringify(c.window.SKATE_4_SUR));'],
            cwd=ROOT, text=True))
        self.assertEqual(cfg['osm']['node'], 11683484732)
        self.assertIsNone(cfg['osm']['way'])
        self.assertIn('ODbL', cfg['osm']['license'])
        self.assertEqual(cfg['osm']['sport'], 'skateboard')
        self.assertEqual(cfg['speed'], 1.9)
        box = cfg['placement']
        self.assertEqual(box['meters'], [box['w'] * 2, box['h'] * 2])
        tiles = self.world['tiles']
        for y in range(box['y'], box['y'] + box['h']):
            for x in range(box['x'], box['x'] + box['w']):
                kind = tiles[str(self.world['ground'][y][x])]['kind']
                self.assertNotIn(kind, ('water', 'creek', 'bridge'), (x, y))
        church = next(mark for mark in self.world['landmarks'] if mark['id'] == 'itagui')
        self.assertTrue(box['y'] + box['h'] <= church['y'] or box['y'] >= church['y'] + church['h'])
        self.assertIn("name:'Patinaje'", self.game.replace(' ', ''))
        self.assertIn('patineta', self.game)
        self.assertIn('S.skating ? 1.9', self.game)
        self.assertIn('id="b-skate"', self.html)
        self.assertIn('id="b-skate-movil"', self.html)
        out = subprocess.check_output(
            ['node', '--input-type=module', '-e',
             'import { skateArrays } from "./play/skate-park.js";'
             'import fs from "fs"; import vm from "vm";'
             'const c={window:{}}; vm.createContext(c);'
             'vm.runInContext(fs.readFileSync("data/skate-4-sur.js","utf8"), c);'
             'const n=skateArrays(c.window.SKATE_4_SUR).triangles;'
             'if(n>=500) process.exit(2); process.stdout.write(String(n));'],
            cwd=ROOT, text=True)
        self.assertLess(int(out), 500)
        self.assertGreater(int(out), 20)

    def _reaches(self, start, goal):
        world = self.world
        blocked = world['collision']

        def walkable(x, y):
            return 0 <= x < world['width'] and 0 <= y < world['height'] and blocked[y][x] == 0

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


if __name__ == '__main__':
    unittest.main()
