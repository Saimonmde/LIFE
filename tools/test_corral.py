#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""El gallo se atrapa y se vende. No se mata. La guacharaca no entra al corral."""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import corral
import gallos
import partida
import purses


class CorralTests(unittest.TestCase):
    def test_catch_sell_and_do_not_kill(self):
        user = {'id': 'ana', 'name': 'Ana', 'corral': corral.empty()}
        other = {'id': 'luis', 'name': 'Luis'}
        caught = corral.catch(user, 'ana', 'gallo', 'gallo-finca-3', 'dorado')
        self.assertEqual(caught['species'], 'gallo')
        self.assertEqual(len(user['corral']['animals']), 1)
        with self.assertRaises(corral.CorralError):
            corral.catch(user, 'luis', 'gallo', 'gallo-monte-1')
        with self.assertRaises(corral.CorralError):
            corral.catch(user, 'ana', 'guacharaca', 'gua-1')
        self.assertEqual(len(user['corral']['animals']), 1)
        with self.assertRaises(corral.CorralError):
            corral.kill(user, 'ana', caught['id'])
        self.assertEqual(len(user['corral']['animals']), 1)
        self.assertFalse(corral.killable('gallo'))
        self.assertFalse(gallos.killable('gallo'))
        wallets = {'Ana': 12, 'Luis': 4}
        before = dict(wallets)
        purse = {'purses': {}}
        sold = corral.sell_one(user, 'ana', caught['id'], purse, 'Luis')
        self.assertEqual(sold['species'], 'gallo')
        self.assertEqual(user['corral']['animals'], [])
        self.assertEqual(purses.count(purse, 'Luis', 'gallo'), 1)
        self.assertEqual(purses.count(purse, 'Ana', 'gallo'), 0)
        self.assertEqual(wallets, before)
        with self.assertRaises(corral.CorralError):
            corral.sell_one(other, 'ana', 'no', purse, 'Ana')

    def test_corral_is_saved_and_animals_stay_inside(self):
        user = {'id': 'ana', 'name': 'Ana'}
        partida.remember(user, {
            'corral': {
                'animals': [
                    {'id': 'g1', 'species': 'gallo', 'color': 'negro', 'place': 'patio'},
                    {'id': 'h1', 'species': 'gallina', 'color': 'pinta', 'place': 'finca'},
                    {'id': 'x', 'species': 'guacharaca', 'color': 'oliva', 'place': 'patio'},
                ],
                'caught': ['gallo-monte-1'],
            },
        })
        saved = user['corral']
        self.assertEqual([item['species'] for item in saved['animals']], ['gallo', 'gallina'])
        self.assertEqual(saved['animals'][0]['color'], 'negro')
        again = partida.recall(user)['corral']
        self.assertEqual(again['animals'][1]['species'], 'gallina')
        self.assertEqual(again['caught'], ['gallo-monte-1'])
        box = corral.bounds({'x': 94, 'y': 267}, 'patio')
        self.assertNotIn((94, 267), {(box['x'], box['y'])})
        animal = {'fx': box['x'] + 3.9, 'fy': box['y'] + 0.4, 'goalX': box['x'] + 20, 'goalY': box['y'] - 8}
        moved = corral.step(animal, box, 1)
        self.assertGreaterEqual(moved['fx'], box['x'])
        self.assertLess(moved['fx'], box['x'] + box['w'])
        self.assertGreaterEqual(moved['fy'], box['y'])
        self.assertLess(moved['fy'], box['y'] + box['h'])

    def test_browser_rules(self):
        run = subprocess.run(
            ['node', os.path.join(ROOT, 'tools', 'test_corral.mjs')],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
