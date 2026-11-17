# SPDX-License-Identifier: AGPL-3.0-or-later
"""El cambio simple mueve monedas que ya existen. No acuña."""
import copy
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import cambio_simple as cambio
import economy as eco


class CambioSimpleTests(unittest.TestCase):
    def test_plata_pays_from_existing_gold(self):
        fondo = 5 * cambio.SUBS
        quoted = cambio.quote('simonplata', 'simoncoin', 250, 250 * cambio.PLATA_SUBS, fondo_smh=fondo)
        self.assertTrue(quoted['ok'])
        self.assertEqual(quoted['das'], 200)
        self.assertEqual(quoted['recibes'], 2)
        self.assertIn('Das 200 Simonplata', quoted['texto'])
        self.assertIn('Recibes 2 Simoncoin', quoted['texto'])

    def test_hundred_smp_is_one_smc_and_sph_is_not_invented(self):
        quoted = cambio.quote(
            'simonplata', 'simoncoin', 100, 100 * cambio.PLATA_SUBS, fondo_smh=5 * cambio.SUBS,
        )
        self.assertTrue(quoted['ok'])
        self.assertEqual(quoted['das'], 100)
        self.assertEqual(quoted['recibes'], 1)
        capped = cambio.quote(
            'simonplata', 'simoncoin', 10_000, 100 * cambio.PLATA_SUBS, fondo_smh=1000 * cambio.SUBS,
        )
        self.assertEqual(capped['das'], 100)
        self.assertEqual(capped['recibes'], 1)

    def test_mineral_stops_when_the_stall_runs_out(self):
        quoted = cambio.quote('mineral_cobre', 'simoncoin', 10, 10, puesto_smh=2)
        self.assertEqual(quoted['das'], 2)
        self.assertEqual(quoted['maximo'], 2)
        self.assertIn('Das 2 de cobre', quoted['texto'])

    def test_other_directions_do_not_create_money(self):
        blocked = cambio.quote('simoncoin', 'simonplata', 1, 1, fondo_smh=10 ** 12, puesto_smh=10 ** 12)
        self.assertFalse(blocked['ok'])
        self.assertIn('ya existe', blocked['texto'])
        same = cambio.quote('simonplata', 'simonplata', 10, 10)
        self.assertFalse(same['ok'])

    def test_moving_a_mineral_keeps_the_same_total(self):
        econ = {'wallets': {'puesto_frutas': 5, 'Ana': 1}}
        before = sum(econ['wallets'].values())
        moved = cambio.mover_mineral(econ, 'Ana', 3)
        self.assertEqual(moved, 3)
        self.assertEqual(sum(econ['wallets'].values()), before)
        self.assertEqual(econ['wallets']['Ana'], 4)
        self.assertEqual(eco.MAX_SUPPLY, 21_000_000)


class CambioEnServidorTests(unittest.TestCase):
    def setUp(self):
        import server
        self.server = server
        self.sent = []
        self._send = server.send
        self._save_econ = server.save_econ
        self._save_vault = server.save_vault
        self._pase = server.anotar_pase
        self._econ = copy.deepcopy(server.ECON)
        self._players = copy.deepcopy(server.PLAYERS)
        server.send = lambda _c, obj: self.sent.append(obj)
        server.save_econ = lambda: None
        server.save_vault = lambda: None
        server.anotar_pase = lambda *args, **kwargs: {'id': 'prueba'}
        server.ECON.clear()
        server.ECON.update(eco.empty_state())

    def tearDown(self):
        server = self.server
        server.send = self._send
        server.save_econ = self._save_econ
        server.save_vault = self._save_vault
        server.anotar_pase = self._pase
        server.ECON.clear()
        server.ECON.update(self._econ)
        server.PLAYERS.clear()
        server.PLAYERS.update(self._players)

    def test_exchange_of_100_smp_pays_1_smc(self):
        import playtime as play
        server = self.server
        who = server.Client(None)
        who.hello = True
        who.wallet_ok = True
        who.name = 'Nico'
        who.ip = '198.51.100.44'
        who.activity_tiles = 8
        who.last_activity_at = time.time()
        who.user = {'id': 'cta-cambio', 'name': 'Nico', 'createdAt': time.time() - 60 * 86400 - 5}
        play.ensure(server.PLAYERS, 'Nico')['playtime'] = 40 * 3600
        server.ECON['plata']['smcPoolSmh'] = 10 * eco.SUBS
        server.ECON['plata']['wallets']['Nico'] = 100 * cambio.PLATA_SUBS
        server.ECON['wallets']['Nico'] = 0
        mined = int(server.ECON.get('minedSmh') or 0)
        server.cambio_simple_msg(who, {'give': 'simonplata', 'receive': 'simoncoin', 'qty': 100})
        done = [item for item in self.sent if item.get('t') == 'cambio_result']
        self.assertTrue(done, [item.get('t') for item in self.sent])
        self.assertTrue(done[-1].get('ok'), done[-1])
        self.assertEqual(done[-1].get('das'), 100)
        self.assertEqual(done[-1].get('recibes'), 1)
        self.assertEqual(int(server.ECON['wallets']['Nico']), eco.SUBS)
        self.assertEqual(int(server.ECON['plata']['wallets']['Nico']), 0)
        self.assertEqual(int(server.ECON.get('minedSmh') or 0), mined)


if __name__ == '__main__':
    unittest.main()
