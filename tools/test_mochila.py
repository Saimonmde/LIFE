# SPDX-License-Identifier: AGPL-3.0-or-later
"""La mochila llena no pierde ni duplica. El servidor manda."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy
import finca
import mochila
import purses
import trades
from trades import TradeError


class MochilaRules(unittest.TestCase):
    def test_a_new_item_needs_a_free_slot_and_more_of_the_same_does_not(self):
        items = {'cosa%02d' % i: 1 for i in range(mochila.SLOTS)}
        self.assertFalse(mochila.fits(items, 'extra', 1))
        self.assertTrue(mochila.fits(items, 'cosa00', 3))
        self.assertFalse(mochila.add(items, 'extra', 1))
        self.assertNotIn('extra', items)
        self.assertTrue(mochila.add(items, 'cosa00', 3))
        self.assertEqual(items['cosa00'], 4)


class TradeAndFarm(unittest.TestCase):
    def test_trade_refuses_a_full_bag_without_moving_anything(self):
        econ = economy.empty_state()
        econ['wallets'] = {'Ana': 10, 'Bea': 10}
        vault = {'purses': {
            'Ana': {'cosa%02d' % i: 1 for i in range(mochila.SLOTS)},
            'Bea': {'extra': 1},
        }}
        before = copy.deepcopy(vault)
        with self.assertRaises(TradeError) as caught:
            trades.apply_exchange(
                econ, vault, None, b'seed', 'Bea', 'Ana',
                {'smc': 0, 'smp': 0, 'cobre': 0, 'items': {'extra': 1}},
                {'smc': 0, 'smp': 0, 'cobre': 0, 'items': {}},
                'lleno',
            )
        self.assertEqual(str(caught.exception), 'Tu mochila está llena')
        self.assertEqual(vault, before)
        self.assertEqual(econ['wallets'], {'Ana': 10, 'Bea': 10})

    def test_a_full_hand_does_not_take_the_bag_out_of_the_bank(self):
        state = finca.empty_state()
        for i in range(mochila.SLOTS):
            state['bags']['X%d' % i] = {'owner': 'Ana', 'place': 'mochila', 'crop': 'x%d' % i, 'serial': 'X%d' % i}
        state['bags']['CAC'] = {'owner': 'Ana', 'place': 'banco', 'crop': 'cacao', 'serial': 'CAC', 'hash': '', 'chain': []}
        with self.assertRaises(finca.FincaError) as caught:
            finca.withdraw(state, {}, 'Ana', 'CAC', 1)
        self.assertEqual(str(caught.exception), 'Tu mochila está llena')
        self.assertEqual(state['bags']['CAC']['place'], 'banco')


class ServerPick(unittest.TestCase):
    def setUp(self):
        import server
        self.server = server
        self.sent = []
        self._send = server.send
        self._save_econ = server.save_econ
        self._save_vault = server.save_vault
        server.send = lambda _c, obj: self.sent.append(obj)
        server.save_econ = lambda: None
        server.save_vault = lambda: None
        self._econ = copy.deepcopy(server.ECON)
        self._vault = copy.deepcopy(server.VAULT_STATE)

    def tearDown(self):
        self.server.send = self._send
        self.server.save_econ = self._save_econ
        self.server.save_vault = self._save_vault
        self.server.ECON.clear()
        self.server.ECON.update(self._econ)
        self.server.VAULT_STATE.clear()
        self.server.VAULT_STATE.update(self._vault)

    def person(self):
        who = self.server.Client(None)
        who.hello = True
        who.zone = 'mine'
        who.name = 'Nica'
        who.user = {'id': 'cta-nica', 'name': 'Nica'}
        who.last_swing = 0
        who.pending_pick = None
        return who

    def test_a_full_server_bag_does_not_take_the_ore(self):
        who = self.person()
        purses.credit(self.server.VAULT_STATE, 'Nica', 'lleno', 1)
        for i in range(mochila.SLOTS - 1):
            purses.credit(self.server.VAULT_STATE, 'Nica', 'cosa%02d' % i, 1)
        before = self.server.ECON.get('crudo')
        self.server.swing_for(who, 'oro', 2)
        refused = next(item for item in self.sent if item.get('t') == 'mochila_llena')
        self.assertEqual(refused['reason'], 'Tu mochila está llena')
        self.assertEqual(self.server.ECON.get('crudo'), before)
        self.assertEqual(purses.count(self.server.VAULT_STATE, 'Nica', 'mineral_oro'), 0)
        self.server.mochila_op(who, 'banco')
        self.assertEqual(self.server.VAULT.account(self.server.VAULT_STATE, 'Nica')['items']['mineral_oro'], 2)
        self.server.mochila_op(who, 'banco')
        again = [item for item in self.sent if item.get('t') == 'mochila_op']
        self.assertFalse(again[-1]['ok'])
        self.assertEqual(self.server.VAULT.account(self.server.VAULT_STATE, 'Nica')['items']['mineral_oro'], 2)

    def test_staff_pick_is_stored_once(self):
        who = self.person()
        self.server.swing_for(who, 'cobre', 1)
        self.assertEqual(purses.count(self.server.VAULT_STATE, 'Nica', 'mineral_cobre'), 1)
        self.assertEqual(self.server.CRUDO.nuggets(self.server.ECON, 'cta-nica', 'mineral_cobre'), 1)


if __name__ == '__main__':
    unittest.main()
