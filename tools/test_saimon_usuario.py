# SPDX-License-Identifier: AGPL-3.0-or-later
"""Los dos Google de Jay quedan en el usuario saimon, sin acuñar y sin tocar a otros."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import accounts as acc
import economy as eco
import ed25519
import fusion
import libro
import saimon_usuario as SU


SEED = bytes(range(32))


class SaimonUsuarioTests(unittest.TestCase):
    def test_both_google_accounts_land_on_saimon_without_minting(self):
        owner = {
            'id': 'e3b1fde0bd778e9f', 'name': 'Simon', 'wallet_name': 'Simon',
            'email': fusion.owner_email(), 'providers': {'google': 'g-dueno'}, 'verified': True,
        }
        otro = {
            'id': 'juan', 'name': 'saimon', 'wallet_name': 'saimon',
            'email': 'juanskasimon@gmail.com', 'providers': {'google': 'g-juan'}, 'verified': True,
        }
        dave = {'id': 'dave', 'name': 'Dave García', 'wallet_name': 'Dave', 'email': 'dave@example.com'}
        cristo = {'id': 'cristo', 'name': 'Cristóbal', 'wallet_name': 'Cristóbal', 'email': 'cristo@example.com'}
        econ = eco.empty_state()
        econ['wallets'] = {
            'saimon': 0, 'id:e3b1fde0bd778e9f': 24, 'id:juan': 352,
            'Simon': 5800, 'Dave': 64, 'Cristóbal': 12, 'tesoro_genesis': 999,
        }
        econ['minedSmh'] = 4000
        econ['crudo'] = {'juan': {'mineral_oro': 8000}, 'e3b1fde0bd778e9f': {'mineral_plata': 1000}}
        vault = {
            'accounts': {
                'id:e3b1fde0bd778e9f': {'smh': 59735, 'items': {'moneda_plata': 2}},
                'Simon': {'smh': 5800, 'items': {'piedra': 1}},
                'Dave': {'smh': 10, 'items': {'piedra': 4}},
            },
            'purses': {
                'id:juan': {'red_pesca': 1, 'pera_seed': 3},
                'saimon': {'pico': 1},
            },
        }
        finca = {'accounts': {
            'Simon': {'goods': {'cafe_cereza': 2}, 'plots': {'cafe-1': {'crop': 'cafe', 'plantedAt': 50}}},
            'saimon': {'goods': {'bolsa_cacao': 1}, 'plots': {'cafe-1': {'crop': 'cafe', 'plantedAt': 0}}},
            'Dave': {'goods': {'cafe_cereza': 9}, 'plots': {}},
        }}
        accounts = {'users': [owner, otro, dave, cristo], 'sessions': {'tok': {'user_id': 'juan', 'exp': 10 ** 12}}, 'states': {}}
        chain = libro.empty(ed25519.publickey(SEED).hex())
        libro.acuñar(chain, SEED, 'id:e3b1fde0bd778e9f', 24, 'ya estaba', ts=1, bits=4, presupuesto=2, kind='migracion')
        antes = libro._emitido(chain)
        first = SU.aplicar(econ, vault, accounts, finca, libro=chain, seed=SEED, ahora=100)
        self.assertTrue(first['changed'])
        self.assertEqual(first['correo'], 'juanskasimon@gmail.com')
        self.assertEqual(first['motivo'], 'unido')
        self.assertEqual(econ['wallets']['saimon'], 24 + 352 + 5800)
        self.assertEqual(econ['wallets']['id:juan'], 0)
        self.assertEqual(econ['wallets']['Dave'], 64)
        self.assertEqual(econ['wallets']['Cristóbal'], 12)
        self.assertEqual(econ['wallets']['tesoro_genesis'], 999)
        self.assertEqual(vault['accounts']['saimon']['smh'], 59735 + 5800)
        self.assertEqual(vault['accounts']['Dave']['smh'], 10)
        self.assertEqual(vault['purses']['saimon']['red_pesca'], 1)
        self.assertEqual(vault['purses']['saimon']['pera_seed'], 3)
        self.assertEqual(vault['purses']['saimon']['pico'], 1)
        self.assertEqual(finca['accounts']['saimon']['goods']['cafe_cereza'], 2)
        self.assertEqual(finca['accounts']['saimon']['plots']['cafe-1']['plantedAt'], 50)
        self.assertEqual(finca['accounts']['Dave']['goods']['cafe_cereza'], 9)
        self.assertEqual(econ['crudo']['e3b1fde0bd778e9f']['mineral_oro'], 8000)
        self.assertNotIn('juan', econ['crudo'])
        self.assertEqual(otro['mergedInto'], owner['id'])
        self.assertEqual(otro['email'], '')
        self.assertEqual(accounts['sessions']['tok']['user_id'], owner['id'])
        self.assertIn('juanskasimon@gmail.com', owner['aliases'])
        self.assertIn('g-juan', acc.google_subs(owner))
        self.assertEqual(owner['wallet_name'], 'saimon')
        self.assertEqual(econ['minedSmh'], 4000)
        self.assertEqual(libro._emitido(chain), antes)
        self.assertEqual(first['ofertaAntes'], first['ofertaDespues'])
        self.assertFalse(any(block.get('kind') == 'acuñacion' for block in chain['blocks']))
        self.assertTrue(any(block.get('kind') == 'transferencia' for block in chain['blocks']))
        again = SU.aplicar(econ, vault, accounts, finca, libro=chain, seed=SEED, ahora=200)
        self.assertFalse(again['changed'])
        self.assertEqual(econ['wallets']['saimon'], 24 + 352 + 5800)
        self.assertEqual(vault['accounts']['Dave']['smh'], 10)
        self.assertEqual(libro._emitido(chain), antes)
        state = acc.start_oauth(accounts, 'google', now=300)
        entered = acc.finish_oauth(
            accounts, 'google', state, state,
            {'sub': 'g-juan', 'email': 'juanskasimon@gmail.com', 'name': 'saimon'}, now=310,
        )
        self.assertEqual(entered['user']['id'], owner['id'])

    def test_a_same_mask_without_the_nick_is_not_jay(self):
        owner = {'id': 'dueño', 'name': 'Simon', 'wallet_name': 'Simon', 'email': fusion.owner_email(), 'providers': {'google': 'g1'}}
        alguien = {'id': 'x', 'name': 'Juan', 'wallet_name': 'Juan', 'email': 'juan@gmail.com', 'providers': {'google': 'g2'}}
        econ = {'wallets': {'saimon': 10, 'Juan': 5}}
        vault = {'accounts': {}, 'purses': {}}
        SU.aplicar(econ, vault, {'users': [owner, alguien]})
        self.assertEqual(econ['wallets']['Juan'], 5)
        self.assertFalse(alguien.get('mergedInto'))

    def test_labels_and_mobile_buttons(self):
        import mi_cuenta
        self.assertEqual(mi_cuenta.nombre_de('pera_seed'), 'Semilla de pera')
        self.assertEqual(mi_cuenta.nombre_de('mineral_oro'), 'Mineral de oro')
        self.assertEqual(mi_cuenta.nombre_de('moneda_oro'), 'Moneda de oro')
        self.assertEqual(mi_cuenta.nombre_de('red_pesca'), 'Red de pesca')
        page = open(os.path.join(os.path.dirname(__file__), '..', 'play', 'cajon.js'), encoding='utf-8').read()
        self.assertIn('hud-inventario', page)
        self.assertIn('hud-banco', page)
        self.assertIn('/auth/cuenta', page)
        baul = open(os.path.join(os.path.dirname(__file__), '..', 'play', 'baul.js'), encoding='utf-8').read()
        self.assertIn('Para guardar o sacar', baul)


if __name__ == '__main__':
    unittest.main()
