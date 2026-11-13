# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plata: tope, halving, cambio sin acuñar SMC y sin bypass de administración."""
import copy
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as eco
import plata
import supply as sup
import vault

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def who(**extra):
    base = {
        'account': 'cta-plata',
        'name': 'Mina',
        'ip': '198.51.100.20',
        'age': 0,
        'play': 0,
        'quests': 0,
        'activity': 8,
        'fresh': True,
    }
    base.update(extra)
    return base


def prove(state, person, now):
    opened = plata.open_challenge(state, person, 'plata', 'libre', now=now)
    if not opened['ok']:
        return opened
    challenge = opened['challenge']
    nonce = sup.search_nonce(challenge['payload'], challenge['bits'])
    proof = dict(challenge)
    proof['nonce'] = nonce
    return plata.redeem(state, person, 'plata', 'libre', proof, now=now + 1)


class PlataTests(unittest.TestCase):
    def fresh(self):
        state = eco.empty_state()
        state['plata']['bits'] = 8
        return state

    def test_supply_halving_and_js_safe_integer(self):
        self.assertEqual(plata.PREMINE_SPH, 0)
        self.assertGreater(plata.MAX_SUPPLY, eco.MAX_SUPPLY)
        self.assertLess(plata.MAX_SPH, 2 ** 53)
        self.assertEqual(plata.reward_sph(0), 5 * plata.SUBS)
        self.assertEqual(plata.reward_sph(plata.HALVING_SPH), 5 * plata.SUBS // 2)
        self.assertEqual(plata.reward_sph(plata.MAX_SPH), 0)
        self.assertEqual(plata.daily_cap_sph(0, 0, 0), 5 * plata.SUBS)
        self.assertEqual(plata.daily_cap_sph(sup.DAY, 0, 0), 6 * plata.SUBS)
        full = plata.daily_cap_sph(60 * sup.DAY, 40 * 3600, 10)
        self.assertEqual(full, 125 * plata.SUBS)
        self.assertEqual(plata.exchange_cap_smh(0, 0, 0), sup.BASE_DAILY_SMH // 5)
        self.assertEqual(plata.exchange_cap_smh(60 * sup.DAY, 40 * 3600, 10), 625_000_000 // 5)

    def test_old_smc_balances_stay_and_admin_is_ignored(self):
        state = eco.empty_state()
        secret = state['supply']['secret']
        state['wallets']['Ana'] = 12 * eco.SUBS
        state['minedSmh'] = 40 * eco.SUBS
        plata.ensure(state)
        eco.normalize_state(state)
        self.assertEqual(state['wallets']['Ana'], 12 * eco.SUBS)
        self.assertEqual(state['minedSmh'], 40 * eco.SUBS)
        self.assertEqual(state['supply']['secret'], secret)
        self.assertEqual(state['plata']['premineSph'], 0)
        self.assertNotIn('fondo_cambio', state['wallets'])
        owner = who(admin=True, owner=True, bypass=True, premine=True, role='admin', account='jay', name='Jay')
        plain = who(account='jay', name='Jay')
        self.assertEqual(
            plata.public_view(state, owner)['dailyCapSph'],
            plata.public_view(state, plain)['dailyCapSph'],
        )
        self.assertEqual(
            plata.public_view(state, owner)['exchangeLeftSmh'],
            plata.public_view(state, plain)['exchangeLeftSmh'],
        )
        self.assertNotIn('secret', plata.public_view(state, owner))
        self.assertTrue(plata.reserved_name('Fondo_Cambio'))

    def test_guest_activity_and_replay(self):
        state = self.fresh()
        now = 1_700_000_000
        guest = prove(state, who(account='', name=''), now)
        self.assertEqual(guest['reason'], 'guest')
        self.assertEqual(guest.get('sph', 0), 0)
        still = prove(state, who(activity=3), now)
        self.assertEqual(still['reason'], 'activity')
        stale = plata.open_challenge(state, who(fresh=False), 'plata', 'libre', now=now)
        self.assertEqual(stale['reason'], 'activity')
        person = who()
        opened = plata.open_challenge(state, person, 'plata', 'libre', now=now)
        self.assertTrue(opened['ok'], opened.get('reason'))
        proof = dict(opened['challenge'])
        proof['nonce'] = sup.search_nonce(proof['payload'], proof['bits'])
        good = plata.redeem(state, person, 'plata', 'libre', proof, now=now + 1)
        self.assertTrue(good['ok'], good.get('reason'))
        self.assertEqual(good['sph'], 5 * plata.SUBS)
        self.assertEqual(plata.balance_of(state, 'Mina'), 5 * plata.SUBS)
        self.assertEqual(state.get('minedSmh') or 0, 0)
        again = plata.redeem(state, person, 'plata', 'libre', proof, now=now + 2)
        self.assertEqual(again['reason'], 'replay')
        other = self.fresh()
        opened = plata.open_challenge(other, who(), 'plata', 'otro', now=now)
        proof = dict(opened['challenge'])
        proof['nonce'] = sup.search_nonce(proof['payload'], proof['bits'])
        mismatch = plata.redeem(other, who(), 'plata', 'libre', proof, now=now + 1)
        self.assertEqual(mismatch['reason'], 'action')

    def test_personal_cap_network_cap_and_no_admin_bonus(self):
        state = self.fresh()
        now = 1_800_000_000
        owner = who(admin=True, owner=True, bypass=True, role='admin')
        first = prove(state, owner, now)
        self.assertTrue(first['ok'], first.get('reason'))
        self.assertEqual(first['sph'], plata.BASE_DAILY_SPH)
        blocked = prove(state, owner, now + sup.CLAIM_COOLDOWN + 1)
        self.assertEqual(blocked['reason'], 'cap')
        state = self.fresh()
        state['plata']['bits'] = 4
        rich = who(account='veterana', name='Vera', ip='203.0.113.8', age=60 * sup.DAY, play=40 * 3600, quests=10)
        one = prove(state, rich, now)
        self.assertEqual(one['sph'], 5 * plata.SUBS)
        two = prove(state, rich, now + sup.CLAIM_COOLDOWN + 1)
        self.assertEqual(two['sph'], 5 * plata.SUBS)
        self.assertLess(one['sph'] + two['sph'], plata.daily_cap_sph(rich['age'], rich['play'], rich['quests']))
        capped = self.fresh()
        plata.ensure(capped, now=now)
        acc = capped['plata']['accounts'].setdefault('llena', {})
        acc['epoch'] = now // sup.DAY
        acc['earned'] = plata.daily_cap_sph(0, 0, 0)
        full = prove(capped, who(account='llena', name='Llena'), now)
        self.assertEqual(full['reason'], 'cap')
        net = self.fresh()
        reward = plata.reward_sph(0)
        net['plata']['epoch'] = now // sup.DAY
        net['plata']['epochSubs'] = reward * sup.PROOFS_PER_DAY
        stopped = prove(net, who(account='red', name='Red', ip='203.0.113.9'), now)
        self.assertEqual(stopped['reason'], 'ceiling')
        ended = self.fresh()
        ended['plata']['minedSph'] = plata.MAX_SPH
        room_before = plata.issuance_room(ended)
        self.assertEqual(room_before, 0)
        done = prove(ended, who(account='fin', name='Fin', ip='203.0.113.10'), now)
        self.assertEqual(done['reason'], 'supply')
        self.assertEqual(plata.issuance_room(ended), 0)

    def test_exchange_burns_plata_and_cannot_mint_smc(self):
        state = self.fresh()
        now = 1_900_000_000
        plata.ensure(state, now=now)
        state['wallets']['Ana'] = 12 * eco.SUBS
        mined = 40 * eco.SUBS
        state['minedSmh'] = mined
        state['plata']['smcPoolSmh'] = 10 * eco.SUBS
        state['plata']['wallets']['Vera'] = 200 * plata.SUBS
        state['plata']['minedSph'] = 200 * plata.SUBS
        room = eco.issuance_room(state)
        plata_room = plata.issuance_room(state)
        sup.ensure(state, now=now)
        sup_acc = state['supply']['accounts'].setdefault('veterana', {})
        sup_acc['epoch'] = now // sup.DAY
        sup_acc['earned'] = sup.daily_cap_smh(60 * sup.DAY, 40 * 3600, 10)
        person = who(account='veterana', name='Vera', ip='203.0.113.15', age=60 * sup.DAY, play=40 * 3600, quests=10)
        admin = dict(person, admin=True, owner=True, bypass=True, role='admin')
        self.assertEqual(plata.public_view(state, person)['exchangeLeftSmh'], plata.public_view(state, admin)['exchangeLeftSmh'])
        got = plata.exchange(state, admin, 200 * plata.SUBS, now=now)
        self.assertTrue(got['ok'], got.get('reason'))
        self.assertEqual(got['smh'], eco.SUBS)
        self.assertEqual(got['sph'], 100 * plata.SUBS)
        self.assertEqual(state['wallets']['Vera'], eco.SUBS)
        self.assertEqual(state['wallets']['Ana'], 12 * eco.SUBS)
        self.assertEqual(state['plata']['smcPoolSmh'], 9 * eco.SUBS)
        self.assertEqual(state['plata']['wallets']['Vera'], 100 * plata.SUBS)
        self.assertEqual(state['plata']['burnedSph'], 100 * plata.SUBS)
        self.assertEqual(state['minedSmh'], mined)
        self.assertEqual(eco.issuance_room(state), room)
        self.assertEqual(plata.issuance_room(state), plata_room)
        self.assertEqual(state['wallets']['Vera'] + state['plata']['smcPoolSmh'], 10 * eco.SUBS)
        again = plata.exchange(state, person, None, now=now + sup.CLAIM_COOLDOWN + 1)
        self.assertEqual(again['reason'], 'slice')
        self.assertEqual(state['minedSmh'], mined)
        dust = self.fresh()
        dust['plata']['smcPoolSmh'] = 5 * eco.SUBS
        dust['plata']['wallets']['Mina'] = 99
        dust['plata']['minedSph'] = 99
        tiny = plata.exchange(dust, who(), 99, now=now)
        self.assertEqual(tiny['reason'], 'dust')
        self.assertEqual(dust['plata']['wallets']['Mina'], 99)
        self.assertEqual(dust['plata']['burnedSph'], 0)
        empty = self.fresh()
        empty['plata']['wallets']['Mina'] = 100 * plata.SUBS
        none = plata.exchange(empty, who(), None, now=now)
        self.assertEqual(none['reason'], 'pool')
        self.assertEqual(empty.get('minedSmh') or 0, 0)
        self.assertEqual(eco.issuance_room(empty), eco.issuance_room(eco.empty_state()))
        self.assertEqual(
            plata.reason_text('pool'),
            'El fondo de oro se está llenando; vuelve cuando se mine más SMC',
        )

    def test_vault_moves_plata_without_minting(self):
        state = self.fresh()
        now = 1_800_000_000
        plata.ensure(state, now=now)
        state['plata']['wallets']['Mina'] = 3 * plata.SUBS
        state['plata']['minedSph'] = 3 * plata.SUBS
        state['minedSmh'] = 9 * eco.SUBS
        mined_smc = state['minedSmh']
        mined_smp = state['plata']['minedSph']
        room = plata.issuance_room(state)
        box = vault.account(vault.empty(), 'Mina')
        self.assertTrue(plata.park(state, 'Mina', plata.SUBS))
        vault.add_smp(box, plata.SUBS)
        self.assertEqual(plata.balance_of(state, 'Mina'), 2 * plata.SUBS)
        self.assertEqual(vault.sph_of(box), plata.SUBS)
        self.assertFalse(plata.park(state, 'Mina', 9 * plata.SUBS))
        self.assertEqual(plata.balance_of(state, 'Mina'), 2 * plata.SUBS)
        self.assertTrue(vault.take_smp(box, plata.SUBS))
        self.assertTrue(plata.unpark(state, 'Mina', plata.SUBS))
        self.assertEqual(plata.balance_of(state, 'Mina'), 3 * plata.SUBS)
        self.assertEqual(vault.sph_of(box), 0)
        self.assertFalse(vault.take_smp(box, 1))
        self.assertEqual(state['minedSmh'], mined_smc)
        self.assertEqual(state['plata']['minedSph'], mined_smp)
        self.assertEqual(plata.issuance_room(state), room)
        self.assertEqual(state['plata'].get('smcPoolSmh') or 0, 0)
        public = vault.public_account(box)
        self.assertEqual(public['sph'], 0)
        self.assertEqual(public['smh'], 0)

    def test_one_account_cannot_drain_the_pool(self):
        state = self.fresh()
        now = 2_000_000_000
        state['plata']['smcPoolSmh'] = 10 * eco.SUBS
        taken = 0
        for i in range(6):
            name = f'P{i}'
            state['plata']['wallets'][name] = 200 * plata.SUBS
            person = who(account=f'c{i}', name=name, ip='198.51.100.77', age=60 * sup.DAY, play=40 * 3600, quests=10)
            result = plata.exchange(state, person, None, now=now + i)
            if i < 5:
                self.assertTrue(result['ok'], result.get('reason'))
                self.assertEqual(result['smh'], eco.SUBS)
                taken += result['smh']
            else:
                self.assertFalse(result['ok'])
                self.assertEqual(result['reason'], 'exchange_ceiling')
        self.assertEqual(taken, 5 * eco.SUBS)
        self.assertEqual(state['plata']['smcPoolSmh'], 5 * eco.SUBS)
        self.assertEqual(state.get('minedSmh') or 0, 0)

    def test_skim_is_one_fifth_and_does_not_create_smc(self):
        state = eco.empty_state()
        state['wallets']['Ana'] = 1000
        mined = state['minedSmh']
        kept, pooled = plata.apartar(state, 'Ana', 1000, now=1_700_000_000)
        self.assertEqual(pooled, 200)
        self.assertEqual(kept, 800)
        self.assertEqual(state['wallets']['Ana'], 800)
        self.assertEqual(state['plata']['smcPoolSmh'], 200)
        self.assertEqual(state['minedSmh'], mined)
        dust_kept, dust_pool = plata.apartar(state, 'Ana', 4, now=1_700_000_100)
        self.assertEqual(dust_pool, 0)
        self.assertEqual(dust_kept, 4)
        plata.devolver(state, 'Ana', 200, now=1_700_000_101)
        self.assertEqual(state['wallets']['Ana'], 1000)
        self.assertEqual(state['plata']['smcPoolSmh'], 0)
        server = open(os.path.join(ROOT, 'server.py'), encoding='utf-8').read()
        quest = server.split('def quest_for', 1)[1].split('\ndef ', 1)[0]
        emitir = server.split('def emitir', 1)[1].split('\ndef ', 1)[0]
        self.assertNotIn('apartar', quest)
        self.assertIn('apartar', emitir)
        self.assertNotIn('def premine', open(os.path.join(ROOT, 'tools', 'plata.py'), encoding='utf-8').read())
        layout = open(os.path.join(ROOT, 'play', 'hud-layout.js'), encoding='utf-8').read()
        self.assertIn("['plata-panel', 'Plata', 'hud']", layout)
        html = open(os.path.join(ROOT, 'play', 'index.html'), encoding='utf-8').read()
        self.assertIn('id="plata-panel" class="hud"', html)
        css = open(os.path.join(ROOT, 'play', 'style.css'), encoding='utf-8').read()
        self.assertIn('#plata-panel', css)
        self.assertIn('var(--sans)', css)
        self.assertNotIn('Unifraktur', css)


class ServerPlataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, ROOT)
        import server
        cls.server = server

    def test_river_skim_and_plata_mint_ignore_admin(self):
        s = self.server
        econ = copy.deepcopy(s.ECON)
        libro = copy.deepcopy(s.LIBRO_CHAIN)
        ready = dict(s.NODE_READY)
        try:
            s.ECON.setdefault('supply', {})['bits'] = 8
            plata.ensure(s.ECON, now=int(time.time()))
            s.ECON['plata']['bits'] = 8
            node = next(n for n in s.GOLD_NODES if n['id'] == 'oro_fluvial_1')
            token = s.bind_wallet('BateaPlata', '')
            before = int(s.ECON.get('minedSmh') or 0)

            class Who:
                bot = False
                w = None
                zone = 'city'
                x, y = 0, 0
                wallet_ok = True
                wallet_token = token
                name = 'BateaPlata'
                ip = '198.51.100.40'
                activity_tiles = 8
                last_activity_at = time.time()
                user = {'id': 'cta-plata-server', 'createdAt': time.time(), 'admin': True, 'owner': True, 'bypass': True, 'role': 'admin'}

            who = Who()
            who.x, who.y = node['x'] + 1, node['y']
            s.mint_for(who, 'oro_fluvial_1')
            challenge = who.pow_challenge
            nonce = sup.search_nonce(challenge['payload'], challenge['bits'])
            proof = dict(challenge)
            proof['nonce'] = nonce
            s.mint_for(who, 'oro_fluvial_1', proof)
            delta = int(s.ECON.get('minedSmh') or 0) - before
            self.assertEqual(delta, sup.BASE_DAILY_SMH)
            pool = int(s.ECON['plata']['smcPoolSmh'])
            wallet = int(s.ECON['wallets']['BateaPlata'])
            self.assertEqual(pool, delta // 5)
            self.assertEqual(wallet, delta - pool)
            self.assertEqual(pool + wallet, delta)

            who.activity_tiles = 8
            who.last_activity_at = time.time()
            before_smc = int(s.ECON.get('minedSmh') or 0)
            s.mint_plata(who)
            challenge = who.pow_challenge
            self.assertEqual(challenge.get('coin'), 'SMP')
            nonce = sup.search_nonce(challenge['payload'], challenge['bits'])
            proof = dict(challenge)
            proof['nonce'] = nonce
            s.mint_plata(who, proof)
            self.assertEqual(plata.balance_of(s.ECON, 'BateaPlata'), 5 * plata.SUBS)
            self.assertEqual(int(s.ECON.get('minedSmh') or 0), before_smc)
            held = plata.balance_of(s.ECON, 'BateaPlata')
            s.mint_plata(who, proof)
            self.assertEqual(plata.balance_of(s.ECON, 'BateaPlata'), held)

            guest = Who()
            guest.user = {}
            guest.name = 'Invitada'
            guest.wallet_ok = True
            s.mint_plata(guest)
            self.assertEqual(plata.balance_of(s.ECON, 'Invitada'), 0)
        finally:
            s.ECON.clear()
            s.ECON.update(econ)
            s.LIBRO_CHAIN.clear()
            s.LIBRO_CHAIN.update(libro)
            s.NODE_READY.clear()
            s.NODE_READY.update(ready)
            s.save_econ()


if __name__ == '__main__':
    unittest.main()
