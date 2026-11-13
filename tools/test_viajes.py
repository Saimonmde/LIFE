# SPDX-License-Identifier: AGPL-3.0-or-later
"""Destinos del mapa: lista, suelo caminable y rechazo de lugares inventados."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import viajes


def world():
    with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
        return json.load(handle)


class ViajeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = world()

    def test_catalog_has_ten_towns_and_bolivar(self):
        found = {item['id']: item for item in viajes.catalog(self.world)}
        self.assertEqual([key for key in viajes.MUNICIPIOS if key in found], list(viajes.MUNICIPIOS))
        self.assertEqual(found['medellin']['name'], 'Medellín')
        self.assertEqual(found['parque_bolivar']['name'], 'Parque de Bolívar')
        self.assertEqual(found['parque_bolivar']['kind'], 'poi')
        self.assertIn('las_palmas', found)
        self.assertLess(found['bello']['y'], found['medellin']['y'])
        self.assertLess(found['medellin']['y'], found['itagui']['y'])
        self.assertLess(found['medellin']['y'], found['envigado']['y'])

    def test_every_spawn_is_walkable_and_near_the_center(self):
        for item in viajes.catalog(self.world):
            dest = viajes.resolve(self.world, item['id'])
            x, y = dest['x'], dest['y']
            self.assertTrue(viajes.walkable(self.world, x, y), item['id'])
            self.assertNotEqual(viajes._kind(self.world, x, y), 'water', item['id'])
            self.assertEqual(self.world['collision'][y][x], 0, item['id'])
            self.assertLessEqual(max(abs(x - item['x']), abs(y - item['y'])), 16, item['id'])
            self.assertIn(viajes._kind(self.world, x, y), viajes.SAFE, item['id'])

    def test_server_rejects_unknown_and_repeats(self):
        with self.assertRaises(viajes.ViajeError):
            viajes.resolve(self.world, 'atlantis')
        with self.assertRaises(viajes.ViajeError):
            viajes.resolve(self.world, '')
        gate = viajes.Gate(cooldown=2.5)
        self.assertTrue(gate.allow('Ana', 10))
        self.assertFalse(gate.allow('Ana', 11))
        self.assertTrue(gate.allow('Ana', 12.5))
        self.assertTrue(gate.allow('Beto', 11))

    def test_water_is_not_a_spawn(self):
        water = None
        tiles = self.world['tiles']
        for y, row in enumerate(self.world['ground']):
            for x, tile_id in enumerate(row):
                if tiles[str(tile_id)]['kind'] == 'water':
                    water = (x, y)
                    break
            if water:
                break
        self.assertIsNotNone(water)
        x, y = viajes.nearest_spawn(self.world, *water)
        self.assertNotEqual(viajes._kind(self.world, x, y), 'water')
        self.assertTrue(viajes.walkable(self.world, x, y))


if __name__ == '__main__':
    unittest.main()
