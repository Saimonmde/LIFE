# SPDX-License-Identifier: AGPL-3.0-or-later
"""Primer ingreso y viajes: la cuenta recuerda la intro, y un salto no es un paso."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import accounts
import viajes


def world():
    with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
        return json.load(handle)


class IntroViajeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = world()

    def test_casa_banco_y_parques_son_lugares(self):
        found = {item['id']: item for item in viajes.catalog(self.world)}
        for key in ('casa', 'banco', 'envigado', 'medellin', 'parque_bolivar', 'las_palmas'):
            self.assertIn(key, found)
            dest = viajes.resolve(self.world, key)
            self.assertTrue(viajes.walkable(self.world, dest['x'], dest['y']), key)
            self.assertIn(viajes._kind(self.world, dest['x'], dest['y']), viajes.SAFE, key)
        self.assertEqual(found['casa']['name'], 'Tu casa')
        self.assertEqual(found['banco']['name'], 'Casa bancaria')
        self.assertEqual(viajes.resolve(self.world, 'casa')['x'], 94)
        self.assertEqual(viajes.resolve(self.world, 'banco')['y'], 257)

    def test_el_paso_largo_no_es_un_viaje(self):
        self.assertTrue(viajes.step_allowed(2, 0.2))
        self.assertTrue(viajes.step_allowed(16, 1))
        self.assertFalse(viajes.step_allowed(80, 0.2))
        self.assertFalse(viajes.step_allowed(400, 1))
        self.assertTrue(viajes.portal_arrival('casa', 94, 267))
        self.assertTrue(viajes.portal_arrival('banco', 113, 258))
        self.assertFalse(viajes.portal_arrival('casa', 20, 20))
        self.assertTrue(viajes.portal_arrival('mine', 50, 40, (49, 41)))
        self.assertFalse(viajes.portal_arrival('mine', 50, 40, None))
        gate = viajes.Gate(cooldown=viajes.ASTRAL_COOLDOWN)
        self.assertTrue(gate.allow('ana', 10))
        self.assertFalse(gate.allow('ana', 12))
        self.assertTrue(gate.allow('ana', 14))

    def test_la_cuenta_guarda_la_intro(self):
        user = {'id': 'u1', 'name': 'Ana', 'email': 'ana@ejemplo.co'}
        self.assertFalse(accounts.public_user(user)['introSeen'])
        accounts.mark_intro(user)
        self.assertTrue(user['introSeen'])
        self.assertTrue(accounts.public_user(user)['introSeen'])
        accounts.mark_intro(None)


if __name__ == '__main__':
    unittest.main()
