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
        }, now=3_010)
        self.assertEqual(len(doc['users']), 1)
        user = doc['users'][0]
        self.assertEqual(entered['user']['id'], user['id'])
        self.assertTrue(acc.is_owner(user))
        self.assertEqual(user['wallet_name'], 'saimon')
        self.assertEqual(user['email'], fusion.owner_email())
        self.assertIn('juanescasimon@gmail.com', user['aliases'])


if __name__ == '__main__':
    unittest.main()
