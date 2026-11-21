# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import galerias
import nodos

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


class GaleriasTest(unittest.TestCase):
    def test_las_dos_minas_crecen_y_siguen_conectadas(self):
        palmas = galerias.veins('palmas')
        ladera = galerias.veins('ladera')
        self.assertGreater(len(palmas), 15)
        self.assertGreater(len(ladera), len(palmas))
        self.assertEqual(len(palmas), 33)
        self.assertEqual(len(ladera), 47)
        self.assertEqual(palmas['mina_cobre_0'], (6, 6, 18000, 'cobre'))
        self.assertEqual(palmas['mina_oro_5'], (24, 27, 32000, 'oro'))
        self.assertEqual(ladera['ladera_oro_0'], (22, 6, 32000, 'oro'))
        self.assertEqual(nodos.MINE['mina_plata_0'], (27, 5, 18000))
        for kind in ('palmas', 'ladera'):
            rows = list(galerias.veins(kind).values())
            spots = [(row[0], row[1]) for row in rows]
            self.assertEqual(len(spots), len(set(spots)))
            viejas = {
                'palmas': {(6, 6), (9, 4), (5, 12), (8, 22), (12, 8), (27, 5), (30, 10), (28, 22), (24, 9), (5, 3), (17, 3), (28, 3), (32, 17), (3, 18), (24, 27)},
                'ladera': {(6, 6), (11, 6), (16, 6), (6, 12), (11, 12), (16, 12), (6, 20), (11, 20), (16, 20), (6, 28), (34, 6), (40, 6), (34, 14), (40, 14), (34, 22), (40, 22), (34, 30), (40, 30), (22, 6), (28, 6), (22, 14), (28, 14), (22, 24), (28, 24), (22, 32), (28, 32), (18, 10), (38, 18), (24, 28), (32, 20)},
            }[kind]
            nuevas = [spot for spot in spots if spot not in viejas]
            self.assertGreater(len(nuevas), 10)
            for left in nuevas:
                for right in spots:
                    if left == right:
                        continue
                    self.assertGreaterEqual(max(abs(left[0] - right[0]), abs(left[1] - right[1])), 3, (kind, left, right))
            _seen, missing = galerias.reachable(kind)
            self.assertEqual(missing, [], kind)
        plan = galerias.plan('palmas')
        self.assertEqual([row['id'] for row in plan['fixtures'] if row['type'] == 'furnace'], ['horno_cantera'])
        self.assertEqual([row for row in plan['fixtures'] if row['id'] == 'baul_mina'][0]['x'], 15)
        ladera_plan = galerias.plan('ladera')
        horno = [row for row in ladera_plan['fixtures'] if row['id'] == 'horno_ladera'][0]
        baul = [row for row in ladera_plan['fixtures'] if row['id'] == 'baul_mina'][0]
        self.assertEqual((horno['x'], horno['y']), (24, 16))
        self.assertEqual((baul['x'], baul['y']), (21, 18))

    def test_el_cliente_usa_la_misma_lista(self):
        run = subprocess.run(
            ['node', '-e', """
const fs = require('fs');
const vm = require('vm');
const ctx = { console, module: {}, exports: {} };
vm.runInNewContext(fs.readFileSync('play/galerias.js', 'utf8'), ctx);
const palmas = ctx.Galerias.cave('palmas', 1);
const ladera = ctx.Galerias.cave('ladera', 1);
const count = (cave) => cave.nodes.filter(n => n.type === 'mineral_rock').length;
if (count(palmas) !== 33 || count(ladera) !== 47) process.exit(2);
if (palmas.width !== 64 || ladera.width !== 72) process.exit(3);
if (!palmas.walls.length || !ladera.walls.length) process.exit(4);
const horno = palmas.nodes.find(n => n.id === 'horno_cantera');
const baul = ladera.nodes.find(n => n.id === 'baul_mina');
if (!horno || horno.x !== 18 || !baul || baul.x !== 21) process.exit(5);
console.log('ok');
"""],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn('ok', run.stdout)
