# SPDX-License-Identifier: AGPL-3.0-or-later
"""El mapa muestra los diez municipios, de norte a sur, sin etiquetas encimadas."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import mapa_etiquetas as mapa


def load_world():
    with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
        return json.load(handle)


def boxes(world):
    scale, left, top = mapa.project(world['width'], world['height'])
    found = []
    for label in world['mapLabels']:
        ax, ay = mapa.anchor(scale, left, top, label['x'], label['y'])
        found.append(mapa.box_of(label['name'], ax, ay, label['dx'], label['dy'], label['kind']))
    return found


class MapaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = load_world()
        cls.labels = {label['id']: label for label in cls.world['mapLabels']}

    def test_ten_municipalities_run_north_to_south(self):
        towns = [label for label in self.world['mapLabels'] if label['kind'] == 'municipio']
        self.assertEqual([label['id'] for label in towns], list(mapa.MUNICIPIOS))
        ys = [self.labels[key]['y'] for key in mapa.MUNICIPIOS]
        self.assertEqual(ys, sorted(ys))
        self.assertLess(self.labels['bello']['y'], self.labels['medellin']['y'])
        self.assertLess(self.labels['medellin']['y'], self.labels['itagui']['y'])
        self.assertLess(self.labels['medellin']['y'], self.labels['envigado']['y'])
        self.assertEqual(self.labels['medellin']['name'], 'Medellín')
        self.assertEqual(self.labels['parque_bolivar']['name'], 'Parque de Bolívar')
        self.assertEqual(self.labels['parque_bolivar']['kind'], 'poi')
        self.assertLess(abs(self.labels['parque_bolivar']['x'] - self.labels['medellin']['x']), 20)
        self.assertLess(abs(self.labels['parque_bolivar']['y'] - self.labels['medellin']['y']), 20)
        names = [label['name'] for label in towns]
        self.assertNotIn('Bolívar', names)
        self.assertNotIn('Bolivar', names)

    def test_label_boxes_do_not_overlap_or_cover_the_park(self):
        world = self.world
        fresh = mapa.labels_for(world)
        stored = [(label['id'], label['dx'], label['dy']) for label in world['mapLabels']]
        solved = [(label['id'], label['dx'], label['dy']) for label in fresh]
        self.assertEqual(stored, solved)
        rects = boxes(world)
        for i, left in enumerate(rects):
            for right in rects[i + 1:]:
                self.assertFalse(mapa.hits(left, right), (left, right))
        scale, origin_x, origin_y = mapa.project(world['width'], world['height'])
        park = mapa.stamp_obstacle(scale, origin_x, origin_y)
        for label, rect in zip(world['mapLabels'], rects):
            self.assertFalse(mapa.hits(rect, park), label['name'])


if __name__ == '__main__':
    unittest.main()
