# SPDX-License-Identifier: AGPL-3.0-or-later
"""El mapa del valle usa centros reales: Caldas al sur, Barbosa al norte, el río dobla al oriente."""
import json
import math
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load():
    with open(os.path.join(ROOT, 'data', 'valle-geo.json'), encoding='utf-8') as handle:
        return json.load(handle)


def km(a, b):
    return math.hypot((a[0] - b[0]) * 110.574, (a[1] - b[1]) * 111.32 * math.cos(math.radians(6.25)))


class ValleGeoTests(unittest.TestCase):
    def test_towns_parks_and_the_river_bend(self):
        geo = load()
        towns = {item['id']: item for item in geo['municipios']}
        self.assertEqual(set(towns), {
            'caldas', 'la_estrella', 'sabaneta', 'itagui', 'envigado',
            'medellin', 'bello', 'copacabana', 'girardota', 'barbosa',
        })
        self.assertLess(towns['caldas']['lat'], towns['sabaneta']['lat'])
        self.assertLess(towns['sabaneta']['lat'], towns['la_estrella']['lat'])
        self.assertLess(towns['la_estrella']['lon'], towns['sabaneta']['lon'])
        self.assertLess(towns['medellin']['lat'], towns['bello']['lat'])
        self.assertLess(towns['bello']['lat'], towns['barbosa']['lat'])
        self.assertLess(towns['girardota']['lon'], towns['barbosa']['lon'])
        names = {item['id'] for item in geo['parques']}
        for key in ('parque_berrio', 'parque_bolivar', 'explora', 'botanico', 'las_palmas'):
            self.assertIn(key, names)
        river = geo['river']
        self.assertGreaterEqual(len(river), 8)
        self.assertLess(len(river), 80)
        self.assertLess(river[0][0], river[-1][0])
        self.assertLess(river[0][1], river[-1][1])
        med = (towns['medellin']['lat'], towns['medellin']['lon'])
        self.assertLess(min(km(tuple(p), med) for p in river), 3)
        text = json.dumps(geo['attribution'])
        self.assertIn('OpenStreetMap', text)
        self.assertIn('SRTM', text)
        self.assertLessEqual(geo['grid']['rows'] * geo['grid']['cols'], 48 * 40)


if __name__ == '__main__':
    unittest.main()
