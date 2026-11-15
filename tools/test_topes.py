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
        self.assertAlmostEqual(quote['recibes'], 0.25)
        self.assertAlmostEqual(quote['gastas'], 1.25)
        self.assertAlmostEqual(quote['sobran'], 98.75)

    def test_two_nuggets_fill_the_quarter_cap(self):
        quote = topes.cotizar(2, 5, 0.25, 21_000_000)
        self.assertAlmostEqual(quote['recibes'], 0.25)
        self.assertAlmostEqual(quote['gastas'], 1.25)

    def test_global_cap_can_stop_the_mint(self):
        quote = topes.cotizar(100, 5, 6.25, 0)
        self.assertEqual(quote['gastas'], 0)
        self.assertEqual(quote['recibes'], 0)
        self.assertEqual(quote['sobran'], 100)

    def test_a_small_global_remainder_is_still_mintable(self):
        quote = topes.cotizar(100, 5, 6.25, 0.1)
        self.assertAlmostEqual(quote['recibes'], 0.1)
        self.assertAlmostEqual(quote['gastas'], 0.5)

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


class LetreroTests(unittest.TestCase):
    def test_sign_text_comes_from_the_real_caps(self):
        import economy
        import plata
        import cobre
        board = topes.letrero()
        text = '\n'.join(board['lines'])
        self.assertIn('Picar no tiene tope.', text)
        self.assertIn('Podés picar las veces que quieras.', text)
        self.assertIn('vuelve en ' + topes._cantidad(topes.VEIN_ORO_S) + ' segundos.', text)
        self.assertIn('La plata vuelve en ' + topes._cantidad(topes.VEIN_PLATA_S) + ' segundos', text)
        self.assertIn('el cobre en ' + topes._cantidad(topes.VEIN_COBRE_S) + ' segundos.', text)
        game = open(os.path.join(os.path.dirname(__file__), '..', 'play', 'game.js'), encoding='utf-8').read()
        self.assertIn("respawnMs:metal==='oro'?%d:%d" % (topes.VEIN_ORO_S * 1000, topes.VEIN_PLATA_S * 1000), game)
        self.assertIn(str(topes.rate('simoncoin')) + ' oros crudos hacen 1 Simoncoin.', text)
        self.assertIn(str(topes.rate('simonplata')) + ' de plata cruda hacen 1 Simonplata.', text)
        self.assertIn(str(topes.rate('simonchis')) + ' de cobre crudo hacen 1 Simonchis.', text)
        base = topes.simoncoin_daily_smh(0, 0, 0) / topes.SUBS
        top = topes.simoncoin_daily_smh(60 * 86400, 40 * 3600, 10) / topes.SUBS
        self.assertIn(topes._cantidad(base), text)
        self.assertIn(topes._cantidad(top), text)
        self.assertIn(topes._cantidad(topes.simonplata_daily_sph(0, 0, 0) / topes.SUBS), text)
        self.assertIn(topes._cantidad(topes.simonchis_daily()), text)
        self.assertIn(topes.RESET_LABEL, text)
        self.assertIn(topes._cantidad(economy.MAX_SUPPLY), text)
        self.assertIn(topes._cantidad(plata.MAX_SUPPLY), text)
        self.assertIn(topes._cantidad(cobre.MAX_SUPPLY), text)
        self.assertIn('sube hasta ' + topes._cantidad(top) + ' con recompensas', text)
        self.assertIn('más bonos:', text)
        self.assertIn('Con esos bonos sube hasta ' + topes._cantidad(topes.simonplata_daily_sph(60 * 86400, 40 * 3600, 10) / topes.SUBS), text)
        self.assertNotIn('21.000.000', '\n'.join(open(os.path.join(os.path.dirname(__file__), '..', 'play', 'letrero.js'), encoding='utf-8').read().split('fetch')[0]))

    def test_sign_follows_an_env_change_and_shows_what_is_left_today(self):
        old = os.environ.get('MINT_SIMONCHIS_DAILY')
        os.environ['MINT_SIMONCHIS_DAILY'] = '123'
        try:
            text = '\n'.join(topes.letrero()['lines'])
            self.assertIn('123 al día', text)
        finally:
            if old is None:
                os.environ.pop('MINT_SIMONCHIS_DAILY', None)
            else:
                os.environ['MINT_SIMONCHIS_DAILY'] = old
        base = topes.simoncoin_daily_smh(0, 0, 0) / topes.SUBS
        plata_base = topes.simonplata_daily_sph(0, 0, 0) / topes.SUBS
        chis = topes.simonchis_daily()
        left = topes.hoy({
            'simoncoin': {'name': 'Simoncoin', 'left': base},
            'simonplata': {'name': 'Simonplata', 'left': plata_base},
            'simonchis': {'name': 'Simonchis', 'left': chis},
        })
        self.assertEqual(left[0], 'Hoy te quedan ' + topes._cantidad(base) + ' Simoncoin.')
        self.assertIn('Hoy te quedan ' + topes._cantidad(plata_base) + ' Simonplata.', left)
        self.assertIn('Hoy te quedan ' + topes._cantidad(chis) + ' Simonchis.', left)

    def test_next_reward_step_and_daily_reset_come_from_the_growth_rules(self):
        steps = topes.siguiente(0, 0, 0)
        edad = next(step for step in steps if step['kind'] == 'edad')
        self.assertEqual(edad['wait'], topes.DAY)
        delta = topes.simoncoin_daily_smh(topes.DAY, 0, 0) / topes.SUBS - topes.simoncoin_daily_smh(0, 0, 0) / topes.SUBS
        self.assertAlmostEqual(edad['simoncoin'], delta)
        juego = next(step for step in steps if step['kind'] == 'juego')
        self.assertEqual(juego['wait'], 3600)
        mision = next(step for step in steps if step['kind'] == 'mision')
        self.assertIsNone(mision['wait'])
        full_age = topes.DEFAULT_AGE_DAYS * topes.DAY
        full_play = topes.DEFAULT_PLAY_HOURS * 3600
        done = topes.siguiente(full_age, full_play, topes.DEFAULT_QUEST_CAP)
        self.assertEqual(done[0]['kind'], 'listo')
        moment = 1_700_000_000
        board = topes.letrero(0, 0, 0, moment)
        self.assertEqual(board['resetAt'], topes.next_reset(moment))
        self.assertTrue(any('peldaño' in step['text'] for step in board['steps']))
        script = open(os.path.join(os.path.dirname(__file__), '..', 'play', 'letrero.js'), encoding='utf-8').read()
        self.assertIn('resetAt', script)
        self.assertIn('setInterval(paint, 1000)', script)
        mesh = open(os.path.join(os.path.dirname(__file__), '..', 'play', 'letrero3d.js'), encoding='utf-8').read()
        self.assertIn('CylinderGeometry', mesh)
        self.assertIn('UnifrakturMaguntia', mesh)
        self.assertIn('BoxGeometry', mesh)


if __name__ == '__main__':
    unittest.main()
