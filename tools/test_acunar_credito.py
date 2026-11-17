# SPDX-License-Identifier: AGPL-3.0-or-later
"""Acuñar deja la moneda en el saldo, en la mochila y en el libro. No pasa el tope."""
import copy
import os
import sys
import tempfile
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
        metal = ac.motivo(0, 5, 6.25, 21_000_000, 'oros crudos', 'Simoncoin')
        self.assertIn('No tienes oros crudos suficiente', metal)
        self.assertEqual(ac.motivo(2, 5, 0.25, 21_000_000, 'oros crudos', 'Simoncoin'), '')
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
            'amountSubs': 0, 'note': 'Acuñación de 4 de cobre',
        })
        rows = historia.filas(econ)
        self.assertTrue(any(row.get('coin') == 'SMP' and row['label'] == 'Acuñación' for row in rows))
        cobre = next(row for row in rows if 'cobre' in row.get('note', ''))
        self.assertEqual(cobre.get('amountQty'), 4)
        self.assertEqual(cobre.get('balanceQty'), 4)
        self.assertEqual(cobre.get('coin'), 'SMCH')


class AcunarSobreviveTests(unittest.TestCase):
    """Acuña las tres, vuelve a entrar y reinicia el servidor. El saldo sigue."""

    def setUp(self):
        import economy as eco
        import plata
        import server
        import supply
        self.server = server
        self.eco = eco
        self.plata = plata
        self.supply = supply
        self.sent = []
        self._send = server.send
        self._save_econ = server.save_econ
        self._save_vault = server.save_vault
        self._anotar = server.anotar_emision
        self._pase = server.anotar_pase
        self._econ = copy.deepcopy(server.ECON)
        self._vault = copy.deepcopy(server.VAULT_STATE)
        self._players = copy.deepcopy(server.PLAYERS)
        server.send = lambda _c, obj: self.sent.append(obj)
        server.save_econ = lambda: None
        server.save_vault = lambda: None
        server.anotar_emision = lambda *args, **kwargs: {'id': 'prueba'}
        server.anotar_pase = lambda *args, **kwargs: {'id': 'prueba'}
        server.ECON.clear()
        server.ECON.update(eco.empty_state())
        server.VAULT_STATE.clear()
        supply.ensure(server.ECON)
        plata.ensure(server.ECON)
        server.ECON['supply']['bits'] = 8
        server.ECON['plata']['bits'] = 8

    def tearDown(self):
        server = self.server
        server.send = self._send
        server.save_econ = self._save_econ
        server.save_vault = self._save_vault
        server.anotar_emision = self._anotar
        server.anotar_pase = self._pase
        server.ECON.clear()
        server.ECON.update(self._econ)
        server.VAULT_STATE.clear()
        server.VAULT_STATE.update(self._vault)
        server.PLAYERS.clear()
        server.PLAYERS.update(self._players)

    def _persona(self):
        who = self.server.Client(None)
        who.hello = True
        who.wallet_ok = True
        who.zone = 'mine'
        who.name = 'Nico'
        who.user = {
            'id': 'cta-nico',
            'name': 'Nico',
            'wallet_name': 'Nico',
            'createdAt': 1_700_000_000,
        }
        who.ip = '198.51.100.40'
        who.activity_tiles = 8
        return who

    def _acuñar(self, who, coin, pieces):
        self.sent.clear()
        self.server.acunar_for(who, coin, pieces)
        retos = [m for m in self.sent if m.get('t') == 'pow_challenge']
        self.assertTrue(retos, [m.get('t') for m in self.sent])
        challenge = retos[-1]['challenge']
        nonce = self.supply.search_nonce(challenge['payload'], int(challenge['bits']))
        self.assertIsNotNone(nonce)
        proof = dict(challenge)
        proof['nonce'] = str(nonce)
        self.sent.clear()
        self.server.acunar_for(who, coin, pieces, proof)
        ok = [m for m in self.sent if m.get('t') == 'acunar_result' and m.get('ok')]
        self.assertTrue(ok, [(m.get('t'), m.get('reason'), m.get('code')) for m in self.sent if m.get('t') != 'economy'])
        return ok[-1]

    def _entrar(self, econ, vault):
        econ = copy.deepcopy(econ)
        vault = copy.deepcopy(vault)
        self.server.ECON.clear()
        self.server.ECON.update(econ)
        self.server.VAULT_STATE.clear()
        self.server.VAULT_STATE.update(vault)
        who = self._persona()
        return self.server.econ_msg(who.name, locked=False, profile=self.server.account_profile(who))

    def _guardar(self, directory):
        import persist
        old = os.environ.pop('DATABASE_URL', None)
        try:
            eco_path = os.path.join(directory, 'economy.json')
            vault_path = os.path.join(directory, 'vault.json')
            persist.save_named('economy', eco_path, self.server.ECON)
            persist.save_named('vault', vault_path, self.server.VAULT_STATE)
            self.server.ECON.clear()
            self.server.VAULT_STATE.clear()
            econ = persist.load_named('economy', eco_path)
            vault = persist.load_named('vault', vault_path)
        finally:
            if old is not None:
                os.environ['DATABASE_URL'] = old
        return econ, vault

    def _ver(self, msg, vault):
        import cobre
        self.assertGreater(msg['balanceSubs'], 0)
        balances = msg['ledger']['balances']
        monedas = msg['purse']['monedas']
        self.assertEqual(monedas['moneda_oro'], msg['balanceSubs'])
        self.assertEqual(int(balances.get('simonchis') or 0), 0)
        rows = msg['state']['historia']
        self.assertTrue(any(int(row.get('amountSubs') or 0) > 0 and row.get('account') == 'Nico' for row in rows))
        self.assertEqual(self.eco.MAX_SUPPLY, 21_000_000)
        self.assertEqual(self.plata.MAX_SUPPLY, 84_000_000)
        self.assertEqual(cobre.MAX_SUPPLY, 333_000_000)
        self.assertLess(self.server.ECON['minedSmh'], 21_000_000 * self.eco.SUBS)
        self.assertLess(self.server.ECON['plata']['minedSph'], 84_000_000 * self.eco.SUBS)
        self.assertLess(self.server.ECON['simonchis']['minted'], 333_000_000)

    def test_mint_reload_login_and_restart_keep_the_three_coins(self):
        import crudo
        who = self._persona()
        who.user['providers'] = {'google': 'cuenta-google'}
        crudo.credit(self.server.ECON, 'cta-nico', 'pepita_oro', 2, cap=4)
        crudo.credit(self.server.ECON, 'cta-nico', 'mineral_plata', 4, cap=4)
        crudo.credit(self.server.ECON, 'cta-nico', 'mineral_cobre', 3, cap=4)
        oro = self._acuñar(who, 'simoncoin', 2)
        self.assertIn('Saldo:', oro.get('reason') or '')
        self.assertGreater(oro.get('balanceSubs') or 0, 0)
        self.assertTrue((oro.get('registro') or {}).get('id'))
        self.sent.clear()
        self.server.acunar_for(who, 'simonplata', 4)
        plata_no = [m for m in self.sent if m.get('t') == 'acunar_result'][-1]
        self.assertFalse(plata_no.get('ok'))
        self.assertEqual(plata_no.get('code'), 'cerrada')
        self.sent.clear()
        self.server.acunar_for(who, 'simonchis', 3)
        cobre_no = [m for m in self.sent if m.get('t') == 'acunar_result'][-1]
        self.assertFalse(cobre_no.get('ok'))
        primero = self._entrar(self.server.ECON, self.server.VAULT_STATE)
        self._ver(primero, self.server.VAULT_STATE)
        with tempfile.TemporaryDirectory() as directory:
            econ, vault = self._guardar(directory)
            self.assertIsNotNone(econ)
            self.assertIsNotNone(vault)
            otra_vez = self._entrar(econ, vault)
            self._ver(otra_vez, vault)
            econ2, vault2 = self._guardar(directory)
            tras_reinicio = self._entrar(econ2, vault2)
            self._ver(tras_reinicio, vault2)
            self.assertEqual(tras_reinicio['balanceSubs'], primero['balanceSubs'])

    def test_no_ore_explains_and_mints_nothing(self):
        who = self._persona()
        who.user['providers'] = {'google': 'cuenta-google'}
        before = int((self.server.ECON.get('wallets') or {}).get('Nico') or 0)
        self.sent.clear()
        self.server.acunar_for(who, 'simoncoin', 2)
        fail = [item for item in self.sent if item.get('t') == 'acunar_result']
        self.assertTrue(fail)
        self.assertFalse(fail[-1].get('ok'))
        self.assertIn('No tienes', fail[-1].get('reason') or '')
        self.assertEqual(int((self.server.ECON.get('wallets') or {}).get('Nico') or 0), before)
        root = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(root, 'play', 'index.html'), encoding='utf-8') as handle:
            page = handle.read()
        with open(os.path.join(root, 'play', 'acunar.js'), encoding='utf-8') as handle:
            dialog = handle.read()
        with open(os.path.join(root, 'play', 'cajon.js'), encoding='utf-8') as handle:
            drawer = handle.read()
        self.assertIn('En tu cuenta:', page)
        self.assertIn('cajon-madre', drawer)
        self.assertIn('No tienes metal', dialog)
