# SPDX-License-Identifier: AGPL-3.0-or-later
"""Diseño de la interfaz y recetas de acuñación del horno."""
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class LayoutMintTests(unittest.TestCase):
    def test_layout_persistence_and_mint_recipes(self):
        script = os.path.join(ROOT, 'tools', 'test_layout_mint.js')
        done = subprocess.run(['node', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + '\n' + done.stderr)
        self.assertIn('ok', done.stdout)

    def test_minted_coins_are_not_a_new_smc_issue(self):
        rules = open(os.path.join(ROOT, 'play', 'mining-rules.js'), encoding='utf-8').read()
        server = open(os.path.join(ROOT, 'server.py'), encoding='utf-8').read()
        self.assertIn("mode==='coin'", rules)
        self.assertIn('moneda_', rules)
        self.assertIn("return{inv:next,coins:0,item:r.coinItem", rules.replace(' ', ''))
        self.assertIn('ECO.issue', server)
        self.assertNotIn("coinItem", server)


if __name__ == '__main__':
    unittest.main()
