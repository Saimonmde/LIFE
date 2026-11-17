# SPDX-License-Identifier: AGPL-3.0-or-later
"""El panel de la cuenta muestra el progreso y no enseña ni crea secretos."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import accounts as acc
import economy as eco
import mi_cuenta
import partida


class MiCuentaTests(unittest.TestCase):
    def test_panel_shows_progress_and_hides_the_password(self):
        doc = acc.empty()
        made = acc.enter_or_create(doc, 'Primo', 'secreto-largo', now=1_000)
        user = next(u for u in doc['users'] if u['id'] == made['user']['id'])
        user['providers'] = {'google': 'sub-secreto'}
        user['favorite_world'] = 3
        acc.set_favorite_place(doc, user, 'envigado')
        partida.remember(user, {
            'inv': [{'item': 'mineral_cobre', 'qty': 2}],
            'position': {'mapId': 'city', 'x': 94, 'y': 267, 'dir': 'down'},
            'rev': 1_700_000_000_000,
        })
        user['corral'] = {'v': 1, 'animals': [{'id': 'g1', 'species': 'gallo', 'color': 'negro', 'place': 'patio'}], 'caught': []}
        econ = {
            'wallets': {'Primo': 50_000_000},
            'plata': {'wallets': {'Primo': 100}},
            'simonchis': {'wallets': {'Primo': 3}},
        }
        before = json.dumps(econ)
        shown = mi_cuenta.resumen(user, econ, {'Primo': {'plots': {'cafe-1': {'crop': 'cafe'}}}}, 1_700_000_060_000)
        self.assertEqual(json.dumps(econ), before)
        self.assertEqual(eco.MAX_SUPPLY, 21_000_000)
        raw = json.dumps(shown)
        self.assertNotIn('scrypt', raw)
        self.assertNotIn('secreto', raw)
        self.assertNotIn('sub-secreto', raw)
        self.assertNotIn('password', raw)
        self.assertEqual(shown['nick'], 'Primo')
        self.assertTrue(shown['google'])
        self.assertEqual(shown['favoritePlace'], 'Parque de Envigado')
        self.assertEqual(shown['favoriteWorld'], 3)
        self.assertIn('En el valle', shown['place'])
        self.assertEqual(shown['saved'], 'Guardado hace 1 min')
        self.assertEqual(shown['inventory'], [{'item': 'mineral_cobre', 'qty': 2}])
        self.assertEqual(shown['coins']['simoncoinSmh'], 50_000_000)
        self.assertEqual(shown['crops']['cafe'], 1)
        self.assertEqual(shown['animals']['gallo'], 1)

    def test_the_panel_reads_the_live_wallet_and_bag(self):
        doc = acc.empty()
        made = acc.enter_or_create(doc, 'Primo', 'secreto-largo', now=1_000)
        user = next(u for u in doc['users'] if u['id'] == made['user']['id'])
        partida.remember(user, {'inv': [{'item': 'mineral_oro', 'qty': 1}, {'item': 'pico', 'qty': 1}], 'rev': 1})
        import crudo
        import economy as eco
        import purses
        econ = eco.empty_state()
        eco.credit(econ, 'Primo', 250)
        crudo.credit(econ, user['id'], 'mineral_oro', 5, cap=5)
        vault = {'accounts': {'Primo': {'items': {'moneda_cobre': 2}, 'smh': 100}}, 'purses': {}}
        purses.credit(vault, 'Primo', 'moneda_plata', 3)
        shown = mi_cuenta.resumen(user, econ, {'Primo': {'goods': {'cafe_cereza': 1}, 'plots': {}}}, vault_state=vault)
        inv = {row['item']: row['qty'] for row in shown['inventory']}
        self.assertEqual(inv['mineral_oro'], 5)
        self.assertEqual(inv['moneda_plata'], 3)
        self.assertEqual(inv['moneda_cobre'], 2)
        self.assertEqual(inv['cafe_cereza'], 1)
        self.assertEqual(inv['pico'], 1)
        self.assertEqual(shown['coins']['simoncoinSmh'], 250)
        self.assertEqual(shown['coins']['totalSmh'], 350)
        self.assertTrue(shown['enVivo'])
        eco.credit(econ, 'Primo', 50)
        later = mi_cuenta.resumen(user, econ, {}, vault_state=vault)
        self.assertEqual(later['coins']['simoncoinSmh'], 300)

    def test_password_change_needs_the_current_one_and_logout_can_be_everywhere(self):
        doc = acc.empty()
        made = acc.enter_or_create(doc, 'Primo', 'secreto-largo', now=2_000)
        user = next(u for u in doc['users'] if u['id'] == made['user']['id'])
        before = user['password_hash']
        name = user['name']
        with self.assertRaises(acc.AuthError) as wrong:
            acc.change_password(doc, user, 'otra-clave-larga', 'clave-nueva-1', now=2_100)
        self.assertEqual(str(wrong.exception), 'Contraseña incorrecta')
        self.assertEqual(user['password_hash'], before)
        self.assertEqual(user['name'], name)
        shown = acc.change_password(doc, user, 'secreto-largo', 'clave-nueva-1', now=2_200)
        self.assertNotIn('password_hash', shown)
        self.assertTrue(user['password_hash'].startswith('scrypt$'))
        self.assertNotEqual(user['password_hash'], before)
        self.assertNotIn('clave-nueva-1', user['password_hash'])
        doc['sessions']['aqui'] = {'user_id': user['id'], 'exp': 9_000}
        doc['sessions']['alla'] = {'user_id': user['id'], 'exp': 9_000}
        doc['sessions']['otra'] = {'user_id': 'ajena', 'exp': 9_000}
        acc.end_session(doc, 'aqui')
        self.assertNotIn('aqui', doc['sessions'])
        self.assertIn('alla', doc['sessions'])
        acc.end_all_sessions(doc, user['id'])
        self.assertEqual(list(doc['sessions']), ['otra'])
