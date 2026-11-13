# SPDX-License-Identifier: AGPL-3.0-or-later
"""Libro madre: unicidad, cadena, manipulación, tope, prueba de trabajo y migración."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy
import ed25519
import libro
import persist


SEED = bytes(range(32))
BITS = 4


def chain():
    return libro.empty(ed25519.publickey(SEED).hex())


def acuñar(doc, owner, smc, lugar='Río Medellín (Aburrá) · 10,20', ts=1, kind='acuñacion'):
    return libro.acuñar(
        doc, SEED, owner, economy.subunits(smc), lugar, ts=ts, bits=BITS, presupuesto=2, kind=kind,
    )


class LibroTests(unittest.TestCase):
    def test_pow_chain_and_unique_ids(self):
        doc = chain()
        first = acuñar(doc, 'Ana', 50, ts=10)
        second = acuñar(doc, 'Ana', 25, 'Quebrada La Presidenta · 81,257', ts=20)
        self.assertNotEqual(first['id'], second['id'])
        self.assertTrue(first['id'].startswith('SMC-1-'))
        self.assertTrue(second['id'].startswith('SMC-2-'))
        self.assertGreaterEqual(libro.bits_cero(bytes.fromhex(first['hash'])), BITS)
        self.assertEqual(first['nonce'] >= 0, True)
        self.assertEqual(second['prev'], first['hash'])
        self.assertEqual(first['miner'], 'Ana')
        self.assertIn('Río Medellín', first['location'])
        dust = libro.acuñar(doc, SEED, 'Ana', 12345, 'Quebrada La Presidenta · 81,257', ts=21, bits=BITS, presupuesto=2)
        self.assertEqual(dust['amountSmh'], 12345)
        self.assertIsInstance(dust['amountSmh'], int)
        self.assertEqual(economy.format_pair(dust['amountSmh']), '0,00012345 SMC = 12.345 SMH')
        ok, message = libro.verificar(doc)
        self.assertTrue(ok, message)
        uno = libro.verificar_uno(doc, first['id'])
        self.assertTrue(uno['verificado'])
        self.assertEqual(uno['motivo'], 'válido')

    def test_set_rejects_a_repeated_id(self):
        doc = chain()
        first = acuñar(doc, 'Ana', 1, ts=3)
        original = libro._codigo
        libro._codigo = lambda *args, **kwargs: first['id']
        try:
            with self.assertRaises(libro.LibroError):
                libro.acuñar(
                    doc, SEED, 'Ana', economy.subunits(1), 'río', ts=4, bits=BITS, presupuesto=2,
                )
        finally:
            libro._codigo = original
        self.assertEqual(len(doc['blocks']), 1)
        self.assertEqual(doc['blocks'][0]['id'], first['id'])

    def test_tamper_breaks_verification(self):
        doc = chain()
        acuñar(doc, 'Ana', 4, ts=5)
        acuñar(doc, 'Beto', 2, ts=6)
        doc['blocks'][0]['amountSmh'] = economy.subunits(99)
        ok, why = libro.verificar(doc)
        self.assertFalse(ok)
        self.assertIn('hash', why)
        doc['blocks'][0]['amountSmh'] = economy.subunits(4)
        doc['blocks'][1]['prev'] = 'ab' * 32
        ok, why = libro.verificar(doc)
        self.assertFalse(ok)
        self.assertIn('eslabón', why)
        doc['blocks'][1]['prev'] = doc['blocks'][0]['hash']
        doc['blocks'][1]['sig'] = '00' * 64
        ok, why = libro.verificar(doc)
        self.assertFalse(ok)
        self.assertIn('firma', why)

    def test_cap_stops_new_mints(self):
        doc = chain()
        room = economy.MAX_SUPPLY
        filled = acuñar(doc, 'Ana', room, ts=7)
        self.assertEqual(filled['amountSmh'], economy.smc_to_smh(room))
        self.assertNotIn('amount', filled)
        self.assertIsNone(acuñar(doc, 'Ana', 1, ts=8))
        self.assertEqual(len(doc['blocks']), 1)
        self.assertEqual(libro.cupo_subs(doc), 0)
        ok, message = libro.verificar(doc)
        self.assertTrue(ok, message)

    def test_migration_keeps_totals(self):
        doc = chain()
        wallets = {
            'tesoro_genesis': economy.subunits(economy.TREASURY),
            'Ana': economy.subunits(40),
            'puesto_frutas': 0,
        }
        vaults = {'Ana': {'smcSubs': economy.subunits(10), 'items': {}}}
        created = libro.migrar(doc, SEED, wallets, vaults, ts=100, bits=BITS, presupuesto=2)
        self.assertEqual(len(created), 3)
        got = libro.balances(doc)
        self.assertEqual(got['Ana'], economy.subunits(40))
        self.assertEqual(got['tesoro_genesis'], economy.subunits(economy.TREASURY))
        self.assertEqual(got['deposito:Ana'], economy.subunits(10))
        self.assertNotIn('puesto_frutas', got)
        again = libro.migrar(doc, SEED, wallets, vaults, ts=200, bits=BITS, presupuesto=2)
        self.assertEqual(again, [])
        move = libro.transferir(doc, SEED, 'Ana', 'Beto', economy.subunits(5), 'pago', ts=300)
        self.assertTrue(move['id'].startswith('MOV-'))
        got = libro.balances(doc)
        self.assertEqual(got['Ana'], economy.subunits(35))
        self.assertEqual(got['Beto'], economy.subunits(5))
        self.assertEqual(got['tesoro_genesis'], economy.subunits(economy.TREASURY))
        supply = sum(b['amountSmh'] for b in doc['blocks'] if b['kind'] != 'transferencia')
        self.assertEqual(supply, economy.subunits(economy.TREASURY + 50))
        ok, message = libro.verificar(doc)
        self.assertTrue(ok, message)

    def test_public_api_pages_and_verify(self):
        doc = chain()
        first = acuñar(doc, 'Ana', 2, ts=9)
        acuñar(doc, 'Ana', 1, ts=11)
        status, page = libro.api_get('/api/libro', {'limite': ['1'], 'pagina': ['1']}, doc)
        self.assertEqual(status, 200)
        self.assertEqual(len(page['blocks']), 1)
        self.assertEqual(page['blocks'][0]['height'], 2)
        self.assertTrue(page['blocks'][0]['verificado'])
        self.assertIn('simulación educativa', page['disclaimer'])
        status, one = libro.api_get('/api/libro/' + first['id'], {}, doc)
        self.assertEqual(status, 200)
        self.assertEqual(one['id'], first['id'])
        self.assertTrue(one['verificado'])
        status, full = libro.api_get('/api/libro/verificar', {}, doc)
        self.assertEqual(status, 200)
        self.assertTrue(full['ok'])
        status, missing = libro.api_get('/api/libro/SMC-0-NOEXISTE', {}, doc)
        self.assertEqual(status, 404)


class ReservaTests(unittest.TestCase):
    def setUp(self):
        self._url = os.environ.pop('DATABASE_URL', None)
        persist.reset_connection()
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, 'libro-madre.json')

    def tearDown(self):
        shutil.rmtree(self.dir)
        if self._url:
            os.environ['DATABASE_URL'] = self._url
        persist.reset_connection()

    def test_id_is_never_reissued(self):
        doc = chain()
        record = acuñar(doc, 'Ana', 3, ts=12)
        libro.save(self.path, doc, [record['id']])
        doc['blocks'].pop()
        doc['ids'].remove(record['id'])
        with self.assertRaises(persist.DuplicateId):
            libro.save(self.path, doc, [record['id']])
        kept = libro.load(self.path, doc['pubkey'])
        self.assertEqual(kept['blocks'][0]['id'], record['id'])
        fresh = acuñar(doc, 'Ana', 3, ts=13)
        self.assertNotEqual(fresh['id'], record['id'])
        libro.save(self.path, doc, [fresh['id']])


class ReservaPostgresTests(unittest.TestCase):
    url = os.environ.get('LIFE_TEST_DATABASE_URL', 'postgresql://life:life@127.0.0.1:5432/life_test')

    def setUp(self):
        try:
            import psycopg
            conn = psycopg.connect(self.url)
        except Exception as exc:
            self.skipTest('Postgres no está disponible: ' + str(exc))
        conn.execute('DROP TABLE IF EXISTS stores')
        conn.execute('DROP TABLE IF EXISTS libro_ids')
        conn.commit()
        conn.close()
        self._url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = self.url
        persist.reset_connection()
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, 'libro-madre.json')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        if self._url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self._url
        persist.reset_connection()

    def test_unique_constraint_blocks_reissue(self):
        doc = chain()
        record = acuñar(doc, 'Ana', 6, ts=14)
        libro.save(self.path, doc, [record['id']])
        other = chain()
        other['blocks'] = [dict(record)]
        other['ids'] = [record['id']]
        with self.assertRaises(persist.DuplicateId):
            libro.save(self.path, other, [record['id']])
        persist.reset_connection()
        kept = libro.load(self.path, doc['pubkey'])
        self.assertEqual(len(kept['blocks']), 1)
        self.assertEqual(kept['blocks'][0]['id'], record['id'])
        self.assertEqual(kept['blocks'][0]['amountSmh'], economy.subunits(6))


if __name__ == '__main__':
    unittest.main()
