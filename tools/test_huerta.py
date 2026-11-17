#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""La huerta nace vacía, gasta semilla y devuelve el fruto a la mochila."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import finca
import huerta
import reloj


class HuertaTests(unittest.TestCase):
    def setUp(self):
        self.config = finca.load_config()
        self.state = finca.empty_state()
        self.now = 1_700_000_000
        self.bag = {'mango_seed': 2, 'cafe_seed': 1}

    def test_eight_beds_start_empty(self):
        rows = huerta.rows(self.state['accounts'].setdefault('Ana', {}), self.now, self.config)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row['phase'] == 'vacio' and row['progress'] == 0 for row in rows))
        self.assertEqual(self.state['harvestedKg']['cafe'], 0)

    def test_seed_is_spent_and_fruit_returns_after_the_clock(self):
        box = self.state['accounts'].setdefault('Ana', {})
        planted = huerta.plant(self.state, self.config, 'Ana', 'huerta-1', 'mango_seed', self.bag, self.now)
        self.assertEqual(planted['spent']['item'], 'mango_seed')
        self.assertEqual(self.bag['mango_seed'], 1)
        with self.assertRaises(finca.FincaError):
            huerta.harvest(self.state, self.config, 'Ana', 'huerta-1', self.bag, self.now + 10)
        later = self.now + huerta.ripe_seconds(self.config)
        row = huerta.rows(box, later, self.config)[0]
        self.assertEqual(row['phase'], 'cosecha')
        self.assertEqual(row['progress'], 1)
        self.assertGreater(row['progress'], 0.99)
        got = huerta.harvest(self.state, self.config, 'Ana', 'huerta-1', self.bag, later)
        self.assertEqual(got['gained'], {'item': 'mango', 'qty': 2, 'name': 'Mango'})
        self.assertEqual(self.bag['mango'], 2)
        self.assertEqual(box['huerta']['huerta-1']['crop'], '')
        self.assertEqual(self.state['harvestedKg']['cafe'], 0)

    def test_cafe_seed_does_not_touch_the_kilo_ledger(self):
        huerta.plant(self.state, self.config, 'Ana', 'huerta-3', 'cafe_seed', self.bag, self.now)
        later = self.now + int(reloj.REAL_SECONDS_PER_DAY * self.config['ripeAfterDays'])
        huerta.harvest(self.state, self.config, 'Ana', 'huerta-3', self.bag, later)
        self.assertEqual(self.bag['cafe_cereza'], 1)
        self.assertNotIn('cafe_seed', self.bag)
        self.assertEqual(self.state['harvestedKg']['cafe'], 0)
        self.assertEqual(self.state['harvestedKg']['cacao'], 0)

    def test_act_rejects_a_missing_seed_and_keeps_the_bed(self):
        class Purse:
            def balance(self, coin, name):
                return 0
        result = finca.act(
            self.state, Purse(), self.config, 'Ana', 'huerta_sembrar',
            {'bed': 'huerta-2', 'seed': 'pera_seed'}, self.now, items=self.bag,
        )
        self.assertFalse(result['ok'])
        beds = result['view']['huerta']
        self.assertTrue(all(row['crop'] == '' for row in beds))


if __name__ == '__main__':
    unittest.main()
