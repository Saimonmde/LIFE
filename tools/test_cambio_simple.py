# SPDX-License-Identifier: AGPL-3.0-or-later
"""El cambio simple mueve monedas que ya existen. No acuña."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import cambio_simple as cambio
import economy as eco


class CambioSimpleTests(unittest.TestCase):
    def test_plata_pays_from_existing_gold(self):
        fondo = 5 * cambio.SUBS
        quoted = cambio.quote('simonplata', 'simoncoin', 250, 250, fondo_smh=fondo)
        self.assertTrue(quoted['ok'])
        self.assertEqual(quoted['das'], 200)
        self.assertEqual(quoted['recibes'], 2)
        self.assertIn('Das 200 Simonplata', quoted['texto'])
        self.assertIn('Recibes 2 Simoncoin', quoted['texto'])

    def test_mineral_stops_when_the_stall_runs_out(self):
        quoted = cambio.quote('mineral_cobre', 'simoncoin', 10, 10, puesto_smh=2_000_000)
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
        econ = {'wallets': {'puesto_frutas': 5_000_000, 'Ana': 1_000_000}}
        before = sum(econ['wallets'].values())
        moved = cambio.mover_mineral(econ, 'Ana', 3)
        self.assertEqual(moved, 3_000_000)
        self.assertEqual(sum(econ['wallets'].values()), before)
        self.assertEqual(econ['wallets']['Ana'], 4_000_000)
        self.assertEqual(eco.MAX_SUPPLY, 21_000_000)


if __name__ == '__main__':
    unittest.main()
