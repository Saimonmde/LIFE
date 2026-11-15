#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""La guacharaca sólo canta al amanecer y no entra a casas ni corrales."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import guacharaca
BANNED = ('casa', 'corral', 'potrero', 'mina', 'finca')


class GuacharacaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
            cls.world = json.load(handle)
        with open(os.path.join(ROOT, 'data', 'hogares.json'), encoding='utf-8') as handle:
            cls.homes = json.load(handle)
        cls.doc = guacharaca.place(cls.world, cls.homes)

    def test_sings_only_at_bogota_dawn(self):
        self.assertFalse(guacharaca.sings(4, 29))
        self.assertTrue(guacharaca.sings(4, 30))
        self.assertTrue(guacharaca.sings(5, 0))
        self.assertTrue(guacharaca.sings(5, 59))
        self.assertFalse(guacharaca.sings(6, 0))
        self.assertFalse(guacharaca.sings(6, 1))
        self.assertFalse(guacharaca.sings(12, 0))
        self.assertFalse(guacharaca.sings(0, 0))
        self.assertFalse(guacharaca.sings(3, 15))
        self.assertFalse(guacharaca.sings('no', 'hora'))

    def test_flocks_stay_out_of_houses_and_corrals(self):
        flocks = self.doc['flocks']
        self.assertGreaterEqual(len(flocks), 4)
        self.assertLessEqual(len(flocks), 14)
        birds = [bird for flock in flocks for bird in flock['birds']]
        self.assertGreaterEqual(len(birds), 8)
        for flock in flocks:
            self.assertGreaterEqual(len(flock['birds']), 2)
            self.assertLessEqual(len(flock['birds']), 6)
            self.assertIn(flock['habitat'], guacharaca.NATURAL)
        for bird in birds:
            kind = guacharaca.inside(self.doc['zones'], bird['x'], bird['y'])
            self.assertNotIn(kind, BANNED, bird['id'])
            self.assertEqual(kind, '')
            self.assertIn(bird['habitat'], guacharaca.NATURAL)
        with open(os.path.join(ROOT, 'data', 'guacharacas.js'), encoding='utf-8') as handle:
            script = handle.read()
        saved = json.loads(script.split('=', 1)[1].rstrip().rstrip(';'))
        self.assertEqual(saved['flocks'], self.doc['flocks'])
        for bird in (bird for flock in saved['flocks'] for bird in flock['birds']):
            self.assertEqual(guacharaca.inside(saved['zones'], bird['x'], bird['y']), '')

    def test_mountain_trees_river_and_las_palmas(self):
        flocks = self.doc['flocks']
        habitats = {flock['habitat'] for flock in flocks}
        self.assertIn('monte', habitats)
        self.assertIn('arbol', habitats)
        self.assertIn('quebrada', habitats)
        self.assertIn('rio', habitats)
        montes = [flock['y'] for flock in flocks if flock['habitat'] == 'monte']
        self.assertGreaterEqual(len(montes), 2)
        self.assertGreater(max(montes) - min(montes), 40)
        palmas = next(item for item in self.world['waypoints'] if item['id'] == 'las_palmas')
        near = [flock for flock in flocks if flock.get('near') == 'las_palmas']
        self.assertEqual(len(near), 1)
        spot = near[0]
        gap = max(abs(spot['x'] - palmas['x']), abs(spot['y'] - palmas['y']))
        self.assertGreaterEqual(gap, 12)
        self.assertLessEqual(gap, 22)
        urban = {'cobble', 'path', 'asphalt', 'pavement', 'bridge'}
        tiles = self.world['tiles']
        ground = self.world['ground']
        for bird in (bird for flock in flocks for bird in flock['birds']):
            kinds = guacharaca.covered(self.doc['zones'], bird['x'], bird['y'])
            self.assertFalse(kinds & set(BANNED) | (kinds & {'urbano'}))
            self.assertNotIn(tiles[str(ground[bird['y']][bird['x']])]['kind'], urban)

    def test_cannot_capture_or_sell(self):
        import partida
        saved = partida.pack({'inv': [{'item': 'guacharaca', 'qty': 1}, {'item': 'pico', 'qty': 1}]})
        self.assertEqual([row['item'] for row in saved['inv']], ['pico'])
        with open(os.path.join(ROOT, 'play', 'game.js'), encoding='utf-8') as handle:
            game = handle.read()
        self.assertIn('Guacharaca.blockedItem', game)
        self.assertIn('fauna protegida', game)
        with open(os.path.join(ROOT, 'play', 'guacharaca3d.js'), encoding='utf-8') as handle:
            model = handle.read()
        self.assertIn('#6e6240', model)
        self.assertIn('#8d9390', model)
        self.assertIn('#c44536', model)

    def test_browser_clock_and_flee(self):
        run = subprocess.run(
            ['node', os.path.join(ROOT, 'tools', 'test_guacharaca.mjs')],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_song_is_a_short_original_chorus(self):
        self.assertEqual([note['name'] for note in guacharaca.SONG['syllables']], ['gua', 'cha', 'ra', 'ca'])
        self.assertEqual(guacharaca.SONG['repeats'], 3)
        self.assertGreater(guacharaca.song_seconds(), 2.4)
        self.assertLess(guacharaca.song_seconds(), 3.2)
        with tempfile.TemporaryDirectory() as folder:
            sample = guacharaca.render_song(os.path.join(folder, 'guacharaca-canto.wav'))
        self.assertLess(sample['bytes'], 100 * 1024)
        self.assertGreater(sample['bytes'], 1000)
