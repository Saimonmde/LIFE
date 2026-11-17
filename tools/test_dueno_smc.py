# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sólo el dueño edita y acuña. El tope de 21.000.000 se respeta y el libro lo anota."""
import asyncio
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import accounts as acc
import economy as eco
import ed25519
import fusion
import libro
import persist
import server
import supply
import vault as VAULT
import dueno_smc as DUENO

SEED = bytes(range(32))


def chain():
    return libro.empty(ed25519.publickey(SEED).hex())


def owner():
    return {
        'id': 'dueño', 'name': 'saimon', 'wallet_name': 'saimon',
        'email': fusion.owner_email(), 'verified': True,
    }


def player():
    return {'id': 'ana', 'name': 'Ana', 'wallet_name': 'Ana', 'email': 'ana@ejemplo.co', 'role': 'owner'}


class DuenoLogicaTests(unittest.TestCase):
    def setUp(self):
        self._owner = os.environ.pop('SIMON_OWNER_EMAIL', None)

    def tearDown(self):
        if self._owner is None:
            os.environ.pop('SIMON_OWNER_EMAIL', None)
        else:
            os.environ['SIMON_OWNER_EMAIL'] = self._owner

    def test_mint_is_signed_chained_and_stops_at_the_cap(self):
        self.assertEqual(supply.GOLD_DAILY_SMC, 50)
        self.assertEqual(supply.COPPER_DAILY_SMC, 150)
        who = owner()
        econ = eco.empty_state()
        vault = {'accounts': {'saimon': {'smh': 65535, 'smcSubs': 65535, 'items': {}}}, 'purses': {}}
        doc = {'users': [who, player()], 'sessions': {}, 'rates': {}}
        madre = chain()
        room = DUENO._cupo(econ, madre)
        econ['minedSmh'] = eco.issuance_room(econ) - 150
        self.assertEqual(DUENO._cupo(econ, madre), 150)
        with self.assertRaises(DUENO.DuenoError) as blocked:
            DUENO.acunar(econ, vault, doc, who, '2', 'de más', madre, SEED, ahora=10, bits=1, presupuesto=1)
        self.assertEqual(blocked.exception.status, '409 Conflict')
        self.assertEqual(int(econ['wallets'].get('saimon') or 0), 0)
        self.assertEqual(len(madre['blocks']), 0)
        self.assertEqual(vault['accounts']['saimon']['smh'], 65535)
        got = DUENO.acunar(econ, vault, doc, who, '1', 'clase', madre, SEED, ahora=11, bits=1, presupuesto=1)
        self.assertEqual(got['codigo'][:4], 'SMC-')
        self.assertEqual(madre['blocks'][-1]['kind'], 'acunacion-admin')
        self.assertEqual(madre['blocks'][-1]['id'], got['codigo'])
        self.assertIn('Simulación educativa', madre['blocks'][-1]['location'])
        self.assertIn(madre['blocks'][-1]['prev'], (libro.GENESIS,))
        ok, _why = libro.verificar(madre)
        self.assertTrue(ok)
        self.assertEqual(int(econ['wallets']['saimon']), 100)
        self.assertEqual(vault['accounts']['saimon']['smh'], 65535)
        with self.assertRaises(DUENO.DuenoError):
            DUENO.acunar(econ, vault, doc, who, '1', 'otra', madre, SEED, ahora=12, bits=1, presupuesto=1)
        self.assertEqual(int(econ['wallets']['saimon']), 100)
        self.assertEqual(len(madre['blocks']), 1)
        self.assertEqual(doc['duenoAudit'][-1]['op'], 'acunar')
        self.assertNotIn('email', doc['duenoAudit'][-1])
        self.assertGreater(room, 150)

    def test_adjust_moves_without_minting_and_records_the_ledger(self):
        who = owner()
        econ = eco.empty_state()
        eco.credit(econ, 'saimon', 376)
        vault = {'accounts': {'saimon': {'smh': 65535, 'smcSubs': 65535, 'items': {}}}, 'purses': {}}
        dave = 64
        econ['wallets']['Dave'] = dave
        doc = {'users': [who], 'rates': {}}
        madre = chain()
        mined = int(econ['minedSmh'] or 0)
        oferta = libro._emitido(madre)
        moved = DUENO.ajustar(
            econ, vault, doc, who, '659,11', '0', 'pasar el baúl a la billetera',
            madre, SEED, ahora=20, bits=1, presupuesto=1,
        )
        self.assertEqual(int(econ['wallets']['saimon']), 376 + 65535)
        self.assertEqual(vault['accounts']['saimon']['smh'], 0)
        self.assertEqual(econ['wallets']['Dave'], dave)
        self.assertEqual(int(econ['minedSmh'] or 0), mined)
        self.assertEqual(libro._emitido(madre), oferta)
        self.assertTrue(all(block.get('kind') == 'ajuste-admin' for block in madre['blocks']))
        self.assertTrue(moved['codigos'])
        self.assertNotEqual(moved['codigos'][0][:3], 'SMC')
        ok, _why = libro.verificar(madre)
        self.assertTrue(ok)
        again = len(madre['blocks'])
        with self.assertRaises(DUENO.DuenoError) as same:
            DUENO.ajustar(
                econ, vault, doc, who, '659,11', '0', 'otra vez',
                madre, SEED, ahora=21, bits=1, presupuesto=1,
            )
        self.assertIn('ya es el saldo', str(same.exception))
        self.assertEqual(len(madre['blocks']), again)

    def test_adjust_up_mints_only_the_difference_and_a_player_cannot(self):
        who = owner()
        ana = player()
        econ = eco.empty_state()
        eco.credit(econ, 'saimon', 376)
        vault = {'accounts': {}, 'purses': {}}
        doc = {'users': [who, ana], 'rates': {}}
        madre = chain()
        DUENO.ajustar(
            econ, vault, doc, who, '5', '1', 'subir',
            madre, SEED, ahora=30, bits=1, presupuesto=1,
        )
        self.assertEqual(int(econ['wallets']['saimon']), 500)
        self.assertEqual(VAULT.smh_of(vault['accounts']['saimon']), 100)
        self.assertEqual(libro._emitido(madre), (500 + 100) - 376)
        self.assertTrue(any(block.get('kind') == 'acunacion-admin' for block in madre['blocks']))
        self.assertFalse(DUENO.autorizado(ana))
        with self.assertRaises(DUENO.DuenoError) as denied:
            DUENO.acunar(econ, vault, doc, ana, '1', 'no', madre, SEED, ahora=31, bits=1, presupuesto=1)
        self.assertEqual(denied.exception.status, '403 Forbidden')
        self.assertEqual(int(econ['wallets']['saimon']), 500)

    def test_rate_limit_stops_the_eleventh_change(self):
        who = owner()
        econ = eco.empty_state()
        vault = {'accounts': {}, 'purses': {}}
        doc = {'users': [who], 'rates': {}}
        madre = chain()
        for index in range(DUENO.POR_HORA):
            DUENO.acunar(
                econ, vault, doc, who, '0,01', 'ritmo %s' % index,
                madre, SEED, ahora=1000 + index, bits=1, presupuesto=1,
            )
        saldo = int(econ['wallets']['saimon'])
        alto = len(madre['blocks'])
        with self.assertRaises(DUENO.DuenoError) as limited:
            DUENO.acunar(econ, vault, doc, who, '0,01', 'de más', madre, SEED, ahora=1000 + DUENO.POR_HORA, bits=1, presupuesto=1)
        self.assertEqual(limited.exception.status, '429 Too Many Requests')
        self.assertEqual(int(econ['wallets']['saimon']), saldo)
        self.assertEqual(len(madre['blocks']), alto)


class DuenoHttpTests(unittest.TestCase):
    def setUp(self):
        self._owner = os.environ.pop('SIMON_OWNER_EMAIL', None)
        self.saved = {
            'ACCOUNTS': server.ACCOUNTS,
            'ECON': server.ECON,
            'VAULT_STATE': server.VAULT_STATE,
            'LIBRO_CHAIN': server.LIBRO_CHAIN,
            'NFT_SEED': server.NFT_SEED,
        }
        self._named = persist.save_named
        self._reserved = persist.save_reserved
        persist.save_named = lambda *args, **kwargs: None
        persist.save_reserved = lambda *args, **kwargs: None
        who = owner()
        ana = player()
        staff = {'id': 'mesa', 'name': 'Mesa', 'wallet_name': 'Mesa', 'email': 'mesa@ejemplo.co', 'role': 'staff'}
        server.NFT_SEED = SEED
        server.LIBRO_CHAIN = chain()
        server.ECON = eco.empty_state()
        eco.credit(server.ECON, 'saimon', 376)
        server.VAULT_STATE = {'accounts': {'saimon': {'smh': 65535, 'smcSubs': 65535, 'items': {}}}, 'purses': {}}
        server.ACCOUNTS = {
            'users': [who, ana, staff],
            'sessions': {
                'tok-dueno': {'user_id': 'dueño', 'exp': 10 ** 12},
                'tok-ana': {'user_id': 'ana', 'exp': 10 ** 12},
                'tok-mesa': {'user_id': 'mesa', 'exp': 10 ** 12},
            },
            'pending': {}, 'states': {}, 'rates': {},
        }

    def tearDown(self):
        persist.save_named = self._named
        persist.save_reserved = self._reserved
        for key, value in self.saved.items():
            setattr(server, key, value)
        if self._owner is None:
            os.environ.pop('SIMON_OWNER_EMAIL', None)
        else:
            os.environ['SIMON_OWNER_EMAIL'] = self._owner

    def post(self, token, body):
        headers = {'cookie': 'life_session=' + token} if token else {}
        raw = json.dumps(body).encode()
        return asyncio.run(server.try_auth('POST', '/auth/dueno/smc', '/auth/dueno/smc', headers, raw))

    def test_non_owner_gets_403_even_with_a_client_flag(self):
        for token in ('tok-ana', 'tok-mesa', ''):
            response = self.post(token, {
                'op': 'acunar', 'smc': '1000', 'razon': 'trampa',
                'owner': True, 'role': 'owner', 'admin': True,
            })
            if token:
                self.assertIn(b'403 Forbidden', response)
            else:
                self.assertIn(b'401 Unauthorized', response)
            self.assertEqual(int(server.ECON['wallets']['saimon']), 376)
            self.assertEqual(len(server.LIBRO_CHAIN['blocks']), 0)
        response = self.post('tok-dueno', {'op': 'acunar', 'smc': '100000000', 'razon': 'tope'})
        self.assertIn(b'409 Conflict', response)
        self.assertEqual(int(server.ECON['wallets']['saimon']), 376)
        ok = self.post('tok-dueno', {'op': 'acunar', 'smc': '0,50', 'razon': 'ensayo de clase'})
        self.assertIn(b'200 OK', ok)
        self.assertEqual(int(server.ECON['wallets']['saimon']), 376 + 50)
        self.assertEqual(server.LIBRO_CHAIN['blocks'][-1]['kind'], 'acunacion-admin')
        self.assertIn('Simulación educativa', server.LIBRO_CHAIN['blocks'][-1]['location'])


if __name__ == '__main__':
    unittest.main()
