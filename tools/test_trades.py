# SPDX-License-Identifier: AGPL-3.0-or-later
import copy
import json
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cobre
import economy
import ed25519
import historia
import libro
import plata
import purses
import trades
from trades import TradeError, Trades


class TradeTests(unittest.TestCase):
    def setUp(self):
        self.clients = {
            i: SimpleNamespace(id=i, name=n, hello=True, bot=False, wallet_ok=True, zone='city', x=0, y=0)
            for i, n in [(1, 'Ana'), (2, 'Luis'), (3, 'Sol')]
        }
        self.wallets = {'Ana': 100, 'Luis': 50, 'Sol': 0}
        self.messages = []
        self.commits = []
        self.tick = 0

        def commit(a, b, left, right, key):
            self.wallets[a] += right['smc'] - left['smc']
            self.wallets[b] += left['smc'] - right['smc']
            self.commits.append(key)

        def balances(name):
            return {'smc': self.wallets[name], 'smp': 0, 'cobre': 0, 'items': {}}

        self.t = Trades(self.clients, lambda c, m: self.messages.append((c.id, m)), balances, commit, lambda: self.tick)
        self.t.handle(self.clients[1], {'t': 'trade_start', 'peer': 2})
        self.s = next(iter(self.t.sessions.values()))

    def act(self, player, action, **kw):
        return self.t.handle(self.clients[player], {
            't': 'trade_' + action, 'id': self.s['id'], 'revision': self.s['revision'], **kw,
        })

    def offers(self):
        self.act(1, 'offer', offer={'smc': 30})
        self.act(2, 'offer', offer={'smc': 10})

    def accept(self):
        self.act(1, 'accept')
        self.act(2, 'accept')

    def test_four_acceptances_and_conservation(self):
        self.offers()
        self.accept()
        self.assertEqual(self.wallets['Ana'], 100)
        self.act(1, 'confirm')
        self.assertFalse(self.commits)
        self.act(2, 'confirm')
        self.assertEqual(self.wallets, {'Ana': 80, 'Luis': 70, 'Sol': 0})
        self.assertEqual(len(self.commits), 1)
        self.assertFalse(self.t.sessions)
        with self.assertRaises(TradeError):
            self.act(2, 'confirm')
        self.assertEqual(len(self.commits), 1)

    def test_offer_change_invalidates_both_stages(self):
        self.offers()
        self.accept()
        self.act(1, 'confirm')
        self.act(2, 'offer', offer={'smc': 15})
        self.assertEqual(self.s['accepted'], [])
        self.assertEqual(self.s['confirmed'], [])
        with self.assertRaises(TradeError):
            self.act(1, 'confirm')

    def test_stale_revision(self):
        self.offers()
        with self.assertRaises(TradeError):
            self.act(1, 'accept', revision=0)

    def test_cannot_confirm_without_both_first_acceptances(self):
        self.offers()
        self.act(1, 'accept')
        with self.assertRaises(TradeError):
            self.act(1, 'confirm')

    def test_invalid_amounts(self):
        for n in [-1, 1.1, True, '3', None, 101, 10 ** 30]:
            with self.subTest(n=n), self.assertRaises(TradeError):
                self.act(1, 'offer', amountSmh=n)
        self.assertFalse(self.commits)

    def test_insufficient_balance_after_acceptance(self):
        self.offers()
        self.accept()
        self.act(1, 'confirm')
        self.wallets['Ana'] = 20
        with self.assertRaises(TradeError):
            self.act(2, 'confirm')
        self.assertFalse(self.commits)
        self.assertEqual(self.s['accepted'], [])

    def test_intruder(self):
        with self.assertRaises(TradeError):
            self.act(3, 'offer', offer={'smc': 0})
        self.t.handle(self.clients[3], {'t': 'trade_cancel', 'id': self.s['id']})
        self.assertTrue(self.t.sessions)

    def test_one_session_per_player(self):
        with self.assertRaises(TradeError):
            self.t.handle(self.clients[3], {'t': 'trade_start', 'peer': 1})

    def test_disconnect_cancels(self):
        self.offers()
        self.t.cancel(1, 'Desconexión')
        self.assertFalse(self.t.by_player)
        self.assertFalse(self.commits)

    def test_distance(self):
        self.offers()
        self.clients[2].x = 16
        self.act(1, 'accept')
        self.assertFalse(self.t.sessions)

    def test_lock(self):
        self.offers()
        self.clients[2].wallet_ok = False
        self.act(1, 'accept')
        self.assertFalse(self.t.sessions)

    def test_timeout(self):
        self.tick = 181
        self.t.expire()
        self.assertFalse(self.t.sessions)

    def test_storage_failure(self):
        self.offers()
        self.accept()
        self.act(1, 'confirm')

        def fail(*args):
            raise OSError('disk full')

        self.t.commit = fail
        self.act(2, 'confirm')
        self.assertEqual(self.wallets['Ana'], 100)
        self.assertFalse(self.t.sessions)

    def test_zero_offer_allows_gift(self):
        self.act(1, 'offer', offer={'smc': 100})
        self.accept()
        self.act(1, 'confirm')
        self.act(2, 'confirm')
        self.assertEqual(self.wallets['Ana'], 0)
        self.assertEqual(self.wallets['Luis'], 150)

    def test_empty_trade_rejected(self):
        with self.assertRaises(TradeError):
            self.act(1, 'accept')

    def test_invalid_start_targets(self):
        self.t.cancel(1)
        for peer in [1, 99, True, '2']:
            with self.subTest(peer=peer), self.assertRaises(TradeError):
                self.t.handle(self.clients[1], {'t': 'trade_start', 'peer': peer})

    def test_cancel_id_must_match(self):
        self.act(1, 'cancel', id='stale')
        self.assertTrue(self.t.sessions)
        self.act(1, 'cancel')
        self.assertFalse(self.t.sessions)

    def test_items_smp_and_copper_with_private_ledger(self):
        econ = economy.empty_state()
        econ['wallets']['Nica'] = 5 * economy.SUBS
        econ['wallets']['Teo'] = economy.SUBS
        plata.ensure(econ)
        econ['plata']['wallets']['Nica'] = 2 * plata.SUBS
        cobre.ensure(econ)
        cobre.credit_named(econ, 'Nica', 4)
        vault = {'purses': {}}
        purses.credit(vault, 'Nica', 'bolsa_cafe', 2)
        purses.credit(vault, 'Teo', 'bolsa_cacao', 1)
        seed = os.urandom(32)
        chain = libro.empty(ed25519.publickey(seed).hex())
        libro.acuñar(chain, seed, 'Nica', 5 * economy.SUBS, 'prueba', bits=1)
        libro.acuñar(chain, seed, 'Teo', economy.SUBS, 'prueba', bits=1)
        trades.apply_exchange(
            econ, vault, chain, seed, 'Nica', 'Teo',
            {'smc': economy.SUBS, 'smp': plata.SUBS, 'cobre': 3, 'items': {'bolsa_cafe': 1}},
            {'items': {'bolsa_cacao': 1}},
            'trade-test',
        )
        self.assertEqual(econ['wallets']['Nica'], 4 * economy.SUBS)
        self.assertEqual(econ['wallets']['Teo'], 2 * economy.SUBS)
        self.assertEqual(plata.balance_of(econ, 'Nica'), plata.SUBS)
        self.assertEqual(plata.balance_of(econ, 'Teo'), plata.SUBS)
        self.assertEqual(cobre.balance_of(econ, 'Nica'), 1)
        self.assertEqual(cobre.balance_of(econ, 'Teo'), 3)
        self.assertEqual(purses.count(vault, 'Teo', 'bolsa_cafe'), 1)
        self.assertEqual(purses.count(vault, 'Nica', 'bolsa_cacao'), 1)
        shown = json.dumps({'mempool': econ['mempool'], 'historia': historia.filas(econ)}, ensure_ascii=False)
        self.assertNotIn('Nica', shown)
        self.assertNotIn('Teo', shown)
        self.assertIn('bolsa_cafe', shown)
        views = [libro.publico(block) for block in chain['blocks'] if block.get('kind') == 'intercambio']
        self.assertEqual(len(views), 1)
        self.assertEqual(views[0]['from'], '')
        self.assertEqual(views[0]['to'], '')
        self.assertNotIn('Nica', json.dumps(views))
        self.assertEqual(libro.balances(chain)['Nica'], 4 * economy.SUBS)
        self.assertEqual(libro.balances(chain)['Teo'], 2 * economy.SUBS)
        self.assertEqual(econ['minedSmh'], 0)
        self.assertEqual(econ['plata']['minedSph'], 0)
        self.assertEqual(econ['simonchis']['minted'], 0)
        txs = [tx for block in econ['blocks'] for tx in (block.get('txs') or [])]
        txs.extend(econ.get('mempool') or [])
        legs = next(tx['legs'] for tx in txs if tx.get('type') == 'trade')
        assets = {leg['asset'] for leg in legs}
        self.assertEqual(assets, {'smc', 'smp', 'cobre', 'item'})

    def test_both_see_the_new_balances_of_the_three_coins(self):
        clients = {
            1: SimpleNamespace(id=1, name='Ana', hello=True, bot=False, wallet_ok=True, zone='city', world=3, x=0, y=0),
            2: SimpleNamespace(id=2, name='Luis', hello=True, bot=False, wallet_ok=True, zone='city', world=3, x=1, y=0),
        }
        box = {
            'Ana': {'smc': 2 * economy.SUBS, 'smp': 3 * plata.SUBS, 'cobre': 4},
            'Luis': {'smc': economy.SUBS, 'smp': plata.SUBS, 'cobre': 1},
        }
        messages = []

        def commit(a, b, left, right, key):
            box[a]['smc'] += right['smc'] - left['smc']
            box[b]['smc'] += left['smc'] - right['smc']
            box[a]['smp'] += right['smp'] - left['smp']
            box[b]['smp'] += left['smp'] - right['smp']
            box[a]['cobre'] += right['cobre'] - left['cobre']
            box[b]['cobre'] += left['cobre'] - right['cobre']

        def balances(name):
            row = box[name]
            return {'smc': row['smc'], 'smp': row['smp'], 'cobre': row['cobre'], 'items': {}}

        desk = Trades(clients, lambda c, m: messages.append((c.id, m)), balances, commit, lambda: 0)
        desk.handle(clients[1], {'t': 'trade_start', 'peer': 2})
        session = next(iter(desk.sessions.values()))

        def step(player, action, **kw):
            desk.handle(clients[player], {
                't': 'trade_' + action, 'id': session['id'], 'revision': session['revision'], **kw,
            })

        step(1, 'offer', offer={'smc': economy.SUBS, 'smp': plata.SUBS, 'cobre': 2})
        step(2, 'offer', offer={'smc': 0, 'smp': 0, 'cobre': 0})
        step(1, 'accept')
        step(2, 'accept')
        step(1, 'confirm')
        step(2, 'confirm')
        done = [msg for _who, msg in messages if msg.get('t') == 'trade_end' and msg.get('ok')]
        self.assertEqual(len(done), 2)
        by_balance = {item['balances']['cobre']: item for item in done}
        ana = by_balance[2]
        luis = by_balance[3]
        self.assertEqual(ana['balances'], {'smc': economy.SUBS, 'smp': 2 * plata.SUBS, 'cobre': 2})
        self.assertEqual(luis['balances'], {'smc': 2 * economy.SUBS, 'smp': 2 * plata.SUBS, 'cobre': 3})
        self.assertIn('Intercambiaste. Saldo: 1 SMC, 2 SMP, 2 Simonchis.', ana['reason'])
        self.assertIn('Intercambiaste. Saldo: 2 SMC, 2 SMP, 3 Simonchis.', luis['reason'])
        self.assertEqual(economy.MAX_SUPPLY, 21_000_000)
        self.assertEqual(plata.MAX_SUPPLY, 84_000_000)

    def test_the_mine_counts_and_a_house_does_not(self):
        self.t.cancel(1)
        ana, luis = self.clients[1], self.clients[2]
        ana.zone = luis.zone = 'mine'
        ana.world = luis.world = 3
        ana.x, ana.y = 100, 100
        luis.x, luis.y = 101, 100
        ana.zx, ana.zy = 18, 27
        luis.zx, luis.zy = 2, 2
        with self.assertRaises(TradeError):
            self.t.handle(ana, {'t': 'trade_start', 'peer': 2})
        luis.zy = 28
        luis.zx = 18
        self.t.handle(ana, {'t': 'trade_start', 'peer': 2})
        self.assertTrue(self.t.sessions)
        self.t.cancel(1)
        ana.zone = luis.zone = 'casa'
        with self.assertRaises(TradeError):
            self.t.handle(ana, {'t': 'trade_start', 'peer': 2})

    def test_the_hud_names_the_three_balances(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        page = open(os.path.join(root, 'play', 'index.html'), encoding='utf-8').read()
        drawer = open(os.path.join(root, 'play', 'cajon.js'), encoding='utf-8').read()
        trade = open(os.path.join(root, 'play', 'economy-ui.js'), encoding='utf-8').read()
        self.assertIn('id="sai-saldo"', page)
        self.assertIn('id="plata-saldo"', page)
        self.assertIn('id="chis-saldo"', page)
        self.assertIn('Sólo hay Simoncoin', page)
        self.assertIn('exactSimoncoin', drawer)
        self.assertIn('0,1 cada uno', drawer)
        self.assertIn('Simoncoin (SMC o SMH)', trade)
        self.assertIn('150 SMH', trade)

    def test_full_bags_can_swap_the_same_item_without_loss(self):
        econ = economy.empty_state()
        seed = bytes(range(32))
        chain = libro.empty(ed25519.publickey(seed).hex())
        vault = {'purses': {'Ana': {'bolsa_cacao': purses.MAX_STACK},
                            'Luis': {'bolsa_cacao': purses.MAX_STACK}}}
        trades.apply_exchange(econ, vault, chain, seed, 'Ana', 'Luis',
                              {'items': {'bolsa_cacao': 1}},
                              {'items': {'bolsa_cacao': 1}}, 'full-swap')
        self.assertEqual(purses.count(vault, 'Ana', 'bolsa_cacao'), purses.MAX_STACK)
        self.assertEqual(purses.count(vault, 'Luis', 'bolsa_cacao'), purses.MAX_STACK)

    def test_destination_overflow_rejects_before_any_changes(self):
        for sender, recipient in [('Ana', 'Luis'), ('Luis', 'Ana')]:
            with self.subTest(sender=sender):
                econ = economy.empty_state()
                econ['wallets'].update(Ana=100, Luis=100)
                seed = bytes(range(32))
                chain = libro.empty(ed25519.publickey(seed).hex())
                libro.acuñar(chain, seed, 'Ana', 100, 'prueba', bits=1)
                libro.acuñar(chain, seed, 'Luis', 100, 'prueba', bits=1)
                plata.ensure(econ)
                cobre.ensure(econ)
                vault = {'purses': {sender: {'bolsa_cacao': 5},
                                    recipient: {'bolsa_cacao': purses.MAX_STACK}}}
                before = copy.deepcopy((econ, vault, chain))
                offer = {'smc': 1, 'items': {'bolsa_cacao': 1}}
                left, right = (offer, {}) if sender == 'Ana' else ({}, offer)
                with self.assertRaisesRegex(TradeError, 'espacio'):
                    trades.apply_exchange(econ, vault, chain, seed, 'Ana', 'Luis',
                                          left, right, 'overflow')
                self.assertEqual((econ, vault, chain), before)

    def test_trade_can_fill_exactly_the_remaining_item_space(self):
        econ = economy.empty_state()
        seed = bytes(range(32))
        chain = libro.empty(ed25519.publickey(seed).hex())
        vault = {'purses': {'Ana': {'bolsa_cacao': 2},
                            'Luis': {'bolsa_cacao': purses.MAX_STACK - 2}}}
        trades.apply_exchange(econ, vault, chain, seed, 'Ana', 'Luis',
                              {'items': {'bolsa_cacao': 2}}, {}, 'exact-fill')
        self.assertEqual(purses.count(vault, 'Ana', 'bolsa_cacao'), 0)
        self.assertEqual(purses.count(vault, 'Luis', 'bolsa_cacao'), purses.MAX_STACK)


if __name__ == '__main__':
    unittest.main()
