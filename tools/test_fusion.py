# SPDX-License-Identifier: AGPL-3.0-or-later
"""La fusión mueve el SMC ya emitido una sola vez y no toca la Plata ni la reserva."""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import economy as eco
import fusion
import plata
import vault as VAULT


def holdings(state, box):
    wallets = sum(int(v or 0) for v in (state.get('wallets') or {}).values())
    pool = int((state.get('plata') or {}).get('smcPoolSmh') or 0)
    deposited = sum(VAULT.smh_of(item) for item in (box.get('accounts') or {}).values())
    return wallets + pool + deposited


class FusionTests(unittest.TestCase):
    def setUp(self):
        self.econ = eco.empty_state()
        plata.ensure(self.econ, now=1_700_000_000)
        self.vault = VAULT.empty()
        self.accounts = {'users': []}

    def test_waits_until_the_founder_signs_in(self):
        eco.issue(self.econ, 'Ana', 50 * eco.SUBS, 'batea', 'mint', now=100)
        before = holdings(self.econ, self.vault)
        first = fusion.apply(self.econ, self.accounts, self.vault, now=200)
        self.assertEqual(first['status'], 'pending')
        self.assertEqual(holdings(self.econ, self.vault), before)
        self.assertEqual(self.econ['wallets']['Ana'], 50 * eco.SUBS)
        again = fusion.apply(self.econ, self.accounts, self.vault, now=300)
        self.assertTrue(again['already'])
        self.assertEqual(self.econ['wallets']['Ana'], 50 * eco.SUBS)

    def test_moves_every_balance_except_the_reserve_and_silver(self):
        eco.issue(self.econ, 'Ana', 10 * eco.SUBS, 'batea', 'mint', now=100)
        plata.apartar(self.econ, 'Ana', 10 * eco.SUBS, now=100)
        eco.issue(self.econ, 'Luz', 4 * eco.SUBS, 'batea', 'mint', now=120)
        self.econ['wallets']['puesto_frutas'] = 2 * eco.SUBS
        self.econ['plata']['wallets']['Ana'] = 80 * plata.SUBS
        self.econ['plata']['minedSph'] = 80 * plata.SUBS
        burned = 3 * plata.SUBS
        self.econ['plata']['burnedSph'] = burned
        VAULT.add_smc(VAULT.account(self.vault, 'Luz'), 1 * eco.SUBS)
        eco.debit(self.econ, 'Luz', 1 * eco.SUBS)
        treasury = self.econ['wallets']['tesoro_genesis']
        mined = self.econ['minedSmh']
        silver = dict(self.econ['plata']['wallets'])
        before = holdings(self.econ, self.vault)
        self.accounts['users'].append({
            'id': 'fundador', 'name': 'Simón', 'email': 'Saimon888Oficial@gmail.com',
            'wallet_name': 'Simon',
        })
        done = fusion.apply(self.econ, self.accounts, self.vault, now=400)
        self.assertEqual(done['status'], 'done')
        self.assertFalse(done['already'])
        self.assertEqual(self.econ['wallets']['tesoro_genesis'], treasury)
        self.assertEqual(self.econ['minedSmh'], mined)
        self.assertEqual(self.econ['maxSupply'], 21_000_000)
        self.assertEqual(plata.MAX_SUPPLY, 84_000_000)
        self.assertEqual(self.econ['plata']['wallets'], silver)
        self.assertEqual(self.econ['plata']['minedSph'], 80 * plata.SUBS)
        self.assertEqual(self.econ['plata']['burnedSph'], burned)
        self.assertEqual(self.econ['plata']['smcPoolSmh'], 0)
        self.assertEqual(self.econ['wallets']['Ana'], 0)
        self.assertEqual(self.econ['wallets']['Luz'], 0)
        self.assertEqual(self.econ['wallets']['puesto_frutas'], 0)
        self.assertEqual(VAULT.smh_of(self.vault['accounts']['Luz']), 0)
        moved = 10 * eco.SUBS + 4 * eco.SUBS + 2 * eco.SUBS
        self.assertEqual(self.econ['wallets']['Simon'], moved)
        self.assertEqual(holdings(self.econ, self.vault), before)
        notes = [tx.get('note') for block in self.econ['blocks'] for tx in block['txs'] if tx.get('type') == 'fusion']
        self.assertGreaterEqual(len(notes), 4)
        self.assertTrue(all(note == fusion.NOTE for note in notes))
        kinds = {tx.get('type') for block in self.econ['blocks'] for tx in block['txs']}
        self.assertIn('fusion', kinds)
        self.assertNotIn('issue', {row['where'] for row in done['record']['transfers']})

    def test_second_run_does_not_move_again(self):
        eco.issue(self.econ, 'Ana', 5 * eco.SUBS, 'batea', 'mint', now=100)
        self.accounts['users'].append({'email': 'saimon888oficial@gmail.com', 'name': 'Simon', 'wallet_name': 'Simon'})
        fusion.apply(self.econ, self.accounts, self.vault, now=200)
        balance = self.econ['wallets']['Simon']
        mined = self.econ['minedSmh']
        again = fusion.apply(self.econ, self.accounts, self.vault, now=500)
        self.assertTrue(again['already'])
        self.assertEqual(again['fresh'], [])
        self.assertEqual(self.econ['wallets']['Simon'], balance)
        self.assertEqual(self.econ['wallets'].get('Ana', 0), 0)
        self.assertEqual(self.econ['minedSmh'], mined)

    def test_a_late_vault_save_does_not_credit_twice(self):
        self.econ['wallets']['Simon'] = 0
        VAULT.add_smc(VAULT.account(self.vault, 'Nube'), 7 * eco.SUBS)
        self.accounts['users'].append({'email': 'saimon888oficial@gmail.com', 'wallet_name': 'Simon', 'name': 'Simon'})
        fusion.apply(self.econ, self.accounts, self.vault, now=200)
        self.vault.pop('fusionSwept', None)
        VAULT.add_smc(VAULT.account(self.vault, 'Nube'), 7 * eco.SUBS)
        balance = self.econ['wallets']['Simon']
        again = fusion.apply(self.econ, self.accounts, self.vault, now=300)
        self.assertTrue(again['changed'])
        self.assertEqual(again['fresh'], [])
        self.assertEqual(self.econ['wallets']['Simon'], balance)
        self.assertEqual(VAULT.smh_of(self.vault['accounts']['Nube']), 0)
        self.assertIn('Nube', self.vault['fusionSwept'])


class HistoriaTests(unittest.TestCase):
    def test_rows_name_the_three_kinds_and_keep_a_running_balance(self):
        import historia
        state = eco.empty_state()
        state['blocks'].append({
            'height': 1, 'ts': 1_700_000_000, 'prev': state['blocks'][0]['hash'], 'hash': 'ab',
            'txs': [
                {'type': 'mint', 'to': 'Ana', 'amountSubs': 1000, 'note': 'batea'},
                {'type': 'pool', 'from': 'Ana', 'to': 'fondo_cambio', 'amountSubs': 200, 'note': 'quinto'},
                {'type': 'exchange', 'from': 'fondo_cambio', 'to': 'Ana', 'amountSubs': 200, 'note': 'Cambio de plata por oro'},
                {'type': 'fusion', 'from': 'Ana', 'to': 'Simon', 'amountSubs': 1000, 'note': fusion.NOTE},
            ],
        })
        state['plata'] = {'txs': [
            {'type': 'pool', 'from': 'Ana', 'amountSmh': 200, 't': 1_700_000_000},
            {'type': 'exchange', 'name': 'Ana', 'gotSmh': 200, 'spentSph': 20000, 't': 1_700_000_010},
        ], 'wallets': {'Ana': 50}}
        rows = historia.filas(state)
        kinds = [row['type'] for row in rows]
        self.assertEqual(kinds, ['reserva', 'minado', 'fondo', 'cambio', 'fusion'])
        self.assertEqual(rows[1]['account'], 'Ana')
        self.assertEqual(rows[1]['balanceSubs'], 1000)
        self.assertEqual(rows[2]['balanceSubs'], 200)
        self.assertEqual(rows[3]['label'], 'Cambio plata→oro')
        self.assertEqual(rows[3]['balanceSubs'], 1000)
        self.assertEqual(rows[4]['label'], 'Fusión')
        self.assertIn(fusion.NOTE, rows[4]['note'])
        self.assertEqual(rows[4]['balanceSubs'], 1000)
        self.assertEqual(rows[4]['account'], 'Ana → Simon')


class HistoriaUiTests(unittest.TestCase):
    def test_browser_history_matches_the_labels(self):
        script = os.path.join(ROOT, 'tools', 'test_historia.js')
        done = subprocess.run(['node', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + '\n' + done.stderr)
        self.assertIn('ok', done.stdout)


if __name__ == '__main__':
    unittest.main()
