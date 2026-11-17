# SPDX-License-Identifier: AGPL-3.0-or-later
"""El apodo Simon no esconde el saldo que quedó en la llave saimon."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import billetera
import fusion
import mi_cuenta


class BilleteraTests(unittest.TestCase):
    def test_the_owner_sees_the_wallet_that_holds_the_money(self):
        econ = {'wallets': {'Simon': 0, 'saimon': 15000}}
        vault = {'accounts': {'saimon': {'smh': 59735, 'items': {'moneda_plata': 2}}, 'Simon': {'smh': 0}}}
        owner = {'id': 'dueño', 'name': 'Simon', 'wallet_name': 'Simon', 'email': fusion.owner_email()}
        self.assertEqual(billetera.elegir(econ, vault, owner, 'Simon'), 'saimon')
        shown = mi_cuenta.resumen(owner, econ, {}, vault_state=vault)
        self.assertEqual(shown['billetera'], 'saimon')
        self.assertEqual(shown['coins']['simoncoinSmh'], 15000)
        self.assertEqual(shown['coins']['bankSmh'], 59735)
        self.assertEqual(shown['coins']['totalSmh'], 74735)
        inv = {row['item']: row['qty'] for row in shown['inventory']}
        self.assertEqual(inv.get('moneda_plata'), 2)
        self.assertIn('@', shown['correo'])
        self.assertNotIn(fusion.owner_email(), shown['correo'])
        other = {'id': 'otro', 'name': 'Simon', 'wallet_name': 'Simon', 'email': 'otro@example.com'}
        self.assertEqual(billetera.elegir(econ, vault, other, 'Simon'), 'Simon')

    def test_the_phone_reads_the_server_wallet_name(self):
        root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'play'))
        with open(os.path.join(root, 'cajon.js'), encoding='utf-8') as handle:
            cajon = handle.read()
        self.assertIn('serverWallet', cajon)
        self.assertIn('id="cajon-inv">Inventario', cajon)
        with open(os.path.join(root, 'mi-cuenta.js'), encoding='utf-8') as handle:
            panel = handle.read()
        self.assertIn('mi-cuenta-sesion', panel)
        self.assertIn('Sesión:', panel)


if __name__ == '__main__':
    unittest.main()
