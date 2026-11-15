# SPDX-License-Identifier: AGPL-3.0-or-later
"""Acuñar deja el saldo en el mensaje que pinta la pantalla, con serial."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server as s
import supply as sup
import historial as hist


class SaldoVisibleTests(unittest.TestCase):
    def setUp(self):
        self.sent = []
        self._send = s.send
        self._save = s.save_econ
        self._libro = s.save_libro
        self._nft = s.save_nft
        self._cast = s.broadcast_econ
        s.send = lambda c, obj: self.sent.append(obj)
        s.save_econ = lambda: None
        s.save_libro = lambda *a, **k: None
        s.save_nft = lambda: None
        s.broadcast_econ = lambda: self.sent.append(s.econ_msg('SaldoPrueba', profile={'account': 'cta-saldo', 'age': 0, 'play': 0, 'quests': 0}))
        s.ECON['historial'] = {'next': {}, 'rows': []}
        s.ECON.setdefault('simonchis', {}).pop('wallets', None)
        s.ECON.setdefault('supply', {})['bits'] = 8

    def tearDown(self):
        s.send = self._send
        s.save_econ = self._save
        s.save_libro = self._libro
        s.save_nft = self._nft
        s.broadcast_econ = self._cast

    def player(self):
        who = s.Client(None)
        who.hello = True
        who.wallet_ok = True
        who.wallet_token = ''
        who.zone = 'mine'
        who.name = 'SaldoPrueba'
        who.user = {'id': 'cta-saldo', 'createdAt': time.time()}
        s.ECON.setdefault('simonchis', {}).setdefault('wallets', {})['SaldoPrueba'] = 0
        who.ip = '198.51.100.40'
        who.activity_tiles = 8
        who.last_activity_at = time.time()
        return who

    def test_mint_puts_the_balance_and_serial_where_the_hud_reads_them(self):
        who = self.player()
        s.acunar_for(who, 'simonchis', 6)
        challenge = next(x for x in self.sent if x.get('t') == 'pow_challenge')
        proof = dict(challenge['challenge'])
        proof['nonce'] = sup.search_nonce(proof['payload'], proof['bits'])
        self.sent.clear()
        s.acunar_for(who, 'simonchis', 6, proof)
        done = next(x for x in self.sent if x.get('t') == 'acunar_result')
        self.assertTrue(done['ok'])
        self.assertEqual(done['ledger']['balances']['simonchis'], 2)
        self.assertEqual(done['historial'][0]['serial'], 'SCH-00000001')
        self.assertEqual(done['historial'][0]['base'], 2)
        economy = next(x for x in self.sent if x.get('t') == 'economy')
        self.assertEqual(economy['ledger']['balances']['simonchis'], 2)
        self.assertEqual(economy['historial'][0]['serial'], 'SCH-00000001')
        again = hist.anotar(s.ECON, 'simonchis', 1, 'Ana', 'otra')
        self.assertEqual(again['serial'], 'SCH-00000002')


if __name__ == '__main__':
    unittest.main()
