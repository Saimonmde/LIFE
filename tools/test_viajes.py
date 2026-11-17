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

    def test_mine_stand_is_walkable_and_near_las_palmas(self):
        dest = viajes.mine_stand(self.world)
        self.assertEqual(dest['name'], 'Mina de Las Palmas')
        self.assertTrue(viajes.walkable(self.world, dest['x'], dest['y']))
        palmas = next(item for item in self.world['waypoints'] if item['id'] == 'las_palmas')
        self.assertLessEqual(max(abs(dest['x'] - palmas['x']), abs(dest['y'] - palmas['y'])), 14)

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

    def test_named_resources_land_beside_the_source(self):
        rio = viajes.resolve(self.world, 'rio_claro')
        gold = [n for n in self.world['nodes'] if n['type'] == 'nodo_oro_fluvial']
        river = {tuple(tile) for tile in self.world['waterBodies']['rio_claro']['tiles']}
        self.assertTrue(all((n['x'], n['y']) in river for n in gold))
        self.assertEqual(rio['recurso'], 'oro (río, batea)')
        self.assertTrue(viajes.safe(self.world, rio['x'], rio['y']))
        self.assertLessEqual(min(max(abs(rio['x'] - n['x']), abs(rio['y'] - n['y'])) for n in gold), 3)
        self.assertNotIn((rio['x'], rio['y']), river)

        cantera = viajes.resolve(self.world, 'cantera')
        ores = [n for n in self.world['nodes'] if n['type'] == 'mineral_rock' and n.get('mineral') in ('cobre', 'plata')]
        self.assertEqual(cantera['recurso'], 'plata, cobre (pico)')
        self.assertLessEqual(min(max(abs(cantera['x'] - n['x']), abs(cantera['y'] - n['y'])) for n in ores), 2)
        self.assertNotIn((cantera['x'], cantera['y']), {(n['x'], n['y']) for n in ores})

        wood = viajes.resolve(self.world, 'madera')
        pines = [n for n in self.world['nodes'] if n['type'] == 'wood_tree']
        self.assertEqual(wood['recurso'], 'madera')
        self.assertLessEqual(min(max(abs(wood['x'] - n['x']), abs(wood['y'] - n['y'])) for n in pines), 2)

        palmas = next(item for item in self.world['waypoints'] if item['id'] == 'las_palmas')
        finca = viajes.resolve(self.world, 'finca')
        cafetal = viajes.resolve(self.world, 'cafetal')
        self.assertEqual(finca['recurso'], 'café, cacao')
        self.assertEqual((finca['x'], finca['y']), (cafetal['x'], cafetal['y']))
        self.assertLessEqual(max(abs(finca['x'] - palmas['x']), abs(finca['y'] - palmas['y'])), 4)
        self.assertLessEqual(max(abs(finca['x'] - palmas['x']), abs(finca['y'] - palmas['y'])), 30)

        banco = viajes.resolve(self.world, 'banco')
        self.assertEqual((banco['x'], banco['y']), viajes.BANK_OUT)
        skate = viajes.resolve(self.world, 'skate')
        self.assertNotIn((skate['x'], skate['y']), viajes.SKATE_BLOCK)
        self.assertLessEqual(min(max(abs(skate['x'] - x), abs(skate['y'] - y)) for x, y in viajes.SKATE_BLOCK), 2)

        parque = viajes.resolve(self.world, 'parque_envigado')
        envigado = next(item for item in viajes.catalog(self.world) if item['id'] == 'envigado')
        self.assertLessEqual(max(abs(parque['x'] - envigado['x']), abs(parque['y'] - envigado['y'])), 16)
        casa = viajes.resolve(self.world, 'casa')
        self.assertEqual((casa['x'], casa['y']), viajes.HOME_STAND)
        mina = viajes.resolve(self.world, 'mina')
        self.assertEqual(mina['name'], 'Mina de Las Palmas')
        self.assertEqual(mina['recurso'], 'plata, cobre (pico)')
        for dest in (rio, cantera, wood, finca, banco, skate, parque, casa, mina):
            self.assertTrue(viajes.walkable(self.world, dest['x'], dest['y']), dest['id'])
            self.assertNotEqual(viajes._kind(self.world, dest['x'], dest['y']), 'water', dest['id'])

    def test_restricted_and_invented_spots_stay_closed(self):
        for key in ('central', 'banco_central', 'atlantis', '12,40'):
            with self.assertRaises(viajes.ViajeError):
                viajes.resolve(self.world, key)

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
