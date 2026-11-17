# SPDX-License-Identifier: AGPL-3.0-or-later
"""El baúl mueve lo de esa cuenta, una sola vez, sin copiarlo."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import economy
import baul
import purses
import vault


class ChestTests(unittest.TestCase):
    def setUp(self):
        self.state = vault.empty()

    def test_deposit_and_withdraw_are_atomic_and_private(self):
        purses.credit(self.state, 'Ana', 'mineral_oro', 3)
        moved = baul.mover(self.state, 'Ana', 'deposit', 'mineral_oro', 2, 'pase-1', now=10)
        self.assertTrue(moved['ok'])
        self.assertFalse(moved['dup'])
        self.assertEqual(purses.count(self.state, 'Ana', 'mineral_oro'), 1)
        self.assertEqual(moved['account']['items']['mineral_oro'], 2)
        again = baul.mover(self.state, 'Ana', 'deposit', 'mineral_oro', 2, 'pase-1', now=11)
        self.assertTrue(again['dup'])
        self.assertEqual(purses.count(self.state, 'Ana', 'mineral_oro'), 1)
        self.assertEqual(vault.account(self.state, 'Ana')['items']['mineral_oro'], 2)
        short = baul.mover(self.state, 'Ana', 'deposit', 'mineral_oro', 5, 'pase-2', now=12)
        self.assertFalse(short['ok'])
        self.assertEqual(vault.account(self.state, 'Ana')['items']['mineral_oro'], 2)
        out = baul.mover(self.state, 'Ana', 'withdraw', 'mineral_oro', 2, 'pase-3', now=13)
        self.assertTrue(out['ok'])
        self.assertEqual(purses.count(self.state, 'Ana', 'mineral_oro'), 3)
        self.assertNotIn('mineral_oro', vault.account(self.state, 'Ana')['items'])
        stolen = baul.mover(self.state, 'Sol', 'withdraw', 'mineral_oro', 1, 'pase-4', now=14)
        self.assertFalse(stolen['ok'])
        self.assertEqual(purses.count(self.state, 'Ana', 'mineral_oro'), 3)
        self.assertEqual(vault.account(self.state, 'Sol')['items'], {})

    def test_a_double_click_without_a_new_token_does_not_duplicate(self):
        purses.credit(self.state, 'Ana', 'mineral_plata', 4)
        baul.mover(self.state, 'Ana', 'deposit', 'mineral_plata', 1, 'a', now=20)
        dup = baul.mover(self.state, 'Ana', 'deposit', 'mineral_plata', 1, 'b', now=20.2)
        self.assertTrue(dup['dup'])
        self.assertEqual(vault.account(self.state, 'Ana')['items']['mineral_plata'], 1)
        self.assertEqual(self.state['accounts']['Ana']['log'][-1]['op'], 'deposit')

    def test_server_uses_the_session_name(self):
        page = open(os.path.join(os.path.dirname(__file__), '..', 'server.py'), encoding='utf-8').read()
        self.assertIn('BAUL.mover(VAULT_STATE, sender.name', page)


class ChestRulesTests(unittest.TestCase):
    def setUp(self):
        self.state = vault.empty()
        self.econ = economy.empty_state()
        self.econ['minedSmh'] = 80
        self.econ['earnedToday'] = 50

    def test_client_amount_cannot_create_or_overdraw(self):
        purses.credit(self.state, 'Ana', 'madera', 3)
        purses.credit(self.state, 'Ana', 'mineral_oro', 2)
        too_many = baul.mover_lote(self.state, 'Ana', 'deposit', 'madera', 40, 't1', now=30)
        self.assertFalse(too_many['ok'])
        self.assertEqual(purses.count(self.state, 'Ana', 'madera'), 3)
        self.assertEqual(vault.account(self.state, 'Ana')['items'], {})
        invented = baul.mover_lote(self.state, 'Ana', 'deposit', 'piedra', 5, 't2', now=31)
        self.assertFalse(invented['ok'])
        self.assertNotIn('piedra', vault.account(self.state, 'Ana')['items'])
        moved = baul.mover_lote(self.state, 'Ana', 'deposit', 'madera', 'all', 't3', now=32)
        self.assertTrue(moved['ok'])
        self.assertEqual(moved['moved'], [{'op': 'deposit', 'item': 'madera', 'qty': 3}])
        self.assertEqual(purses.count(self.state, 'Ana', 'madera'), 0)
        self.assertEqual(vault.account(self.state, 'Ana')['items']['madera'], 3)
        short = baul.mover_lote(self.state, 'Ana', 'withdraw', 'madera', 9, 't4', now=33)
        self.assertFalse(short['ok'])
        self.assertEqual(vault.account(self.state, 'Ana')['items']['madera'], 3)
        self.assertEqual(purses.count(self.state, 'Ana', 'madera'), 0)

    def test_all_uses_the_server_count_and_rolls_back(self):
        purses.credit(self.state, 'Ana', 'mineral_cobre', 4)
        purses.credit(self.state, 'Ana', 'piedra', 2)
        everything = baul.mover_lote(self.state, 'Ana', 'deposit', '', 1, 'todo', now=40)
        self.assertTrue(everything['ok'])
        self.assertEqual(purses.inventory(self.state, 'Ana'), {})
        self.assertEqual(vault.account(self.state, 'Ana')['items'], {'mineral_cobre': 4, 'piedra': 2})
        back = baul.mover_lote(self.state, 'Ana', 'withdraw', '', 'all', 'volver', now=41)
        self.assertTrue(back['ok'])
        self.assertEqual(purses.count(self.state, 'Ana', 'mineral_cobre'), 4)
        self.assertEqual(purses.count(self.state, 'Ana', 'piedra'), 2)
        self.assertEqual(vault.account(self.state, 'Ana')['items'], {})

    def test_smc_move_keeps_the_sum_and_the_cap(self):
        economy.credit(self.econ, 'Ana', 5 * economy.SUBS)
        before = sum(self.econ['wallets'].values()) + vault.smh_of(vault.account(self.state, 'Ana'))
        saved = baul.mover_smc(self.econ, self.state, 'Ana', 'deposit', '1,5', 'c1', now=50)
        self.assertTrue(saved['ok'], saved.get('reason'))
        self.assertEqual(self.econ['wallets']['Ana'], 350)
        self.assertEqual(vault.smh_of(vault.account(self.state, 'Ana')), 150)
        self.assertEqual(sum(self.econ['wallets'].values()) + vault.smh_of(vault.account(self.state, 'Ana')), before)
        self.assertEqual(self.econ['minedSmh'], 80)
        self.assertEqual(self.econ['earnedToday'], 50)
        whole = baul.mover_smc(self.econ, self.state, 'Ana', 'deposit', 'all', 'c2', now=51)
        self.assertTrue(whole['ok'])
        self.assertEqual(self.econ['wallets']['Ana'], 0)
        self.assertEqual(vault.smh_of(vault.account(self.state, 'Ana')), 5 * economy.SUBS)
        economy.credit(self.econ, 'Ana', economy.MAX_SMH)
        blocked = baul.mover_smc(self.econ, self.state, 'Ana', 'withdraw', 'all', 'c3', now=52)
        self.assertFalse(blocked['ok'])
        self.assertIn('21.000.000 SMC', blocked['reason'])
        self.assertNotIn('SMH', blocked['reason'])
        self.assertEqual(vault.smh_of(vault.account(self.state, 'Ana')), 5 * economy.SUBS)
        self.assertEqual(self.econ['minedSmh'], 80)

    def test_view_is_smc_only_and_groups_minerals(self):
        economy.credit(self.econ, 'Ana', 250)
        purses.credit(self.state, 'Ana', 'mineral_cobre', 4)
        purses.credit(self.state, 'Ana', 'madera', 6)
        baul.mover_lote(self.state, 'Ana', 'deposit', 'mineral_cobre', 1, 'v', now=60)
        shown = baul.vista(self.state, self.econ, 'Ana')
        blob = json.dumps(shown, ensure_ascii=False)
        for banned in ('SMH', 'SMP', 'SPH', 'Simonchi', 'Simonplata'):
            self.assertNotIn(banned, blob)
        self.assertIn('SMC', shown['smc']['total']['exacto'])
        self.assertEqual(shown['smc']['total']['exacto'], '2,5 SMC')
        self.assertIn('50 SMC', shown['smc']['topes'])
        self.assertIn('150 SMC', shown['smc']['topes'])
        cobre = next(row for row in shown['filas'] if row['id'] == 'mineral_cobre')
        self.assertEqual(cobre['grupo'], 'mineral')
        self.assertEqual((cobre['encima'], cobre['baul'], cobre['total']), (3, 1, 4))
        wood = next(row for row in shown['filas'] if row['id'] == 'madera')
        self.assertEqual(wood['grupo'], 'recurso')
        self.assertEqual(shown['totales']['mineral'], 4)
        self.assertEqual(shown['totales']['recurso'], 6)

    def test_coffee_moves_in_place_and_is_not_copied(self):
        import finca
        bags = finca.empty_state()
        bags['bags']['B1'] = {'serial': 'B1', 'owner': 'Ana', 'place': 'mochila', 'crop': 'cafe', 'hash': 'a', 'chain': []}
        purses.credit(self.state, 'Ana', 'bolsa_cafe', 1)
        copied = baul.mover(self.state, 'Ana', 'deposit', 'bolsa_cafe', 1, 'no', now=70)
        self.assertFalse(copied['ok'])
        self.assertEqual(purses.count(self.state, 'Ana', 'bolsa_cafe'), 1)
        self.assertEqual(vault.account(self.state, 'Ana')['items'], {})
        moved = baul.mover_bultos(bags, None, 'Ana', 'deposit', 'bolsa_cafe', 9, now=71)
        self.assertTrue(moved['ok'])
        self.assertEqual(moved['qty'], 1)
        self.assertEqual(bags['bags']['B1']['place'], 'banco')
        self.assertEqual(vault.account(self.state, 'Ana')['items'], {})
        shown = baul.vista(self.state, self.econ, 'Ana', bultos_encima={}, bultos_baul={'bolsa_cafe': 1})
        cafe = next(row for row in shown['filas'] if row['id'] == 'bolsa_cafe')
        self.assertEqual((cafe['encima'], cafe['baul']), (0, 1))

    def test_migration_is_once_and_the_save_roundtrips(self):
        import persist
        import tempfile
        previous = os.environ.pop('DATABASE_URL', None)
        persist.reset_connection()
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, 'vault.json')
        try:
            raw = {
                'accounts': {
                    'Ana': {
                        'smh': 250,
                        'smcSubs': 250,
                        'sph': 3,
                        'items': [{'item': 'madera', 'qty': 4}, {'item': 'mineral_oro', 'qty': 2}],
                    },
                },
                'purses': {'Ana': {'piedra': 5}},
            }
            self.assertTrue(baul.migrate(raw))
            self.assertEqual(raw['accounts']['Ana']['smh'], 250)
            self.assertEqual(raw['accounts']['Ana']['sph'], 3)
            self.assertEqual(raw['accounts']['Ana']['items'], {'madera': 4, 'mineral_oro': 2})
            self.assertEqual(raw['purses']['Ana']['piedra'], 5)
            self.assertEqual(raw['meta']['baul'], 1)
            self.assertFalse(baul.migrate(raw))
            persist.save_named('vault', path, raw)
            loaded = vault.load(path)
            self.assertEqual(loaded['accounts']['Ana']['items']['madera'], 4)
            self.assertEqual(loaded['accounts']['Ana']['smh'], 250)
            self.assertEqual(loaded['purses']['Ana']['piedra'], 5)
            baul.mover_lote(loaded, 'Ana', 'deposit', 'piedra', 'all', 'guarda', now=80)
            persist.save_named('vault', path, loaded)
            again = persist.load_named('vault', path)
            self.assertEqual(again['accounts']['Ana']['items']['piedra'], 5)
            self.assertEqual(again['purses']['Ana'].get('piedra', 0), 0)
            self.assertEqual(again['accounts']['Ana']['items']['madera'], 4)
        finally:
            if previous:
                os.environ['DATABASE_URL'] = previous
            persist.reset_connection()

    def test_server_uses_the_session_and_the_mine_stays_on_the_list(self):
        page = open(os.path.join(os.path.dirname(__file__), '..', 'server.py'), encoding='utf-8').read()
        start = page.index('def baul_mover(')
        body = page[start:page.index('\ndef baul_smc(', start)]
        self.assertIn('sender.name', body)
        self.assertNotIn("get('name')", body)
        self.assertIn("BAUL.mover_lote(VAULT_STATE, sender.name", body)
        game = open(os.path.join(os.path.dirname(__file__), '..', 'play', 'game.js'), encoding='utf-8').read()
        self.assertIn("'mina'", game)
        self.assertIn('DESTINO_IDS', game)
        self.assertIn('Baul.open()', game)
        window = open(os.path.join(os.path.dirname(__file__), '..', 'play', 'baul.js'), encoding='utf-8').read()
        css = open(os.path.join(os.path.dirname(__file__), '..', 'play', 'baul.css'), encoding='utf-8').read()
        for banned in ('SMH', 'SMP', 'SPH', 'Simonchi', 'Simonplata'):
            self.assertNotIn(banned, window)
            self.assertNotIn(banned, css)


if __name__ == '__main__':
    unittest.main()
