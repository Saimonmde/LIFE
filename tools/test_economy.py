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
        import re
        features = json.load(open(os.path.join(ROOT, 'data', 'simulacion.json'), encoding='utf-8'))
        offset = json.load(open(os.path.join(ROOT, 'data', 'valle-offset.json'), encoding='utf-8'))
        casa = open(os.path.join(ROOT, 'play', 'casa.js'), encoding='utf-8').read()
        found = re.search(r'VALLE_OFFSET = \{ x: (-?\d+), y: (-?\d+) \}', casa)
        self.assertIsNotNone(found)
        self.assertEqual((int(found.group(1)), int(found.group(2))), (offset['x'], offset['y']))
        self.assertIn('PARK_DOOR = { x: 226 + VALLE_OFFSET.x, y: 64 + VALLE_OFFSET.y }', casa)
        self.assertIn('PARK_STAND = { x: 227 + VALLE_OFFSET.x, y: 64 + VALLE_OFFSET.y }', casa)
        self.assertIn('SPAWN = { x: 4, y: 6, dir: \'down\' }', casa)
        dx, dy = offset['x'], offset['y']
        door = {(226 + dx, 64 + dy), (227 + dx, 64 + dy)}
        spots = [(features['stable']['x'] + dx, features['stable']['y'] + dy), (features['npc']['x'] + dx, features['npc']['y'] + dy), (features['stand']['x'] + dx, features['stand']['y'] + dy)]
        spots += [(s['x'] + dx, s['y'] + dy) for s in features['mounts'][0]['spawn']]
        self.assertTrue(door.isdisjoint(spots))
        self.assertGreaterEqual(len(features['skill']['lessons']), 8)
        self.assertNotIn('Satoshi', features['npc']['name'])
        self.assertIn('Peer-to-Peer Electronic Cash System', features['skill']['citation']['title'])

    def test_old_sai_balance_stays_one_to_one(self):
        old = eco.empty_state()
        old['symbol'] = 'SAI'
        old['wallets']['Ana'] = eco.subunits(12)
        eco.normalize_state(old)
        self.assertEqual(old['wallets']['Ana'], eco.subunits(12))
        eco.normalize_state(old)
        self.assertEqual(old['wallets']['Ana'], eco.subunits(12))

    def test_issue_respects_the_cap(self):
        st = eco.empty_state()
        st['mined'] = eco.MAX_SUPPLY - eco.TREASURY - 3
        got = eco.issue(st, 'Ana', 10, 'prueba', 'mint', now=10)
        self.assertEqual(got, 3)
        self.assertEqual(eco.issue(st, 'Ana', 1, 'otra', 'mint', now=20), 0)
        self.assertLessEqual(st['mined'] + eco.TREASURY, eco.MAX_SUPPLY)

    def test_old_coins_convert_once(self):
        st = eco.empty_state()
        first = eco.migrate_monedas(st, 'Ana', 40, now=30)
        self.assertFalse(first['already'])
        self.assertEqual(first['rate'], 1)
        self.assertEqual(first['credited'], 40)
        self.assertEqual(st['wallets']['Ana'], eco.subunits(40))
        again = eco.migrate_monedas(st, 'Ana', 40, now=40)
        self.assertTrue(again['already'])
        self.assertEqual(again['credited'], 0)
        self.assertEqual(st['wallets']['Ana'], eco.subunits(40))
        st['mined'] = eco.MAX_SUPPLY - eco.TREASURY - 2
        capped = eco.migrate_monedas(st, 'Beto', 9, now=50)
        self.assertEqual(capped['credited'], 2)
        self.assertEqual(st['migrations']['Beto']['requested'], 9)


class ServerGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, ROOT)
        import server
        cls.server = server

    def test_mint_requires_the_river_and_a_real_pan(self):
        s = self.server
        offset = json.load(open(os.path.join(ROOT, 'data', 'valle-offset.json'), encoding='utf-8'))
        dx, dy = offset['x'], offset['y']
        node = next(n for n in s.GOLD_NODES if n['id'] == 'oro_fluvial_1')
        self.assertEqual((node['x'], node['y']), (214 + dx, 54 + dy))
        self.assertIsNone(s.gold_node_for(227 + dx, 64 + dy, 'oro_fluvial_1'))
        self.assertIsNotNone(s.gold_node_for(node['x'] + 1, node['y'], 'oro_fluvial_1'))
        name = 'BateaPrueba'
        token = s.bind_wallet(name, '')
        before = float(s.ECON.get('mined') or 0)

        class Who:
            bot = True
            zone = 'city'
            x, y = 227 + dx, 64 + dy
            wallet_ok = True
            wallet_token = token
            name = 'BateaPrueba'
            last_mint = 0
        who = Who()
        s.mint_for(who, 'oro_fluvial_1')
        self.assertEqual(float(s.ECON.get('mined') or 0), before)
        who.x, who.y = node['x'] + 1, node['y']
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

    def test_foundry_needs_the_mine(self):
        s = self.server
        before = float(s.ECON.get('mined') or 0)
        who = s.Client(None)
        who.hello = True
        who.wallet_ok = True
        who.zone = 'city'
        who.name = 'Fundidor'
        s.smelt_for(who, 'mineral_cobre', 1)
        self.assertEqual(float(s.ECON.get('mined') or 0), before)


if __name__ == '__main__':
    unittest.main()
