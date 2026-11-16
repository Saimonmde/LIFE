# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seguir avisa y respeta quien no quiere ser seguido. No mueve monedas."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import seguir
import social


class SeguirTests(unittest.TestCase):
    def test_privacy_blocks_and_a_public_player_can_be_followed(self):
        blocked = seguir.pedir({'followable': False}, True, True)
        self.assertFalse(blocked['ok'])
        self.assertIn('no ser seguida', blocked['reason'])
        ok = seguir.pedir({'followable': True}, True, True)
        self.assertTrue(ok['ok'])
        self.assertEqual(seguir.label('caballo'), 'a caballo')
        self.assertEqual(seguir.label('casa'), 'en casa')
        self.assertEqual(seguir.pace_of('corriendo', 'city', True), 'corriendo')
        self.assertEqual(seguir.pace_of('caminando', 'casa', True), 'casa')
        gone = seguir.pedir({}, False, False)
        self.assertFalse(gone['ok'])
        box = social.empty()
        social.request_friend(box, 'acct:a', 'acct:b')
        refused = social.reject_friend(box, 'acct:b', 'acct:a')
        self.assertTrue(refused['ok'])
        self.assertNotIn('acct:a', box['friends']['acct:b']['in'])
        self.assertNotIn('acct:b', box['friends']['acct:a']['friends'])

    def test_the_card_and_account_mention_follow_and_friends(self):
        root = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(root, 'play', 'ficha.js'), encoding='utf-8') as handle:
            card = handle.read()
        with open(os.path.join(root, 'play', 'mi-cuenta.js'), encoding='utf-8') as handle:
            account = handle.read()
        with open(os.path.join(root, 'play', 'seguir.js'), encoding='utf-8') as handle:
            follow = handle.read()
        with open(os.path.join(root, 'tools', 'social.py'), encoding='utf-8') as handle:
            social = handle.read()
        self.assertIn('Seguir', card)
        self.assertIn('Agregar', card)
        self.assertIn('Pueden seguirme', account)
        self.assertIn('Ir con él', account)
        self.assertIn('Rechazar', account)
        self.assertIn('auto = true', follow)
        self.assertIn('Dejar de seguir', follow)
        self.assertIn('def reject_friend', social)
        self.assertIn('Caminar detrás', follow)
        self.assertNotIn('issue(', follow)
