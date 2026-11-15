# SPDX-License-Identifier: AGPL-3.0-or-later
"""El reloj de 1777 es el mismo para todos y no depende del navegador."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reloj


class RelojTests(unittest.TestCase):
    def test_epoch_is_fixed_and_shared(self):
        state = {}
        epoch, changed = reloj.anchor(state, env='')
        self.assertTrue(changed)
        self.assertEqual(epoch, reloj.DEPLOY_EPOCH)
        again, changed = reloj.anchor(state, env='no-es-un-numero')
        self.assertFalse(changed)
        self.assertEqual(again, epoch)
        other = {}
        self.assertEqual(reloj.anchor(other, env=None)[0], epoch)

    def test_starts_on_1_january_1777_and_a_day_is_twenty_minutes(self):
        epoch = 1_700_000_000
        start = reloj.describe(epoch, epoch)
        self.assertEqual(start['fecha'], '1 de enero de 1777')
        self.assertEqual(start['hora'], '00:00')
        self.assertIn('1 de enero de 1777', start['label'])
        later = reloj.describe(epoch + 20 * 60, epoch)
        self.assertEqual(later['fecha'], '2 de enero de 1777')
        self.assertEqual(later['hora'], '00:00')
        hour = reloj.describe(epoch + 50, epoch)
        self.assertEqual(hour['fecha'], '1 de enero de 1777')
        self.assertEqual(hour['hora'], '01:00')

    def test_saved_epoch_survives_a_restart(self):
        state = {'relojEpoch': 1_700_000_000}
        epoch, changed = reloj.anchor(state, env='')
        self.assertFalse(changed)
        self.assertEqual(epoch, 1_700_000_000)
        moved, changed = reloj.anchor(state, env='1800000000')
        self.assertTrue(changed)
        self.assertEqual(moved, 1800000000)


if __name__ == '__main__':
    unittest.main()
