# SPDX-License-Identifier: AGPL-3.0-or-later
"""El chat del mundo se ve y llega a quien está lejos en el mismo mundo."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import server

ROOT = os.path.dirname(os.path.dirname(__file__))


def _read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as handle:
        return handle.read()


class ChatMundoTests(unittest.TestCase):
    def setUp(self):
        self.sent = {}
        self._send = server.send
        server.send = lambda who, obj: self.sent.setdefault(who.id, []).append(obj)
        self.made = []

    def tearDown(self):
        server.send = self._send
        for who in self.made:
            server.clients.pop(who.id, None)

    def person(self, name, world, x, y):
        who = server.Client(None)
        who.hello = True
        who.bot = False
        who.name = name
        who.world = world
        who.zone = 'city'
        who.place = 'parque-envigado'
        who.x = float(x)
        who.y = float(y)
        who.clan = ''
        who.group = ''
        who.stamps = []
        server.clients[who.id] = who
        self.made.append(who)
        return who

    def chats(self, who):
        return [item for item in self.sent.get(who.id, []) if item.get('t') == 'chat']

    def test_same_world_hears_a_far_message_with_the_nickname(self):
        near = self.person('Nico', 3, 10, 10)
        far = self.person('Lina', 3, 400, 400)
        other = self.person('Otto', 4, 12, 12)
        server.chat(near, 'global', 'hola mundo')
        heard = self.chats(far)
        self.assertEqual(len(heard), 1)
        self.assertEqual(heard[0]['from'], 'Nico')
        self.assertEqual(heard[0]['text'], 'hola mundo')
        self.assertEqual(heard[0]['channel'], 'global')
        self.assertEqual(self.chats(near)[0]['from'], 'Nico')
        self.assertEqual(self.chats(other), [])

    def test_nearby_chat_stays_nearby(self):
        near = self.person('Nico', 3, 10, 10)
        far = self.person('Lina', 3, 400, 400)
        server.chat(near, 'proximidad', 'solo cerca')
        self.assertEqual(self.chats(far), [])
        self.assertEqual(self.chats(near)[0]['text'], 'solo cerca')

    def test_chat_button_and_player_list_are_in_the_page(self):
        page = _read('play/index.html')
        css = _read('play/cajon.css')
        bar = _read('play/pulgar.js')
        drawer = _read('play/cajon.js')
        vida = _read('play/vida.js')
        self.assertIn('id="chat-toggle"', page)
        self.assertIn('id="chat-gente-btn"', page)
        self.assertIn('Jugadores en línea', page)
        self.assertIn('Invitar a mi lugar', page)
        self.assertIn('data-canal="global" class="activa"', page)
        self.assertIn('display: flex !important', css)
        self.assertIn("'Chat'", bar)
        self.assertIn('Chat del mundo', drawer)
        self.assertIn('Jugadores en línea · ', vida)
