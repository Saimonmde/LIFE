# SPDX-License-Identifier: AGPL-3.0-or-later
"""Permisos, ida y vuelta y el mundo de muestras separado del público."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'server'))
import world_edits as ed


def admin():
    return {'id': 'adm', 'name': 'Admin', 'email': 'admin@ejemplo.co', 'role': 'admin'}


def player():
    return {'id': 'ply', 'name': 'Ana', 'email': 'ana@ejemplo.co', 'role': 'player'}


def role_of(user, header=''):
    if str(user.get('email') or '') == 'dueno@ejemplo.co':
        return 'simon'
    role = user.get('role') or 'player'
    return role if role in ('player', 'staff', 'admin', 'simon') else 'player'


class PermissionTests(unittest.TestCase):
    def test_only_admins_can_write(self):
        doc = ed.empty_doc('public')
        body = {'op': 'replace', 'baseVersion': 0, 'current': {'paths': [{'style': 'piedra', 'x': 3, 'z': 4}]}}
        denied = ed.apply_request(doc, player(), body, role_of=role_of)
        self.assertFalse(denied['ok'])
        self.assertEqual(denied['code'], 403)
        self.assertIn('administrador', denied['error'])
        self.assertEqual(doc['version'], 0)
        staff = ed.apply_request(doc, {'role': 'staff', 'email': 's@ejemplo.co'}, body, role_of=role_of)
        self.assertEqual(staff['code'], 403)
        guest = ed.apply_request(doc, None, body)
        self.assertEqual(guest['code'], 403)
        allowed = ed.apply_request(doc, admin(), body, role_of=role_of)
        self.assertTrue(allowed['ok'])
        self.assertEqual(allowed['code'], 200)
        self.assertEqual(allowed['stored']['current']['paths'][0]['style'], 'piedra')
        owner = {'role': 'player', 'email': 'dueno@ejemplo.co', 'name': 'Simon'}
        again = ed.apply_request(allowed['stored'], owner, {'op': 'replace', 'baseVersion': 1, 'current': {'paths': []}}, role_of=role_of)
        self.assertTrue(again['ok'])

    def test_admin_flag_and_env_list(self):
        self.assertTrue(ed.can_edit({'admin': True, 'role': 'player'}))
        self.assertTrue(ed.can_edit({'owner': True}))
        self.assertTrue(ed.can_edit({'role': 'dev'}))
        self.assertFalse(ed.can_edit({'role': 'player', 'bypass': True, 'premine': True}))
        old = os.environ.get('ADMIN_USERS')
        os.environ['ADMIN_USERS'] = 'otra@ejemplo.co, Ana@Ejemplo.co'
        try:
            self.assertTrue(ed.can_edit({'role': 'player', 'email': 'ana@ejemplo.co'}))
            self.assertFalse(ed.can_edit({'role': 'player', 'email': 'no@ejemplo.co'}))
        finally:
            if old is None:
                os.environ.pop('ADMIN_USERS', None)
            else:
                os.environ['ADMIN_USERS'] = old


class RoundTripTests(unittest.TestCase):
    def test_serialization_rollback_and_promote(self):
        current = {
            'paths': [
                {'style': 'piedra', 'x': 1, 'z': 2},
                {'style': 'adoquin', 'x': 1, 'z': 3},
                {'style': 'carretera', 'x': 1, 'z': 4},
                {'style': 'barro', 'x': 9, 'z': 9},
            ],
            'props': [{'id': 'v1', 'type': 'palma', 'x': 4, 'y': 0, 'z': 6, 'scale': 9, 'rotY': 375, 'grounded': True}],
            'objects': [{'id': 'banco_norte', 'x': 8, 'y': 1, 'z': 9, 'scale': 1.5, 'rotY': 15}],
            'terrain': [{'x': 2, 'z': 2, 'dy': 1.25}],
            'surfaces': [{'x': 2, 'z': 3, 'material': 'brick', 'tint': '#C4784E'}],
        }
        doc = ed.empty_doc('preview')
        saved = ed.apply_request(doc, admin(), {'op': 'replace', 'baseVersion': 0, 'current': current}, now=100)
        self.assertTrue(saved['ok'])
        stored = saved['stored']
        self.assertEqual(ed.loads(ed.dumps(stored)), stored)
        self.assertEqual([p['style'] for p in stored['current']['paths']], ['piedra', 'adoquin', 'carretera'])
        self.assertEqual(stored['current']['props'][0]['scale'], 4)
        self.assertEqual(stored['current']['props'][0]['rotY'], 15)
        self.assertEqual(stored['current']['surfaces'][0]['tint'], '#c4784e')
        self.assertEqual(stored['env'], 'preview')
        nxt = ed.apply_request(stored, admin(), {
            'op': 'replace', 'baseVersion': stored['version'],
            'current': {'paths': [{'style': 'piedra', 'x': 8, 'z': 8}]},
        }, now=200)
        self.assertEqual(nxt['stored']['version'], 2)
        back = ed.apply_request(nxt['stored'], admin(), {'op': 'rollback', 'baseVersion': 2, 'version': 1}, now=300)
        self.assertTrue(back['ok'])
        self.assertEqual(len(back['stored']['current']['paths']), 3)
        clash = ed.apply_request(back['stored'], admin(), {'op': 'replace', 'baseVersion': 1, 'current': {}})
        self.assertEqual(clash['code'], 409)
        named = ed.apply_request(back['stored'], admin(), {
            'op': 'save_design', 'baseVersion': back['stored']['version'], 'name': 'Plaza norte',
        }, now=400)
        design_id = named['stored']['designs'][0]['id']
        package = ed.apply_request(named['stored'], admin(), {'op': 'export_design', 'id': design_id})['package']
        self.assertEqual(package['kind'], 'life-world-design')
        self.assertEqual(package['fromEnv'], 'preview')
        public = ed.empty_doc('public')
        blocked = ed.apply_request(public, admin(), {'op': 'import_design', 'baseVersion': 0, 'package': package, 'apply': True})
        self.assertEqual(blocked['code'], 400)
        promoted = ed.apply_request(public, admin(), {
            'op': 'import_design', 'baseVersion': 0, 'confirm': 'PROMOVER', 'package': package, 'apply': True,
        }, now=500)
        self.assertTrue(promoted['ok'])
        self.assertEqual(promoted['stored']['env'], 'public')
        self.assertEqual(len(promoted['stored']['current']['paths']), 3)
        self.assertTrue(promoted['doc']['editor'])
        hidden = ed.packet(promoted['stored'], player(), role_of=role_of)
        self.assertFalse(hidden['editor'])
        seen = ed.packet(promoted['stored'], admin(), role_of=role_of)
        self.assertTrue(seen['editor'])
        self.assertNotIn('snapshot', seen['designs'][0])

    def test_preview_namespace_seed_and_reset(self):
        self.assertEqual(ed.env_name('preview'), 'preview')
        self.assertEqual(ed.env_name(''), 'public')
        self.assertEqual(ed.env_name('otro'), 'public')
        self.assertEqual(ed.storage_filename('preview'), 'world-edits-preview.json')
        self.assertEqual(ed.storage_filename('public'), 'world-edits.json')
        self.assertNotEqual(ed.storage_name('preview'), ed.storage_name('public'))
        public = ed.empty_doc('public')
        self.assertEqual(ed.apply_request(public, admin(), {'op': 'reset_preview', 'confirm': 'RESTABLECER'})['code'], 400)
        self.assertEqual(ed.apply_request(public, admin(), {'op': 'seed_preview', 'anchor': {'x': 1, 'z': 1}})['code'], 400)
        preview = ed.empty_doc('preview')
        seeded = ed.apply_request(preview, admin(), {'op': 'seed_preview', 'baseVersion': 0, 'anchor': {'x': 10, 'z': 12}}, now=10)
        self.assertTrue(seeded['ok'])
        styles = {item['style'] for item in seeded['stored']['current']['paths']}
        self.assertEqual(styles, {'piedra', 'adoquin', 'carretera'})
        needs = ed.apply_request(seeded['stored'], admin(), {'op': 'reset_preview', 'baseVersion': 1, 'confirm': 'no'})
        self.assertEqual(needs['code'], 400)
        cleared = ed.apply_request(seeded['stored'], admin(), {'op': 'reset_preview', 'baseVersion': 1, 'confirm': 'RESTABLECER'}, now=20)
        self.assertEqual(cleared['stored']['current']['paths'], [])
        self.assertGreater(cleared['stored']['version'], seeded['stored']['version'])


class ServerGateTests(unittest.TestCase):
    def test_server_rejects_non_admin_and_keeps_the_layer(self):
        sys.path.insert(0, ROOT)
        import server
        old = server.WORLD_EDITS
        server.WORLD_EDITS = ed.empty_doc()
        try:
            denied = server.world_edit_request(player(), {
                'op': 'replace', 'baseVersion': 0,
                'current': {'paths': [{'style': 'carretera', 'x': 1, 'z': 1}]},
            }, save=False, announce=False)
            self.assertEqual(denied['code'], 403)
            self.assertEqual(server.WORLD_EDITS['version'], 0)
            ok = server.world_edit_request(admin(), {
                'op': 'replace', 'baseVersion': 0,
                'current': {'paths': [{'style': 'adoquin', 'x': 2, 'z': 5}]},
            }, save=False, announce=False)
            self.assertTrue(ok['ok'])
            self.assertEqual(server.WORLD_EDITS['version'], 1)
            self.assertEqual(server.WORLD_EDITS['current']['paths'][0]['style'], 'adoquin')
        finally:
            server.WORLD_EDITS = old


if __name__ == '__main__':
    unittest.main()
