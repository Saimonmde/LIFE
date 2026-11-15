# SPDX-License-Identifier: AGPL-3.0-or-later
"""El horno no funde lingotes. El Banco Central sí, y sólo para el dueño o el personal."""
import copy
import json
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
        with self.assertRaises(PermissionError):
            lingotes.fundir(state, 'Simon', 'oro', 2, 1_700_000_000)
        done = lingotes.fundir(state, 'Simon', 'oro', 2, 1_700_000_000, autorizado=True)
        self.assertEqual(done['serials'], ['LGO-000001', 'LGO-000002'])
        self.assertEqual(done['reserve']['oro'], 2)
        self.assertEqual(state['foundry']['minted']['lingote_oro'], 2)
        self.assertEqual(len(state['foundry']['history']), 1)
        self.assertEqual(state['foundry']['chain'][0]['prev'], lingotes.GENESIS)
        self.assertEqual(state['foundry']['chain'][1]['prev'], state['foundry']['chain'][0]['hash'])
        self.assertEqual(state['foundry']['head'], state['foundry']['chain'][1]['hash'])
        self.assertNotIn('by', state['foundry']['chain'][0])
        public = lingotes.publico(state)
        self.assertEqual(public['oro'], 2)
        self.assertEqual(public['head'], state['foundry']['head'])
        self.assertNotIn('by', public)
        self.assertTrue(lingotes.autorizado(staff))
        again = lingotes.fundir(state, 'Mesa', 'oro', 1, 1_700_000_100, autorizado=True)
        self.assertEqual(again['serials'], ['LGO-000003'])
        self.assertEqual(lingotes.reserva(state)['oro'], 3)
        self.assertEqual(lingotes.publico(state)['oro'], 3)

    def test_quantity_and_metal_are_checked(self):
        state = {}
        with self.assertRaises(ValueError):
            lingotes.fundir(state, 'Simon', 'oro', 0, 1, autorizado=True)
        with self.assertRaises(ValueError):
            lingotes.fundir(state, 'Simon', 'hierro', 1, 1, autorizado=True)


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
        self.assertEqual(ok['ledger']['ingots']['plata'], 1)
        self.assertTrue(ok['ledger']['ingots']['head'])
        self.assertNotIn('by', ok['ledger']['ingots'])
        public = server.public_counters()
        self.assertEqual(public['ingots']['plata'], 1)
        self.assertNotIn('Ana', json.dumps(public['ingots']))

    def test_staff_mints_and_a_player_cannot_enter(self):
        guest = self.person('alguien@ejemplo.co', 'player', 'city')
        self.assertEqual(server.zona_pedida(guest, 'central'), 'city')
        closed = next(item for item in self.sent if item.get('t') == 'central_result')
        self.assertFalse(closed['ok'])
        self.assertIn('recinto del personal', closed['reason'])
        self.assertTrue(lingotes.REFUSALS)
        self.sent.clear()
        staff = self.person('mesa@ejemplo.co', 'staff', 'city')
        self.assertEqual(server.zona_pedida(staff, 'central'), 'central')
        staff.zone = 'central'
        server.lingote_for(staff, 'cobre', 1)
        ok = next(item for item in self.sent if item.get('t') == 'lingote_result')
        self.assertTrue(ok['ok'])
        self.assertEqual(ok['ledger']['ingots']['cobre'], 1)
        self.sent.clear()
        server.acunar_for(guest, 'lingote_oro', 1)
        denied = next(item for item in self.sent if item.get('t') == 'acunar_result')
        self.assertFalse(denied['ok'])
        self.assertIn('no se acuñan', denied['reason'])
        self.assertEqual(server.ECON.get('foundry', {}).get('minted', {}).get('lingote_oro', 0), 0)

    def test_trade_and_workshop_do_not_create_ingots(self):
        import economy
        import finca
        import purses
        import trades
        econ = economy.empty_state()
        econ['wallets'] = {'Ana': 40, 'Bea': 10}
        econ['minedSmh'] = 50
        econ['foundry'] = {'minted': {'lingote_oro': 4}, 'head': 'abc'}
        vault = {}
        purses.credit(vault, 'Ana', 'bolsa_cafe', 1)
        purses.credit(vault, 'Ana', 'lingote_oro', 1)
        trades.apply_exchange(
            econ, vault, None, b'seed', 'Ana', 'Bea',
            {'smc': 0, 'smp': 0, 'cobre': 0, 'items': {'bolsa_cafe': 1, 'lingote_oro': 1}},
            {'smc': 0, 'smp': 0, 'cobre': 0, 'items': {}},
            'oficio-1',
        )
        self.assertEqual(econ['minedSmh'], 50)
        self.assertEqual(econ['wallets'], {'Ana': 40, 'Bea': 10})
        self.assertEqual(econ['foundry']['minted']['lingote_oro'], 4)
        self.assertEqual(purses.count(vault, 'Bea', 'lingote_oro'), 1)
        purse = type('Bolsa', (), {
            'foundry': {'lingote_oro': 4},
            'balance': lambda self, coin, name: 0,
            'move': lambda self, *args: False,
            'supply': lambda self: {
                'simoncoin': 100, 'simonplata': 0, 'simonchis': 0,
                'simoncoinSum': 0, 'simonplataSum': 0, 'simonchisSum': 0,
                'foundry': dict(self.foundry),
            },
        })()
        state = finca.empty_state()
        sold = finca.act(state, purse, finca.load_config(), 'Ana', 'vender', {'serial': 'no-existe', 'coin': 'simoncoin'}, 1_700_000_000)
        self.assertFalse(sold['ok'])
        self.assertEqual(purse.foundry['lingote_oro'], 4)


if __name__ == '__main__':
    unittest.main()
