# SPDX-License-Identifier: AGPL-3.0-or-later
"""La casa del municipio: lista, ovni una sola vez y aparición guardada."""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import accounts as acc
import casa_cuenta
import hogar
import persist

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
        self.assertEqual(user['casa']['municipio'], 'la_estrella')
        self.assertFalse(user['casa']['migrated'])

    def test_house_record_keeps_furniture_items_and_pet(self):
        user = {'id': 'u1', 'name': 'Ana', 'municipio': 'bello'}
        layout = {'wall': '#f4f0e6', 'floor': '#c45c38', 'items': [
            {'id': 'bed', 'type': 'bed', 'x': 1, 'y': 1, 'rot': 0},
        ]}
        pet = {'species': 'cat', 'breed': 'siames', 'variant': 1, 'name': 'Luna'}
        shown = casa_cuenta.apply(user, {
            'layout': layout, 'items': {'madera': 4, 'piedra': 2}, 'pet': pet,
        })
        self.assertEqual(shown['municipio'], 'bello')
        self.assertEqual(shown['items'], [{'item': 'madera', 'qty': 4}, {'item': 'piedra', 'qty': 2}])
        self.assertEqual(shown['pet']['breed'], 'siames')
        self.assertEqual(shown['layout']['items'][0]['type'], 'bed')
        with self.assertRaises(casa_cuenta.CasaError):
            casa_cuenta.apply(user, {'pet': {'species': 'dog', 'breed': 'siames', 'variant': 0}})
        marked = casa_cuenta.apply(user, {}, migrate=True)
        self.assertTrue(marked['migrated'])
        blocked = casa_cuenta.apply(user, {'items': [{'item': 'oro', 'qty': 9}], 'pet': {'species': 'dog', 'breed': 'beagle', 'variant': 0, 'name': 'Sol'}}, migrate=True)
        self.assertEqual(blocked['items'][0]['item'], 'madera')
        self.assertEqual(blocked['pet']['name'], 'Luna')

    def test_pet_and_layout_share_the_account_and_the_vida_store(self):
        user = {'id': 'abc', 'name': 'Ana', 'casa': {
            'municipio': 'caldas', 'layout': {'v': 1, 'wall': '#f4f0e6', 'floor': '#c45c38', 'items': []},
            'items': [], 'pet': {'species': 'dog', 'breed': 'beagle', 'variant': 0, 'name': 'Sol'},
            'migrated': True,
        }}
        state = {'pets': {}, 'homes': {}}
        casa_cuenta.mirror(state, 'acct:abc', user)
        self.assertEqual(state['pets']['acct:abc']['breed'], 'beagle')
        self.assertIn('homes', state)
        other = {'id': 'abc', 'name': 'Ana'}
        vida = {'pets': {'acct:abc': {'species': 'cat', 'breed': 'siames', 'variant': 0, 'name': 'Luna'}}, 'homes': {}}
        self.assertTrue(casa_cuenta.absorb(other, vida, 'acct:abc'))
        self.assertEqual(other['casa']['pet']['name'], 'Luna')

    def test_account_file_roundtrip_is_the_persist_store(self):
        os.environ.pop('DATABASE_URL', None)
        persist.reset_connection()
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, 'accounts.json')
        user = {'id': 'u9', 'name': 'Ana', 'email': 'ana@example.com', 'wallet_name': 'Ana'}
        casa_cuenta.apply(user, {
            'municipio': 'itagui',
            'items': [{'item': 'madera', 'qty': 3}],
            'pet': {'species': 'cat', 'breed': 'siames', 'variant': 2, 'name': 'Nube'},
        }, migrate=True)
        doc = {'users': [user], 'sessions': {}, 'pending': {}, 'states': {}, 'rates': {}, 'resets': {}}
        persist.save_named('accounts', path, doc)
        loaded = persist.load_named('accounts', path)
        casa = loaded['users'][0]['casa']
        self.assertEqual(casa['municipio'], 'itagui')
        self.assertEqual(casa['items'][0]['qty'], 3)
        self.assertEqual(casa['pet']['name'], 'Nube')
        self.assertTrue(casa['migrated'])


if __name__ == '__main__':
    unittest.main()
