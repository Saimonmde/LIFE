#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""El gallo se vende y canta al amanecer. La guacharaca no se vende."""
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gallos
import guacharaca
import partida
import purses


class GallosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
            cls.world = json.load(handle)
        with open(os.path.join(ROOT, 'data', 'hogares.json'), encoding='utf-8') as handle:
            cls.homes = json.load(handle)
        cls.doc = gallos.place(cls.world, cls.homes)

    def test_yards_and_farm_not_the_house_or_the_plots(self):
        roosters = self.doc['roosters']
        self.assertGreaterEqual(sum(1 for item in roosters if item['where'] == 'patio'), 8)
        self.assertGreaterEqual(sum(1 for item in roosters if item['where'] == 'finca'), 2)
        doors = {(house['x'], house['y']) for house in self.homes['casas']}
        plots = {(item['x'], item['y']) for item in self.doc['plots']}
        for bird in roosters:
            self.assertIn(bird['where'], ('patio', 'finca'))
            self.assertNotIn((bird['x'], bird['y']), doors)
            self.assertNotIn((bird['x'], bird['y']), plots)
            self.assertNotEqual(self.world['tiles'][str(self.world['ground'][bird['y']][bird['x']])]['kind'], 'water')

    def test_rooster_sells_and_guacharaca_does_not(self):
        self.assertTrue(gallos.sellable('gallo'))
        self.assertFalse(gallos.sellable('guacharaca'))
        self.assertFalse(guacharaca.sings(12, 0))
        state = {'purses': {}}
        wallets = {'Ana': 40, 'Luis': 10}
        before = dict(wallets)
        purses.credit(state, 'Ana', 'gallo', 1)
        moved = gallos.sell(state, 'Ana', 'Luis', 'gallo', 1)
        self.assertEqual(moved['qty'], 1)
        self.assertEqual(purses.count(state, 'Luis', 'gallo'), 1)
        self.assertEqual(purses.count(state, 'Ana', 'gallo'), 0)
        self.assertEqual(wallets, before)
        with self.assertRaises(gallos.GallosError):
            gallos.sell(state, 'Luis', 'Ana', 'guacharaca', 1)
        saved = partida.pack({'inv': [{'item': 'gallo', 'qty': 20}, {'item': 'guacharaca', 'qty': 3}, {'item': 'pico', 'qty': 1}]})
        self.assertEqual(saved['gallos'], gallos.CAP)
        self.assertEqual(sum(row['qty'] for row in saved['inv'] if row['item'] == 'gallo'), gallos.CAP)
        self.assertNotIn('guacharaca', [row['item'] for row in saved['inv']])
        self.assertIn('pico', [row['item'] for row in saved['inv']])
        purse = {'purses': {}}
        self.assertEqual(gallos.sync_purse(purse, 'Ana', 2), 2)
        self.assertEqual(gallos.sync_purse(purse, 'Ana', 2), 2)
        self.assertNotIn('smc', purse)

    def test_real_dawn_and_game_day(self):
        self.assertFalse(gallos.crows_real(4, 59))
        self.assertTrue(gallos.crows_real(5, 0))
        self.assertTrue(gallos.crows_real(5, 59))
        self.assertFalse(gallos.crows_real(6, 0))
        self.assertFalse(gallos.crows_real(12, 0))
        epoch = 1_700_000_000
        self.assertEqual(gallos.game_day(epoch, epoch), 1)
        self.assertEqual(gallos.game_day(epoch + 20 * 60 - 1, epoch), 1)
        self.assertEqual(gallos.game_day(epoch + 20 * 60, epoch), 2)
        self.assertFalse(gallos.game_dawn(1, 1))
        self.assertTrue(gallos.game_dawn(1, 2))
        self.assertEqual(gallos.notice(2), 'Amaneció: día 2')

    def test_browser_clock(self):
        run = subprocess.run(
            ['node', os.path.join(ROOT, 'tools', 'test_gallos.mjs')],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
