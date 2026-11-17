# SPDX-License-Identifier: AGPL-3.0-or-later
"""Las llaves partidas de una cuenta se juntan sin acuñar."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import economy as eco
import fusion
import libro
import reunir


class ReunirTests(unittest.TestCase):
    def test_owner_keys_fold_into_the_account_id(self):
        owner = {'id': 'dueño', 'name': 'Simon', 'wallet_name': 'Simon', 'email': fusion.owner_email()}
        dave = {'id': 'dave', 'name': 'Dave García', 'wallet_name': 'Dave García', 'email': 'dave@example.com'}
        cristo = {'id': 'cristo', 'name': 'Cristóbal', 'wallet_name': 'Cristóbal', 'email': 'cristo@example.com'}
        econ = eco.empty_state()
        econ['wallets'] = {
            'Simon': 0, 'saimon': 1500, 'Saimon2': 200, 'Saimon888': 50,
            'Dave': 54, 'Dave García': 10,
            'Cristóbal': 8, 'Cristóbal  Garcí': 4,
            'tesoro_genesis': 999,
        }
        econ['minedSmh'] = 4000
        vault = {
            'accounts': {
                'saimon': {'smh': 59735, 'smcSubs': 59735, 'items': {'moneda_plata': 2}},
                'Dave': {'smh': 0, 'items': {'piedra': 1}},
            },
            'purses': {'saimon': {'moneda_cobre': 3}, 'Cristóbal  Garcí': {'bolsa_cafe': 1}},
        }
        accounts = {'users': [owner, dave, cristo]}
        chain = {'blocks': [], 'ids': [], 'smhPerSmc': eco.SMH_PER_SMC}
        first = reunir.aplicar(econ, vault, accounts, libro=chain, seed=os.urandom(32), ahora=100)
        self.assertTrue(first['changed'])
        self.assertEqual(econ['minedSmh'], 4000)
        self.assertEqual(econ['wallets']['id:dueño'], 1750)
        self.assertEqual(econ['wallets']['saimon'], 0)
        self.assertEqual(econ['wallets']['Saimon2'], 0)
        self.assertEqual(vault['accounts']['id:dueño']['smh'], 59735)
        self.assertEqual(vault['accounts']['id:dueño']['items']['moneda_plata'], 2)
        self.assertEqual(vault['purses']['id:dueño']['moneda_cobre'], 3)
        self.assertEqual(econ['wallets']['id:dave'], 64)
        self.assertEqual(vault['accounts']['id:dave']['items']['piedra'], 1)
        self.assertEqual(econ['wallets']['id:cristo'], 12)
        self.assertEqual(vault['purses']['id:cristo']['bolsa_cafe'], 1)
        self.assertEqual(econ['wallets']['tesoro_genesis'], 999)
        again = reunir.aplicar(econ, vault, accounts, libro=chain, seed=os.urandom(32), ahora=200)
        self.assertFalse(again['changed'])
        self.assertEqual(econ['wallets']['id:dueño'], 1750)
        self.assertEqual(econ['minedSmh'], 4000)
        row = next(item for item in reunir.informe(econ, vault, accounts) if item['dueno'])
        self.assertEqual(row['llave'], 'id:dueño')
        self.assertEqual(row['smhBilletera'], 1750)
        self.assertEqual(row['smhBaul'], 59735)
        self.assertGreaterEqual(row['objetos'], 5)
        self.assertTrue(all(block.get('kind') == 'transferencia' for block in chain.get('blocks') or []))
        self.assertFalse(any(block.get('kind') == 'acuñacion' for block in chain.get('blocks') or []))
        page = open(os.path.join(os.path.dirname(__file__), '..', 'server.py'), encoding='utf-8').read()
        handle = page.split('async def handle(', 1)[1]
        auth = page.split('async def try_auth(', 1)[1].split('\nasync def ', 1)[0]
        self.assertIn("path == '/api/diagnostico'", handle)
        self.assertNotIn('/api/diagnostico', auth)
        self.assertIn('reunir_llaves()', page)
        self.assertIn("m['bankSmh']", page)
        sim = open(os.path.join(os.path.dirname(__file__), '..', 'play', 'simulacion.js'), encoding='utf-8').read()
        self.assertIn('m.bankSmh', sim)
        hud = open(os.path.join(os.path.dirname(__file__), '..', 'play', 'cajon.js'), encoding='utf-8').read()
        self.assertIn('Baúl', hud)
        self.assertIn('Billetera', hud)
        game = open(os.path.join(os.path.dirname(__file__), '..', 'play', 'game.js'), encoding='utf-8').read()
        self.assertIn('Entrar con Google', game)

    def test_a_stranger_does_not_receive_the_owner_wallet(self):
        other = {'id': 'otro', 'name': 'Simon', 'wallet_name': 'Simon', 'email': 'otro@example.com'}
        econ = {'wallets': {'saimon': 100, 'Simon': 0}, 'minedSmh': 0}
        vault = {'accounts': {}, 'purses': {}}
        reunir.aplicar(econ, vault, {'users': [other]})
        self.assertEqual(econ['wallets']['saimon'], 100)
        self.assertEqual(econ['wallets'].get('id:otro', 0), 0)


if __name__ == '__main__':
    unittest.main()
