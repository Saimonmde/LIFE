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

    def test_clock_map_and_clean_screen_sources(self):
        root = os.path.join(ROOT, 'play')
        html = open(os.path.join(root, 'index.html'), encoding='utf-8').read()
        css = open(os.path.join(root, 'style.css'), encoding='utf-8').read()
        layout = open(os.path.join(root, 'hud-layout.js'), encoding='utf-8').read()
        game = open(os.path.join(root, 'game.js'), encoding='utf-8').read()
        clock = css.split('#hud-reloj {', 1)[1].split('}', 1)[0]
        self.assertIn('background: none', clock)
        self.assertNotIn('#24180ee6', clock)
        self.assertIn('text-shadow', css.split('#reloj-ahora {', 1)[1].split('}', 1)[0])
        self.assertNotIn("['hud-reloj'", layout)
        self.assertIn('hud-fijo', layout)
        self.assertIn('id="b-globo"', html)
        self.assertIn('id="b-limpio"', html)
        self.assertIn('id="anillo-vida"', html)
        self.assertIn('id="vida-pct"', html)
        self.assertIn('Ir aquí', html)
        self.assertIn('pantalla-limpia', layout)
        self.assertIn('walkFromMinimap', game)
        self.assertNotIn("$('#hud-mapa').addEventListener('click',openCityMap)", game)
        self.assertIn('damagePlayer', game)
        self.assertIn('sprintLock', game)


if __name__ == '__main__':
    unittest.main()
