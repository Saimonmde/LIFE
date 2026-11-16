# SPDX-License-Identifier: AGPL-3.0-or-later
"""El lugar favorito es un parque que ya existe. No cambia la contraseña."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import accounts as acc
import corral
import hogar
import lugares


def world():
    with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
        return json.load(handle)


def walkable(doc, x, y):
    return 0 <= int(x) < doc['width'] and 0 <= int(y) < doc['height'] and doc['collision'][int(y)][int(x)] == 0


class LugarTests(unittest.TestCase):
    def test_catalog_uses_parks_that_already_exist(self):
        found = {item['id']: item for item in lugares.catalog()}
        self.assertEqual(found['envigado']['name'], 'Parque de Envigado')
        self.assertEqual((found['envigado']['x'], found['envigado']['y']), (94, 267))
        self.assertEqual(found['las_palmas']['name'], 'Las Palmas')
        self.assertEqual(found['parque_bolivar']['name'], 'Parque de Bolívar')
        self.assertIn('caldas', found)
        self.assertIsNone(lugares.get('paris'))
        doc = world()
        for item in found.values():
            self.assertTrue(walkable(doc, item['x'], item['y']), item['id'])

    def test_favorite_is_the_spawn_and_the_password_stays(self):
        bag = acc.empty()
        user = {'id': 'u1', 'name': 'Ana', 'email': 'ana@example.com', 'wallet_name': 'Ana', 'password_hash': 'scrypt$aa$bb'}
        bag['users'].append(user)
        shown = acc.set_favorite_place(bag, user, 'envigado')
        self.assertEqual(user['password_hash'], 'scrypt$aa$bb')
        self.assertEqual(shown['favoritePlace'], 'envigado')
        self.assertEqual(shown['municipio'], 'envigado')
        doc = world()
        check = lambda x, y: walkable(doc, x, y)
        self.assertEqual(hogar.arrival(user, None, check), (94.0, 267.0))
        pen = corral.bounds({'id': 'envigado', 'x': 94, 'y': 267}, 'finca')
        self.assertEqual((pen['x'], pen['y']), (100, 268))
        self.assertEqual(corral.bounds({'x': 94, 'y': 267}, 'finca')['x'], 148)
        acc.set_favorite_place(bag, user, 'las_palmas')
        self.assertEqual(user['password_hash'], 'scrypt$aa$bb')
        self.assertEqual(hogar.arrival(user, None, check), (float(lugares.get('las_palmas')['x']), float(lugares.get('las_palmas')['y'])))
        self.assertEqual(hogar.arrival(user, {'x': 49, 'y': 362}, check), (49.0, 362.0))
        with self.assertRaises(acc.AuthError):
            acc.set_favorite_place(bag, user, 'paris')
        self.assertEqual(user['favorite_place'], 'las_palmas')
        self.assertEqual(acc.public_user({'id': 'v', 'name': 'Viejo'})['favoritePlace'], '')
