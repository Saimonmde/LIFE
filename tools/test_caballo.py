# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pelaje del caballo en la cuenta, y el contrato del cliente (malla, paso y casas)."""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import accounts as acc
import caballo_cuenta


class CaballoCuentaTests(unittest.TestCase):
    def test_default_coat_is_bay_and_the_choice_is_saved(self):
        user = {'id': 'u1', 'name': 'Ana', 'email': 'ana@example.com'}
        self.assertEqual(caballo_cuenta.view(user)['coat'], 'bay')
        self.assertEqual(acc.public_user(user)['caballo']['coat'], 'bay')
        shown = acc.set_caballo(user, 'gris')
        self.assertEqual(shown['caballo']['coat'], 'grey')
        self.assertEqual(user['caballo']['coat'], 'grey')
        self.assertEqual(acc.set_caballo(user, 'negro')['caballo']['coat'], 'black')
        self.assertEqual(acc.set_caballo(user, 'bay')['caballo']['coat'], 'bay')

    def test_unknown_coat_is_rejected_and_the_saved_one_stays(self):
        user = {'id': 'u2', 'name': 'Ana', 'email': 'ana@example.com'}
        acc.set_caballo(user, 'grey')
        with self.assertRaises(acc.AuthError):
            acc.set_caballo(user, 'pinto')
        self.assertEqual(user['caballo']['coat'], 'grey')

    def test_client_horse_contract(self):
        script = os.path.join(ROOT, 'tools', 'test_caballo.mjs')
        subprocess.check_call(['node', script], cwd=ROOT)


if __name__ == '__main__':
    unittest.main()
