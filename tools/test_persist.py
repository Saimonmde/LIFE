# SPDX-License-Identifier: AGPL-3.0-or-later
"""El estado se guarda en JSON y, si hay DATABASE_URL, en Postgres."""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import persist
import economy


class JsonModeTests(unittest.TestCase):
    def setUp(self):
        self._url = os.environ.pop('DATABASE_URL', None)
        persist.reset_connection()
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, 'economy.json')

    def tearDown(self):
        shutil.rmtree(self.dir)
        if self._url:
            os.environ['DATABASE_URL'] = self._url
        persist.reset_connection()

    def test_roundtrip_file(self):
        state = economy.empty_state()
        state['wallets']['Ana'] = 5
        economy.save_state(self.path, state)
        loaded = economy.load_state(self.path)
        self.assertEqual(loaded['wallets']['Ana'], 5)
        self.assertEqual(loaded['symbol'], 'SMC')


class PostgresModeTests(unittest.TestCase):
    url = os.environ.get('LIFE_TEST_DATABASE_URL', 'postgresql://life:life@127.0.0.1:5432/life_test')

    def setUp(self):
        try:
            import psycopg
            conn = psycopg.connect(self.url)
        except Exception as exc:
            self.skipTest('Postgres no está disponible: ' + str(exc))
        conn.execute('DROP TABLE IF EXISTS stores')
        conn.commit()
        conn.close()
        self._url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = self.url
        persist.reset_connection()
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        if self._url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self._url
        persist.reset_connection()

    def test_import_once_and_roundtrip(self):
        path = os.path.join(self.dir, 'economy.json')
        original = economy.empty_state()
        original['wallets']['Ana'] = 9
        original['migrations'] = {'Ana': {'credited': 1}}
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(original, handle)
        loaded = economy.load_state(path)
        self.assertEqual(loaded['wallets']['Ana'], 9)
        loaded['wallets']['Ana'] = 12
        economy.save_state(path, loaded)
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump({'wallets': {'Ana': 1}}, handle)
        persist.reset_connection()
        again = economy.load_state(path)
        self.assertEqual(again['wallets']['Ana'], 12)
        self.assertIn('Ana', again['migrations'])


if __name__ == '__main__':
    unittest.main()
