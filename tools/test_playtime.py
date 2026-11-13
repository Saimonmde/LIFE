# SPDX-License-Identifier: AGPL-3.0-or-later
"""El tiempo jugado suma los latidos activos y descarta la inactividad."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import playtime


class PlaytimeTests(unittest.TestCase):
    def test_two_beats_accumulate_and_idle_does_not(self):
        state = playtime.empty()
        first = playtime.beat(state, 'Ana', active=True, now=1_000)
        self.assertEqual(first['playtime'], 0)
        self.assertEqual(first['createdAt'], 1_000)
        second = playtime.beat(state, 'Ana', active=True, now=1_000 + 30)
        self.assertEqual(second['added'], 30)
        self.assertEqual(second['playtime'], 30)
        third = playtime.beat(state, 'Ana', active=True, now=1_000 + 30 + 30)
        self.assertEqual(third['playtime'], 60)
        idle = playtime.beat(state, 'Ana', active=True, now=1_000 + 60 + 600)
        self.assertEqual(idle['added'], 0)
        self.assertEqual(idle['playtime'], 60)
        paused = playtime.beat(state, 'Ana', active=False, now=1_000 + 60 + 600 + 30)
        self.assertEqual(paused['added'], 0)
        self.assertEqual(paused['playtime'], 60)
        again = playtime.beat(state, 'Ana', active=True, now=1_000 + 60 + 600 + 60)
        self.assertEqual(again['added'], 30)
        self.assertEqual(again['playtime'], 90)


if __name__ == '__main__':
    unittest.main()
