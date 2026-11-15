# SPDX-License-Identifier: AGPL-3.0-or-later
"""La casa del municipio: lista, ovni una sola vez y aparición guardada."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import accounts as acc
import hogar

ORDEN = ('caldas', 'la_estrella', 'sabaneta', 'itagui', 'envigado', 'medellin', 'bello', 'copacabana', 'girardota', 'barbosa')


def world():
    with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
        return json.load(handle)


def walkable(doc, x, y):
    return 0 <= x < doc['width'] and 0 <= y < doc['height'] and doc['collision'][y][x] == 0


class HogarTests(unittest.TestCase):
    def test_list_runs_south_to_north_with_a_house_each(self):
        self.assertEqual(hogar.ORDEN, ORDEN)
        self.assertEqual(list(hogar.CASAS), list(ORDEN))
        doc = world()
        tiles = doc['tiles']
        for key in ORDEN:
            x, y = hogar.stand(key)
            self.assertTrue(walkable(doc, x, y), key)
            self.assertNotEqual(tiles[str(doc['ground'][y][x])]['kind'], 'water', key)
        self.assertEqual(hogar.stand('envigado'), (94, 267))
        self.assertIsNone(hogar.stand('otro'))

    def test_first_choice_is_the_ufo_and_the_next_entry_is_only_the_house(self):
        self.assertEqual(hogar.entry_mode(True), 'ovni')
        self.assertEqual(hogar.entry_mode(False), 'casa')

    def test_saved_home_is_the_spawn_unless_a_live_session_resumes(self):
        doc = world()
        user = {'municipio': 'bello'}
        check = lambda x, y: walkable(doc, x, y)
        self.assertEqual(hogar.arrival(user, None, check), (122.0, 130.0))
        self.assertEqual(hogar.arrival(user, {'x': 49, 'y': 362}, check), (49.0, 362.0))
        self.assertEqual(hogar.arrival({'municipio': ''}, None, check), None)
        self.assertEqual(hogar.arrival(None, {'x': -1, 'y': 4}, check), None)

    def test_account_stores_the_municipality_and_old_accounts_stay_blank(self):
        bag = acc.empty()
        user = {'id': 'u1', 'name': 'Ana', 'email': 'ana@example.com', 'wallet_name': 'Ana'}
        bag['users'].append(user)
        self.assertEqual(acc.public_user(user)['municipio'], '')
        shown = acc.set_municipio(bag, user, 'La_Estrella')
        self.assertEqual(shown['municipio'], 'la_estrella')
        self.assertEqual(user['municipio'], 'la_estrella')
        with self.assertRaises(acc.AuthError):
            acc.set_municipio(bag, user, 'paris')


if __name__ == '__main__':
    unittest.main()
