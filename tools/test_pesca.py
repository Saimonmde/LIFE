#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""La red entrega pez a la mochila y la batea no crea oro fuera del río."""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import minerales_mundo as mm
import pesca


RIVER = {
    'id': 'pesca_rio_1', 'type': 'fishing_spot', 'waterBody': 'rio_claro', 'x': 10, 'y': 4,
    'yield': {'table': [{'item': 'trucha', 'weight': 1}, {'item': 'bocachico', 'weight': 1}], 'qty': 1},
    'respawnMs': 15000,
}
POND = {
    'id': 'pesca_estanque_1', 'type': 'fishing_spot', 'waterBody': 'estanque', 'x': 20, 'y': 8,
    'yield': {'table': [{'item': 'mojarra', 'weight': 1}], 'qty': 1},
    'respawnMs': 15000,
}
WORLD = {'nodes': [RIVER, POND]}


class PescaTests(unittest.TestCase):
    def test_river_and_pond_fill_the_bag_once_per_cooldown(self):
        bag = {}
        ready = {}
        rng = random.Random(2)
        got = pesca.cast(WORLD, bag, 'Ana', 10, 5, 'pesca_rio_1', 100, ready, 3, rng)
        self.assertTrue(got['ok'])
        self.assertIn(got['item'], ('trucha', 'bocachico'))
        self.assertEqual(bag[got['item']], 1)
        again = pesca.cast(WORLD, bag, 'Ana', 10, 5, 'pesca_rio_1', 101, ready, 3, rng)
        self.assertFalse(again['ok'])
        self.assertEqual(sum(bag.values()), 1)
        pond = pesca.cast(WORLD, bag, 'Ana', 20, 8, 'pesca_estanque_1', 100, ready, 3, rng)
        self.assertEqual(pond['item'], 'mojarra')
        self.assertEqual(bag['mojarra'], 1)

    def test_far_from_the_water_does_not_catch(self):
        bag = {}
        got = pesca.cast(WORLD, bag, 'Ana', 0, 0, 'pesca_rio_1', 100, {}, 1, random.Random(1))
        self.assertFalse(got['ok'])
        self.assertEqual(bag, {})

    def test_real_world_has_river_and_pond_spots(self):
        root = os.path.dirname(os.path.dirname(__file__))
        import json
        with open(os.path.join(root, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
            world = json.load(handle)
        spots = [node for node in world['nodes'] if node.get('type') == 'fishing_spot']
        waters = {node.get('waterBody') for node in spots}
        self.assertIn('rio_claro', waters)
        self.assertIn('estanque', waters)
        fish = set()
        for node in spots:
            for row in (node.get('yield') or {}).get('table') or []:
                fish.add(row.get('item'))
        self.assertTrue({'trucha', 'bocachico', 'mojarra'} <= fish)


class OroRioTests(unittest.TestCase):
    def test_pepita_only_from_river_sands_in_worlds_1_to_5(self):
        nodes = [
            {'id': 'oro_medellin_centro', 'type': 'nodo_oro_fluvial', 'waterBody': 'rio_medellin'},
            {'id': 'mina_oro_0', 'type': 'mineral_rock', 'waterBody': ''},
        ]
        node, why = mm.gold_spot(nodes, 'oro_medellin_centro', 3)
        self.assertEqual(node['id'], 'oro_medellin_centro')
        self.assertEqual(why, '')
        missing, reason = mm.gold_spot(nodes, 'mina_oro_0', 3)
        self.assertIsNone(missing)
        self.assertIn('río', reason)
        outside, reason = mm.gold_spot(nodes, 'oro_medellin_centro', 9)
        self.assertIsNone(outside)
        self.assertIn('1 a 5', reason)


if __name__ == '__main__':
    unittest.main()
