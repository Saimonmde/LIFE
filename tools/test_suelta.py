# SPDX-License-Identifier: AGPL-3.0-or-later
"""Soltar: sale ya, aparece a los 10 segundos y cualquiera lo recoge."""
import unittest

import crudo
import purses
import suelta


class SueltaTests(unittest.TestCase):
    def setUp(self):
        self.econ = {'crudo': {}}
        self.vault = {'accounts': {}, 'purses': {}}

    def test_simoncoin_stays_and_minerals_can_drop(self):
        blocked = suelta.soltar(self.econ, self.vault, 'ana', 'Ana', 'simoncoin', 1, 4, 5, 'city', now=100)
        self.assertFalse(blocked['ok'])
        crudo.credit(self.econ, 'ana', 'mineral_oro', 2, cap=4)
        crudo.credit(self.econ, 'ana', 'mineral_plata', 1, cap=4)
        oro = suelta.soltar(self.econ, self.vault, 'ana', 'Ana', 'mineral_oro', 2, 4, 5, 'city', now=100, token='a')
        self.assertTrue(oro['ok'], oro)
        self.assertEqual(crudo.nuggets(self.econ, 'ana', 'mineral_oro'), 0)
        plata = suelta.soltar(self.econ, self.vault, 'ana', 'Ana', 'mineral_plata', 1, 4, 5, 'city', now=100, token='b')
        self.assertTrue(plata['ok'], plata)

    def test_it_waits_ten_seconds_then_anyone_picks_it_up(self):
        purses.credit(self.vault, 'Ana', 'moneda_plata', 3)
        done = suelta.soltar(self.econ, self.vault, 'ana', 'Ana', 'moneda_plata', 2, 10, 12, 'city', now=500, token='c')
        self.assertTrue(done['ok'], done)
        self.assertEqual(purses.count(self.vault, 'Ana', 'moneda_plata'), 1)
        visible = suelta.publicos(self.econ, 'city', now=505)
        self.assertTrue(visible[0]['espera'])
        early = suelta.alzar(self.econ, self.vault, 'Ana', visible[0]['id'], 10, 12, 'city', now=509)
        self.assertFalse(early['ok'])
        self.assertEqual(purses.count(self.vault, 'Ana', 'moneda_plata'), 1)
        ready = suelta.publicos(self.econ, 'city', now=510)
        self.assertFalse(ready[0]['espera'])
        other = suelta.alzar(self.econ, self.vault, 'Luis', ready[0]['id'], 11, 12, 'city', now=511)
        self.assertTrue(other['ok'], other)
        self.assertEqual(purses.count(self.vault, 'Luis', 'moneda_plata'), 2)
        again = suelta.alzar(self.econ, self.vault, 'Ana', ready[0]['id'], 10, 12, 'city', now=512)
        self.assertFalse(again['ok'])

    def test_the_same_token_does_not_drop_twice(self):
        purses.credit(self.vault, 'Ana', 'madera', 2)
        first = suelta.soltar(self.econ, self.vault, 'ana', 'Ana', 'madera', 1, 1, 1, 'city', now=20, token='misma')
        second = suelta.soltar(self.econ, self.vault, 'ana', 'Ana', 'madera', 1, 1, 1, 'city', now=21, token='misma')
        self.assertTrue(first['ok'] and second.get('dup'))
        self.assertEqual(purses.count(self.vault, 'Ana', 'madera'), 1)
        self.assertEqual(len(suelta.publicos(self.econ, 'city', now=21)), 1)

    def test_it_despawns_with_the_puma_sack(self):
        import fauna
        purses.credit(self.vault, 'Ana', 'piedra', 1)
        suelta.soltar(self.econ, self.vault, 'ana', 'Ana', 'piedra', 1, 3, 3, 'mine', now=0, token='d')
        self.assertEqual(suelta.VIDA, fauna.DROP_TTL)
        self.assertEqual(suelta.publicos(self.econ, 'mine', now=fauna.DROP_TTL), [])


if __name__ == '__main__':
    unittest.main()
