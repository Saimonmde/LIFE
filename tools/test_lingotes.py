# SPDX-License-Identifier: AGPL-3.0-or-later
"""El horno no funde lingotes. El Banco Central sí, y sólo para el dueño o el personal."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fusion
import lingotes
import server


class LingoteRules(unittest.TestCase):
    def test_player_is_refused_and_owner_gets_a_serial(self):
        state = {}
        player = {'email': 'alguien@ejemplo.co', 'role': 'player'}
        self.assertFalse(lingotes.autorizado(player))
        self.assertIn('no está abierta', lingotes.rechazar(player, 'central'))
        owner = {'email': fusion.owner_email(), 'role': 'player'}
        self.assertEqual(lingotes.rechazar(owner, 'mine'), 'Los lingotes se funden en el Banco Central.')
        self.assertEqual(lingotes.rechazar(owner, 'central'), '')
        staff = {'email': 'mesa@ejemplo.co', 'role': 'staff'}
        done = lingotes.fundir(state, 'Simon', 'oro', 2, 1_700_000_000)
        self.assertEqual(done['serials'], ['LGO-000001', 'LGO-000002'])
        self.assertEqual(done['reserve']['oro'], 2)
        self.assertEqual(state['foundry']['minted']['lingote_oro'], 2)
        self.assertEqual(len(state['foundry']['history']), 1)
        self.assertTrue(lingotes.autorizado(staff))
        again = lingotes.fundir(state, 'Mesa', 'oro', 1, 1_700_000_100)
        self.assertEqual(again['serials'], ['LGO-000003'])
        self.assertEqual(lingotes.reserva(state)['oro'], 3)

    def test_quantity_and_metal_are_checked(self):
        state = {}
        with self.assertRaises(ValueError):
            lingotes.fundir(state, 'Simon', 'oro', 0, 1)
        with self.assertRaises(ValueError):
            lingotes.fundir(state, 'Simon', 'hierro', 1, 1)


class LingoteServer(unittest.TestCase):
    def setUp(self):
        self.server = server
        self.sent = []
        self._send = server.send
        self._save = server.save_econ
        server.send = lambda _c, obj: self.sent.append(obj)
        server.save_econ = lambda: None
        self._econ = copy.deepcopy(server.ECON)

    def tearDown(self):
        server.send = self._send
        server.save_econ = self._save
        server.ECON.clear()
        server.ECON.update(self._econ)

    def person(self, email, role, zone):
        who = server.Client(None)
        who.hello = True
        who.wallet_ok = True
        who.zone = zone
        who.name = 'Cajero'
        who.user = {'id': 'cta', 'email': email, 'role': role, 'name': 'Cajero'}
        who.ip = '198.51.100.20'
        return who

    def test_furnace_rejects_a_normal_player(self):
        who = self.person('alguien@ejemplo.co', 'player', 'mine')
        before = copy.deepcopy((server.ECON.get('foundry') or {}).get('minted') or {})
        server.smelt_for(who, 'mineral_oro', 2, mode='ingot')
        result = next(item for item in self.sent if item.get('t') == 'smelt_result')
        self.assertFalse(result['ok'])
        self.assertIn('horno', result['reason'])
        self.assertEqual((server.ECON.get('foundry') or {}).get('minted') or {}, before)
        self.sent.clear()
        server.lingote_for(who, 'oro', 1)
        closed = next(item for item in self.sent if item.get('t') == 'lingote_result')
        self.assertFalse(closed['ok'])
        self.assertIn('no está abierta', closed['reason'])

    def test_owner_mints_only_at_the_central_bank(self):
        who = self.person(fusion.owner_email(), 'player', 'mine')
        server.lingote_for(who, 'plata', 1)
        refused = next(item for item in self.sent if item.get('t') == 'lingote_result')
        self.assertFalse(refused['ok'])
        self.assertIn('Banco Central', refused['reason'])
        who.zone = 'central'
        self.sent.clear()
        server.lingote_for(who, 'plata', 1)
        ok = next(item for item in self.sent if item.get('t') == 'lingote_result')
        self.assertTrue(ok['ok'])
        self.assertEqual(ok['serials'], ['LGP-000001'])
        self.assertEqual(ok['reserve']['plata'], 1)
        self.assertEqual(ok['item'], 'lingote_plata')
        coins = {row['id'] for row in ok['ledger']['coins']}
        self.assertEqual(coins, {'simoncoin', 'simonplata', 'simonchis'})


if __name__ == '__main__':
    unittest.main()
