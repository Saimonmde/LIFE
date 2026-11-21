# SPDX-License-Identifier: AGPL-3.0-or-later
"""Una veta a la vez, y cada una vuelve con su propio reloj."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nodos


ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


class NodeTests(unittest.TestCase):
    def test_two_players_mine_different_veins_and_the_same_one_is_busy(self):
        state = nodos.empty()
        now = 1_000.0
        jay = nodos.claim(state, 3, 'mina_oro_0', 'jay', now)
        dave = nodos.claim(state, 3, 'mina_oro_1', 'dave', now)
        self.assertTrue(jay['ok'])
        self.assertTrue(dave['ok'])
        busy = nodos.claim(state, 3, 'mina_oro_0', 'cris', now + 0.1)
        self.assertFalse(busy['ok'])
        self.assertEqual(busy['reason'], 'ocupado')
        second = nodos.claim(state, 3, 'mina_plata_0', 'jay', now + 0.1)
        self.assertFalse(second['ok'])
        self.assertEqual(second['reason'], 'una')

    def test_finish_starts_only_that_timer_and_the_player_waits(self):
        state = nodos.empty()
        now = 2_000.0
        nodos.claim(state, 3, 'mina_oro_0', 'jay', now)
        until = nodos.finish(state, 3, 'mina_oro_0', 'jay', now, ())
        self.assertAlmostEqual(until, now + 32)
        other = nodos.claim(state, 3, 'mina_oro_1', 'dave', now + 0.2)
        self.assertTrue(other['ok'])
        resting = nodos.claim(state, 3, 'mina_oro_0', 'dave', now + 1)
        self.assertEqual(resting['reason'], 'agotada')
        again = nodos.claim(state, 3, 'mina_plata_0', 'jay', now + 0.2)
        self.assertEqual(again['reason'], 'una')
        later = nodos.claim(state, 3, 'mina_plata_0', 'jay', now + 1)
        self.assertTrue(later['ok'])
        rows = nodos.cooling(state, 3, now + 1)
        self.assertEqual([row['id'] for row in rows], ['mina_oro_0'])
        self.assertEqual(nodos.cooling(state, 5, now + 1), [])

    def test_another_player_does_not_reset_a_resting_vein(self):
        state = nodos.empty()
        now = 3_000.0
        nodos.claim(state, 3, 'mina_cobre_0', 'jay', now)
        first = nodos.finish(state, 3, 'mina_cobre_0', 'jay', now)
        nodos.claim(state, 3, 'mina_cobre_1', 'dave', now + 1)
        nodos.finish(state, 3, 'mina_cobre_1', 'dave', now + 1)
        self.assertAlmostEqual(state['ready']['3:mina_cobre_0'], first)
        self.assertNotEqual(state['ready']['3:mina_cobre_0'], state['ready']['3:mina_cobre_1'])

    def test_leave_frees_the_hold_and_each_vein_comes_back_alone(self):
        state = nodos.empty()
        now = 4_000.0
        nodos.claim(state, 3, 'mina_oro_2', 'jay', now)
        self.assertEqual(nodos.release_player(state, 'jay', now), '3:mina_oro_2')
        free = nodos.claim(state, 3, 'mina_oro_2', 'dave', now + 0.1)
        self.assertTrue(free['ok'])
        nodos.finish(state, 3, 'mina_oro_2', 'dave', now + 0.1)
        self.assertEqual(nodos.revive(state, now + 10), [])
        back = nodos.revive(state, now + 33)
        self.assertEqual(back, [{'world': 3, 'id': 'mina_oro_2'}])
        self.assertEqual(nodos.revive(state, now + 34), [])

    def test_spawn_layout_and_rates_stay_as_they_are(self):
        page = open(os.path.join(ROOT, 'play', 'galerias.js'), encoding='utf-8').read()
        self.assertIn('[6, 6], [9, 4], [5, 12], [8, 22], [12, 8]', page)
        self.assertIn('[27, 5], [30, 10], [28, 22], [24, 9]', page)
        self.assertIn('[5, 3], [17, 3], [28, 3], [32, 17], [3, 18], [24, 27]', page)
        self.assertIn("respawnMs: metal === 'oro' ? 32000 : 18000", page)
        self.assertEqual(nodos.MINE['mina_oro_0'], (5, 3, 32000))
        self.assertEqual(nodos.MINE['mina_plata_1'], (30, 10, 18000))
        world = [
            {'id': 'oro_fluvial_1', 'type': 'nodo_oro_fluvial', 'respawnMs': 30000},
            {'id': 'roca_cobre_1', 'type': 'mineral_rock', 'respawnMs': 18000},
            {'id': 'roca_plata_1', 'type': 'mineral_rock', 'respawnMs': 25000},
        ]
        self.assertEqual(nodos.millis(world, 'oro_fluvial_1'), 30000)
        self.assertEqual(nodos.millis(world, 'roca_plata_1'), 25000)
        self.assertIsNone(nodos.millis(world, 'pino_1'))


if __name__ == '__main__':
    unittest.main()
