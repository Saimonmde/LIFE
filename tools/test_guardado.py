#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Guardar y recuperar la partida de una cuenta, sin duplicar monedas ni inventario."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import guardado
import partida


def economia():
    return {
        'wallets': {'Ana': 80},
        'plata': {'wallets': {'Ana': 15}},
        'simonchis': {'wallets': {'Ana': 4}},
    }


class GuardadoTests(unittest.TestCase):
    def test_reload_by_account_and_ignore_client_coins(self):
        user = {'id': 'cuenta-ana', 'name': 'Ana', 'wallet_name': 'Ana', 'casa': {}, 'caballo': {}}
        econ = economia()
        payload = {
            'rev': 100,
            'accountId': 'otra-cuenta',
            'nick': 'Hacker',
            'inv': [{'item': 'pico', 'qty': 2}, {'item': 'bolsa_cafe', 'qty': 1}, {'item': 'simoncoin', 'qty': 9}],
            'position': {'mapId': 'city', 'x': 12, 'y': 8, 'dir': 'right'},
            'pet': {'species': 'cat', 'breed': 'angora', 'variant': 0, 'name': 'Luna'},
            'coat': 'black',
            'horse': {'x': 40, 'y': 12, 'dir': 'up', 'coat': 'black'},
            'corral': {'animals': [{'id': 'g1', 'species': 'gallo', 'color': 'rojo', 'place': 'patio'}]},
            'coins': 999999,
            'wallets': {'Ana': 1},
            'finca': {'plots': 3},
        }
        shown = guardado.remember(user, payload, econ)
        self.assertEqual(shown['accountId'], 'cuenta-ana')
        self.assertEqual(shown['nick'], 'Ana')
        self.assertEqual(user['name'], 'Ana')
        self.assertEqual(shown['inv'], [{'item': 'pico', 'qty': 2}, {'item': 'bolsa_cafe', 'qty': 1}])
        self.assertEqual(shown['position']['mapId'], 'city')
        self.assertEqual(shown['pet']['name'], 'Luna')
        self.assertEqual(shown['coat'], 'black')
        self.assertEqual(shown['horse']['x'], 40)
        self.assertEqual(shown['corral']['animals'][0]['color'], 'rojo')
        self.assertEqual(shown['monedas'], {'simoncoin': 80, 'simonplata': 15, 'simonchis': 4})
        self.assertEqual(shown['finquita'], 'en la cuenta')
        self.assertEqual(econ['wallets']['Ana'], 80)
        again = guardado.remember(user, payload, econ)
        pico = [row for row in again['inv'] if row['item'] == 'pico'][0]
        self.assertEqual(pico['qty'], 2)
        self.assertEqual(econ['wallets']['Ana'], 80)
        self.assertEqual(econ['plata']['wallets']['Ana'], 15)
        self.assertEqual(econ['simonchis']['wallets']['Ana'], 4)

    def test_old_offline_copy_does_not_replace_a_newer_save(self):
        user = {'id': 'cuenta-ana', 'name': 'Ana', 'wallet_name': 'Ana', 'casa': {}, 'caballo': {}}
        partida.remember(user, {'rev': 50, 'inv': [{'item': 'pico', 'qty': 4}], 'position': {'mapId': 'city', 'x': 3, 'y': 3, 'dir': 'down'}})
        stale = partida.remember(user, {'rev': 20, 'inv': [{'item': 'pico', 'qty': 1}], 'position': {'mapId': 'mine', 'x': 1, 'y': 1, 'dir': 'up'}})
        self.assertEqual([row['qty'] for row in stale['inv'] if row['item'] == 'pico'], [4])
        self.assertEqual(stale['position']['mapId'], 'city')
        self.assertEqual(stale['accountId'], 'cuenta-ana')
