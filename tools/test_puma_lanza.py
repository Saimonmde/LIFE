#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cinco aciertos con la lanza, sin un mordisco, dejan la piel."""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import fauna


def puma():
    return {
        'id': 'puma-1', 'x': 3.0, 'y': 4.0, 'homeX': 9.0, 'homeY': 9.0,
        'hp': fauna.PUMA_HP, 'mode': 'attack', 'streak': 0, 'cue': 1,
        'dir': 'down',
    }


class SpearTests(unittest.TestCase):
    def test_five_clean_hits_drop_the_hide(self):
        foe = puma()
        state = fauna.empty_state()
        rng = random.Random(4)
        last = None
        for _ in range(5):
            last = fauna.spear_tap(foe, 3, 4, foe['cue'], True, 50, rng)
            self.assertTrue(last['hit'])
        self.assertTrue(last['dead'])
        self.assertEqual(foe['hp'], 0)
        self.assertEqual((foe['x'], foe['y']), (9.0, 9.0))
        hide = fauna.drop_pelt(state, 'Ana', last['x'], last['y'], 50)
        got = fauna.take_pelt(state, 'Ana', hide['id'], last['x'], last['y'], 51)
        self.assertEqual(got['item'], 'piel_puma')
        with self.assertRaises(fauna.FaunaError):
            fauna.take_pelt(state, 'Ana', hide['id'], last['x'], last['y'], 52)

    def test_a_bite_wipes_the_streak(self):
        foe = puma()
        rng = random.Random(1)
        fauna.spear_tap(foe, 3, 4, foe['cue'], True, 10, rng)
        fauna.spear_tap(foe, 3, 4, foe['cue'], True, 11, rng)
        self.assertEqual(foe['streak'], 2)
        foe['streak'] = 0
        fauna._arm_cue(foe, rng, force=True)
        nxt = fauna.spear_tap(foe, 3, 4, foe['cue'], True, 12, rng)
        self.assertEqual(nxt['streak'], 1)
        self.assertFalse(nxt['dead'])

    def test_a_miss_or_bare_hands_do_not_count(self):
        foe = puma()
        rng = random.Random(3)
        miss = fauna.spear_tap(foe, 3, 4, (foe['cue'] + 1) % 3, True, 10, rng)
        self.assertFalse(miss['hit'])
        self.assertEqual(foe['streak'], 0)
        bare = fauna.spear_tap(foe, 3, 4, foe['cue'], False, 11, rng)
        self.assertFalse(bare['ok'])
        self.assertEqual(foe['hp'], fauna.PUMA_HP)


if __name__ == '__main__':
    unittest.main()
