# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cuentas: contraseña, códigos, sesión y el state de OAuth, con proveedores simulados."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import accounts as acc


class AccountTests(unittest.TestCase):
    def test_password_hash_and_session(self):
        stored = acc.hash_password('secreto-largo')
        self.assertTrue(acc.verify_password('secreto-largo', stored))
        self.assertFalse(acc.verify_password('otra-clave', stored))
        doc = acc.empty()
        sent = {}

        def send_email(email, code):
            sent['email'] = code

        def start_sms(phone):
            sent['phone'] = phone

        def check_sms(phone, code):
            return phone == '+573001112233' and code == '654321'

        acc.begin_signup(doc, 'Ana', 'ana@ejemplo.co', '+573001112233', 'secreto-largo', send_email, start_sms, now=1_000)
        self.assertEqual(len(sent['email']), 6)
        with self.assertRaises(acc.AuthError):
            acc.verify_signup(doc, 'ana@ejemplo.co', '000000', '654321', check_sms, now=1_100)
        result = acc.verify_signup(doc, 'ana@ejemplo.co', sent['email'], '654321', check_sms, now=1_200)
        self.assertEqual(result['user']['wallet_name'], 'Ana')
        self.assertEqual(acc.session_user(doc, result['token'], now=1_200)['email'], 'ana@ejemplo.co')
        self.assertIsNone(acc.session_user(doc, result['token'], now=1_200 + acc.SESSION_TTL + 1))
        with self.assertRaises(acc.AuthError):
            acc.verify_signup(doc, 'ana@ejemplo.co', sent['email'], '654321', check_sms, now=1_000 + acc.CODE_TTL + 5)

    def test_rate_limit(self):
        doc = acc.empty()
        calls = {'n': 0}

        def send_email(email, code):
            calls['n'] += 1

        def start_sms(phone):
            pass

        for i in range(5):
            acc.begin_signup(doc, 'Ana', 'ana@ejemplo.co', '+573001112233', 'secreto-largo', send_email, start_sms, now=2_000 + i)
        with self.assertRaises(acc.AuthError):
            acc.begin_signup(doc, 'Ana', 'ana@ejemplo.co', '+573001112233', 'secreto-largo', send_email, start_sms, now=2_010)

    def test_oauth_state(self):
        doc = acc.empty()
        state = acc.start_oauth(doc, 'google', now=3_000)
        with self.assertRaises(acc.AuthError):
            acc.finish_oauth(doc, 'google', 'mal', state, {'sub': 'g1', 'email': 'a@b.co', 'name': 'Ana'}, now=3_010)
        result = acc.finish_oauth(doc, 'google', state, state, {'sub': 'g1', 'email': 'a@b.co', 'name': 'Ana'}, now=3_010)
        self.assertEqual(result['user']['name'], 'Ana')
        state2 = acc.start_oauth(doc, 'google', now=3_100)
        again = acc.finish_oauth(doc, 'google', state2, state2, {'sub': 'g1', 'name': 'Ana'}, now=3_110)
        self.assertEqual(again['user']['id'], result['user']['id'])

    def test_link_keeps_the_old_wallet(self):
        doc = acc.empty()
        state = acc.start_oauth(doc, 'google', now=4_000)
        result = acc.finish_oauth(doc, 'google', state, state, {'sub': 'g9', 'name': 'Nuevo'}, now=4_010)
        user = next(u for u in doc['users'] if u['id'] == result['user']['id'])
        acc.link_wallet(user, 'Ana', 'abc123')
        self.assertEqual(user['wallet_name'], 'Ana')
        self.assertEqual(user['wallet_token'], 'abc123')

    def test_provider_buttons_follow_env(self):
        keys = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'FACEBOOK_APP_ID', 'FACEBOOK_APP_SECRET', 'RESEND_API_KEY', 'EMAIL_FROM', 'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_VERIFY_SERVICE_SID']
        old = {k: os.environ.pop(k, None) for k in keys}
        try:
            self.assertTrue(acc.providers()['guest'])
            self.assertFalse(acc.providers()['google'])
            os.environ['GOOGLE_CLIENT_ID'] = 'id'
            os.environ['GOOGLE_CLIENT_SECRET'] = 'secret'
            self.assertTrue(acc.providers()['google'])
            self.assertFalse(acc.providers()['registro'])
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == '__main__':
    unittest.main()
