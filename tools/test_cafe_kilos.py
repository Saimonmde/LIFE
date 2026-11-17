# SPDX-License-Identifier: AGPL-3.0-or-later
"""Café en kilos: lavar, secar, tostar y vender por SMC. No se crea masa."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy
import finca
import purses
import reloj

SECRET = 'CuentaAnaPrivada'


class Purse:
    def __init__(self):
        self.bal = {}
        self.minted = {'simoncoin': 100, 'simonplata': 50, 'simonchis': 7}
        self.foundry = {}

    def balance(self, coin, name):
        return int(self.bal.get((coin, name), 0))

    def move(self, coin, src, dst, amount):
        amount = int(amount)
        if amount <= 0 or self.balance(coin, src) < amount:
            return False
        self.bal[(coin, src)] = self.balance(coin, src) - amount
        self.bal[(coin, dst)] = self.balance(coin, dst) + amount
        return True

    def supply(self):
        sums = {'simoncoin': 0, 'simonplata': 0, 'simonchis': 0}
        for (coin, _name), value in self.bal.items():
            sums[coin] = sums.get(coin, 0) + int(value)
        return {
            'simoncoin': self.minted['simoncoin'],
            'simonplata': self.minted['simonplata'],
            'simonchis': self.minted['simonchis'],
            'simoncoinSum': sums['simoncoin'],
            'simonplataSum': sums['simonplata'],
            'simonchisSum': sums['simonchis'],
            'foundry': dict(self.foundry),
        }


class CafeKilosTests(unittest.TestCase):
    def setUp(self):
        self.config = finca.load_config()
        self.state = finca.empty_state()
        self.purse = Purse()
        self.purse.bal[('simoncoin', 'tesoro_genesis')] = 5_000 * economy.SUBS
        self.purse.bal[('simoncoin', self.config['buyer'])] = 500 * economy.SUBS
        self.now = 1_700_000_000

    def act(self, op, args=None, now=None, present=True, account=SECRET):
        return finca.act(
            self.state, self.purse, self.config, account, op, args or {},
            self.now if now is None else now, present=present,
        )

    def cereza(self, kg):
        self.act('ver')
        box = self.state['accounts'][SECRET]
        finca._add_kg(box, 'cafe_cereza', kg)
        return box

    def test_prices_are_only_smc(self):
        for crop in ('cafe', 'cacao'):
            prices = self.config['crops'][crop]['prices']
            self.assertEqual(set(prices), {'simoncoin'})
        self.assertEqual(economy.format_smc(economy.parse_amount('0.01 SMC')), '0,01 SMC')
        self.assertEqual(self.config['crops']['cafe']['tostadoPrice']['kg'], 14)
        self.assertEqual(self.config['crops']['cafe']['tostadoPrice']['simoncoin'], '0.01')

    def test_harvest_puts_cherry_kilos_in_the_inventory(self):
        plots = [row['id'] for row in self.act('ver')['view']['plots'] if row['crop'] == 'cafe']
        self.act('plantar', {'plot': plots[0]})
        self.now += 2 * reloj.REAL_SECONDS_PER_DAY + 5
        picked = self.act('recoger', {'crop': 'cafe'})
        self.assertTrue(picked['ok'], picked.get('error'))
        self.assertEqual(self.state['accounts'][SECRET]['goods']['cafe_cereza'], 1)
        self.assertEqual(self.state['accounts'][SECRET]['kilos']['cafe_cereza'], 94)
        self.assertEqual(picked['view']['kilos']['cafe_cereza'], 94)
        self.assertEqual(self.state['harvestedKg']['cafe'], 94)

    def test_each_step_spends_kilos_and_creates_none(self):
        self.cereza(105)
        before = 105
        washed = self.act('lavar', {'kg': 'todo'})
        self.assertTrue(washed['ok'], washed.get('error'))
        box = self.state['accounts'][SECRET]['kilos']
        self.assertEqual(box['cafe_cereza'], 0)
        self.assertEqual(box['cafe_lavado'], 42)
        self.assertLess(box['cafe_lavado'], before)
        dried = self.act('secar', {'kg': 42})
        self.assertTrue(dried['ok'], dried.get('error'))
        self.assertEqual(box['cafe_lavado'], 0)
        self.assertEqual(box['cafe_pergamino'], 21)
        self.assertLess(box['cafe_pergamino'], 42)
        roasted = self.act('tostar', {'kg': 21})
        self.assertTrue(roasted['ok'], roasted.get('error'))
        self.assertEqual(box['cafe_pergamino'], 0)
        self.assertEqual(box['cafe_tostado'], 14)
        self.assertLess(box['cafe_tostado'], 21)
        self.assertLess(box['cafe_tostado'], before)
        self.assertEqual(self.state['harvestedKg']['cafe'], 0)

    def test_steps_reject_distance_and_short_input(self):
        box = self.cereza(4)
        away = self.act('lavar', {'kg': 5}, present=False)
        self.assertFalse(away['ok'])
        self.assertIn('Las Palmas', away['error'])
        self.assertEqual(box['kilos']['cafe_cereza'], 4)
        short = self.act('lavar', {'kg': 5})
        self.assertFalse(short['ok'])
        self.assertEqual(box['kilos']['cafe_cereza'], 4)
        odd = self.act('lavar', {'kg': 6})
        self.assertFalse(odd['ok'])
        self.assertEqual(box['kilos']['cafe_cereza'], 4)
        self.act('lavar', {'kg': 'todo'})
        self.assertEqual(box['kilos']['cafe_cereza'], 4)
        self.assertEqual(box['kilos']['cafe_lavado'], 0)
        dry = self.act('secar', {'kg': 2})
        self.assertFalse(dry['ok'])
        self.assertEqual(box['kilos']['cafe_pergamino'], 0)
        roast = self.act('tostar', {'kg': 3})
        self.assertFalse(roast['ok'])
        self.assertEqual(box['kilos']['cafe_tostado'], 0)

    def test_partial_wash_blocks_the_sack_from_the_same_cherries(self):
        self.act('ver')
        box = self.state['accounts'][SECRET]
        box['goods']['cafe_cereza'] = 10
        finca._add_kg(box, 'cafe_cereza', 940)
        spent = self.act('lavar', {'kg': 5})
        self.assertTrue(spent['ok'], spent.get('error'))
        self.assertEqual(box['kilos']['cafe_cereza'], 935)
        blocked = self.act('procesar', {'crop': 'cafe'})
        self.assertFalse(blocked['ok'])
        self.assertIn('lavaron', blocked['error'])
        self.assertEqual(box['goods']['cafe_cereza'], 10)
        self.assertEqual(box['kilos']['cafe_cereza'], 935)
        self.assertEqual(self.state['processedBags']['cafe'], 0)

    def test_a_full_sack_batch_still_uses_the_cherry_kilos(self):
        self.act('ver')
        box = self.state['accounts'][SECRET]
        box['goods']['cafe_cereza'] = 10
        finca._add_kg(box, 'cafe_cereza', 940)
        started = self.act('procesar', {'crop': 'cafe'})
        self.assertTrue(started['ok'], started.get('error'))
        self.assertEqual(box['goods']['cafe_cereza'], 0)
        self.assertEqual(box['kilos']['cafe_cereza'], 0)
        self.assertIn('cafe', box['batches'])

    def test_roasted_kilos_sell_for_smc_and_hit_the_ledger_and_the_cap(self):
        box = self.cereza(0)
        finca._add_kg(box, 'cafe_tostado', 28)
        buyer = self.config['buyer']
        before_buyer = self.purse.balance('simoncoin', buyer)
        before_mint = self.minted_copy()
        mark = finca.supply_fingerprint(self.purse.supply())
        short = self.act('vender_kg', {'kg': 10})
        self.assertFalse(short['ok'])
        self.assertEqual(box['kilos']['cafe_tostado'], 28)
        away = self.act('vender_kg', {'kg': 14}, present=False)
        self.assertFalse(away['ok'])
        self.assertEqual(box['kilos']['cafe_tostado'], 28)
        sold = self.act('vender_kg', {'kg': 14})
        self.assertTrue(sold['ok'], sold.get('error'))
        self.assertEqual(box['kilos']['cafe_tostado'], 14)
        self.assertEqual(self.purse.balance('simoncoin', SECRET), 1)
        self.assertEqual(self.purse.balance('simoncoin', buyer), before_buyer - 1)
        self.assertEqual(self.purse.minted, before_mint)
        self.assertEqual(finca.supply_fingerprint(self.purse.supply()), mark)
        self.assertEqual(sold['sales'][0]['coin'], 'SMC')
        self.assertEqual(sold['sales'][0]['amountSubs'], 1)
        self.assertNotIn('simonplata', sold['sales'][0])
        self.assertIn('0,01 SMC', sold['note'])
        book = economy.empty_state()
        economy.append_tx(book, sold['sales'][0], now=self.now)
        notes = [tx.get('note') for tx in book.get('mempool') or []]
        notes += [tx.get('note') for block in book.get('blocks') or [] for tx in block.get('txs') or []]
        self.assertIn('Compra de 14 kg de café tostado.', notes)
        self.assertEqual(sold['sales'][0]['amountSubs'], 1)
        self.purse.bal[('simoncoin', SECRET)] = economy.MAX_SMH
        capped = self.act('vender_kg', {'kg': 14})
        self.assertFalse(capped['ok'])
        self.assertIn('21.000.000', capped['error'])
        self.assertEqual(box['kilos']['cafe_tostado'], 14)
        self.assertEqual(self.purse.balance('simoncoin', buyer), before_buyer - 1)
        self.assertEqual(self.purse.minted, before_mint)

    def minted_copy(self):
        return dict(self.purse.minted)

    def test_old_cherry_counts_migrate_once_and_sacks_stay(self):
        state = {
            'accounts': {
                'Ana': {
                    'goods': {'cafe_cereza': 3, 'cacao_baba': 2},
                    'batches': {},
                    'plots': {},
                },
            },
            'bags': {
                'CAF-viejo': {
                    'serial': 'CAF-viejo', 'crop': 'cafe', 'kg': 70,
                    'owner': 'Ana', 'place': 'mochila', 'product': 'Café excelso',
                },
            },
            'harvestedKg': {'cafe': 282, 'cacao': 180},
        }
        loaded = finca.normalize(state)
        self.assertEqual(loaded['kilosV'], 0)
        self.assertTrue(finca.migrate_kilos(loaded, self.config))
        self.assertEqual(loaded['accounts']['Ana']['kilos']['cafe_cereza'], 282)
        self.assertEqual(loaded['accounts']['Ana']['goods']['cafe_cereza'], 3)
        self.assertEqual(loaded['accounts']['Ana']['goods']['cacao_baba'], 2)
        self.assertEqual(loaded['bags']['CAF-viejo']['kg'], 70)
        self.assertEqual(loaded['bags']['CAF-viejo']['place'], 'mochila')
        loaded['accounts']['Ana']['kilos']['cafe_cereza'] = 10
        self.assertFalse(finca.migrate_kilos(loaded, self.config))
        self.assertEqual(loaded['accounts']['Ana']['kilos']['cafe_cereza'], 10)
        self.assertEqual(loaded['bags']['CAF-viejo']['kg'], 70)

    def test_roasted_kilos_can_be_traded_without_creating_any(self):
        state = finca.empty_state()
        state['accounts']['Ana'] = {
            'goods': {}, 'batches': {}, 'plots': {}, 'soldDay': 0, 'soldCount': 0,
            'kilos': {'cafe_tostado': 4},
            'kilosBanco': {'cafe_tostado': 8},
        }
        state['accounts']['Luis'] = {
            'goods': {}, 'batches': {}, 'plots': {}, 'soldDay': 0, 'soldCount': 0,
        }
        vault = {'purses': {'Ana': {}, 'Luis': {}}}
        offer = {'items': {'cafe_tostado': 10, 'bolsa_cafe': 1}}
        finca.alinear_kilos(state, vault, 'Ana', offer)
        self.assertEqual(state['accounts']['Ana']['kilos']['cafe_tostado'], 10)
        self.assertEqual(state['accounts']['Ana']['kilosBanco']['cafe_tostado'], 2)
        self.assertEqual(purses.count(vault, 'Ana', 'cafe_tostado'), 10)
        purses.debit(vault, 'Ana', 'cafe_tostado', 10)
        purses.credit(vault, 'Luis', 'cafe_tostado', 10)
        finca.entregar_kilos(state, 'Ana', 'Luis', offer)
        self.assertEqual(state['accounts']['Ana']['kilos']['cafe_tostado'], 0)
        self.assertEqual(state['accounts']['Ana']['kilosBanco']['cafe_tostado'], 2)
        self.assertEqual(state['accounts']['Luis']['kilos']['cafe_tostado'], 10)
        self.assertEqual(
            state['accounts']['Ana']['kilos']['cafe_tostado']
            + state['accounts']['Ana']['kilosBanco']['cafe_tostado']
            + state['accounts']['Luis']['kilos']['cafe_tostado'],
            12,
        )
        missing = {'items': {'cafe_tostado': 9}}
        with self.assertRaises(finca.FincaError):
            finca.entregar_kilos(state, 'Ana', 'Luis', missing)

    def test_cacao_export_pays_smc_and_does_not_mint(self):
        self.act('ver')
        serial = 'CAC-TEST'
        self.state['bags'][serial] = {
            'serial': serial, 'crop': 'cacao', 'kg': 150, 'product': 'Cacao seco',
            'owner': SECRET, 'place': 'mochila', 'hash': 'abc', 'chain': [],
        }
        before = self.minted_copy()
        mark = finca.supply_fingerprint(self.purse.supply())
        exported = self.act('exportar', {'crop': 'cacao'})
        self.assertTrue(exported['ok'], exported.get('error'))
        self.assertEqual(exported['exports'][0]['coin'], 'simoncoin')
        self.assertGreater(exported['exports'][0]['amount'], 0)
        self.assertEqual(self.state['bags'][serial]['place'], 'vendido')
        self.assertEqual(self.purse.minted, before)
        self.assertEqual(finca.supply_fingerprint(self.purse.supply()), mark)
        self.assertEqual(self.purse.balance('simonplata', SECRET), 0)


if __name__ == '__main__':
    unittest.main()
