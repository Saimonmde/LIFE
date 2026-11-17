# SPDX-License-Identifier: AGPL-3.0-or-later
"""Monedas físicas de plata y de cobre. El libro mayor no las anota."""
import os
import unittest

import piezas
import purses

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))


class PiezaTests(unittest.TestCase):
    def setUp(self):
        self.econ = {'crudo': {}}
        self.vault = {'accounts': {}, 'purses': {}}

    def test_four_silver_minerals_make_one_coin_and_skip_the_ledger(self):
        import crudo
        before = int(self.econ.get('minedSmh') or 0)
        crudo.credit(self.econ, 'ana', 'mineral_plata', 4, cap=4)
        done = piezas.acuñar_crudo(self.econ, self.vault, 'ana', 'Ana', 'plata', 4)
        self.assertTrue(done['ok'], done.get('reason'))
        self.assertEqual(done['item'], 'moneda_plata')
        self.assertEqual(done['qty'], 1)
        self.assertEqual(purses.count(self.vault, 'Ana', 'moneda_plata'), 1)
        self.assertEqual(crudo.nuggets(self.econ, 'ana', 'mineral_plata'), 0)
        self.assertEqual(int(self.econ.get('minedSmh') or 0), before)

    def test_three_copper_minerals_make_one_coin(self):
        import crudo
        crudo.credit(self.econ, 'ana', 'mineral_cobre', 3, cap=4)
        done = piezas.acuñar_crudo(self.econ, self.vault, 'ana', 'Ana', 'cobre', 3)
        self.assertTrue(done['ok'], done)
        self.assertEqual(done['qty'], 1)
        self.assertEqual(purses.count(self.vault, 'Ana', 'moneda_cobre'), 1)

    def test_short_copper_does_not_mint(self):
        import crudo
        crudo.credit(self.econ, 'ana', 'mineral_cobre', 2, cap=4)
        done = piezas.acuñar_crudo(self.econ, self.vault, 'ana', 'Ana', 'cobre', 2)
        self.assertFalse(done['ok'])
        self.assertEqual(crudo.nuggets(self.econ, 'ana', 'mineral_cobre'), 2)
        self.assertEqual(purses.count(self.vault, 'Ana', 'moneda_cobre'), 0)

    def test_one_ingot_makes_one_coin(self):
        purses.credit(self.vault, 'Ana', 'lingote_plata', 1)
        done = piezas.acuñar_lingote(self.vault, 'Ana', 'plata', 1)
        self.assertTrue(done['ok'], done)
        self.assertEqual(purses.count(self.vault, 'Ana', 'lingote_plata'), 0)
        self.assertEqual(purses.count(self.vault, 'Ana', 'moneda_plata'), 1)
        self.assertIn('lingote', done['reason'])

    def test_redeem_uses_the_mineral_inside_and_floors(self):
        self.assertEqual(piezas.smh_de('plata', 1), 4)
        self.assertEqual(piezas.smh_de('cobre', 1), 0)
        self.assertEqual(piezas.smh_de('cobre', 4), 1)
        purses.credit(self.vault, 'Ana', 'moneda_cobre', 1)
        corto = piezas.preparar_canje(self.vault, 'Ana', 'cobre', 1)
        self.assertFalse(corto['ok'])
        self.assertEqual(purses.count(self.vault, 'Ana', 'moneda_cobre'), 1)

    def test_icons_and_categories_are_distinct(self):
        colores = []
        for metal in ('oro', 'plata', 'cobre'):
            with open(os.path.join(ROOT, 'graphics', 'mining', 'mineral_%s.svg' % metal), encoding='utf-8') as handle:
                colores.append(handle.read().split('stop-color="')[1].split('"')[0])
        self.assertEqual(len(set(colores)), 3)
        with open(os.path.join(ROOT, 'play', 'baul.js'), encoding='utf-8') as handle:
            baul = handle.read()
        self.assertIn('Monedas acuñadas', baul)
        self.assertIn('moneda_plata', baul)
        self.assertIn('moneda_cobre', baul)
        with open(os.path.join(ROOT, 'play', 'objeto.js'), encoding='utf-8') as handle:
            ficha = handle.read()
        self.assertIn('Examinar', ficha)
        self.assertIn('Soltar', ficha)
        self.assertIn('El Simoncoin no se suelta', ficha)


if __name__ == '__main__':
    unittest.main()
