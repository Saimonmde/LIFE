# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prueba de trabajo, retarget, tope y curva por cuenta. Nadie tiene bypass."""
import copy
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as eco
import supply as sup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def profile(**extra):
    base = {
        'account': 'cta-1',
        'ip': '198.51.100.10',
        'age': 0,
        'play': 0,
        'quests': 0,
        'activity': 8,
        'fresh': True,
    }
    base.update(extra)
    return base


def prove(state, who, action, context, now, **kw):
    opened = sup.open_challenge(state, who, action, context, now=now)
    if not opened['ok']:
        return opened
    challenge = opened['challenge']
    nonce = sup.search_nonce(challenge['payload'], challenge['bits'])
    proof = dict(challenge)
    proof['nonce'] = nonce
    return sup.redeem(state, who, action, context, proof, now=now + 1, **kw)


class ProofTests(unittest.TestCase):
    def fresh(self):
        state = eco.empty_state()
        state['supply']['bits'] = 8
        return state

    def test_verify_replay_and_expiry(self):
        state = self.fresh()
        who = profile()
        now = 1_700_000_000
        opened = sup.open_challenge(state, who, 'mint', 'oro_1', now=now)
        self.assertTrue(opened['ok'])
        challenge = opened['challenge']
        bad = dict(challenge)
        bad['nonce'] = '0'
        weak = sup.redeem(state, who, 'mint', 'oro_1', bad, now=now + 1)
        if sup.leading_zero_bits(__import__('hashlib').sha256(f"{challenge['payload']}|0".encode()).hexdigest()) < challenge['bits']:
            self.assertFalse(weak['ok'])
            self.assertEqual(weak['reason'], 'weak')
        nonce = sup.search_nonce(challenge['payload'], challenge['bits'])
        proof = dict(challenge)
        proof['nonce'] = nonce
        good = sup.redeem(state, who, 'mint', 'oro_1', proof, now=now + 1)
        self.assertTrue(good['ok'], good.get('reason'))
        self.assertGreater(good['smh'], 0)
        again = sup.redeem(state, who, 'mint', 'oro_1', proof, now=now + 2)
        self.assertFalse(again['ok'])
        self.assertEqual(again['reason'], 'replay')
        later = sup.redeem(state, who, 'mint', 'oro_1', proof, now=challenge['exp'] + 5)
        self.assertFalse(later['ok'])
        self.assertIn(later['reason'], ('replay', 'expired'))
        other = self.fresh()
        opened = sup.open_challenge(other, who, 'mint', 'oro_1', now=now)
        proof = dict(opened['challenge'])
        proof['nonce'] = sup.search_nonce(proof['payload'], proof['bits'])
        expired = sup.redeem(other, who, 'mint', 'oro_1', proof, now=proof['exp'] + 1)
        self.assertEqual(expired['reason'], 'expired')
        forged = dict(opened['challenge'])
        forged['sig'] = '0' * 64
        forged['nonce'] = '1'
        self.assertEqual(sup.redeem(other, who, 'mint', 'oro_1', forged, now=now + 1)['reason'], 'signature')

    def test_retarget_follows_the_recent_rate(self):
        self.assertEqual(sup.retarget_bits(16, 12, 12 * sup.TARGET_INTERVAL), 16)
        self.assertEqual(sup.retarget_bits(16, 12, 12 * 150), 18)
        self.assertEqual(sup.retarget_bits(16, 1, 8000), 12)
        self.assertEqual(sup.retarget_bits(18, 12, 12), 20)
        state = self.fresh()
        state['supply']['bits'] = 8
        start = 1_700_000_000
        sup.ensure(state, now=start)
        state['supply']['windowStart'] = start
        for i in range(12):
            who = profile(account=f'cta-{i}', ip=f'198.51.100.{i + 1}')
            result = prove(state, who, 'mint', 'oro_1', start + i)
            self.assertTrue(result['ok'], result.get('reason'))
        self.assertEqual(state['supply']['bits'], 12)
        self.assertEqual(state['supply']['windowProofs'], 0)

    def test_cap_and_unlock_curve_and_no_admin_bypass(self):
        self.assertEqual(sup.daily_cap_smh(0, 0, 0), sup.BASE_DAILY_SMH)
        self.assertEqual(sup.daily_cap_smh(sup.DAY, 0, 0), sup.BASE_DAILY_SMH + sup.AGE_SMH)
        full = sup.daily_cap_smh(60 * sup.DAY, 40 * 3600, 10)
        self.assertEqual(full, 625_000_000)
        self.assertEqual(sup.daily_cap_smh(0, 0, 0), sup.daily_cap_smh(0, 0, 0))
        owner = profile(admin=True, owner=True, bypass=True, premine=True, role='admin', account='jay')
        plain = profile(account='jay')
        self.assertEqual(
            sup.daily_cap_smh(owner['age'], owner['play'], owner['quests']),
            sup.daily_cap_smh(plain['age'], plain['play'], plain['quests']),
        )
        state = self.fresh()
        now = 1_800_000_000
        owned = prove(state, owner, 'mint', 'oro_1', now)
        self.assertTrue(owned['ok'], owned.get('reason'))
        self.assertEqual(owned['smh'], sup.BASE_DAILY_SMH)
        self.assertLess(owned['smh'], eco.SUBS)
        state = self.fresh()
        state['minedSmh'] = eco.smc_to_smh(eco.MAX_SUPPLY - eco.TREASURY) - 1000
        state['supply']['epochSubs'] = 0
        room = eco.issuance_room(state)
        veteran = profile(account='veterana', ip='203.0.113.8', age=60 * sup.DAY, play=40 * 3600, quests=10)
        first = prove(state, veteran, 'mint', 'oro_1', now)
        self.assertTrue(first['ok'], first.get('reason'))
        self.assertEqual(first['smh'], min(eco.SUBS, full, room))
        self.assertEqual(first['smh'], 1000)
        state['minedSmh'] += first['smh']
        blocked = prove(state, profile(account='otra', ip='203.0.113.9'), 'mint', 'oro_2', now + 5)
        self.assertFalse(blocked['ok'])
        self.assertEqual(blocked['reason'], 'supply')
        curve = eco.empty_state()
        curve['supply']['bits'] = 4
        rich = profile(account='rica', ip='203.0.113.15', age=60 * sup.DAY, play=40 * 3600, quests=10)
        base = 1_900_000_000
        one = prove(curve, rich, 'mint', 'oro_1', base)
        self.assertEqual(one['smh'], eco.SUBS)
        two = prove(curve, rich, 'mint', 'oro_1', base + sup.CLAIM_COOLDOWN + 1)
        self.assertEqual(two['smh'], eco.SUBS // 2)
        three = prove(curve, rich, 'mint', 'oro_1', base + 2 * (sup.CLAIM_COOLDOWN + 1))
        self.assertEqual(three['smh'], eco.SUBS // 4)
        guest = prove(curve, profile(account=''), 'mint', 'oro_1', base + 10)
        self.assertEqual(guest['reason'], 'guest')
        self.assertNotIn('secret', str(sup.public_view(curve, rich)))

    def test_old_ledger_keeps_balances_and_treasury(self):
        old = eco.empty_state()
        wallets = old['wallets']['tesoro_genesis']
        genesis = old['blocks'][0]['hash']
        old['wallets']['Ana'] = 12 * eco.SUBS
        old['minedSmh'] = 40 * eco.SUBS
        secret_before = old['supply']['secret']
        eco.normalize_state(old)
        self.assertEqual(old['wallets']['tesoro_genesis'], wallets)
        self.assertEqual(old['wallets']['tesoro_genesis'], eco.TREASURY_SMH)
        self.assertEqual(old['wallets']['Ana'], 12 * eco.SUBS)
        self.assertEqual(old['minedSmh'], 40 * eco.SUBS)
        self.assertEqual(old['blocks'][0]['hash'], genesis)
        self.assertEqual(old['supply']['secret'], secret_before)
        self.assertNotIn('admin_mint', open(os.path.join(ROOT, 'server.py'), encoding='utf-8').read())
        self.assertNotIn('def premine', open(os.path.join(ROOT, 'tools', 'supply.py'), encoding='utf-8').read())

    def test_partial_migration_can_continue_next_day(self):
        state = eco.empty_state()
        first = eco.migrate_monedas(state, 'Ana', 40, limit_smh=eco.SUBS)
        self.assertEqual(first['credited'], eco.SUBS)
        self.assertFalse(first['done'])
        again = eco.migrate_monedas(state, 'Ana', 40, limit_smh=eco.SUBS)
        self.assertEqual(again['credited'], eco.SUBS)
        self.assertEqual(state['wallets']['Ana'], 2 * eco.SUBS)
        legacy = eco.empty_state()
        legacy['migrations'] = {'Ana': {'requested': eco.SUBS, 'credited': eco.SUBS, 'unit': 'SMH'}}
        done = eco.migrate_monedas(legacy, 'Ana', 40)
        self.assertTrue(done['already'])
        self.assertEqual(done['credited'], 0)


class ServerMintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, ROOT)
        import server
        cls.server = server

    def test_river_mint_needs_proof_and_admin_gets_the_same_cap(self):
        s = self.server
        econ = copy.deepcopy(s.ECON)
        libro = copy.deepcopy(s.LIBRO_CHAIN)
        ready = dict(s.NODE_READY)
        try:
            s.ECON.setdefault('supply', {})['bits'] = 8
            node = next(n for n in s.GOLD_NODES if n['id'] == 'oro_fluvial_1')
            name = 'BateaPrueba'
            token = s.bind_wallet(name, '')
            before = int(s.ECON.get('minedSmh') or 0)

            class Who:
                bot = False
                w = None
                zone = 'city'
                x, y = 0, 0
                wallet_ok = True
                wallet_token = token
                name = 'BateaPrueba'
                ip = '198.51.100.40'
                activity_tiles = 8
                last_activity_at = time.time()
                user = {'id': 'cta-batea', 'createdAt': time.time(), 'admin': True, 'owner': True, 'bypass': True, 'role': 'admin'}
            who = Who()
            who.x, who.y = node['x'] + 20, node['y'] + 20
            s.mint_for(who, 'oro_fluvial_1')
            self.assertEqual(int(s.ECON.get('minedSmh') or 0), before)
            who.x, who.y = node['x'] + 1, node['y']
            who.user = {}
            s.mint_for(who, 'oro_fluvial_1')
            self.assertEqual(int(s.ECON.get('minedSmh') or 0), before)
            who.user = {'id': 'cta-batea', 'createdAt': time.time(), 'admin': True, 'bypass': True}
            s.mint_for(who, 'oro_fluvial_1')
            self.assertEqual(int(s.ECON.get('minedSmh') or 0), before)
            challenge = who.pow_challenge
            nonce = sup.search_nonce(challenge['payload'], challenge['bits'])
            proof = dict(challenge)
            proof['nonce'] = nonce
            s.mint_for(who, 'oro_fluvial_1', proof)
            self.assertEqual(int(s.ECON.get('minedSmh') or 0) - before, sup.BASE_DAILY_SMH)
            mid = int(s.ECON.get('minedSmh') or 0)
            s.mint_for(who, 'oro_fluvial_1', proof)
            self.assertEqual(int(s.ECON.get('minedSmh') or 0), mid)
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
