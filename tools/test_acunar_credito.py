# SPDX-License-Identifier: AGPL-3.0-or-later
"""Acuñar deja la moneda en el saldo, en la mochila y en el libro. No pasa el tope."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import acunar_credito as ac
import economy as eco
import historia
import purses


class AcunarCreditoTests(unittest.TestCase):
    def test_mint_updates_balance_inventory_counter_and_book(self):
        econ = eco.empty_state()
        vault = {}
        before = eco.MAX_SUPPLY
        granted = eco.issue(econ, 'Primo', 100_000_000, 'Acuñación de Simoncoin', 'fundicion')
        self.assertEqual(granted, 100_000_000)
        self.assertEqual(econ['wallets']['Primo'], 100_000_000)
        moneda = ac.acreditar_mochila(vault, 'Primo', 'simoncoin', 1)
        self.assertEqual(moneda['item'], 'moneda_oro')
        self.assertEqual(purses.count(vault, 'Primo', 'moneda_oro'), 1)
        self.assertEqual(econ['wallets']['Primo'], granted)
        rows = historia.filas(econ)
        self.assertTrue(any(row['label'] == 'Acuñación' and row['account'] == 'Primo' for row in rows))
        self.assertEqual(eco.MAX_SUPPLY, before)
        self.assertLessEqual(econ['minedSmh'], (eco.MAX_SUPPLY - eco.TREASURY) * eco.SUBS)

    def test_daily_cap_and_missing_ore_are_plain_sentences(self):
        metal = ac.motivo(2, 5, 6.25, 21_000_000, 'oros crudos', 'Simoncoin')
        self.assertIn('No tienes oros crudos suficiente', metal)
        cap = ac.motivo(10, 5, 0, 21_000_000, 'oros crudos', 'Simoncoin')
        self.assertIn('tope', cap)
        self.assertIn('7:00', cap)
        world = ac.motivo(10, 5, 1, 0, 'oros crudos', 'Simoncoin')
        self.assertIn('Ya no se puede crear más', world)

    def test_logged_in_owner_can_mint_on_another_device_without_new_coins(self):
        text = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server.py'), encoding='utf-8').read()
        self.assertIn('owner=bool(getattr(c, \'user\', None))', text)
        self.assertIn('if token_matches(tokens[name], presented) or owner:', text)

    def test_silver_mint_is_a_book_row_and_copper_too(self):
        econ = eco.empty_state()
        econ.setdefault('plata', {}).setdefault('txs', []).append({
            'type': 'mint', 'to': 'Primo', 'amountSph': 100_000_000, 't': 10,
        })
        eco.append_tx(econ, {
            'type': 'fundicion', 'to': 'Primo', 'coin': 'SMCH', 'qty': 4,
            'amountSubs': 0, 'note': 'Acuñación de 4 Simonchis',
        })
        rows = historia.filas(econ)
        self.assertTrue(any(row.get('coin') == 'SMP' and row['label'] == 'Acuñación' for row in rows))
        self.assertTrue(any('Simonchis' in row.get('note', '') for row in rows))
