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
        keys = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'FACEBOOK_APP_ID', 'FACEBOOK_APP_SECRET', 'RESEND_API_KEY', 'EMAIL_FROM', 'SMTP_HOST', 'SMTP_FROM', 'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_VERIFY_SERVICE_SID']
        old = {k: os.environ.pop(k, None) for k in keys}
        try:
            bare = acc.providers()
            self.assertFalse(bare['guest'])
            self.assertFalse(bare['google'])
            self.assertFalse(bare['facebook'])
            self.assertFalse(bare['registro'])
            self.assertFalse(bare['reset'])
            self.assertTrue(bare['email_login'])
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


class EmailLinkTests(unittest.TestCase):
    def test_link_is_single_use_and_blocks_login_until_then(self):
        doc = acc.empty()
        sent = {}

        def send_link(email, raw):
            sent['raw'] = raw

        acc.begin_email_account(doc, 'Nica', 'nica@ejemplo.co', 'secreto-largo', send_link, now=5_000)
        self.assertEqual(doc['users'], [])
        with self.assertRaises(acc.AuthError) as blocked:
            acc.login_password(doc, 'nica@ejemplo.co', 'secreto-largo', now=5_010)
        self.assertIn('Confirma', str(blocked.exception))
        result = acc.confirm_email_link(doc, sent['raw'], now=5_020)
        self.assertEqual(result['user']['wallet_name'], 'Nica')
        self.assertTrue(doc['users'][0]['verified'])
        with self.assertRaises(acc.AuthError):
            acc.confirm_email_link(doc, sent['raw'], now=5_030)
        again = acc.login_password(doc, 'nica@ejemplo.co', 'secreto-largo', now=5_040)
        self.assertEqual(again['user']['id'], result['user']['id'])

    def test_expired_link_and_resend_replaces_it(self):
        doc = acc.empty()
        sent = {}

        def send_link(email, raw):
            sent['raw'] = raw

        acc.begin_email_account(doc, 'Nica', 'nica@ejemplo.co', 'secreto-largo', send_link, now=6_000)
        old = sent['raw']
        with self.assertRaises(acc.AuthError):
            acc.confirm_email_link(doc, old, now=6_000 + acc.LINK_TTL + 1)
        acc.resend_verification(doc, 'nica@ejemplo.co', send_link, now=6_100)
        self.assertNotEqual(sent['raw'], old)
        with self.assertRaises(acc.AuthError):
            acc.confirm_email_link(doc, old, now=6_110)
        acc.confirm_email_link(doc, sent['raw'], now=6_120)
        self.assertEqual(len(doc['users']), 1)

    def test_password_reset_is_single_use(self):
        doc = acc.empty()
        sent = {}

        def send_link(email, raw):
            sent['raw'] = raw

        acc.begin_email_account(doc, 'Nica', 'nica@ejemplo.co', 'secreto-largo', send_link, now=7_000)
        acc.confirm_email_link(doc, sent['raw'], now=7_010)
        acc.request_password_reset(doc, 'nica@ejemplo.co', send_link, now=7_020)
        token = sent['raw']
        acc.reset_password(doc, token, 'otra-clave-larga', now=7_030)
        with self.assertRaises(acc.AuthError):
            acc.login_password(doc, 'nica@ejemplo.co', 'secreto-largo', now=7_040)
        acc.login_password(doc, 'nica@ejemplo.co', 'otra-clave-larga', now=7_050)
        with self.assertRaises(acc.AuthError):
            acc.reset_password(doc, token, 'tercera-clave', now=7_060)

    def test_old_account_without_verified_flag_still_enters(self):
        doc = acc.empty()
        doc['users'].append({
            'id': 'vieja', 'name': 'Ana', 'email': 'ana@ejemplo.co', 'phone': '',
            'password_hash': acc.hash_password('secreto-largo'),
            'providers': {}, 'wallet_name': 'Ana', 'wallet_token': '', 'createdAt': 1,
        })
        result = acc.login_password(doc, 'ana@ejemplo.co', 'secreto-largo', now=8_000)
        self.assertEqual(result['user']['wallet_name'], 'Ana')

    def test_resend_is_rate_limited(self):
        doc = acc.empty()
        acc.begin_email_account(doc, 'Nica', 'nica@ejemplo.co', 'secreto-largo', lambda email, raw: None, now=9_000)
        for i in range(5):
            acc.resend_verification(doc, 'nica@ejemplo.co', lambda email, raw: None, now=9_010 + i)
        with self.assertRaises(acc.AuthError):
            acc.resend_verification(doc, 'nica@ejemplo.co', lambda email, raw: None, now=9_020)


    def test_google_account_sets_nick_and_password_then_logs_in(self):
        doc = acc.empty()
        state = acc.start_oauth(doc, 'google', now=10_000)
        made = acc.finish_oauth(doc, 'google', state, state, {'sub': 'g-ana', 'email': 'ana@gmail.com', 'name': 'Ana'}, now=10_010)
        user = next(u for u in doc['users'] if u['id'] == made['user']['id'])
        self.assertTrue(made['user']['needsPassword'])
        self.assertNotIn('password_hash', made['user'])
        self.assertIn('frase', acc.set_nick_and_password.__doc__)
        with self.assertRaises(acc.AuthError):
            acc.set_nick_and_password(doc, user, 'Ana', 'corta', 'corta', now=10_020)
        with self.assertRaises(acc.AuthError):
            acc.set_nick_and_password(doc, user, 'Ana', 'secreto-largo', 'otra-distinta', now=10_030)
        shown = acc.set_nick_and_password(doc, user, 'ana', 'Secreto-largo-1', 'Secreto-largo-1', now=10_040)
        self.assertFalse(shown['needsPassword'])
        self.assertEqual(user['name'], 'ana')
        self.assertTrue(user['password_hash'].startswith('scrypt$'))
        self.assertNotIn('Secreto-largo-1', user['password_hash'])
        entered = acc.login_nick(doc, 'Ana', 'Secreto-largo-1', now=10_050)
        self.assertEqual(entered['user']['id'], user['id'])
        with self.assertRaises(acc.AuthError) as wrong:
            acc.login_nick(doc, 'Ana', 'clave-equivocada', now=10_060)
        with self.assertRaises(acc.AuthError) as missing:
            acc.login_nick(doc, 'Nadie', 'clave-equivocada', now=10_070)
        self.assertEqual(str(wrong.exception), str(missing.exception))
        other = acc.start_oauth(doc, 'google', now=10_200)
        acc.finish_oauth(doc, 'google', other, other, {'sub': 'g-luz', 'email': 'luz@gmail.com', 'name': 'Luz'}, now=10_210)
        luz = next(u for u in doc['users'] if u['email'] == 'luz@gmail.com')
        with self.assertRaises(acc.AuthError):
            acc.set_nick_and_password(doc, luz, 'Ana', 'Secreto-largo-1', 'Secreto-largo-1', now=10_220)

    def test_simon_is_reserved_for_the_owner_and_has_no_seeded_password(self):
        import os
        old = os.environ.pop('SIMON_OWNER_EMAIL', None)
        self.assertTrue(acc.simon_reserved('Simon'))
        self.assertTrue(acc.simon_reserved('s1mon'))
        self.assertTrue(acc.simon_reserved('$imon'))
        self.assertTrue(acc.simon_reserved('Simón'))
        self.assertFalse(acc.simon_reserved('Minero'))
        doc = acc.empty()
        state = acc.start_oauth(doc, 'google', now=12_000)
        made = acc.finish_oauth(doc, 'google', state, state, {
            'sub': 'g-owner', 'email': 'saimon888oficial@gmail.com', 'name': 'Minero',
        }, now=12_010)
        owner = next(u for u in doc['users'] if u['id'] == made['user']['id'])
        self.assertEqual(owner['password_hash'], '')
        self.assertTrue(made['user']['canClaimSimon'])
        other = acc.start_oauth(doc, 'google', now=12_100)
        copied = acc.finish_oauth(doc, 'google', other, other, {'sub': 'g-copy', 'email': 'otro@gmail.com', 'name': 'S1mon'}, now=12_110)
        self.assertNotEqual(acc.simon_key(copied['user']['name']), 'simon')
        with self.assertRaises(acc.AuthError):
            acc.begin_email_account(doc, '$imon', 'x@ejemplo.co', 'secreto-largo', lambda email, raw: None, now=12_200)
        claimed = acc.claim_simon(doc, owner, now=12_300)
        self.assertEqual(claimed['name'], 'Simon')
        self.assertEqual(owner['password_hash'], '')
        self.assertFalse(claimed['canClaimSimon'])
        stranger = next(u for u in doc['users'] if u['email'] == 'otro@gmail.com')
        with self.assertRaises(acc.AuthError):
            acc.claim_simon(doc, stranger, now=12_310)
        with self.assertRaises(acc.AuthError):
            acc.set_nick_and_password(doc, stranger, 'Simon', 'Secreto-largo-1', 'Secreto-largo-1', now=12_320)

    def test_only_owner_email_can_save_simon_variants(self):
        import os
        old = os.environ.get('SIMON_OWNER_EMAIL')
        os.environ['SIMON_OWNER_EMAIL'] = 'dueno@ejemplo.co'
        try:
            doc = acc.empty()
            stranger = {
                'id': 'minero', 'name': 'Minero', 'email': 'minero@ejemplo.co',
                'password_hash': '', 'wallet_name': 'Minero',
            }
            owner = {
                'id': 'dueno', 'name': 'Fundador', 'email': 'dueno@ejemplo.co',
                'password_hash': '', 'wallet_name': 'Fundador',
            }
            doc['users'].extend([stranger, owner])
            variants = ('Simon', 'simon', 'SIMON', 'Simón', 'S imon', '  símon  ', 'S1mon', '$imon')
            for index, nick in enumerate(variants):
                doc['rates'].pop('clave:minero', None)
                with self.assertRaises(acc.AuthError) as blocked:
                    acc.set_nick_and_password(doc, stranger, nick, 'Secreto-largo-1', 'Secreto-largo-1', now=13_000 + index)
                self.assertIn('reservado', str(blocked.exception).lower())
            self.assertEqual(stranger['name'], 'Minero')
            self.assertEqual(stranger['password_hash'], '')
            saved = acc.set_nick_and_password(doc, owner, 'Simón', 'Secreto-largo-1', 'Secreto-largo-1', now=13_100)
            self.assertEqual(saved['name'], 'Simon')
            self.assertEqual(saved['email'], 'dueno@ejemplo.co')
        finally:
            if old is None:
                os.environ.pop('SIMON_OWNER_EMAIL', None)
            else:
                os.environ['SIMON_OWNER_EMAIL'] = old
        if old is None:
            os.environ.pop('SIMON_OWNER_EMAIL', None)
        else:
            os.environ['SIMON_OWNER_EMAIL'] = old

    def test_owner_favorite_is_world_five_without_touching_the_password(self):
        import os
        old = os.environ.get('SIMON_OWNER_EMAIL')
        os.environ['SIMON_OWNER_EMAIL'] = 'dueno-mundos@ejemplo.co'
        try:
            doc = acc.empty()
            stored = acc.hash_password('Secreto-largo-1')
            owner = {
                'id': 'simon', 'name': 'Simon', 'email': 'dueno-mundos@ejemplo.co',
                'password_hash': stored, 'providers': {}, 'wallet_name': 'Simon', 'wallet_token': '',
            }
            ana = {
                'id': 'ana', 'name': 'Ana', 'email': 'ana@ejemplo.co',
                'password_hash': acc.hash_password('Secreto-largo-1'), 'providers': {},
                'wallet_name': 'Ana', 'wallet_token': '',
            }
            doc['users'].extend([owner, ana])
            entered = acc.login_nick(doc, 'Simon', 'Secreto-largo-1', now=20_000)
            self.assertEqual(owner['password_hash'], stored)
            self.assertTrue(owner['password_hash'].startswith('scrypt$'))
            self.assertEqual(entered['user']['favoriteWorld'], 5)
            self.assertEqual(entered['user']['name'], 'Simon')
            shown = acc.set_favorite_world(doc, owner, 2)
            self.assertEqual(shown['favoriteWorld'], 2)
            self.assertEqual(owner['password_hash'], stored)
            again = acc.login_nick(doc, 'Simon', 'Secreto-largo-1', now=20_100)
            self.assertEqual(again['user']['favoriteWorld'], 2)
            with self.assertRaises(acc.AuthError):
                acc.set_favorite_world(doc, owner, 9)
            guest = acc.login_nick(doc, 'Ana', 'Secreto-largo-1', now=20_200)
            self.assertIsNone(guest['user']['favoriteWorld'])
            self.assertFalse(acc.ensure_owner_favorite(ana))
        finally:
            if old is None:
                os.environ.pop('SIMON_OWNER_EMAIL', None)
            else:
                os.environ['SIMON_OWNER_EMAIL'] = old

    def test_nick_login_is_rate_limited(self):
        doc = acc.empty()
        for i in range(5):
            with self.assertRaises(acc.AuthError):
                acc.login_nick(doc, 'Ana', 'mala-clave', now=11_000 + i)
        with self.assertRaises(acc.AuthError) as limited:
            acc.login_nick(doc, 'Ana', 'mala-clave', now=11_010)
        self.assertIn('Espera', str(limited.exception))


if __name__ == '__main__':
    unittest.main()
