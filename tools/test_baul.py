# SPDX-License-Identifier: AGPL-3.0-or-later
"""El baúl mueve lo de esa cuenta, una sola vez, sin copiarlo."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baul
import purses
import vault


class ChestTests(unittest.TestCase):
    def setUp(self):
        self.state = vault.empty()

    def test_deposit_and_withdraw_are_atomic_and_private(self):
        purses.credit(self.state, 'Ana', 'mineral_oro', 3)
        moved = baul.mover(self.state, 'Ana', 'deposit', 'mineral_oro', 2, 'pase-1', now=10)
        self.assertTrue(moved['ok'])
        self.assertFalse(moved['dup'])
        self.assertEqual(purses.count(self.state, 'Ana', 'mineral_oro'), 1)
        self.assertEqual(moved['account']['items']['mineral_oro'], 2)
        again = baul.mover(self.state, 'Ana', 'deposit', 'mineral_oro', 2, 'pase-1', now=11)
        self.assertTrue(again['dup'])
        self.assertEqual(purses.count(self.state, 'Ana', 'mineral_oro'), 1)
        self.assertEqual(vault.account(self.state, 'Ana')['items']['mineral_oro'], 2)
        short = baul.mover(self.state, 'Ana', 'deposit', 'mineral_oro', 5, 'pase-2', now=12)
        self.assertFalse(short['ok'])
        self.assertEqual(vault.account(self.state, 'Ana')['items']['mineral_oro'], 2)
        out = baul.mover(self.state, 'Ana', 'withdraw', 'mineral_oro', 2, 'pase-3', now=13)
        self.assertTrue(out['ok'])
        self.assertEqual(purses.count(self.state, 'Ana', 'mineral_oro'), 3)
        self.assertNotIn('mineral_oro', vault.account(self.state, 'Ana')['items'])
        stolen = baul.mover(self.state, 'Sol', 'withdraw', 'mineral_oro', 1, 'pase-4', now=14)
        self.assertFalse(stolen['ok'])
        self.assertEqual(purses.count(self.state, 'Ana', 'mineral_oro'), 3)
        self.assertEqual(vault.account(self.state, 'Sol')['items'], {})

    def test_a_double_click_without_a_new_token_does_not_duplicate(self):
        purses.credit(self.state, 'Ana', 'mineral_plata', 4)
        baul.mover(self.state, 'Ana', 'deposit', 'mineral_plata', 1, 'a', now=20)
        dup = baul.mover(self.state, 'Ana', 'deposit', 'mineral_plata', 1, 'b', now=20.2)
        self.assertTrue(dup['dup'])
        self.assertEqual(vault.account(self.state, 'Ana')['items']['mineral_plata'], 1)
        self.assertEqual(self.state['accounts']['Ana']['log'][-1]['op'], 'deposit')

    def test_server_uses_the_session_name(self):
        page = open(os.path.join(os.path.dirname(__file__), '..', 'server.py'), encoding='utf-8').read()
        self.assertIn('BAUL.mover(VAULT_STATE, sender.name', page)


if __name__ == '__main__':
    unittest.main()
