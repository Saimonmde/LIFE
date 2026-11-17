# SPDX-License-Identifier: AGPL-3.0-or-later
"""juanescasimon entra en saimon. La suma no cambia y la segunda pasada tampoco."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import accounts as acc
import economy as eco
import ed25519
import fusion
import libro
import persist
import reunir
import saimon_usuario as SU
import unir_jay as UJ

SEED = bytes(range(32))


def suma(econ, vault):
    total = sum(int(value or 0) for value in (econ.get('wallets') or {}).values())
    for box in (vault.get('accounts') or {}).values():
        total += reunir._smh_baul(box)
    return total


class UnirJayTests(unittest.TestCase):
    def setUp(self):
        self._url = os.environ.pop('DATABASE_URL', None)
        self._owner = os.environ.pop('SIMON_OWNER_EMAIL', None)
        persist.reset_connection()
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)
        if self._url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self._url
        if self._owner is None:
            os.environ.pop('SIMON_OWNER_EMAIL', None)
        else:
            os.environ['SIMON_OWNER_EMAIL'] = self._owner
        persist.reset_connection()

    def mundo(self):
        """La foto del #148 más la cuenta que ese pase no reconocía."""
        owner = {
            'id': 'e3b1fde0bd778e9f', 'name': 'saimon', 'wallet_name': 'saimon',
            'email': fusion.owner_email(), 'providers': {'google': 'g-oficial'},
            'googleSubs': ['g-oficial'], 'verified': True, 'aliases': ['juanskasimon@gmail.com'],
        }
        juan = {
            'id': 'juanes', 'name': 'Juan Esca', 'wallet_name': 'Juan Esca',
            'email': 'juanescasimon@gmail.com', 'providers': {'google': 'g-juanes'},
            'verified': True,
        }
        dave = {'id': 'dave', 'name': 'Dave García', 'wallet_name': 'Dave', 'email': 'dave@example.com'}
        cristo = {
            'id': 'cristo', 'name': 'Cristóbal', 'wallet_name': 'Cristóbal',
            'email': 'gamillo2007@gmail.com', 'providers': {'google': 'g-gami'},
        }
        econ = eco.empty_state()
        econ['wallets'] = {
            'saimon': 376, 'Juan Esca': 2000, 'id:juanes': 50,
            'Dave': 64, 'Cristóbal': 12, 'tesoro_genesis': 999,
        }
        econ['minedSmh'] = 4000
        econ['crudo'] = {'juanes': {'mineral_oro': 1000}}
        vault = {
            'accounts': {
                'saimon': {'smh': 65535, 'smcSubs': 65535, 'items': {'piedra': 1}},
                'Juan Esca': {'smh': 250, 'smcSubs': 250, 'items': {'pico': 2}},
                'Dave': {'smh': 10, 'items': {'piedra': 4}},
                'Cristóbal': {'smh': 8, 'items': {'bolsa_cafe': 1}},
            },
            'purses': {
                'id:juanes': {'red_pesca': 1},
                'Cristóbal': {'bolsa_cafe': 3},
            },
        }
        finca = {'accounts': {
            'Juan Esca': {'goods': {'cafe_cereza': 2}, 'plots': {'cafe-1': {'crop': 'cafe', 'plantedAt': 40}}},
            'Dave': {'goods': {'cafe_cereza': 9}, 'plots': {}},
        }}
        accounts = {
            'users': [owner, juan, dave, cristo],
            'sessions': {'tok-juan': {'user_id': 'juanes', 'exp': 10 ** 12}},
            'states': {},
        }
        chain = libro.empty(ed25519.publickey(SEED).hex())
        libro.acuñar(chain, SEED, 'Juan Esca', 2000, 'ya estaba', ts=1, bits=1, presupuesto=1, kind='migracion')
        libro.acuñar(chain, SEED, 'deposito:Juan Esca', 250, 'baúl', ts=2, bits=1, presupuesto=1, kind='migracion')
        return econ, vault, accounts, finca, chain, owner, juan

    def test_merge_conserves_sums_and_both_logins_resolve(self):
        econ, vault, accounts, finca, chain, owner, juan = self.mundo()
        antes = suma(econ, vault)
        oferta = libro._emitido(chain)
        bloques = len(chain['blocks'])
        first = UJ.aplicar(
            econ, vault, accounts, finca, libro=chain, seed=SEED, ahora=100, folder=self.dir,
        )
        self.assertTrue(first['changed'])
        self.assertEqual(suma(econ, vault), antes)
        self.assertEqual(first['sumaAntes'], first['sumaDespues'])
        self.assertEqual(econ['wallets']['saimon'], 376 + 2000 + 50)
        self.assertEqual(econ['wallets']['Juan Esca'], 0)
        self.assertEqual(econ['wallets']['id:juanes'], 0)
        self.assertEqual(econ['wallets']['Dave'], 64)
        self.assertEqual(econ['wallets']['Cristóbal'], 12)
        self.assertEqual(econ['wallets']['tesoro_genesis'], 999)
        self.assertEqual(vault['accounts']['saimon']['smh'], 65535 + 250)
        self.assertEqual(vault['accounts']['Dave']['smh'], 10)
        self.assertEqual(vault['accounts']['Cristóbal']['smh'], 8)
        self.assertEqual(vault['accounts']['Cristóbal']['items']['bolsa_cafe'], 1)
        self.assertEqual(vault['purses']['Cristóbal']['bolsa_cafe'], 3)
        self.assertEqual(vault['purses']['saimon']['red_pesca'], 1)
        self.assertEqual(vault['accounts']['saimon']['items']['pico'], 2)
        self.assertEqual(finca['accounts']['saimon']['goods']['cafe_cereza'], 2)
        self.assertEqual(finca['accounts']['Dave']['goods']['cafe_cereza'], 9)
        self.assertEqual(econ['crudo']['e3b1fde0bd778e9f']['mineral_oro'], 1000)
        self.assertNotIn('juanes', econ['crudo'])
        self.assertEqual(juan['mergedInto'], owner['id'])
        self.assertEqual(juan['email'], '')
        self.assertEqual(accounts['sessions']['tok-juan']['user_id'], owner['id'])
        self.assertIn('juanescasimon@gmail.com', owner['aliases'])
        self.assertIn('g-juanes', acc.google_subs(owner))
        self.assertEqual(owner['wallet_name'], 'saimon')
        self.assertEqual(econ['minedSmh'], 4000)
        self.assertEqual(libro._emitido(chain), oferta)
        self.assertGreater(len(chain['blocks']), bloques)
        self.assertTrue(any(block.get('kind') == 'transferencia' for block in chain['blocks']))
        self.assertFalse(any(block.get('kind') == 'acunacion-admin' for block in chain['blocks']))
        self.assertTrue(os.path.isfile(os.path.join(self.dir, 'jay-unido-respaldo.json')))
        respaldo = persist.load_named('jay_unido_respaldo', os.path.join(self.dir, 'jay-unido-respaldo.json'))
        self.assertEqual(respaldo['pasadas'][0]['fuentes'][1]['email'], 'juanescasimon@gmail.com')
        otra = UJ.aplicar(econ, vault, accounts, finca, libro=chain, seed=SEED, ahora=200, folder=self.dir)
        self.assertFalse(otra['changed'])
        self.assertEqual(suma(econ, vault), antes)
        self.assertEqual(econ['wallets']['saimon'], 376 + 2000 + 50)
        self.assertEqual(vault['accounts']['Dave']['smh'], 10)
        self.assertEqual(libro._emitido(chain), oferta)
        self.assertEqual(len(respaldo['pasadas']), len(persist.load_named(
            'jay_unido_respaldo', os.path.join(self.dir, 'jay-unido-respaldo.json'),
        )['pasadas']))
        state = acc.start_oauth(accounts, 'google', now=300)
        entered = acc.finish_oauth(
            accounts, 'google', state, state,
            {'sub': 'g-juanes', 'email': 'juanescasimon@gmail.com', 'name': 'Juan Esca'}, now=310,
        )
        self.assertEqual(entered['user']['id'], owner['id'])
        state = acc.start_oauth(accounts, 'google', now=320)
        oficial = acc.finish_oauth(
            accounts, 'google', state, state,
            {'sub': 'g-oficial', 'email': fusion.owner_email(), 'name': 'saimon'}, now=330,
        )
        self.assertEqual(oficial['user']['id'], owner['id'])
        self.assertFalse(any(user.get('email') == 'gamillo2007@gmail.com' and user.get('mergedInto') for user in accounts['users']))
        self.assertFalse(cristo_merged(accounts))

    def test_without_libro_balance_it_still_moves_and_does_not_mint(self):
        econ, vault, accounts, finca, _chain, owner, _juan = self.mundo()
        vacio = libro.empty(ed25519.publickey(SEED).hex())
        antes = suma(econ, vault)
        UJ.aplicar(econ, vault, accounts, finca, libro=vacio, seed=SEED, ahora=10)
        self.assertEqual(suma(econ, vault), antes)
        self.assertEqual(libro._emitido(vacio), 0)
        self.assertTrue(any(block.get('kind') == 'ajuste-admin' for block in vacio['blocks']))
        self.assertFalse(any(block.get('kind') in libro.KINDS_MINT for block in vacio['blocks']))
        self.assertEqual(econ['wallets']['Dave'], 64)
        self.assertEqual(owner['id'], 'e3b1fde0bd778e9f')

    def test_a_stranger_with_the_same_mask_stays_put(self):
        owner = {
            'id': 'dueño', 'name': 'saimon', 'wallet_name': 'saimon',
            'email': fusion.owner_email(), 'providers': {'google': 'g1'},
        }
        alguien = {
            'id': 'x', 'name': 'Juan', 'wallet_name': 'Juan',
            'email': 'juan@gmail.com', 'providers': {'google': 'g2'},
        }
        econ = {'wallets': {'saimon': 10, 'Juan': 5}, 'minedSmh': 0}
        vault = {'accounts': {}, 'purses': {}}
        UJ.aplicar(econ, vault, {'users': [owner, alguien], 'sessions': {}})
        self.assertEqual(econ['wallets']['Juan'], 5)
        self.assertFalse(alguien.get('mergedInto'))

    def test_labels_do_not_touch_sara_files(self):
        root = os.path.join(os.path.dirname(__file__), '..')
        page = open(os.path.join(root, 'play', 'dueno-smc.js'), encoding='utf-8').read()
        css = open(os.path.join(root, 'play', 'dueno-smc.css'), encoding='utf-8').read()
        for text in (page, css):
            self.assertNotIn('SMH', text)
            self.assertNotIn('SMP', text)
            self.assertNotIn('SPH', text)
        self.assertIn('Simulación educativa', page)
        self.assertIn("data.role === 'owner'", page)
        self.assertIn('dueno-smc.js', open(os.path.join(root, 'play', 'index.html'), encoding='utf-8').read())


def cristo_merged(accounts):
    for user in accounts['users']:
        if user.get('email') == 'gamillo2007@gmail.com' or user.get('id') == 'cristo':
            return bool(user.get('mergedInto'))
    return False


if __name__ == '__main__':
    unittest.main()
