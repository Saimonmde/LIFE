# SPDX-License-Identifier: AGPL-3.0-or-later
"""Metal en la cuenta, tope parcial y el correo del fundador."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crudo
import fusion
import supply as sup
import topes


class CrudoTests(unittest.TestCase):
    def test_gold_spends_nuggets_then_ore(self):
        state = {}
        crudo.credit(state, 'cta', 'pepita_oro', 1, cap=4)
        crudo.credit(state, 'cta', 'mineral_oro', 2, cap=4)
        self.assertAlmostEqual(crudo.total(state, 'cta', crudo.ORO), 3)
        spent = crudo.debit(state, 'cta', crudo.ORO, 1.25)
        self.assertAlmostEqual(spent['pepita_oro'], 1)
        self.assertAlmostEqual(spent['mineral_oro'], 0.25)
        self.assertIsNone(crudo.debit(state, 'cta', crudo.ORO, 5))

    def test_migration_is_once_and_capped(self):
        state = {}
        self.assertTrue(crudo.migrar(state, 'cta', {'mineral_oro': 9999, 'madera': 40}))
        self.assertFalse(crudo.migrar(state, 'cta', {'mineral_oro': 10}))
        self.assertEqual(crudo.nuggets(state, 'cta', 'mineral_oro'), 200)
        self.assertEqual(crudo.nuggets(state, 'cta', 'madera'), 0)

    def test_swing_credit_is_capped_per_action(self):
        state = {}
        self.assertEqual(crudo.credit(state, 'cta', 'mineral_cobre', 9), 4)
        self.assertEqual(crudo.nuggets(state, 'cta', 'mineral_cobre'), 4)


class QuoteTests(unittest.TestCase):
    def test_quarter_cap_uses_the_leftover_fraction(self):
        quote = topes.cotizar(2, 5, 0.25, 21_000_000)
        self.assertAlmostEqual(quote['recibes'], 0.25)
        self.assertAlmostEqual(quote['gastas'], 1.25)
        self.assertEqual(topes.simoncoin_daily_smh(60 * 86400, 40 * 3600, 10), int(6.25 * topes.SUBS))


class ReasonTests(unittest.TestCase):
    def test_cooldown_names_the_wait_and_wallet_is_not_the_furnace(self):
        self.assertIn('12 s', sup.reason_text('cooldown', 12))
        wallet = sup.reason_text('wallet')
        self.assertNotIn('horno', wallet.lower())
        self.assertIn('otro aparato', wallet)


class OwnerEmailTests(unittest.TestCase):
    def test_env_overrides_the_hardcoded_fallback(self):
        self.assertEqual(fusion.EMAIL, 'saimon888oficial@gmail.com')
        old = os.environ.get('SIMON_OWNER_EMAIL')
        try:
            os.environ.pop('SIMON_OWNER_EMAIL', None)
            self.assertEqual(fusion.owner_email(), 'saimon888oficial@gmail.com')
            os.environ['SIMON_OWNER_EMAIL'] = 'simon888oficial@gmail.com'
            self.assertEqual(fusion.owner_email(), 'simon888oficial@gmail.com')
        finally:
            if old is None:
                os.environ.pop('SIMON_OWNER_EMAIL', None)
            else:
                os.environ['SIMON_OWNER_EMAIL'] = old


class RelinkTests(unittest.TestCase):
    def test_only_the_owner_can_relink_a_mismatched_wallet(self):
        import server
        old_save = server.save_econ
        old_env = os.environ.get('SIMON_OWNER_EMAIL')
        wallets = server.ECON.setdefault('wallets', {})
        tokens = server.ECON.setdefault('walletTokens', {})
        prev = (wallets.get('Simon'), tokens.get('Simon'), wallets.get('Ana'), tokens.get('Ana'))
        server.save_econ = lambda: None
        os.environ['SIMON_OWNER_EMAIL'] = 'simon888oficial@gmail.com'
        try:
            owner = {'id': 'own', 'email': 'simon888oficial@gmail.com', 'name': 'Simon', 'wallet_name': 'Simon'}
            wallets['Simon'] = 5
            tokens['Simon'] = 'token-viejo'
            server.settle_wallet(owner, 'Simon', 'token-de-otro-aparato')
            self.assertTrue(owner.get('wallet_token'))
            self.assertNotEqual(owner['wallet_token'], 'token-viejo')
            self.assertEqual(tokens['Simon'], owner['wallet_token'])
            other = {'id': 'ana', 'email': 'ana@ejemplo.co', 'name': 'Ana', 'wallet_name': 'Ana'}
            wallets['Ana'] = 1
            tokens['Ana'] = 'secreto'
            server.settle_wallet(other, 'Ana', 'token-ajeno')
            self.assertEqual(tokens['Ana'], 'secreto')
            self.assertFalse(other.get('wallet_token'))
        finally:
            server.save_econ = old_save
            wallets['Simon'], tokens['Simon'], wallets['Ana'], tokens['Ana'] = prev
            if old_env is None:
                os.environ.pop('SIMON_OWNER_EMAIL', None)
            else:
                os.environ['SIMON_OWNER_EMAIL'] = old_env


if __name__ == '__main__':
    unittest.main()
