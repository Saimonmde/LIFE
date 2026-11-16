#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""La caída suelta la mochila una vez. El puma no entra al parque ni al pueblo."""
import json
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import fauna


class PackTests(unittest.TestCase):
    def setUp(self):
        self.gear = {'hacha', 'pico', 'lanza', 'red_pesca', 'batea'}
        self.profile = {
            'inv': [
                {'item': 'madera', 'qty': 4},
                {'item': 'hacha', 'qty': 1},
                {'item': 'mango', 'qty': 2},
                {'item': 'lanza', 'qty': 1},
            ],
            'xp': {'mining': 40, 'gathering': 12},
            'wallet': 250,
            'libro': {'started': True, 'done': True, 'turnedIn': False},
        }

    def test_split_keeps_gear_and_leaves_progress(self):
        kept, lost = fauna.split_pack(self.profile['inv'], self.gear)
        self.assertEqual(sorted(row['item'] for row in kept), ['hacha', 'lanza'])
        self.assertEqual(sorted(row['item'] for row in lost), ['madera', 'mango'])
        self.assertEqual(self.profile['xp']['mining'], 40)
        self.assertEqual(self.profile['wallet'], 250)
        self.assertTrue(self.profile['libro']['done'])
        self.assertFalse(self.profile['libro']['turnedIn'])

    def test_protected_names_never_drop(self):
        _, lost = fauna.split_pack(
            [{'item': 'smc', 'qty': 9}, {'item': 'libro', 'qty': 1}, {'item': 'piedra', 'qty': 3}],
            self.gear,
        )
        self.assertEqual(lost, [{'item': 'piedra', 'qty': 3}])


class DropTests(unittest.TestCase):
    def setUp(self):
        self.purse = {'purses': {'Ana': {'madera': 4, 'bolsa_cafe': 2}, 'Bea': {'madera': 1}}}
        self.book = fauna.Book(
            gear={'hacha', 'pico', 'lanza', 'red_pesca', 'batea'},
            ttl=1800,
            purse_state=self.purse,
        )
        self.slots = [
            {'item': 'madera', 'qty': 4},
            {'item': 'hacha', 'qty': 1},
            {'item': 'bolsa_cafe', 'qty': 2},
            {'item': 'mango', 'qty': 1},
        ]

    def test_drop_and_owner_pickup_once(self):
        xp, wallet, libro = {'mining': 15}, 80, {'done': True}
        drop = self.book.commit('Ana', 120.5, 40.25, self.slots, 'marca-1', now=1000)
        self.assertEqual(drop['x'], 120.5)
        self.assertEqual(drop['y'], 40.25)
        self.assertEqual(sorted(row['item'] for row in drop['items']), ['bolsa_cafe', 'madera', 'mango'])
        self.assertEqual(sorted(row['item'] for row in drop['kept']), ['hacha'])
        self.assertEqual(self.purse['purses']['Ana'].get('madera', 0), 0)
        self.assertEqual(self.purse['purses']['Ana'].get('bolsa_cafe', 0), 0)
        self.assertEqual(xp['mining'], 15)
        self.assertEqual(wallet, 80)
        self.assertTrue(libro['done'])
        with self.assertRaises(fauna.FaunaError):
            self.book.pickup('Bea', drop['id'], now=1001)
        self.assertEqual(self.purse['purses']['Bea']['madera'], 1)
        got = self.book.pickup('Ana', drop['id'], now=1002)
        self.assertEqual(sum(row['qty'] for row in got['items'] if row['item'] == 'madera'), 4)
        self.assertEqual(self.purse['purses']['Ana']['madera'], 4)
        self.assertEqual(self.purse['purses']['Ana']['bolsa_cafe'], 2)
        with self.assertRaises(fauna.FaunaError):
            self.book.pickup('Ana', drop['id'], now=1003)
        self.assertEqual(self.purse['purses']['Ana']['madera'], 4)
        self.assertEqual(self.purse['purses']['Ana']['bolsa_cafe'], 2)

    def test_same_mark_and_second_death_do_not_copy(self):
        first = self.book.commit('Ana', 10, 12, self.slots, 'marca-1', now=50)
        again = self.book.commit('Ana', 99, 99, self.slots, 'marca-1', now=51)
        self.assertEqual(again['id'], first['id'])
        self.assertEqual(len(self.book.state['drops']), 1)
        self.assertEqual(sum(row['qty'] for row in self.book.state['drops'][0]['items']), 7)
        with self.assertRaises(fauna.FaunaError):
            self.book.commit('Ana', 10, 12, self.slots, 'marca-2', now=52)
        self.assertEqual(len(self.book.state['drops']), 1)

    def test_drop_expires(self):
        drop = self.book.commit('Ana', 3, 4, [{'item': 'piedra', 'qty': 2}], 'marca-3', now=10)
        self.assertEqual(self.book.expire(10 + 1799), [])
        self.assertEqual(len(self.book.state['drops']), 1)
        gone = self.book.expire(10 + 1800)
        self.assertEqual([row['id'] for row in gone], [drop['id']])
        self.assertEqual(self.book.state['drops'], [])
        with self.assertRaises(fauna.FaunaError):
            self.book.pickup('Ana', drop['id'], now=10 + 1801)


class WorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
            world = json.load(handle)
        with open(os.path.join(ROOT, 'data', 'vida.json'), encoding='utf-8') as handle:
            places = json.load(handle).get('places')
        cls.land = fauna.Range(world, places)

    def test_pumas_stay_out_of_park_skate_and_town(self):
        self.assertGreaterEqual(len(self.land.homes), 1)
        blocked = [(98, 264), (100, 214), (85, 273), (54, 266), (106, 272), (49, 275)]
        for x, y in blocked:
            self.assertFalse(self.land.allowed(x, y), (x, y))
        for x, y in self.land.homes:
            self.assertTrue(self.land.allowed(x, y), (x, y))
            self.assertFalse(fauna.inside_box(x, y, self.land.boxes))

    def test_step_does_not_enter_a_forbidden_tile(self):
        puma = self.land.spawn_pumas()[0]
        rng = random.Random(3)
        for _ in range(40):
            fauna.step_puma(puma, [], self.land.allowed, self.land.boxes, 0, 0.4, rng)
            self.assertTrue(self.land.allowed(puma['x'], puma['y']))
        park = {'id': 7, 'name': 'Ana', 'x': 106, 'y': 272}
        puma['mode'] = 'charge'
        for n in range(30):
            fauna.step_puma(puma, [park], self.land.allowed, self.land.boxes, n, 0.4, rng)
            self.assertTrue(self.land.allowed(puma['x'], puma['y']))
            self.assertFalse(fauna.inside_box(puma['x'], puma['y'], self.land.boxes))


if __name__ == '__main__':
    unittest.main()
