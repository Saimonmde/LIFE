# SPDX-License-Identifier: AGPL-3.0-or-later
"""El staff modera y edita. No nombra personal, no toca al dueño y no acuña."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import accounts as acc
import social
import staff
import supply


def person(uid, name, email, role='player'):
    return {'id': uid, 'name': name, 'wallet_name': name, 'email': email, 'role': role}


class StaffRoleTests(unittest.TestCase):
    def setUp(self):
        self.owner_email = os.environ.get('SIMON_OWNER_EMAIL')
        self.staff_env = os.environ.get('SIMON_STAFF')
        os.environ['SIMON_OWNER_EMAIL'] = 'dueno@ejemplo.co'
        os.environ.pop('SIMON_STAFF', None)
        self.doc = acc.empty()
        self.owner = person('due', 'Jay', 'dueno@ejemplo.co')
        self.mesa = person('mesa', 'Mesa', 'mesa@ejemplo.co', 'staff')
        self.ana = person('ana', 'Ana', 'ana@ejemplo.co')
        self.doc['users'] = [self.owner, self.mesa, self.ana]

    def tearDown(self):
        if self.owner_email is None:
            os.environ.pop('SIMON_OWNER_EMAIL', None)
        else:
            os.environ['SIMON_OWNER_EMAIL'] = self.owner_email
        if self.staff_env is None:
            os.environ.pop('SIMON_STAFF', None)
        else:
            os.environ['SIMON_STAFF'] = self.staff_env

    def test_owner_grants_and_revokes_and_staff_cannot(self):
        self.assertEqual(social.role_of(self.owner), 'owner')
        self.assertEqual(social.role_of(self.mesa), 'staff')
        self.assertEqual(social.role_of(self.ana), 'player')
        shown = staff.set_staff(self.doc, self.owner, 'ana', True, now=1_700_000_100)
        self.assertEqual(shown['role'], 'staff')
        self.assertEqual(social.role_of(self.ana), 'staff')
        denied = staff.handle(self.doc, self.mesa, {'id': 'ana', 'grant': False})
        self.assertFalse(denied['ok'])
        self.assertEqual(denied['status'], '403 Forbidden')
        self.assertEqual(social.role_of(self.ana), 'staff')
        touched = staff.handle(self.doc, self.owner, {'id': self.owner['id'], 'grant': False})
        self.assertFalse(touched['ok'])
        self.assertEqual(social.role_of(self.owner), 'owner')
        player = staff.handle(self.doc, self.ana, {'id': 'mesa', 'grant': False})
        self.assertFalse(player['ok'])
        self.assertEqual(social.role_of(self.mesa), 'staff')
        gone = staff.set_staff(self.doc, self.owner, 'ana', False, now=1_700_000_200)
        self.assertEqual(gone['role'], 'player')
        self.assertTrue(self.ana.get('staffRevoked'))
        log = self.doc['staffAudit']
        self.assertGreaterEqual(len(log), 2)
        self.assertEqual(log[0]['account'], 'due')
        self.assertEqual(log[0]['action'], 'otorgar_staff')
        self.assertEqual(log[0]['at'], 1_700_000_100)
        self.assertNotIn('password', str(log))

    def test_bootstrap_email_and_revoke_sticks(self):
        os.environ['SIMON_STAFF'] = ' Mesa@ejemplo.co , ana@ejemplo.co '
        fresh = person('nueva', 'Nueva', 'ana@ejemplo.co')
        self.assertEqual(staff.role_of(fresh), 'staff')
        self.assertTrue(staff.apply_bootstrap(fresh))
        self.assertEqual(fresh['role'], 'staff')
        self.assertFalse(staff.apply_bootstrap(self.owner))
        staff.set_staff(self.doc, self.owner, 'ana', False, now=50)
        self.doc['users'].append(self.ana)
        self.assertEqual(staff.role_of(self.ana), 'player')
        self.assertFalse(staff.apply_bootstrap(self.ana))
        listed = {item['id'] for item in staff.list_staff(self.doc)}
        self.assertIn('mesa', listed)
        self.assertNotIn('ana', listed)
        self.assertNotIn('dave', open(os.path.join(os.path.dirname(__file__), 'staff.py'), encoding='utf-8').read().lower())

    def test_google_email_match_is_case_insensitive_for_a_later_account(self):
        os.environ['SIMON_STAFF'] = 'persona@gmail.com,vieja@ejemplo.co,mesa@ejemplo.co'
        doc = acc.empty()
        state = acc.start_oauth(doc, 'google', now=10)
        profile = {'sub': 'sub-nueva', 'email': 'Persona@Gmail.com', 'name': 'Persona'}
        result = acc.finish_oauth(doc, 'google', state, state, profile, now=20)
        created = next(u for u in doc['users'] if (u.get('providers') or {}).get('google') == 'sub-nueva')
        self.assertEqual(created['email'], 'persona@gmail.com')
        self.assertEqual(created['role'], 'staff')
        self.assertEqual(result['user']['role'], 'staff')

        older = {
            'id': 'vieja', 'name': 'Vieja', 'wallet_name': 'Vieja', 'email': '',
            'phone': '', 'password_hash': '', 'providers': {'google': 'sub-vieja'},
            'role': 'player', 'createdAt': 1,
        }
        mixed = {
            'id': 'mixta', 'name': 'Mixta', 'wallet_name': 'Mixta',
            'email': 'Mesa@Ejemplo.CO', 'phone': '', 'password_hash': '',
            'providers': {'google': 'sub-mixta'}, 'role': 'player', 'createdAt': 1,
        }
        doc['users'].extend([older, mixed])
        state = acc.start_oauth(doc, 'google', now=30)
        acc.finish_oauth(doc, 'google', state, state, {
            'sub': 'sub-vieja', 'email': 'VIEJA@ejemplo.co', 'name': 'Vieja',
        }, now=40)
        self.assertEqual(older['email'], 'vieja@ejemplo.co')
        self.assertEqual(older['role'], 'staff')
        state = acc.start_oauth(doc, 'google', now=41)
        acc.finish_oauth(doc, 'google', state, state, {
            'sub': 'sub-mixta', 'email': 'MESA@ejemplo.co', 'name': 'Mixta',
        }, now=42)
        self.assertEqual(mixed['email'], 'mesa@ejemplo.co')
        self.assertEqual(mixed['role'], 'staff')

        sent = {}
        acc.begin_email_account(
            doc, 'Tardia', 'Tardia@ejemplo.co', 'clave-larga-1',
            lambda email, raw: sent.update(raw=raw), now=50,
        )
        os.environ['SIMON_STAFF'] = 'persona@gmail.com,tardia@ejemplo.co'
        linked = acc.confirm_email_link(doc, sent['raw'], now=60)
        tardia = next(u for u in doc['users'] if u.get('email') == 'tardia@ejemplo.co')
        self.assertEqual(tardia['role'], 'staff')
        self.assertEqual(linked['user']['role'], 'staff')

    def test_search_by_nick_or_email(self):
        found = staff.search(self.doc, 'ana@')
        self.assertEqual(found[0]['id'], 'ana')
        found = staff.search(self.doc, 'Mesa')
        self.assertEqual(found[0]['nick'], 'Mesa')
        self.assertEqual(staff.search(self.doc, 'a'), [])

    def test_staff_moderates_and_a_player_does_not(self):
        state = social.empty()
        note = social.add_note(state, 'Ana', 'acct:ana', 'Una nota en el parque', 'parque-envigado', 1, now=30)
        self.assertTrue(note['ok'])
        ident = state['notes'][-1]['id']
        refused = social.moderate(state, 'player', 'note', ident, 'hide', '')
        self.assertFalse(refused['ok'])
        self.assertFalse(state['notes'][-1].get('hidden'))
        hidden = social.moderate(state, 'staff', 'note', ident, 'hide', '')
        self.assertTrue(hidden['ok'])
        self.assertTrue(state['notes'][-1]['hidden'])
        self.assertTrue(social.allows('owner', 'answer_note'))
        self.assertFalse(social.allows('player', 'hide_note'))

    def test_staff_does_not_raise_the_coin_cap(self):
        common = {'account': 'cta', 'name': 'Mesa', 'age': 0, 'play': 0, 'quests': 0, 'activity': 8, 'fresh': True, 'ip': '198.51.100.9'}
        staff_profile = supply._clean_profile(dict(common, role='staff', admin=True, owner=True, bypass=True, premine=True))
        player_profile = supply._clean_profile(dict(common, role='player'))
        self.assertNotIn('role', staff_profile)
        self.assertNotIn('admin', staff_profile)
        self.assertEqual(
            supply.daily_cap_smh(staff_profile['age'], staff_profile['play'], staff_profile['quests']),
            supply.daily_cap_smh(player_profile['age'], player_profile['play'], player_profile['quests']),
        )


if __name__ == '__main__':
    unittest.main()
