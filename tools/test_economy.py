# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprueba la emisión, el tope, el halving y el libro mayor de las SaiMonCoins (SMC)."""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as eco

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EconomyTests(unittest.TestCase):
    def test_old_file_keeps_blocks_and_shows_smc(self):
        old = eco.empty_state()
        old['symbol'] = 'SAI'
        old['unit'] = 'Saimon Coin'
        old['alias'] = ['Saimony']
        old['disclaimer'] = 'Las Saimon Coins (SAI, alias Saimony) son sólo una moneda del juego.'
        genesis = old['blocks'][0]['hash']
        eco.normalize_state(old)
        self.assertEqual(old['symbol'], 'SMC')
        self.assertEqual(old['unit'], 'SaiMonCoin')
        self.assertNotIn('alias', old)
        self.assertIn('SaiMonCoins', old['disclaimer'])
        self.assertEqual(old['blocks'][0]['hash'], genesis)

    def test_reward_and_cap(self):
        self.assertEqual(eco.reward_sai(0), 50)
        self.assertEqual(eco.reward_sai(10_500_000), 25)
        self.assertEqual(eco.reward_sai(21_000_000), 0)
        self.assertEqual(eco.SUBS, 100_000_000)
        self.assertEqual(eco.MAX_SUPPLY, 21_000_000)

    def test_chain_and_payment(self):
        st = eco.empty_state()
        self.assertTrue(eco.verify_block(st['blocks'][0], eco.GENESIS_PREV))
        eco.credit(st, 'Ana', eco.subunits(50))
        st['mined'] = 50
        self.assertTrue(eco.debit(st, 'Ana', eco.subunits(5)))
        eco.credit(st, 'puesto_frutas', eco.subunits(5))
        eco.append_tx(st, {'type': 'pay', 'from': 'Ana', 'to': 'puesto_frutas', 'amountSubs': eco.subunits(5), 'note': 'Compra'}, now=0)
        self.assertFalse(eco.seal_if_due(st, now=30))
        block = eco.seal_if_due(st, now=120)
        self.assertIsNotNone(block)
        self.assertTrue(eco.verify_block(block, st['blocks'][0]['hash']))
        self.assertFalse(eco.debit(st, 'Ana', eco.subunits(999)))

    def test_features_stay_off_the_house_door(self):
        features = json.load(open(os.path.join(ROOT, 'data', 'simulacion.json'), encoding='utf-8'))
        casa = open(os.path.join(ROOT, 'play', 'casa.js'), encoding='utf-8').read()
        self.assertIn('PARK_DOOR = { x: 226, y: 64 }', casa)
        self.assertIn('PARK_STAND = { x: 227, y: 64 }', casa)
        self.assertIn('SPAWN = { x: 4, y: 6, dir: \'down\' }', casa)
        door = {(226, 64), (227, 64)}
        spots = [(features['stable']['x'], features['stable']['y']), (features['npc']['x'], features['npc']['y']), (features['stand']['x'], features['stand']['y'])]
        spots += [(s['x'], s['y']) for s in features['mounts'][0]['spawn']]
        self.assertTrue(door.isdisjoint(spots))
        self.assertGreaterEqual(len(features['skill']['lessons']), 8)
        self.assertNotIn('Satoshi', features['npc']['name'])
        self.assertIn('Peer-to-Peer Electronic Cash System', features['skill']['citation']['title'])


class ServerGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, ROOT)
        import server
        cls.server = server

    def test_mint_requires_the_river_and_a_real_pan(self):
        s = self.server
        self.assertIsNone(s.gold_node_for(227, 64, 'oro_fluvial_1'))
        self.assertIsNotNone(s.gold_node_for(215, 54, 'oro_fluvial_1'))
        name = 'BateaPrueba'
        token = s.bind_wallet(name, '')
        before = float(s.ECON.get('mined') or 0)

        class Who:
            bot = True
            zone = 'city'
            x, y = 227, 64
            wallet_ok = True
            wallet_token = token
            name = 'BateaPrueba'
            last_mint = 0
        who = Who()
        s.mint_for(who, 'oro_fluvial_1')
        self.assertEqual(float(s.ECON.get('mined') or 0), before)
        who.x, who.y = 215, 54
        s.mint_for(who, 'oro_fluvial_1')
        self.assertGreater(float(s.ECON.get('mined') or 0), before)
        mid = float(s.ECON.get('mined') or 0)
        who.last_mint = 0
        s.mint_for(who, 'oro_fluvial_1')
        self.assertEqual(float(s.ECON.get('mined') or 0), mid)

    def test_wallet_token_blocks_a_stranger(self):
        s = self.server
        token = s.bind_wallet('Duena', '')
        self.assertEqual(s.bind_wallet('Duena', token), token)
        self.assertIsNone(s.bind_wallet('Duena', '0' * len(token)))
        self.assertLessEqual(len(s.block_page()), s.LEDGER_PAGE)


if __name__ == '__main__':
    unittest.main()
