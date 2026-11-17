# SPDX-License-Identifier: AGPL-3.0-or-later
"""Entrar con juanescasimon@gmail.com abre la cuenta saimon aunque esa ficha no exista."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import accounts as acc
import fusion


class AliasDuenoTests(unittest.TestCase):
    def setUp(self):
        self._owner = os.environ.pop('SIMON_OWNER_EMAIL', None)

    def tearDown(self):
        if self._owner is None:
            os.environ.pop('SIMON_OWNER_EMAIL', None)
        else:
            os.environ['SIMON_OWNER_EMAIL'] = self._owner

    def test_google_login_without_a_record_lands_on_saimon(self):
        doc = acc.empty()
        owner = {
            'id': 'e3b1fde0bd778e9f', 'name': 'saimon', 'wallet_name': 'saimon',
            'email': fusion.owner_email(), 'providers': {'google': 'g-oficial'},
            'googleSubs': ['g-oficial'], 'verified': True,
            'aliases': ['juanskasimon@gmail.com'],
        }
        dave = {'id': 'dave', 'name': 'Dave', 'wallet_name': 'Dave', 'email': 'dave@example.com'}
        doc['users'] = [owner, dave]
        state = acc.start_oauth(doc, 'google', now=1_000)
        entered = acc.finish_oauth(doc, 'google', state, state, {
            'sub': 'g-juanes', 'email': 'JuanEscaSimon@gmail.com', 'name': 'Juan Esca',
            'email_verified': True,
        }, now=1_010)
        self.assertEqual(entered['user']['id'], owner['id'])
        self.assertEqual(len(doc['users']), 2)
        self.assertEqual(owner['wallet_name'], 'saimon')
        self.assertEqual(owner['email'], fusion.owner_email())
        self.assertEqual(owner['aliases'].count('juanescasimon@gmail.com'), 1)
        self.assertIn('g-juanes', acc.google_subs(owner))
        self.assertEqual(dave['email'], 'dave@example.com')
        self.assertFalse(dave.get('mergedInto'))
        otra = acc.start_oauth(doc, 'google', now=1_100)
        otra_vez = acc.finish_oauth(doc, 'google', otra, otra, {
            'sub': 'g-juanes', 'email': 'juanescasimon@gmail.com', 'name': 'Juan Esca',
            'email_verified': True,
        }, now=1_110)
        self.assertEqual(otra_vez['user']['id'], owner['id'])
        self.assertEqual(owner['aliases'].count('juanescasimon@gmail.com'), 1)
        self.assertEqual(len(doc['users']), 2)

    def test_the_same_mask_with_another_mailbox_stays_a_new_account(self):
        doc = acc.empty()
        owner = {
            'id': 'dueño', 'name': 'saimon', 'wallet_name': 'saimon',
            'email': fusion.owner_email(), 'providers': {'google': 'g1'},
        }
        doc['users'] = [owner]
        state = acc.start_oauth(doc, 'google', now=2_000)
        entered = acc.finish_oauth(doc, 'google', state, state, {
            'sub': 'g-otro', 'email': 'juan@gmail.com', 'name': 'Juan',
        }, now=2_010)
        self.assertNotEqual(entered['user']['id'], owner['id'])
        self.assertEqual(len(doc['users']), 2)
        self.assertNotIn('juan@gmail.com', owner.get('aliases') or [])

    def test_without_an_owner_yet_the_alias_becomes_saimon(self):
        doc = acc.empty()
        state = acc.start_oauth(doc, 'google', now=3_000)
        entered = acc.finish_oauth(doc, 'google', state, state, {
            'sub': 'g-juanes', 'email': 'juanescasimon@gmail.com', 'name': 'Juan Esca',
            'email_verified': True,
        }, now=3_010)
        self.assertEqual(len(doc['users']), 1)
        user = doc['users'][0]
        self.assertEqual(entered['user']['id'], user['id'])
        self.assertTrue(acc.is_owner(user))
        self.assertEqual(user['wallet_name'], 'saimon')
        self.assertEqual(user['email'], fusion.owner_email())
        self.assertIn('juanescasimon@gmail.com', user['aliases'])

    def _dueno(self):
        return {
            'id': 'e3b1fde0bd778e9f', 'name': 'saimon', 'wallet_name': 'saimon',
            'email': fusion.owner_email(), 'providers': {'google': 'g-oficial'},
            'googleSubs': ['g-oficial'], 'aliases': ['juanskasimon@gmail.com'],
        }

    def test_google_verified_lands_on_saimon(self):
        doc = acc.empty()
        owner = self._dueno()
        doc['users'] = [owner]
        state = acc.start_oauth(doc, 'google', now=4_000)
        entered = acc.finish_oauth(doc, 'google', state, state, {
            'sub': 'g-nuevo', 'email': 'juanescasimon@gmail.com', 'name': 'Juan',
            'email_verified': True,
        }, now=4_010)
        self.assertEqual(entered['user']['id'], 'e3b1fde0bd778e9f')
        self.assertEqual(owner['wallet_name'], 'saimon')
        self.assertIn('juanescasimon@gmail.com', owner['aliases'])

    def test_google_unverified_does_not_land_on_saimon(self):
        for flag in (False, None):
            doc = acc.empty()
            owner = self._dueno()
            doc['users'] = [owner]
            aliases = list(owner['aliases'])
            state = acc.start_oauth(doc, 'google', now=5_000)
            profile = {'sub': 'g-nuevo', 'email': 'juanescasimon@gmail.com', 'name': 'Juan'}
            if flag is not None:
                profile['email_verified'] = flag
            with self.assertRaises(acc.AuthError):
                acc.finish_oauth(doc, 'google', state, state, profile, now=5_010)
            self.assertEqual(len(doc['users']), 1)
            self.assertEqual(doc['users'][0]['id'], 'e3b1fde0bd778e9f')
            self.assertEqual(owner['aliases'], aliases)
            self.assertNotIn('g-nuevo', acc.google_subs(owner))

    def test_facebook_with_owner_email_does_not_land_on_saimon(self):
        for email in ('juanescasimon@gmail.com', fusion.owner_email()):
            doc = acc.empty()
            owner = self._dueno()
            doc['users'] = [owner]
            state = acc.start_oauth(doc, 'facebook', now=6_000)
            with self.assertRaises(acc.AuthError):
                acc.finish_oauth(doc, 'facebook', state, state, {
                    'sub': 'fb-1', 'email': email, 'name': 'Juan', 'email_verified': True,
                }, now=6_010)
            self.assertEqual([user['id'] for user in doc['users']], ['e3b1fde0bd778e9f'])
            self.assertNotIn('facebook', owner.get('providers') or {})

    def test_google_profile_treats_missing_or_false_as_unverified(self):
        self.assertTrue(acc.perfil_google({'sub': 'g', 'email': 'a@b.co', 'email_verified': True})['email_verified'])
        self.assertFalse(acc.perfil_google({'sub': 'g', 'email': 'a@b.co', 'email_verified': False})['email_verified'])
        self.assertFalse(acc.perfil_google({'sub': 'g', 'email': 'a@b.co'})['email_verified'])
        self.assertFalse(acc.perfil_google({'email_verified': 'true'})['email_verified'])
        import base64
        import json
        body = base64.urlsafe_b64encode(json.dumps({'email_verified': False}).encode()).decode().rstrip('=')
        token = 'e30.' + body + '.sig'
        denied = acc.perfil_google({'email_verified': True, 'sub': 'g', 'email': 'a@b.co'}, token)
        self.assertFalse(denied['email_verified'])

    def test_another_player_without_the_flag_still_gets_an_account(self):
        doc = acc.empty()
        state = acc.start_oauth(doc, 'google', now=7_000)
        entered = acc.finish_oauth(doc, 'google', state, state, {
            'sub': 'g-ana', 'email': 'ana@gmail.com', 'name': 'Ana',
        }, now=7_010)
        self.assertEqual(entered['user']['email'], 'ana@gmail.com')
        self.assertFalse(acc.is_owner(doc['users'][0]))


if __name__ == '__main__':
    unittest.main()
