# SPDX-License-Identifier: AGPL-3.0-or-later
"""POST /auth/delete-account: sólo la cuenta propia, sin romper el libro ni la oferta."""
import asyncio
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import accounts as acc
import borrar_cuenta as borrar
import economy as eco
import ed25519
import fusion
import libro
import nft
import persist
import plata
import server
import vault as VAULT

SUBS = eco.SUBS
NOTE = borrar.NOTE


def smc_total(economy, vault_state):
    wallets = sum(int(v or 0) for v in (economy.get('wallets') or {}).values())
    pool = int((economy.get('plata') or {}).get('smcPoolSmh') or 0)
    deposited = sum(VAULT.smh_of(box) for box in (vault_state.get('accounts') or {}).values())
    return wallets + pool + deposited


def smp_total(economy, vault_state):
    box = economy.get('plata') or {}
    wallets = sum(int(v or 0) for v in (box.get('wallets') or {}).values())
    burned = int(box.get('burnedSph') or 0)
    deposited = sum(VAULT.sph_of(item) for item in (vault_state.get('accounts') or {}).values())
    return wallets + burned + deposited


def txs_de(economy):
    rows = list(economy.get('mempool') or [])
    for block in economy.get('blocks') or []:
        rows.extend(block.get('txs') or [])
    rows.extend(((economy.get('plata') or {}).get('txs') or []))
    return rows


def cadena_ok(economy):
    prev = None
    for block in economy.get('blocks') or []:
        if not eco.verify_block(block, prev):
            return False
        prev = block['hash']
    return True


class DeleteAccountTests(unittest.TestCase):
    def setUp(self):
        self.saved = {
            'ACCOUNTS': server.ACCOUNTS,
            'ECON': server.ECON,
            'VAULT_STATE': server.VAULT_STATE,
            'PLAYERS': server.PLAYERS,
            'NFT_CHAIN': server.NFT_CHAIN,
            'LIBRO_CHAIN': server.LIBRO_CHAIN,
            'NFT_SEED': server.NFT_SEED,
        }
        self.saves = []
        self._save = persist.save_bundle
        self.fail_save = False

        def capture(docs, new_ids=None, ids_directory=None):
            if self.fail_save:
                raise RuntimeError('la base rechazó la escritura')
            self.saves.append(([name for name, _path, _doc in docs], list(new_ids or [])))

        persist.save_bundle = capture
        self.seed = bytes(range(32))
        server.NFT_SEED = self.seed

    def tearDown(self):
        persist.save_bundle = self._save
        for key, value in self.saved.items():
            setattr(server, key, value)

    def mundo(self):
        economy = eco.empty_state()
        plata.ensure(economy, now=1_700_000_000)
        economy['founderFusion'] = {
            'status': 'done', 'email': fusion.EMAIL, 'movedSmh': 1,
            'transfers': [{'where': 'billetera', 'from': 'Luz', 'to': 'Simon', 'amountSubs': 1}],
        }
        economy['migrations'] = {
            'Ana': {'done': True, 'requested': 5 * SUBS, 'credited': 5 * SUBS, 'unit': 'SMH'},
        }
        economy['questGrants'] = {'Ana': ['primeros_pasos'], 'Luz': ['primeros_pasos']}
        economy['questOwed'] = {'Ana': 10}
        eco.credit(economy, 'Ana', 5 * SUBS)
        eco.credit(economy, 'Luz', 1 * SUBS)
        economy['walletTokens'] = {'Ana': 'token-secreto-ana', 'Luz': 'token-luz'}
        economy['supply']['accounts'] = {'user-ana': {'earned': 1}, 'user-luz': {'earned': 2}}
        economy['supply']['flags'] = [{'account': 'user-ana', 'ip': '203.0.113.9', 'reason': 'rate'}]
        economy['plata']['wallets']['Ana'] = 4 * SUBS
        economy['plata']['wallets']['Luz'] = SUBS
        economy['plata']['accounts'] = {'user-ana': {'earned': 4}}
        economy['plata']['minedSph'] = 8 * SUBS
        economy['plata']['txs'] = [{'type': 'mint', 'to': 'Ana', 'amountSph': 4 * SUBS, 't': 1}]
        eco.append_tx(economy, {
            'type': 'pay', 'from': 'Ana', 'to': 'Luz', 'amountSubs': 10, 'note': 'pago',
        }, now=10)
        eco.seal_if_due(economy, now=80, force=True)
        economy['mempool'].append({
            'type': 'pay', 'from': 'Luz', 'to': 'Ana', 'amountSubs': 1, 'note': 'vuelta',
        })
        vault_state = VAULT.empty()
        ana = VAULT.account(vault_state, 'Ana')
        VAULT.add_smc(ana, 2 * SUBS)
        VAULT.add_smp(ana, 3 * SUBS)
        ana['items'] = {'silla': 1}
        luz = VAULT.account(vault_state, 'Luz')
        VAULT.add_smc(luz, SUBS)
        pub = ed25519.publickey(self.seed).hex()
        chain = nft.empty_chain(pub)
        nft.issue(chain, self.seed, 'Ana', 100, 'rio', '1,1', now=1)
        nft.issue(chain, self.seed, 'Luz', 40, 'rio', '2,2', now=2)
        madre = libro.empty(pub)
        libro.acuñar(madre, self.seed, 'Ana', 100, 'rio', ts=1, bits=1, presupuesto=1)
        libro.acuñar(madre, self.seed, 'Luz', 40, 'rio', ts=2, bits=1, presupuesto=1)
        ana_user = {
            'id': 'user-ana', 'name': 'Ana', 'email': 'ana@ejemplo.co', 'phone': '+573001112233',
            'password_hash': 'scrypt$ana', 'providers': {'google': 'sub-google-ana', 'facebook': 'fb-ana'},
            'wallet_name': 'Ana', 'wallet_token': 'token-secreto-ana', 'createdAt': 10,
        }
        luz_user = {
            'id': 'user-luz', 'name': 'Luz', 'email': 'luz@ejemplo.co', 'phone': '',
            'password_hash': 'scrypt$luz', 'providers': {'google': 'sub-google-luz'},
            'wallet_name': 'Luz', 'wallet_token': 'token-luz', 'createdAt': 11,
        }
        accounts = acc.empty()
        accounts['users'] = [ana_user, luz_user]
        accounts['sessions'] = {
            'tok-ana': {'user_id': 'user-ana', 'exp': 10 ** 12},
            'tok-luz': {'user_id': 'user-luz', 'exp': 10 ** 12},
        }
        accounts['pending']['ana@ejemplo.co'] = {'name': 'Ana', 'exp': 10 ** 12}
        accounts['rates'] = {'login:ana@ejemplo.co': [1], 'login:luz@ejemplo.co': [1]}
        players = {'players': {'Ana': {'playtime': 90, 'createdAt': 10}, 'Luz': {'playtime': 30, 'createdAt': 11}}}
        return {
            'accounts': accounts, 'economy': economy, 'vault': vault_state,
            'players': players, 'nft': chain, 'libro': madre, 'ana': ana_user,
        }

    def instalar(self, bundle):
        server.ACCOUNTS = bundle['accounts']
        server.ECON = bundle['economy']
        server.VAULT_STATE = bundle['vault']
        server.PLAYERS = bundle['players']
        server.NFT_CHAIN = bundle['nft']
        server.LIBRO_CHAIN = bundle['libro']

    def post(self, token, body):
        headers = {'cookie': 'life_session=' + token} if token else {}
        raw = json.dumps(body).encode()
        return asyncio.run(server.try_auth(
            'POST', '/auth/delete-account', '/auth/delete-account', headers, raw,
        ))

    def test_own_account_personal_data_ledger_and_supply(self):
        bundle = self.mundo()
        self.instalar(bundle)
        economy, vault_state = bundle['economy'], bundle['vault']
        antes_smc = smc_total(economy, vault_state)
        antes_smp = smp_total(economy, vault_state)
        mined = economy['minedSmh']
        mined_sph = economy['plata']['minedSph']
        tesoro = economy['wallets']['tesoro_genesis']
        fusion_antes = copy.deepcopy(economy['founderFusion'])
        pool_antes = int(economy['plata']['smcPoolSmh'] or 0)
        burned_antes = int(economy['plata']['burnedSph'] or 0)
        luz_smc = economy['wallets']['Luz']
        response = self.post('tok-ana', {'id': 'user-luz', 'confirm': 'ELIMINAR'})
        self.assertIn(b'200 OK', response)
        self.assertIn(b'Set-Cookie: life_session=', response)
        self.assertEqual(len(self.saves), 1)
        self.assertEqual(self.saves[0][0], ['accounts', 'economy', 'vault', 'players', 'nft', 'libro_madre', 'hogar'])
        self.assertEqual(smc_total(economy, vault_state), antes_smc)
        self.assertEqual(smp_total(economy, vault_state), antes_smp)
        self.assertEqual(economy['minedSmh'], mined)
        self.assertEqual(economy['plata']['minedSph'], mined_sph)
        self.assertEqual(economy['wallets']['tesoro_genesis'], tesoro)
        self.assertEqual(economy['founderFusion'], fusion_antes)
        self.assertEqual(economy['plata']['smcPoolSmh'], pool_antes + 7 * SUBS)
        self.assertEqual(economy['plata']['burnedSph'], burned_antes + 7 * SUBS)
        self.assertEqual(economy['wallets']['Luz'], luz_smc)
        self.assertNotIn('Ana', economy['wallets'])
        self.assertNotIn('Ana', economy['plata']['wallets'])
        self.assertNotIn('Ana', vault_state['accounts'])
        self.assertIn('Luz', vault_state['accounts'])
        self.assertNotIn('Ana', bundle['players']['players'])
        self.assertIn('Luz', bundle['players']['players'])
        estado = {k: bundle[k] for k in ('accounts', 'economy', 'vault', 'players', 'nft', 'libro')}
        dumped = json.dumps(estado, ensure_ascii=False)
        for secret in ('ana@ejemplo.co', 'sub-google-ana', 'fb-ana', '+573001112233', 'scrypt$ana', 'token-secreto-ana'):
            self.assertNotIn(secret, dumped)
        self.assertNotIn('"Ana"', dumped)
        self.assertIn('luz@ejemplo.co', dumped)
        self.assertIn('sub-google-luz', dumped)
        self.assertTrue(acc.name_available(bundle['accounts'], 'Ana', email='nueva@ejemplo.co', now=5_000))
        self.assertFalse(acc.reserved_nickname(bundle['accounts'], 'Ana'))
        alias = borrar.alias_de('user-ana')
        self.assertIn(alias, dumped)
        self.assertTrue(any(tx.get('note') == NOTE for tx in txs_de(economy)))
        self.assertTrue(all(tx.get(key) != 'Ana' for tx in txs_de(economy) for key in ('from', 'to', 'name', 'owner')))
        self.assertTrue(cadena_ok(economy))
        ok_nft, _msg = nft.verify_chain(bundle['nft'])
        self.assertTrue(ok_nft, _msg)
        ok_libro, msg_libro = libro.verificar(bundle['libro'])
        self.assertTrue(ok_libro, msg_libro)
        owners = [token['owner'] for token in bundle['nft']['tokens']]
        self.assertEqual(owners, [alias, 'Luz'])
        self.assertEqual(bundle['libro']['blocks'][1]['owner'], 'Luz')
        self.assertNotEqual(bundle['libro']['blocks'][0]['owner'], 'Ana')
        self.assertEqual(acc.session_user(bundle['accounts'], 'tok-luz', now=20)['email'], 'luz@ejemplo.co')
        self.assertIsNone(acc.session_user(bundle['accounts'], 'tok-ana', now=20))
        again = eco.migrate_monedas(economy, 'Ana', 5, now=90)
        self.assertTrue(again['already'])
        self.assertEqual(economy['minedSmh'], mined)
        sent = {}
        borrar_code = {}

        def send_email(email, code):
            sent['email'] = email

        acc.begin_signup(
            bundle['accounts'], 'Ana', 'nueva@ejemplo.co', '', 'secreto-largo',
            send_email, lambda phone: None, now=5_000,
        )
        self.assertEqual(sent['email'], 'nueva@ejemplo.co')
        self.assertEqual(bundle['accounts']['pending']['nueva@ejemplo.co']['name'], 'Ana')
        otra = self.post('', {'confirm': 'ELIMINAR'})
        self.assertIn(b'401', otra)
        self.assertIn('luz@ejemplo.co', json.dumps(bundle['accounts']))

    def test_founder_is_refused(self):
        bundle = self.mundo()
        bundle['accounts']['users'][0]['email'] = fusion.EMAIL
        self.instalar(bundle)
        antes = smc_total(bundle['economy'], bundle['vault'])
        response = self.post('tok-ana', {'confirm': 'ELIMINAR'})
        self.assertIn(b'403', response)
        self.assertIn('no se puede eliminar'.encode(), response)
        self.assertEqual(smc_total(bundle['economy'], bundle['vault']), antes)
        self.assertEqual(bundle['accounts']['users'][0]['email'], fusion.EMAIL)
        self.assertEqual(self.saves, [])
        self.assertIn('Ana', bundle['economy']['wallets'])

    def test_repeat_call_is_safe(self):
        bundle = self.mundo()
        self.instalar(bundle)
        first = self.post('tok-ana', {'confirm': 'Ana'})
        self.assertIn(b'200 OK', first)
        pool = bundle['economy']['plata']['smcPoolSmh']
        burned = bundle['economy']['plata']['burnedSph']
        second = self.post('tok-ana', {'confirm': 'ELIMINAR'})
        self.assertIn(b'401', second)
        self.assertEqual(bundle['economy']['plata']['smcPoolSmh'], pool)
        self.assertEqual(bundle['economy']['plata']['burnedSph'], burned)
        self.assertEqual(len(self.saves), 1)
        again = borrar.aplicar(bundle, {'id': 'user-ana'}, 'ELIMINAR', seed=self.seed, now=120)
        self.assertTrue(again['already'])
        self.assertEqual(bundle['economy']['plata']['smcPoolSmh'], pool)
        self.assertEqual(bundle['economy']['plata']['burnedSph'], burned)

    def test_confirm_required_and_failed_save_rolls_nothing(self):
        bundle = self.mundo()
        self.instalar(bundle)
        antes = json.dumps(bundle['accounts'])
        pool = bundle['economy']['plata']['smcPoolSmh']
        missing = self.post('tok-ana', {'confirm': 'no'})
        self.assertIn(b'400', missing)
        self.assertEqual(json.dumps(bundle['accounts']), antes)
        self.assertEqual(self.saves, [])
        self.fail_save = True
        failed = self.post('tok-ana', {'confirm': 'ELIMINAR'})
        self.assertIn(b'500', failed)
        self.assertIn(b'No se cambi', failed)
        self.assertEqual(json.dumps(bundle['accounts']), antes)
        self.assertEqual(bundle['economy']['plata']['smcPoolSmh'], pool)
        self.assertIn('Ana', bundle['economy']['wallets'])
        self.assertEqual(acc.session_user(bundle['accounts'], 'tok-ana', now=20)['email'], 'ana@ejemplo.co')


class BundleTests(unittest.TestCase):
    def setUp(self):
        self._url = os.environ.pop('DATABASE_URL', None)
        persist.reset_connection()
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        if self._url:
            os.environ['DATABASE_URL'] = self._url
        persist.reset_connection()

    def test_json_bundle_writes_every_store_together(self):
        docs = []
        for name in ('accounts', 'economy', 'vault'):
            path = os.path.join(self.dir, name + '.json')
            docs.append((name, path, {'marca': name}))
        persist.save_bundle(docs, ['SMC-1-ABCDEF01'], self.dir)
        for name, path, doc in docs:
            with open(path, encoding='utf-8') as handle:
                self.assertEqual(json.load(handle)['marca'], name)
        with open(os.path.join(self.dir, 'libro-ids.json'), encoding='utf-8') as handle:
            self.assertIn('SMC-1-ABCDEF01', json.load(handle)['ids'])
        with self.assertRaises(persist.DuplicateId):
            persist.save_bundle([(
                'accounts', os.path.join(self.dir, 'accounts.json'), {'marca': 'rota'},
            )], ['SMC-1-ABCDEF01'], self.dir)
        with open(os.path.join(self.dir, 'accounts.json'), encoding='utf-8') as handle:
            self.assertEqual(json.load(handle)['marca'], 'accounts')


if __name__ == '__main__':
    unittest.main()
