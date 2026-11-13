# SPDX-License-Identifier: AGPL-3.0-or-later
"""Los centros de los municipios coinciden con la brújula: norte es -y, oriente es +x."""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CompassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
            cls.world = json.load(handle)
        cls.parks = {park['id']: park for park in cls.world['waypoints']}

    def test_axes_match_the_valley(self):
        compass = self.world['valle']['compass']
        self.assertEqual(compass['north'], [0, -1])
        self.assertEqual(compass['east'], [1, 0])
        p = self.parks
        self.assertLess(p['bello']['y'], p['medellin']['y'])
        self.assertLess(p['copacabana']['y'], p['medellin']['y'])
        self.assertGreater(p['caldas']['y'], p['medellin']['y'])
        self.assertGreater(p['la_estrella']['y'], p['medellin']['y'])
        self.assertGreater(p['sabaneta']['y'], p['medellin']['y'])
        self.assertGreater(p['envigado']['y'], p['medellin']['y'])
        self.assertGreater(p['itagui']['y'], p['medellin']['y'])
        self.assertLess(p['itagui']['x'], p['medellin']['x'])
        self.assertLess(p['itagui']['x'], p['envigado']['x'])
        self.assertGreater(p['copacabana']['x'], p['bello']['x'])
        self.assertGreater(p['barbosa']['x'], p['medellin']['x'])
        self.assertLess(p['barbosa']['y'], p['bello']['y'])


if __name__ == '__main__':
    unittest.main()
