# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conversión de metal a moneda y el tope del día."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import topes


class ConversionTests(unittest.TestCase):
    def test_five_nuggets_make_one_simoncoin(self):
        quote = topes.cotizar(5, 5, 1, 21_000_000)
        self.assertEqual(quote['alcanzan'], 1)
        self.assertEqual(quote['recibes'], 1)
        self.assertEqual(quote['gastas'], 5)
        self.assertEqual(quote['sobran'], 0)

    def test_daily_cap_beats_a_full_bag(self):
        quote = topes.cotizar(100, 5, 0.25, 21_000_000)
        self.assertEqual(quote['alcanzan'], 20)
        self.assertEqual(quote['gastas'], 1)
        self.assertAlmostEqual(quote['recibes'], 0.2)
        self.assertEqual(quote['sobran'], 99)

    def test_global_cap_can_stop_the_mint(self):
        quote = topes.cotizar(100, 5, 6.25, 0.1)
        self.assertEqual(quote['gastas'], 0)
        self.assertEqual(quote['recibes'], 0)
        self.assertEqual(quote['sobran'], 100)

    def test_silver_and_copper_use_their_rates(self):
        silver = topes.cotizar(8, topes.DEFAULT_PLATA_POR_MONEDA, 5, 84_000_000, pieces=8)
        self.assertEqual(silver['recibes'], 2)
        self.assertEqual(silver['gastas'], 8)
        copper = topes.cotizar(9, topes.DEFAULT_COBRE_POR_MONEDA, 200, 333_000_000, pieces=7, whole=True)
        self.assertEqual(copper['gastas'], 6)
        self.assertEqual(copper['recibes'], 2)
        self.assertEqual(copper['sobran'], 3)

    def test_defaults_match_the_reference_caps(self):
        self.assertEqual(topes.simoncoin_daily_smh(0, 0, 0), int(0.25 * topes.SUBS))
        full = 60 * 86400, 40 * 3600, 10
        self.assertEqual(topes.simoncoin_daily_smh(*full), int(6.25 * topes.SUBS))
        self.assertEqual(topes.simonplata_daily_sph(0, 0, 0), 5 * topes.SUBS)
        self.assertEqual(topes.simonchis_daily(), 200)

    def test_reset_is_the_next_utc_midnight(self):
        noon = 1_700_000_000
        nxt = topes.next_reset(noon)
        self.assertEqual(nxt % topes.DAY, 0)
        self.assertGreater(nxt, noon)
        self.assertLessEqual(nxt - noon, topes.DAY)
        self.assertIn('00:00 UTC', topes.RESET_LABEL)
        self.assertIn('7:00 p. m.', topes.RESET_LABEL)

    def test_env_can_change_the_gold_rate(self):
        old = os.environ.get('MINT_ORO_POR_MONEDA')
        os.environ['MINT_ORO_POR_MONEDA'] = '10'
        try:
            self.assertEqual(topes.rate('simoncoin'), 10)
            quote = topes.cotizar(10, topes.rate('simoncoin'), 1, 100)
            self.assertEqual(quote['recibes'], 1)
            self.assertEqual(quote['gastas'], 10)
        finally:
            if old is None:
                os.environ.pop('MINT_ORO_POR_MONEDA', None)
            else:
                os.environ['MINT_ORO_POR_MONEDA'] = old


if __name__ == '__main__':
    unittest.main()
