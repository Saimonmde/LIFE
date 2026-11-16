# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mascotas, muebles, amigos, mundos, feedback, poste e instructivo."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import accounts as acc
import mascotas
import muebles
import mundos
import partida
import social

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def world():
    with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
        return json.load(handle)


class WorldTests(unittest.TestCase):
    def test_architecture_opens_five_of_333(self):
        self.assertEqual(mundos.CAP, 333)
        self.assertEqual(mundos.open_ids(), (1, 2, 3, 4, 5))
        self.assertEqual(mundos.DEFAULT_WORLD, 3)
        self.assertEqual(mundos.OWNER_FAVORITE_WORLD, 5)
        self.assertEqual(mundos.normalize(None) or mundos.DEFAULT_WORLD, 3)
        self.assertEqual(mundos.normalize(1), 1)
        self.assertEqual(mundos.normalize('5'), 5)
        self.assertIsNone(mundos.normalize(6))
        self.assertIsNone(mundos.normalize(333))
        self.assertTrue(mundos.known(333))
        self.assertFalse(mundos.known(334))
        page = open(os.path.join(ROOT, 'play', 'vida.js'), encoding='utf-8').read()
        self.assertIn('const DEFAULT_WORLD = 3', page)
        self.assertIn("id = 'mundo-tab'", page)
        self.assertIn('Marcar como favorito', page)
        self.assertNotIn('Elige un mundo', page)
        self.assertIn('mundo-juntos', open(os.path.join(ROOT, 'play', 'index.html'), encoding='utf-8').read())

    def test_same_world_and_place_see_each_other(self):
        boxes = mundos.boxes(world())
        self.assertEqual(mundos.place_of(94, 267, 'city', boxes), 'parque-envigado')
        self.assertEqual(mundos.place_of(108, 272, 'city', boxes), 'parque-envigado')
        data = world()
        self.assertEqual(data['collision'][272][108], 0)
        park = type('P', (), {})()
        other = type('P', (), {})()
        park.world = other.world = 2
        park.place = other.place = 'parque-envigado'
        self.assertTrue(mundos.same_room(park, other))
        other.world = 3
        self.assertFalse(mundos.same_room(park, other))
        other.world = 2
        other.place = 'parque-caldas'
        self.assertFalse(mundos.same_room(park, other))
        house = type('P', (), {'world': 2, 'place': 'casa'})()
        self.assertFalse(mundos.same_room(park, house))
        self.assertEqual(mundos.place_of(1, 1, 'casa', boxes), 'casa')

    def test_counts_ignore_closed_worlds_and_bots(self):
        people = [
            type('P', (), {'hello': True, 'bot': False, 'world': 1})(),
            type('P', (), {'hello': True, 'bot': False, 'world': 1})(),
            type('P', (), {'hello': True, 'bot': True, 'world': 2})(),
            type('P', (), {'hello': False, 'bot': False, 'world': 2})(),
        ]
        body = mundos.counts(people)
        self.assertEqual(body['total'], 2)
        self.assertEqual(body['worlds']['1'], 2)
        self.assertEqual(body['worlds']['2'], 0)
        self.assertNotIn('6', body['worlds'])


class PetTests(unittest.TestCase):
    def test_more_breeds_and_colors(self):
        dogs = mascotas.breeds('dog')
        cats = mascotas.breeds('cat')
        dog_ids = [item['id'] for item in dogs]
        cat_ids = [item['id'] for item in cats]
        for breed in ('criollo', 'labrador', 'golden', 'pastor', 'bulldog', 'beagle', 'husky', 'pug', 'boxer', 'cocker', 'dalmata', 'chihuahua'):
            self.assertIn(breed, dog_ids)
        for breed in ('criollo', 'siames', 'persa', 'atigrado', 'negro', 'calico', 'angora', 'bengali', 'azul', 'esfinge', 'carey', 'tricolor'):
            self.assertIn(breed, cat_ids)
        for breed in dogs + cats:
            self.assertGreaterEqual(len(breed['colors']), 3)
            self.assertLessEqual(len(breed['colors']), 4)
        pet = mascotas.validate({'species': 'cat', 'breed': 'siames', 'variant': 2, 'name': 'Luna'})
        self.assertEqual(pet['name'], 'Luna')
        husky = mascotas.validate({'species': 'dog', 'breed': 'husky', 'variant': 3, 'name': 'Nieve'})
        self.assertEqual(husky['variant'], 3)
        self.assertIsNone(mascotas.validate({'species': 'dog', 'breed': 'siames', 'variant': 0}))
        self.assertIsNone(mascotas.validate({'species': 'dog', 'breed': 'beagle', 'variant': 3}))
        self.assertIsNone(mascotas.validate({'species': 'dog', 'breed': 'husky', 'variant': 4}))
        script = open(os.path.join(ROOT, 'play', 'estilo-jabo.js'), encoding='utf-8').read()
        for breed in dogs + cats:
            self.assertIn(breed['id'], script)


class FurnitureTests(unittest.TestCase):
    def test_variants_and_overlap(self):
        layout = muebles.sanitize({
            'wall': '#f4f0e6', 'floor': '#c45c38',
            'items': [
                {'id': 'cama', 'type': 'bed', 'x': 1, 'y': 1, 'rot': 0, 'variant': 'hamaca'},
                {'id': 'otro', 'type': 'bed', 'x': 1, 'y': 1, 'rot': 0, 'variant': 'nogal'},
                {'id': 'altar', 'type': 'altar', 'x': 3, 'y': 1, 'rot': 0, 'variant': 'dorado'},
                {'id': 'mala', 'type': 'altar', 'x': 4, 'y': 1, 'rot': 0, 'variant': 'no-existe'},
                {'id': 'matera', 'type': 'plant', 'x': 11, 'y': 3, 'rot': 0, 'variant': 'colgante'},
                {'id': 'cocina', 'type': 'stove', 'x': 6, 'y': 1, 'rot': 0, 'variant': 'lena'},
            ],
        })
        by_id = {item['id']: item for item in layout['items']}
        self.assertEqual(by_id['cama']['variant'], 'hamaca')
        self.assertNotIn('otro', by_id)
        self.assertEqual(by_id['altar']['variant'], 'dorado')
        self.assertNotIn('variant', by_id['mala'])
        self.assertEqual(by_id['matera']['variant'], 'colgante')
        self.assertEqual(by_id['cocina']['variant'], 'lena')


class SocialTests(unittest.TestCase):
    def setUp(self):
        self.doc = acc.empty()
        self.doc['users'].append({
            'id': 'ana', 'name': 'Ana', 'wallet_name': 'Ana', 'email': 'ana@example.com', 'role': 'player',
        })
        self.doc['users'].append({
            'id': 'simon', 'name': 'Simon', 'wallet_name': 'Simon', 'email': 'simon@example.com', 'role': 'player',
        })
        self.state = social.empty()

    def test_nick_change_is_only_a_paid_hook(self):
        quoted = social.quote_nick(self.doc, self.doc['users'][0], 'Luna')
        self.assertTrue(quoted['payment_required'])
        self.assertFalse(quoted['changed'])
        self.assertEqual(quoted['flag'], 'nick_change_paid')
        self.assertEqual(self.doc['users'][0]['name'], 'Ana')
        blocked = social.grant_paid_nick(self.doc, self.doc['users'][0], 'Luna')
        self.assertFalse(blocked['changed'])
        self.assertEqual(self.doc['users'][0]['name'], 'Ana')
        self.doc['users'][0]['nick_change_paid'] = True
        granted = social.grant_paid_nick(self.doc, self.doc['users'][0], 'Luna')
        self.assertTrue(granted['changed'])
        self.assertEqual(self.doc['users'][0]['name'], 'Luna')
        self.assertFalse(self.doc['users'][0]['nick_change_paid'])

    def test_friends_and_private_chat(self):
        found = social.search_nick(self.doc, 'ana', [])
        self.assertEqual(found['key'], 'acct:ana')
        self.assertIsNone(social.search_nick(self.doc, 'nadie', []))
        asked = social.request_friend(self.state, 'acct:simon', 'acct:ana')
        self.assertEqual(asked['status'], 'pedido')
        denied = social.private_message(self.state, 'acct:simon', 'Simon', 'Ana', 'hola', self.doc, now=10)
        self.assertFalse(denied['ok'])
        accepted = social.accept_friend(self.state, 'acct:ana', 'acct:simon')
        self.assertEqual(accepted['status'], 'amigos')
        sent = social.private_message(self.state, 'acct:simon', 'Simon', 'Ana', 'hola', self.doc, now=10)
        self.assertTrue(sent['ok'])
        self.assertEqual(sent['message']['channel'], 'privado')
        self.assertEqual(len(social.thread_for(self.state, 'acct:ana', 'acct:simon')), 1)

    def test_moderation_masks_and_limits(self):
        self.assertEqual(social.mask('hola mierda', 160), 'hola ···')
        self.assertEqual(social.mask('x' * 400, 20), 'x' * 20)
        stamps = []
        self.assertTrue(social.allow(stamps, 1, 2, 10))
        self.assertTrue(social.allow(stamps, 2, 2, 10))
        self.assertFalse(social.allow(stamps, 3, 2, 10))

    def test_feedback_and_poste_roles(self):
        saved = social.add_feedback(self.state, 'Ana', 'Quiero más bancas', 1, 'parque-envigado', now=20)
        self.assertTrue(saved['ok'])
        self.assertEqual(social.role_of(self.doc['users'][0]), 'player')
        self.assertEqual(social.role_of({'role': 'admin', 'email': 'a@b.c'}), 'admin')
        self.assertEqual(social.role_of({'role': 'staff', 'email': 'a@b.c'}), 'staff')
        self.assertFalse(social.allows('admin', 'answer_note'))
        self.assertFalse(social.allows('staff', 'hide_note'))
        self.assertTrue(social.allows('simon', 'see_feedback'))
        note = social.add_note(self.state, 'Ana', 'acct:ana', 'Una fuente en el parque', 'parque-envigado', 1, now=30)
        self.assertTrue(note['ok'])
        ident = self.state['notes'][-1]['id']
        refused = social.moderate(self.state, 'admin', 'note', ident, 'answer', 'Luego')
        self.assertFalse(refused['ok'])
        answered = social.moderate(self.state, 'simon', 'note', ident, 'answer', 'La anoto')
        self.assertEqual(answered['board']['notes'][-1]['answer'], 'La anoto')
        poll = social.add_poll(self.state, 'Ana', 'acct:ana', '¿Más color?', ['Sí', 'No'], 'parque-envigado', 1, now=40)
        self.assertTrue(poll['ok'])
        poll_id = self.state['polls'][-1]['id']
        voted = social.vote_poll(self.state, 'acct:simon', poll_id, 'o0')
        self.assertEqual(voted['board']['polls'][-1]['options'][0]['votes'], 1)
        social.vote_poll(self.state, 'acct:simon', poll_id, 'o1')
        self.assertEqual(self.state['polls'][-1]['votes']['acct:simon'], 'o1')
        os.environ['SIMON_ADMIN_TOKEN'] = 'clave-de-prueba'
        try:
            self.assertEqual(social.role_of(None, 'clave-de-prueba'), 'simon')
            self.assertEqual(social.role_of(None, 'otra'), 'player')
            os.environ['SIMON_OWNER_EMAIL'] = 'simon@example.com'
            self.assertEqual(social.role_of(self.doc['users'][1]), 'simon')
        finally:
            os.environ.pop('SIMON_ADMIN_TOKEN', None)
            os.environ.pop('SIMON_OWNER_EMAIL', None)

    def test_instructivo_uses_real_controls(self):
        text = open(os.path.join(ROOT, 'play', 'instructivo.js'), encoding='utf-8').read()
        for phrase in ('/play/', '/movil/', 'Descansar', 'Cerrar sesión', 'Salir al Parque', '<kbd>W</kbd>', 'joystick', '<kbd>X</kbd>'):
            self.assertIn(phrase, text)
        self.assertNotIn('doble toque para correr', text.lower())
        self.assertIn('no hay un botón de correr', text)


class SaveTests(unittest.TestCase):
    def test_pet_stays_inside_the_house(self):
        layout = muebles.default_layout()
        tiles = set(muebles.pet_tiles(layout))
        self.assertNotIn((4, 9), tiles)
        self.assertNotIn((4, 8), tiles)
        self.assertIn((5, 6), tiles)
        self.assertNotIn((1, 1), tiles)
        self.assertEqual(muebles.pet_step(layout, 5, 6, 6, 6), (6, 6))
        self.assertEqual(muebles.pet_step(layout, 5, 6, 5, 9), (5, 6))
        self.assertEqual(muebles.pet_step(layout, 5, 6, 5, 20), (5, 6))
        outside = muebles.pet_step(layout, 0, 0, 1, 0)
        self.assertIn(outside, tiles)

    def test_reload_keeps_the_save_and_drops_coins(self):
        user = {'id': 'ana', 'name': 'Ana', 'wallet_name': 'Ana', 'casa': {}, 'caballo': {}}
        payload = {
            'inv': [{'item': 'pico', 'qty': 1}, {'item': 'simoncoin', 'qty': 9}],
            'xp': {'mining': 40},
            'quest': {'stage': 2, 'steps': {'madera': 3}, 'done': False, 'turnedIn': False},
            'libro': {'started': True, 'done': False, 'turnedIn': False, 'steps': {'lavar_oro_sai': 1}},
            'studied': {'oro': True},
            'hp': 80, 'energy': 40,
            'position': {'mapId': 'casa', 'x': 4, 'y': 6, 'dir': 'down'},
            'hud': {'lifeinc.hud.layout.desktop.horizontal': {'hud-mapa': {'x': 12, 'y': 20, 'scale': 1.1}}},
            'pet': {'species': 'dog', 'breed': 'husky', 'variant': 3, 'name': 'Nieve'},
            'layout': muebles.default_layout(),
            'coat': 'grey',
            'horse': {'x': 94.5, 'y': 268, 'dir': 'left', 'coat': 'grey'},
            'coins': 999999, 'wallets': {'Ana': 50}, 'finca': {'plots': 9},
        }
        saved = partida.remember(user, payload)
        disk = json.loads(json.dumps(user))
        again = partida.recall(disk)
        self.assertEqual(again['inv'], [{'item': 'pico', 'qty': 1}])
        self.assertEqual(again['pet']['breed'], 'husky')
        self.assertEqual(again['pet']['name'], 'Nieve')
        self.assertEqual(again['pet']['variant'], 3)
        self.assertEqual(again['position'], {'mapId': 'casa', 'x': 4.0, 'y': 6.0, 'dir': 'down'})
        self.assertEqual(again['hud']['lifeinc.hud.layout.desktop.horizontal']['hud-mapa']['x'], 12)
        self.assertEqual(again['coat'], 'grey')
        self.assertEqual(again['horse']['x'], 94.5)
        self.assertEqual(again['horse']['y'], 268)
        self.assertEqual(again['horse']['dir'], 'left')
        self.assertTrue(again['libro']['started'])
        self.assertEqual(again['studied'], {'oro': True})
        self.assertNotIn('coins', again)
        self.assertNotIn('wallets', again)
        self.assertNotIn('finca', again)
        self.assertEqual(saved['nick'], 'Ana')
        self.assertEqual(again['layout']['items'][0]['type'], 'bed')


class ServerRoomTests(unittest.TestCase):
    def test_place_chat_stays_in_the_room(self):
        import server as srv
        made = []

        def person(name, world_id, place):
            writer = type('W', (), {'buf': [], 'write': lambda self, data: self.buf.append(data)})()
            client = srv.Client(writer)
            client.hello = True
            client.name = name
            client.world = world_id
            client.place = place
            client.zone = 'city'
            client.x, client.y = 100, 270
            srv.clients[client.id] = client
            made.append(client)
            return client

        try:
            here = person('Ana', 1, 'parque-envigado')
            near = person('Sol', 1, 'parque-envigado')
            away = person('Noe', 2, 'parque-envigado')
            srv.chat(here, 'lugar', 'buenas')
            self.assertTrue(near.w.buf)
            self.assertFalse(away.w.buf)
            srv.chat(here, 'lugar', 'esto es mierda')
            raw = b''.join(near.w.buf)
            self.assertIn('···'.encode(), raw)
            self.assertNotIn(b'mierda', raw)
        finally:
            for client in made:
                srv.clients.pop(client.id, None)


if __name__ == '__main__':
    unittest.main()
