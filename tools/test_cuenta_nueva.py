# SPDX-License-Identifier: AGPL-3.0-or-later
"""Un primo nuevo entra una vez. Al volver, la partida y la clave siguen igual."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import accounts as acc
import partida


class CuentaNuevaTests(unittest.TestCase):
    def test_new_nickname_creates_once_and_a_wrong_password_does_not_overwrite(self):
        doc = acc.empty()
        made = acc.enter_or_create(doc, 'Primo', 'secreto-largo', now=1_000)
        user = next(u for u in doc['users'] if u['id'] == made['user']['id'])
        self.assertTrue(user['password_hash'].startswith('scrypt$'))
        self.assertNotIn('secreto-largo', user['password_hash'])
        self.assertEqual(made['max_age'], acc.SESSION_TTL)
        self.assertEqual(acc.SESSION_TTL, 60 * 60 * 24 * 30)
        self.assertTrue(acc.nick_preview(doc, 'Primo')['nuevo'] is False)
        self.assertTrue(acc.nick_preview(doc, 'Lucia')['nuevo'] is True)
        again = acc.enter_or_create(doc, 'primo', 'secreto-largo', now=1_100)
        self.assertEqual(again['user']['id'], user['id'])
        self.assertEqual(len(doc['users']), 1)
        before = user['password_hash']
        with self.assertRaises(acc.AuthError) as wrong:
            acc.enter_or_create(doc, 'Primo', 'otra-clave-larga', now=1_200)
        self.assertEqual(str(wrong.exception), 'Contraseña incorrecta')
        self.assertEqual(user['password_hash'], before)
        with self.assertRaises(acc.AuthError) as reserved:
            acc.enter_or_create(doc, 'Simon', 'secreto-largo', now=1_300)
        self.assertIn('reservado', str(reserved.exception))
        self.assertEqual(len(doc['users']), 1)
        self.assertFalse(acc.nick_preview(doc, 'Simon')['nuevo'])

    def test_google_creates_one_account_and_the_session_lasts_thirty_days(self):
        doc = acc.empty()
        state = acc.start_oauth(doc, 'google', now=2_000)
        made = acc.finish_oauth(doc, 'google', state, state, {
            'sub': 'g-primo', 'email': 'primo@gmail.com', 'name': 'Primo',
        }, now=2_010)
        self.assertEqual(len(doc['users']), 1)
        self.assertEqual(made['max_age'], 60 * 60 * 24 * 30)
        other = acc.start_oauth(doc, 'google', now=2_100)
        again = acc.finish_oauth(doc, 'google', other, other, {
            'sub': 'g-primo', 'email': 'primo@gmail.com', 'name': 'Primo',
        }, now=2_110)
        self.assertEqual(again['user']['id'], made['user']['id'])
        self.assertEqual(len(doc['users']), 1)
        cookie = acc.cookie('life_session', 'tok', made['max_age'], secure=True)
        self.assertIn('HttpOnly', cookie)
        self.assertIn('Max-Age=%d' % (60 * 60 * 24 * 30), cookie)
        self.assertIn('Secure', cookie)

    def test_returning_player_keeps_progress_nickname_and_favorite(self):
        doc = acc.empty()
        made = acc.enter_or_create(doc, 'Primo', 'secreto-largo', now=3_000)
        user = next(u for u in doc['users'] if u['id'] == made['user']['id'])
        user['finca'] = {'cafe': 4}
        acc.set_favorite_place(doc, user, 'envigado')
        partida.remember(user, {
            'inv': [{'item': 'mineral_cobre', 'qty': 3}],
            'xp': {'mining': 40},
            'position': {'mapId': 'city', 'x': 94.5, 'y': 267.2, 'dir': 'down'},
            'rev': 5,
        })
        shown = partida.recall(user)
        self.assertTrue(shown['saved'])
        self.assertEqual(shown['inv'], [{'item': 'mineral_cobre', 'qty': 3}])
        self.assertEqual(shown['position']['x'], 94.5)
        self.assertEqual(shown['position']['mapId'], 'city')
        self.assertEqual(shown['nick'], 'Primo')
        self.assertEqual(user['favorite_place'], 'envigado')
        self.assertEqual(user['finca']['cafe'], 4)
        self.assertTrue(user['password_hash'].startswith('scrypt$'))

    def test_local_email_signup_creates_one_verified_account(self):
        doc = acc.empty()
        made = acc.create_local_email_account(doc, 'Lucia', 'lucia@ejemplo.co', 'secreto-largo', now=4_000)
        user = next(u for u in doc['users'] if u['id'] == made['user']['id'])
        self.assertTrue(user['verified'])
        self.assertEqual(user['email'], 'lucia@ejemplo.co')
        self.assertNotIn('secreto-largo', user['password_hash'])
        self.assertEqual(len(doc.get('pending') or {}), 0)
        again = acc.login_password(doc, 'lucia@ejemplo.co', 'secreto-largo', now=4_100)
        self.assertEqual(again['user']['id'], user['id'])
        with self.assertRaises(acc.AuthError):
            acc.create_local_email_account(doc, 'Otra', 'lucia@ejemplo.co', 'secreto-largo', now=4_200)
