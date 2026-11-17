# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tocar a otra persona abre la ficha. El intercambio no crea monedas."""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))


def read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as handle:
        return handle.read()


class FichaTests(unittest.TestCase):
    def test_tap_opens_the_card_and_trade_stays_the_old_one(self):
        page = read('play/index.html')
        card = read('play/ficha.js')
        world = read('play/unified3d.js')
        people = read('play/vida.js')
        trades = read('tools/trades.py')
        self.assertIn('ficha.js?v=ficha-trueque', page)
        self.assertIn('id="ficha-cambiar"', card)
        self.assertIn('Trueque', card)
        self.assertIn('TradeUI.openTrade', card)
        self.assertNotIn('eco.issue', card)
        self.assertIn('Ficha.open', world)
        self.assertIn('Ficha.open(row)', people)
        self.assertIn('se mueve el saldo', trades)
        self.assertIn("t:'trade_start'", trades.replace(' ', ''))
