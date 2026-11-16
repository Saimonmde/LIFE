# SPDX-License-Identifier: AGPL-3.0-or-later
"""La ciudad de un mundo es una sola sala. La casa sigue siendo privada."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mundos
import server


ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


class SightTests(unittest.TestCase):
    def test_parks_share_the_city_and_the_house_does_not(self):
        boxes = mundos.boxes({'areas': []})
        self.assertEqual(mundos.place_of(94, 267, 'city', boxes), 'parque-envigado')
        park = type('P', (), {'world': 3, 'place': 'parque-envigado', 'zone': 'city'})()
        other = type('P', (), {'world': 3, 'place': 'parque-medellin', 'zone': 'city'})()
        self.assertTrue(mundos.same_sight(park, other))
        self.assertFalse(mundos.same_room(park, other))
        other.world = 5
        self.assertFalse(mundos.same_sight(park, other))
        house = type('P', (), {'world': 3, 'place': 'casa', 'zone': 'casa'})()
        self.assertFalse(mundos.same_sight(park, house))
        mine = type('P', (), {'world': 3, 'place': 'mina-palmas', 'zone': 'mine'})()
        self.assertFalse(mundos.same_sight(park, mine))

    def test_presence_counts_the_world_and_lists_the_place(self):
        people = [
            type('P', (), {'hello': True, 'bot': False, 'id': 1, 'name': 'Ana', 'world': 3, 'place': 'parque-envigado', 'zone': 'city'})(),
            type('P', (), {'hello': True, 'bot': False, 'id': 2, 'name': 'Sol', 'world': 3, 'place': 'parque-medellin', 'zone': 'city'})(),
            type('P', (), {'hello': True, 'bot': True, 'id': 3, 'name': 'Bot', 'world': 3, 'place': 'valle', 'zone': 'city'})(),
            type('P', (), {'hello': True, 'bot': False, 'id': 4, 'name': 'Noe', 'world': 5, 'place': 'valle', 'zone': 'city'})(),
        ]
        body = mundos.presence(people, [])
        self.assertEqual(body['total'], 3)
        self.assertEqual(body['worlds']['3'], 2)
        self.assertEqual(body['worlds']['5'], 1)
        nicks = [row['nick'] for row in body['players']]
        self.assertEqual(nicks, ['Ana', 'Sol', 'Noe'])
        self.assertEqual(body['players'][0]['place'], 'parque-envigado')
        self.assertEqual(body['players'][0]['world'], 3)


class ServerSightTests(unittest.TestCase):
    def tearDown(self):
        for client in list(server.clients.values()):
            if getattr(client, 'name', '') in ('Ana', 'Sol', 'Noe'):
                server.clients.pop(client.id, None)

    def person(self, name, world, place, x, y, zone='city'):
        writer = type('W', (), {'buf': [], 'write': lambda self, data: self.buf.append(data)})()
        client = server.Client(writer)
        client.hello = True
        client.name = name
        client.world = world
        client.place = place
        client.zone = zone
        client.x, client.y = float(x), float(y)
        server.clients[client.id] = client
        return client

    def test_a_step_in_another_park_is_still_visible(self):
        ana = self.person('Ana', 3, 'parque-envigado', 108, 272)
        sol = self.person('Sol', 3, 'parque-medellin', 120, 140)
        noe = self.person('Noe', 5, 'parque-envigado', 108, 272)
        peers = server.city_peers(ana)
        self.assertEqual([row['name'] for row in peers], ['Sol'])
        ana.place = 'parque-bello'
        ana.x += 1
        server.room_shift(ana, 3, 'parque-envigado')
        heard = b''.join(sol.w.buf)
        self.assertIn(b'"t": "move"', heard)
        self.assertNotIn(b'"t": "leave"', heard)
        muted = b''.join(noe.w.buf)
        self.assertNotIn(b'"t": "move"', muted)
        self.assertNotIn(b'"t": "join"', muted)

    def test_leaving_a_town_house_becomes_visible(self):
        ana = self.person('Ana', 3, 'casa', 94, 267, 'casa')
        ana.city_x, ana.city_y = 122, 130
        sol = self.person('Sol', 3, 'parque-envigado', 108, 272)
        sol.w.buf.clear()
        server.handle_client_message(ana, {'t': 'move', 'zone': 'city', 'x': 122, 'y': 130, 'dir': 'down', 'moving': False}, 'move')
        self.assertEqual(ana.zone, 'city')
        self.assertEqual((int(ana.x), int(ana.y)), (122, 130))
        self.assertIn(b'"t": "join"', b''.join(sol.w.buf))

    def test_ir_con_el_switches_world_and_stands_beside(self):
        ana = self.person('Ana', 5, 'valle', 10, 10)
        sol = self.person('Sol', 3, 'parque-envigado', 108, 272)
        server.handle_client_message(ana, {'t': 'ir_con', 'id': sol.id}, 'ir_con')
        self.assertEqual(ana.world, 3)
        self.assertEqual(ana.zone, 'city')
        self.assertLessEqual(max(abs(ana.x - sol.x), abs(ana.y - sol.y)), 2)
        self.assertNotEqual((int(ana.x), int(ana.y)), (int(sol.x), int(sol.y)))
        raw = b''.join(ana.w.buf)
        self.assertIn(b'travel_result', raw)
        self.assertIn(b'cerca', raw)
        page = open(os.path.join(ROOT, 'play', 'vida.js'), encoding='utf-8').read()
        self.assertIn('Jugadores en línea', page)
        self.assertIn('en su casa', page)
        self.assertIn('Ir con él', page)
        self.assertIn('life-revision', open(os.path.join(ROOT, 'play', 'game.js'), encoding='utf-8').read())
        self.assertIn('Invitar a mi lugar', page)
        self.assertIn("params.get('mundo')", page)
        self.assertIn('const DEFAULT_WORLD = 3', page)
        game = open(os.path.join(ROOT, 'play', 'game.js'), encoding='utf-8').read()
        self.assertIn('Vida.world() : 3', game)
        self.assertNotIn('beginAtHome(); const zone', game)


if __name__ == '__main__':
    unittest.main()
