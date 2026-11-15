# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import os
import sys
import unittest
from collections import deque
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bridge4sur

ROOT = Path(__file__).resolve().parents[1]


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = json.loads((ROOT / 'data' / 'el-jardin.json').read_text())
        cls.w = json.loads(json.dumps(original))
        cls.c = bridge4sur.install(cls.w)

    def test_idempotent(self):
        again = bridge4sur.install(self.w)
        self.assertEqual(again['id'], self.c['id'])
        self.assertEqual(sum(1 for p in self.w['waypoints'] if p['id'].startswith('puente_4_sur')), 2)

    def test_walkable_crossing_and_rails(self):
        w, c = self.w, self.c
        y = c['y0'] + 2
        self.assertTrue(all(w['collision'][y][x] == 0 for x in range(c['x0'] - 1, c['x1'] + 1)))
        for x in range(c['x0'] + 1, c['x1'] - 1):
            self.assertEqual(w['collision'][c['y0'] - 1][x], 1)
            self.assertEqual(w['collision'][c['y1']][x], 1)
        for x in c['pylonTiles']:
            self.assertEqual(w['collision'][c['y0'] + 1][x], 1)

    def test_existing_city_and_both_accesses_connected(self):
        w, c = self.w, self.c
        start = (94, 267)
        q = deque([start])
        seen = {start}
        while q:
            x, y = q.popleft()
            for a, b in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= a < w['width'] and 0 <= b < w['height'] and not w['collision'][b][a] and (a, b) not in seen:
                    seen.add((a, b))
                    q.append((a, b))
        for point in w['waypoints']:
            self.assertIn((point['x'], point['y']), seen, point['id'])
        self.assertIn((c['x0'], c['y0'] + 2), seen)
        self.assertIn((c['x1'] - 1, c['y0'] + 2), seen)

    def test_no_claim_of_scan_and_adjustable_proportions(self):
        c = self.c
        self.assertFalse(c['surveyed'])
        self.assertEqual(c['scan']['status'], 'not-loaded')
        self.assertEqual(c['nominalMeters']['length'], 560)
        self.assertAlmostEqual((c['x1'] - c['x0']) * 2 / c['nominalMeters']['length'], c['renderUnitsPerNominalMeter'])


if __name__ == '__main__':
    unittest.main()
