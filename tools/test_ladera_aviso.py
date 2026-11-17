# SPDX-License-Identifier: AGPL-3.0-or-later
"""La Mina de La Ladera se ve en el mapa y tiene un atajo que se puede cerrar."""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as handle:
        return handle.read()


class LaderaAvisoTests(unittest.TestCase):
    def test_marker_badge_and_shortcut(self):
        game = read('play/game.js')
        mapa = read('play/valle-mapa.js')
        aviso = read('play/ladera-aviso.js')
        css = read('play/ladera-aviso.css')
        page = read('play/index.html')
        self.assertIn("{nueva:true}", game)
        self.assertIn('function marcaNueva', game)
        self.assertIn("fillText('Nueva'", game)
        self.assertIn("text:'LA LADERA'", game)
        self.assertIn('function badgeNueva', mapa)
        self.assertIn("fillText('Nueva'", mapa)
        self.assertIn('badgeNueva(ctx, x, y)', mapa)
        self.assertIn('spot.nueva', mapa)
        self.assertIn('Ir a la Mina de La Ladera', aviso)
        self.assertIn("askTravel('mina_ladera')", aviso)
        self.assertIn('lifeinc.ladera.aviso', aviso)
        self.assertIn('ladera-aviso-cerrar', aviso)
        self.assertIn('min-height: 48px', css)
        self.assertIn('ladera-aviso.css?v=ladera-aviso-r1', page)
        self.assertIn('ladera-aviso.js?v=ladera-aviso-r1', page)
        self.assertNotIn('#hud-gear-menu', css)
        self.assertNotIn('#cajon-editor', css)


if __name__ == '__main__':
    unittest.main()
