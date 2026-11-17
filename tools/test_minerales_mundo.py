# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cada mundo mina sus rocas. El oro nuevo sigue en un río y el reloj es por mundo."""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, os.path.join(ROOT, 'tools'))
import minerales_mundo as mm


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as handle:
        return handle.read()


class MineralWorldTests(unittest.TestCase):
    def test_five_worlds_two_rocks_and_river_gold(self):
        data = mm.catalog()
        self.assertEqual([row['id'] for row in data['worlds']], [1, 2, 3, 4, 5])
        for row in data['worlds']:
            self.assertEqual(len(row['rocks']), 2)
        self.assertEqual(len(mm.gold_nodes()), 5)
        for node in mm.gold_nodes():
            self.assertEqual(node['type'], 'nodo_oro_fluvial')
            self.assertEqual(node['waterBody'], 'rio_medellin')
            self.assertEqual(node['yield']['item'], 'pepita_oro')
            self.assertEqual(node['respawnMs'], 30000)
        for node in mm.rock_nodes():
            self.assertEqual(node['type'], 'mineral_rock')
            self.assertNotEqual(node['yield']['item'], 'pepita_oro')
            self.assertEqual(node['respawnMs'], 18000)

    def test_gold_clock_is_per_world_and_rocks_refuse_the_wrong_world(self):
        self.assertNotEqual(mm.clock_key(1, 'oro_fluvial_1'), mm.clock_key(2, 'oro_fluvial_1'))
        ready = {}
        mm.mark(ready, 1, 'oro_medellin_sur', 100)
        self.assertTrue(mm.resting(ready, 1, 'oro_medellin_sur', 50))
        self.assertFalse(mm.resting(ready, 2, 'oro_medellin_sur', 50))
        self.assertFalse(mm.rivers_rest(ready, None, mm.gold_nodes(), 50))
        self.assertEqual(mm.reject(2, 'mundo1_carbon', 'carbon_amaga'), 'Ese mineral es del Mundo 1.')
        self.assertEqual(mm.reject(1, 'mundo1_carbon', 'carbon_amaga'), '')
        self.assertEqual(mm.reject(1, 'oro_fluvial_1', 'pepita_oro'), '')

    def test_new_gold_sits_on_the_medellin_river(self):
        with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
            world = json.load(handle)
        river = {(int(x), int(y)) for x, y in world['waterBodies']['rio_medellin']['tiles']}
        pond = {(int(x), int(y)) for x, y in world['waterBodies']['estanque']['tiles']}
        for node in mm.gold_nodes():
            self.assertIn((node['x'], node['y']), river)
            self.assertNotIn((node['x'], node['y']), pond)

    def test_client_asks_before_changing_world_and_shows_the_reset(self):
        page = read('play/index.html')
        viaje = read('play/viaje-mundo.js')
        reloj = read('play/reloj-mina.js')
        self.assertIn('minerales-mundo.js', page)
        self.assertIn('viaje-mundo.js', page)
        self.assertIn('reloj-mina.js', page)
        self.assertIn('¿Seguro que deseas ir a este mundo?', viaje)
        self.assertIn('Ir al Mundo ', viaje)
        self.assertIn('>Sí<', viaje)
        self.assertIn('>No<', viaje)
        self.assertIn('Minado se restablece en ', reloj)
        self.assertIn("fetch('/reglas-mina'", reloj)
        self.assertIn('La veta vuelve en ', reloj)
        script = read('data/minerales-mundo.js')
        self.assertEqual(json.loads(script.split('=', 1)[1].strip().rstrip(';')), mm.catalog())


if __name__ == '__main__':
    unittest.main()
