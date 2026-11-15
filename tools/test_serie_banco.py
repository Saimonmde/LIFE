# SPDX-License-Identifier: AGPL-3.0-or-later
"""Series de moneda y lingotes que sólo crea el Banco Central."""
import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banco
import serie


class SerieTests(unittest.TestCase):
    def test_serials_are_unique_and_the_chain_checks(self):
        state = {}
        first = serie.record(state, 'simoncoin', 100, 'cta-ana', 10, '1 de enero de 1777 · 00:00')
        second = serie.record(state, 'simoncoin', 50, 'cta-ana', 11, '1 de enero de 1777 · 00:01')
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(first['serialTo'] + 1, second['serialFrom'])
        self.assertEqual(second['prev'], first['hash'])
        self.assertTrue(serie.intact(state))
        found = serie.lookup(state, 'simoncoin', 120)
        self.assertEqual(found['id'], second['id'])
        self.assertEqual(found['minter'], 'cta-ana')
        self.assertIsNone(serie.lookup(state, 'simoncoin', 151))

    def test_a_broken_link_fails_the_check(self):
        state = {}
        serie.record(state, 'simonchis', 4, 'cta-ana', 10, '2 de enero de 1777')
        serie.record(state, 'simonchis', 4, 'cta-ana', 11, '2 de enero de 1777')
        state['serie']['entries'][1]['prev'] = 'f' * 64
        self.assertFalse(serie.intact(state))

    def test_the_cap_cannot_be_passed_or_rewritten(self):
        state = {}
        with self.assertRaises(serie.SerieError):
            serie.record(state, 'simonchis', serie.CAPS['simonchis'] + 1, 'cta', 1, 'fecha')
        self.assertEqual(serie.CAPS['simoncoin'], 21_000_000 * 100_000_000)
        self.assertEqual(serie.CAPS['simonplata'], 84_000_000 * 100_000_000)
        self.assertEqual(serie.CAPS['simonchis'], 333_000_000)
        self.assertFalse(hasattr(serie, 'set_cap'))

    def test_concurrent_mints_do_not_share_a_serial(self):
        state = {}
        errors = []

        def once():
            try:
                serie.record(state, 'simonchis', 1, 'cta', 20, 'fecha')
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=once) for _ in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        entries = state['serie']['entries']
        self.assertEqual(len(entries), 12)
        ranges = [(item['serialFrom'], item['serialTo']) for item in entries]
        self.assertEqual(len(set(ranges)), 12)
        self.assertTrue(serie.intact(state))


class BancoTests(unittest.TestCase):
    def test_only_admin_or_creator_may_make_ingots(self):
        os.environ['SIMON_ADMIN_TOKEN'] = 'token-prueba'
        try:
            self.assertFalse(banco.autorizado('', {}))
            self.assertFalse(banco.autorizado('otro', {'role': 'player'}))
            self.assertTrue(banco.autorizado('token-prueba', None))
            self.assertTrue(banco.autorizado('', {'creator': True}))
            self.assertTrue(banco.autorizado('', {'role': 'creator'}))
        finally:
            os.environ.pop('SIMON_ADMIN_TOKEN', None)
        state = {}
        entry = banco.crear_lingotes(state, 'oro', 3, 'admin', 50, '3 de enero de 1777')
        self.assertEqual(entry['account'], banco.BANK)
        self.assertEqual(entry['qty'], 3)
        self.assertEqual(state['foundry']['players'][banco.BANK]['lingote_oro'], 3)
        self.assertEqual(state['bancoCentral']['ingots'][0]['id'], entry['id'])
        self.assertNotIn('serie', state)
        with self.assertRaises(banco.BancoError):
            banco.crear_lingotes(state, 'hierro', 1, 'admin', 51, 'fecha')


if __name__ == '__main__':
    unittest.main()
