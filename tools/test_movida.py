# SPDX-License-Identifier: AGPL-3.0-or-later
"""El paso se reparte sólo a quien comparte la vista."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server


class MotionTests(unittest.TestCase):
    def tearDown(self):
        for client in list(server.clients.values()):
            if getattr(client, 'name', '') in ('Ana', 'Sol', 'Noe', 'Paz'):
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
        client.move_at = 10_000
        server.clients[client.id] = client
        return client

    def test_a_tick_reaches_the_same_world_and_skips_the_others(self):
        ana = self.person('Ana', 3, 'parque-envigado', 10, 10)
        sol = self.person('Sol', 3, 'parque-medellin', 12, 12)
        noe = self.person('Noe', 5, 'parque-envigado', 10, 10)
        paz = self.person('Paz', 3, 'casa', 4, 4, 'casa')
        ana.x = 11
        ana.move_at = server.time.time()
        for who in (sol, noe, paz):
            who.w.buf.clear()
        server.broadcast_motion()
        self.assertIn(b'"t": "move"', b''.join(sol.w.buf))
        self.assertNotIn(b'"t": "move"', b''.join(noe.w.buf))
        self.assertNotIn(b'"t": "move"', b''.join(paz.w.buf))

    def test_miners_in_the_same_cave_see_the_step(self):
        ana = self.person('Ana', 3, 'mina-palmas', 100, 100, 'mine')
        sol = self.person('Sol', 3, 'mina-palmas', 100, 101, 'mine')
        noe = self.person('Noe', 3, 'valle', 40, 40)
        ana.zx, ana.zy = 18, 27
        sol.zx, sol.zy = 19, 27
        ana.zx = 19
        ana.move_at = server.time.time()
        sol.w.buf.clear()
        noe.w.buf.clear()
        server.broadcast_motion()
        heard = b''.join(sol.w.buf)
        self.assertIn(b'"t": "move"', heard)
        self.assertIn(b'"zone": "mine"', heard)
        self.assertNotIn(b'"t": "move"', b''.join(noe.w.buf))

    def test_a_tap_stays_in_sight(self):
        ana = self.person('Ana', 3, 'valle', 10, 10)
        sol = self.person('Sol', 3, 'valle', 11, 10)
        noe = self.person('Noe', 1, 'valle', 10, 10)
        sol.w.buf.clear()
        noe.w.buf.clear()
        server.handle_client_message(ana, {'t': 'gesto', 'kind': 'toque', 'x': 12, 'y': 14}, 'gesto')
        self.assertIn(b'"kind": "toque"', b''.join(sol.w.buf))
        self.assertNotIn(b'toque', b''.join(noe.w.buf))


if __name__ == '__main__':
    unittest.main()
