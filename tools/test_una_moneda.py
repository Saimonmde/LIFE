# SPDX-License-Identifier: AGPL-3.0-or-later
"""La plata, el cobre y el mineral de oro pasan a Simoncoin. El SMC que ya existe no."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as eco
import plata
import una_moneda as una


def _econ():
    state = eco.empty_state()
    state['minedSmh'] = 0
    state['plata'] = {'wallets': {}, 'txs': [], 'minedSph': 0}
    state['simonchis'] = {'wallets': {}, 'minted': 0}
    state['crudo'] = {}
    return state


class ConversionTests(unittest.TestCase):
    def test_rates_floor_to_two_decimals_and_leave_smc_alone(self):
        econ = _econ()
        eco.credit(econ, 'Ana', 5 * eco.SUBS)
        antes = econ['wallets']['Ana']
        econ['plata']['wallets']['Ana'] = 2 * plata.SUBS + 100
        econ['plata']['txs'] = [{'type': 'mint', 'to': 'Ana', 'amountSph': 100}]
        econ['simonchis']['wallets']['Ana'] = 2500
        econ['crudo']['cuenta-ana'] = {'mineral_oro': 3 * 1000, 'mineral_plata': 4 * 1000, 'mineral_cobre': 9 * 1000}
        accounts = {'users': [{'id': 'cuenta-ana', 'wallet_name': 'Ana'}]}
        plan = una.preview(econ, {'accounts': {}, 'purses': {}}, accounts)
        self.assertTrue(plan['ok'])
        ana = next(row for row in plan['filas'] if row['cuenta'] == 'Ana')
        # 2 SMP * 0,01 = 0,02. 100 unidades viejas no llegan a 0,01.
        # 2500 cobres * 0,001 = 2,5. 3 oros * 0,1 = 0,3. 4 platas * 0,01 = 0,04. 9 cobres mineral * 0,001 = 0,009.
        # Suma exacta 0,02+2,5+0,3+0,04+0,009 = 2,869 → baja a 2,86.
        self.assertEqual(ana['smc'], 2.86)
        self.assertAlmostEqual(ana['descartado'], 0.009, places=6)
        self.assertEqual(len(plan['bug118']), 1)
        self.assertEqual(plan['bug118'][0]['unidades'], 100)
        result = una.aplicar(econ, {'accounts': {}, 'purses': {}}, accounts, now=10)
        self.assertEqual(result['estado'], 'hecha')
        self.assertEqual(econ['wallets']['Ana'], antes + int(2.86 * eco.SUBS))
        self.assertEqual(econ['plata']['wallets']['Ana'], 0)
        self.assertEqual(econ['simonchis']['wallets']['Ana'], 0)
        self.assertEqual(econ['crudo']['cuenta-ana']['mineral_oro'], 0)
        otra = una.aplicar(econ, {'accounts': {}, 'purses': {}}, accounts, now=11)
        self.assertEqual(otra['estado'], 'ya')
        self.assertEqual(econ['wallets']['Ana'], antes + int(2.86 * eco.SUBS))
        self.assertEqual(eco.MAX_SUPPLY, 21_000_000)

    def test_cap_blocks_every_balance(self):
        econ = _econ()
        econ['minedSmh'] = (eco.MAX_SUPPLY - eco.TREASURY) * eco.SUBS
        econ['plata']['wallets']['Ana'] = 1 * plata.SUBS
        antes = dict(econ['plata']['wallets'])
        result = una.aplicar(econ, {'accounts': {}, 'purses': {}}, {'users': []}, now=1)
        self.assertEqual(result['estado'], 'bloqueada')
        self.assertEqual(econ['plata']['wallets'], antes)
        self.assertNotIn('Ana', econ['wallets'])


if __name__ == '__main__':
    unittest.main()
