# SPDX-License-Identifier: AGPL-3.0-or-later
"""Acuñación parcial, saldo en SMC, minado holgado, traslado y finca."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acunar_credito as ac
import economy as eco
import finca
import historia
import mover_al_banco as mover
import supply as sup
import topes
import traslado
import vault

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CompactTests(unittest.TestCase):
    def test_soft_spanish_decimals(self):
        self.assertEqual(eco.format_compact(950), '950')
        self.assertEqual(eco.format_compact(1200), '1,2 k')
        self.assertEqual(eco.format_compact(3450), '3,45 k')
        self.assertEqual(eco.format_compact(1_200_000), '1,2 M')
        self.assertEqual(eco.format_compact(0), '0')
        self.assertEqual(eco.format_compact(0.5), '0,5')

    def test_balance_is_smc_not_the_raw_simonchi_count(self):
        half = 50_000_000
        hundreds = 500 * eco.SUBS
        self.assertEqual(eco.format_smc(half), '0,5 SMC')
        self.assertNotIn('50.000.000 SMC', eco.format_smc(half))
        self.assertEqual(eco.format_compact(half / eco.SUBS), '0,5')
        self.assertEqual(eco.format_smc(hundreds), '500 SMC')
        self.assertEqual(eco.format_compact(hundreds / eco.SUBS), '500')
        self.assertEqual(eco.format_smh(hundreds), '50.000.000.000 SMH')
        page = open(os.path.join(ROOT, 'play', 'simulacion.js'), encoding='utf-8').read()
        self.assertIn('function formatCompact', page)
        self.assertIn('holdingsSmh', page)


class RepairTests(unittest.TestCase):
    def test_only_impossible_balances_are_divided_and_logged(self):
        state = eco.empty_state()
        state['wallets']['Ana'] = 12 * eco.SUBS
        state['wallets']['Luz'] = 3 * eco.SUBS * eco.SUBS
        lines = []
        eco.repair_balances(state, log=lines.append)
        self.assertEqual(state['wallets']['Ana'], 12 * eco.SUBS)
        self.assertEqual(state['wallets']['Luz'], 3 * eco.SUBS)
        self.assertEqual(state['wallets']['tesoro_genesis'], eco.TREASURY_SMH)
        self.assertTrue(any('Luz' in line and 'antes' in line and 'después' in line for line in lines))
        self.assertFalse(any('Ana' in line for line in lines))
        again = eco.repair_balances(state, log=lines.append)
        self.assertEqual(again, [])


class MintTests(unittest.TestCase):
    def test_partial_gold_and_a_clear_copper_message(self):
        one = topes.cotizar(1, 5, 50, 21_000_000)
        self.assertAlmostEqual(one['recibes'], 0.2)
        self.assertAlmostEqual(one['gastas'], 1)
        two = topes.cotizar(2, 5, 50, 21_000_000)
        self.assertAlmostEqual(two['recibes'], 0.4)
        self.assertEqual(ac.motivo(2, 5, 50, 21_000_000, 'oros crudos', 'Simoncoin'), '')
        self.assertIn('te falta 1', ac.explicar(2, 3, 'cobre', whole=True))
        self.assertIn('Tienes 2', ac.explicar(2, 3, 'cobre', whole=True))
        self.assertEqual(ac.explicar(2, 5, 'oros crudos', whole=False), '')
        dialog = open(os.path.join(ROOT, 'play', 'acunar.js'), encoding='utf-8').read()
        self.assertIn('No tienes metal', dialog)
        self.assertIn('crudo', dialog)

    def test_cap_still_stops_at_21_million(self):
        state = eco.empty_state()
        state['minedSmh'] = eco.smc_to_smh(eco.MAX_SUPPLY - eco.TREASURY - 1)
        got = eco.issue(state, 'Ana', eco.smc_to_smh(5), 'prueba', 'mint', now=10)
        self.assertEqual(got, eco.SUBS)
        self.assertEqual(eco.issue(state, 'Ana', eco.SUBS, 'otra', 'mint', now=20), 0)
        self.assertLessEqual(state['minedSmh'] + eco.TREASURY_SMH, eco.MAX_SMH)


class MineLimitTests(unittest.TestCase):
    def test_daily_limit_is_loose_and_configurable_without_duplicating(self):
        self.assertGreaterEqual(sup.enforced_daily_smh(0, 0, 0), 50 * eco.SUBS)
        old = os.environ.get('MINE_DAILY_SMC')
        os.environ['MINE_DAILY_SMC'] = '2'
        try:
            self.assertGreaterEqual(sup.enforced_daily_smh(0, 0, 0), 2 * eco.SUBS)
        finally:
            if old is None:
                os.environ.pop('MINE_DAILY_SMC', None)
            else:
                os.environ['MINE_DAILY_SMC'] = old
        state = eco.empty_state()
        state['supply']['bits'] = 4
        who = {
            'account': 'cta-mina', 'ip': '198.51.100.20', 'age': 0, 'play': 0,
            'quests': 0, 'activity': 8, 'fresh': True,
        }
        opened = sup.open_challenge(state, who, 'mint', 'oro_1', now=1_000)
        self.assertTrue(opened['ok'], opened.get('reason'))
        proof = dict(opened['challenge'])
        proof['nonce'] = sup.search_nonce(proof['payload'], proof['bits'])
        first = sup.redeem(state, who, 'mint', 'oro_1', proof, now=1_001)
        self.assertTrue(first['ok'], first.get('reason'))
        again = sup.redeem(state, who, 'mint', 'oro_1', proof, now=1_002)
        self.assertFalse(again['ok'])
        self.assertEqual(again['reason'], 'replay')
        self.assertEqual(first['smh'], min(eco.SUBS, sup.enforced_daily_smh(0, 0, 0)))


class TransferTests(unittest.TestCase):
    def test_transfer_all_to_bank_and_wallet_is_ledgered_once(self):
        state = eco.empty_state()
        box = vault.empty()
        eco.credit(state, 'Jay', 500 * eco.SUBS)
        eco.append_tx(state, {'type': 'mint', 'to': 'Jay', 'amountSubs': 500 * eco.SUBS, 'note': 'minado'}, now=10)
        first = traslado.trasladar(state, box, 'Jay', 'banco')
        self.assertTrue(first['ok'], first.get('reason'))
        self.assertEqual(state['wallets']['Jay'], 0)
        self.assertEqual(vault.smh_of(vault.account(box, 'Jay')), 500 * eco.SUBS)
        second = traslado.trasladar(state, box, 'Jay', 'banco')
        self.assertFalse(second['ok'])
        self.assertEqual(vault.smh_of(vault.account(box, 'Jay')), 500 * eco.SUBS)
        back = traslado.trasladar(state, box, 'Jay', 'billetera')
        self.assertTrue(back['ok'])
        self.assertEqual(state['wallets']['Jay'], 500 * eco.SUBS)
        self.assertEqual(vault.smh_of(vault.account(box, 'Jay')), 0)
        notes = [tx.get('note') for block in state['blocks'] for tx in block.get('txs', [])]
        notes += [tx.get('note') for tx in state.get('mempool') or []]
        self.assertIn('Transferir todo al banco', notes)
        self.assertIn('Transferir todo a la billetera', notes)
        self.assertEqual(notes.count('Transferir todo al banco'), 1)
        rows = historia.filas(state)
        self.assertTrue(any(row.get('label') == 'Banquito' and int(row.get('amountSubs') or 0) == 500 * eco.SUBS for row in rows))
        page = open(os.path.join(ROOT, 'play', 'index.html'), encoding='utf-8').read()
        self.assertIn('Transferir todo al banco', page)
        self.assertIn('Transferir todo a la billetera', page)


class FincaButtonTests(unittest.TestCase):
    def test_pick_process_chain_and_export_does_not_mint_smc(self):
        import reloj
        config = finca.load_config()
        state = finca.empty_state()
        purse = type('P', (), {})()
        purse.bal = {}
        purse.minted = {'simoncoin': 10, 'simonplata': 4, 'simonchis': 1}
        purse.foundry = {}

        def balance(coin, name):
            return int(purse.bal.get((coin, name), 0))

        def move(coin, src, dst, amount):
            amount = int(amount)
            if amount <= 0 or balance(coin, src) < amount:
                return False
            purse.bal[(coin, src)] = balance(coin, src) - amount
            purse.bal[(coin, dst)] = balance(coin, dst) + amount
            return True

        def supply():
            return {
                'simoncoin': purse.minted['simoncoin'], 'simonplata': purse.minted['simonplata'],
                'simonchis': purse.minted['simonchis'], 'simoncoinSum': 0, 'simonplataSum': 0,
                'simonchisSum': 0, 'foundry': {},
            }

        purse.balance = balance
        purse.move = move
        purse.supply = supply
        purse.bal[('simonplata', config['buyer'])] = 20 * eco.SUBS
        now = 1_700_000_000
        planted = finca.act(state, purse, config, 'Jay', 'plantar', {'plot': 'cafe-1'}, now, present=True)
        self.assertTrue(planted['ok'], planted.get('error'))
        picked = finca.act(state, purse, config, 'Jay', 'recoger', {'crop': 'cafe'}, now + 3 * reloj.REAL_SECONDS_PER_DAY, present=True)
        self.assertTrue(picked['ok'], picked.get('error'))
        self.assertIn('inventario', picked.get('note') or '')
        goods = state['accounts']['Jay']['goods']['cafe_cereza']
        self.assertGreaterEqual(goods, 1)
        self.assertGreater(state['harvestedKg']['cafe'], 0)
        empty = finca.act(state, purse, config, 'Jay', 'procesar', {'crop': 'cafe'}, now + 3 * reloj.REAL_SECONDS_PER_DAY, present=True)
        self.assertFalse(empty['ok'])
        self.assertIn('recolecciones', empty.get('error') or '')
        serial = 'CAF-TEST'
        state['bags'][serial] = {
            'serial': serial, 'crop': 'cafe', 'kg': 70, 'product': 'Café excelso',
            'owner': 'Jay', 'place': 'mochila', 'hash': 'abc', 'chain': [],
        }
        before = purse.minted['simoncoin']
        exported = finca.act(state, purse, config, 'Jay', 'exportar', {'crop': 'cafe'}, now + 4 * reloj.REAL_SECONDS_PER_DAY, present=True)
        self.assertTrue(exported['ok'], exported.get('error'))
        self.assertEqual(purse.minted['simoncoin'], before)
        self.assertGreater(balance('simonplata', 'Jay'), 0)
        self.assertEqual(state['bags'][serial]['place'], 'vendido')
        self.assertEqual(finca.batch_balance(config['crops']['cafe'], config)['sackKg'], 70)
        self.assertEqual(finca.batch_balance(config['crops']['cacao'], config)['sackKg'], 150)
        ui = open(os.path.join(ROOT, 'play', 'finca.js'), encoding='utf-8').read()
        for label in ('Recoger café', 'Procesar café', 'Exportar café', 'Recoger cacao', 'Procesar cacao', 'Exportar cacao'):
            self.assertIn(label, ui)


class BankMoveTests(unittest.TestCase):
    def test_dry_run_prints_and_apply_lands_in_the_bank(self):
        state = eco.empty_state()
        box = vault.empty()
        accounts = {'users': [{'email': 'saimon888oficial@gmail.com', 'name': 'Jay', 'wallet_name': 'Jay'}]}
        eco.credit(state, 'Jay', 200 * eco.SUBS)
        eco.credit(state, 'Ana', 40 * eco.SUBS)
        eco.credit(state, 'tesoro_genesis', 0)
        planned = mover.plan(state, box, accounts, scope='jay')
        self.assertEqual(planned['dest'], 'Jay')
        self.assertEqual([row['from'] for row in planned['rows']], ['Jay'])
        self.assertEqual(planned['rows'][0]['smh'], 200 * eco.SUBS)
        self.assertTrue(planned['dryRun'])
        self.assertEqual(state['wallets']['Jay'], 200 * eco.SUBS)
        everyone = mover.plan(state, box, accounts, scope='all')
        self.assertCountEqual([row['from'] for row in everyone['rows']], ['Jay', 'Ana'])
        done = mover.apply_plan(state, box, accounts, scope='jay')
        self.assertFalse(done['dryRun'])
        self.assertEqual(state['wallets']['Jay'], 0)
        self.assertEqual(state['wallets']['Ana'], 40 * eco.SUBS)
        self.assertEqual(vault.smh_of(vault.account(box, 'Jay')), 200 * eco.SUBS)
        notes = [tx.get('note') for block in state['blocks'] for tx in block.get('txs') or []]
        notes += [tx.get('note') for tx in state.get('mempool') or []]
        self.assertIn('SMC minado al banco de Jay', notes)
        directory = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(directory, 'state'))
            env = dict(os.environ)
            env.pop('DATABASE_URL', None)
            proc = subprocess.run(
                [sys.executable, os.path.join(ROOT, 'tools', 'mover_al_banco.py'), '--scope', 'jay', '--state-dir', directory],
                cwd=ROOT, env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('Ensayo solamente', proc.stdout)
        finally:
            shutil.rmtree(directory)


if __name__ == '__main__':
    unittest.main()
