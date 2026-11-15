# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tres monedas, topes fijos y acuñación que se detiene al llegar."""
import copy
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cobre
import economy as eco
import monedas
import plata
import supply as sup


def solve(challenge):
    nonce = sup.search_nonce(challenge['payload'], challenge['bits'])
    proof = dict(challenge)
    proof['nonce'] = nonce
    return proof


class CapTests(unittest.TestCase):
    def test_ledger_names_and_maximums(self):
        state = eco.empty_state()
        view = monedas.ledger(state, name='Ana')
        found = {row['id']: row for row in view['coins']}
        self.assertEqual(list(found), ['simoncoin', 'simonplata', 'simonchis'])
        self.assertEqual(found['simoncoin']['name'], 'Simoncoin')
        self.assertEqual(found['simoncoin']['max'], 21_000_000)
        self.assertEqual(found['simonplata']['name'], 'Simonplata')
        self.assertEqual(found['simonplata']['max'], 84_000_000)
        self.assertEqual(found['simonchis']['name'], 'Simonchis')
        self.assertEqual(found['simonchis']['max'], 333_000_000)
        self.assertEqual(found['simoncoin']['minted'], 0)
        self.assertEqual(view['balances']['simonchis'], 0)

    def test_simoncoin_mint_stops_at_the_cap(self):
        state = eco.empty_state()
        room = eco.issuance_room(state)
        granted = eco.issue(state, 'Ana', room, 'llenar', 'mint')
        self.assertEqual(granted, room)
        self.assertEqual(eco.issue(state, 'Ana', 1, 'de más', 'mint'), 0)
        self.assertLessEqual(int(state['minedSmh']), (eco.MAX_SUPPLY - eco.TREASURY) * eco.SUBS)
        view = monedas.ledger(state)
        self.assertLessEqual(view['coins'][0]['minted'], 21_000_000)

    def test_simonplata_room_stops_at_84_million(self):
        state = eco.empty_state()
        state['plata']['minedSph'] = plata.MAX_SPH
        self.assertEqual(plata.issuance_room(state), 0)
        self.assertEqual(plata.reward_sph(plata.MAX_SPH), 0)

    def test_simonchis_stop_and_cannot_be_replayed(self):
        state = {}
        opened = cobre.open_challenge(state, 'cta', 'mineral_cobre:1', now=1_700_000_000)
        self.assertTrue(opened['ok'])
        proof = solve(opened['challenge'])
        first = cobre.redeem(state, 'cta', 'mineral_cobre:1', proof, 4, now=1_700_000_001, purse='Nica')
        self.assertTrue(first['ok'], first)
        self.assertEqual(first['qty'], 4)
        self.assertEqual(cobre.balance_of(state, 'Nica'), 4)
        again = cobre.redeem(state, 'cta', 'mineral_cobre:1', proof, 4, now=1_700_000_002, purse='Nica')
        self.assertEqual(again['reason'], 'replay')
        self.assertEqual(state['simonchis']['minted'], 4)
        state['simonchis']['minted'] = cobre.MAX_SUPPLY
        opened = cobre.open_challenge(state, 'cta', 'mineral_cobre:2', now=1_700_000_010)
        self.assertEqual(opened['reason'], 'supply')
        state['simonchis']['minted'] = cobre.MAX_SUPPLY - 1
        opened = cobre.open_challenge(state, 'cta', 'mineral_cobre:3', now=1_700_000_020)
        proof = solve(opened['challenge'])
        last = cobre.redeem(state, 'cta', 'mineral_cobre:3', proof, 4, now=1_700_000_021, purse='Nica')
        self.assertEqual(last['qty'], 1)
        self.assertEqual(state['simonchis']['minted'], cobre.MAX_SUPPLY)
        self.assertEqual(cobre.room(state), 0)

    def test_ingots_are_stored_without_becoming_a_fourth_coin(self):
        state = eco.empty_state()
        self.assertEqual(monedas.anotar_lingotes(state, 'Nica', 'lingote_oro', 2), 2)
        view = monedas.ledger(state, name='Nica')
        self.assertEqual(len(view['coins']), 3)
        self.assertEqual(view['foundry']['lingote_oro'], 2)
        self.assertEqual(view['coins'][0]['minted'], 0)


class FurnaceMintTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import server
        self.server = server
        self.sent = []
        self._send = server.send
        server.send = lambda _c, obj: self.sent.append(obj)
        self._save_econ = server.save_econ
        self._save_libro = server.save_libro
        self._save_nft = server.save_nft
        server.save_econ = lambda: None
        server.save_libro = lambda *_a, **_k: None
        server.save_nft = lambda: None
        self._econ = copy.deepcopy(server.ECON)
        self._libro = copy.deepcopy(server.LIBRO_CHAIN)
        server.ECON.setdefault('supply', {})['bits'] = 8

    def tearDown(self):
        self.server.send = self._send
        self.server.save_econ = self._save_econ
        self.server.save_libro = self._save_libro
        self.server.save_nft = self._save_nft
        self.server.ECON.clear()
        self.server.ECON.update(self._econ)
        if isinstance(self.server.LIBRO_CHAIN, dict):
            self.server.LIBRO_CHAIN.clear()
            self.server.LIBRO_CHAIN.update(self._libro)

    def player(self):
        who = self.server.Client(None)
        who.hello = True
        who.wallet_ok = True
        who.wallet_token = ''
        who.zone = 'mine'
        who.name = 'Minero' + str(who.id)
        who.user = {'id': 'cta-' + who.name, 'createdAt': 0}
        who.ip = '198.51.100.40'
        who.activity_tiles = 8
        who.last_activity_at = time.time()
        return who

    def test_gold_mint_credits_simoncoin_under_the_cap(self):
        who = self.player()
        self.server.smelt_for(who, 'mineral_oro', 1, mode='simoncoin')
        challenge = next(item['challenge'] for item in self.sent if item.get('t') == 'pow_challenge')
        proof = solve(challenge)
        before = int(self.server.ECON.get('minedSmh') or 0)
        self.sent.clear()
        self.server.smelt_for(who, 'mineral_oro', 1, proof, 'simoncoin')
        after = int(self.server.ECON.get('minedSmh') or 0)
        self.assertGreater(after, before)
        self.assertLess(after - before, 30 * eco.SUBS)
        ok = next(item for item in self.sent if item.get('t') == 'smelt_result' and item.get('ok'))
        self.assertEqual(ok['mode'], 'simoncoin')
        coined = next(row for row in ok['ledger']['coins'] if row['id'] == 'simoncoin')
        self.assertLessEqual(coined['minted'], 21_000_000)
        self.assertGreater(ok['ledger']['balances']['simoncoin'], 0)

    def test_copper_mint_credits_simonchis(self):
        who = self.player()
        self.server.smelt_for(who, 'mineral_cobre', 1, mode='simonchis')
        challenge = next(item['challenge'] for item in self.sent if item.get('t') == 'pow_challenge')
        proof = solve(challenge)
        self.sent.clear()
        self.server.smelt_for(who, 'mineral_cobre', 1, proof, 'simonchis')
        ok = next(item for item in self.sent if item.get('t') == 'smelt_result' and item.get('ok'))
        self.assertEqual(ok['coin'], 'Simonchis')
        self.assertEqual(ok['qty'], 4)
        chis = next(row for row in ok['ledger']['coins'] if row['id'] == 'simonchis')
        self.assertGreaterEqual(chis['minted'], 4)
        self.assertEqual(chis['max'], 333_000_000)
        self.assertEqual(ok['ledger']['balances']['simonchis'], 4)

    def test_ingot_is_saved_on_the_server(self):
        who = self.player()
        self.server.smelt_for(who, 'mineral_oro', 2, mode='ingot')
        ok = next(item for item in self.sent if item.get('t') == 'smelt_result')
        self.assertTrue(ok['ok'])
        self.assertEqual(ok['item'], 'lingote_oro')
        self.assertEqual(ok['qty'], 2)
        self.assertEqual(self.server.ECON['foundry']['players'][who.name]['lingote_oro'], 2)


if __name__ == '__main__':
    unittest.main()
