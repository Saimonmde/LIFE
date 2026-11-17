# SPDX-License-Identifier: AGPL-3.0-or-later
"""El celular carga la revisión nueva y el saldo del servidor, no la copia local."""
import os
import unittest

import server

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))


class CacheMovilTests(unittest.TestCase):
    def test_each_deploy_changes_the_script_url(self):
        html = '<script src="game.js?v=ladera-r1"></script><link rel="stylesheet" href="style.css?v=en-vivo">'
        marked = server.marcar_recursos(html, '5829384f230c2c595d0938cd74d03089c44e55d2')
        self.assertIn('game.js?v=ladera-r1&r=5829384f230c', marked)
        self.assertIn('style.css?v=en-vivo&r=5829384f230c', marked)
        again = server.marcar_recursos(marked, '5829384f230c2c595d0938cd74d03089c44e55d2')
        self.assertEqual(again, marked)
        remote = server.marcar_recursos('<script src="https://cdn.example/app.js"></script>', 'abc')
        self.assertNotIn('r=', remote)

    def test_the_page_reloads_itself_when_the_revision_changes(self):
        with open(os.path.join(ROOT, 'play', 'index.html'), encoding='utf-8') as handle:
            page = handle.read()
        self.assertIn('/session.json?t=', page)
        self.assertIn('life-recarga', page)
        self.assertIn('Hay una versión nueva', page)
        with open(os.path.join(ROOT, 'play', 'game.js'), encoding='utf-8') as handle:
            game = handle.read()
        self.assertIn('meterMonedas', game)
        self.assertIn('lifeinc.recarga.', game)

    def test_the_phone_reads_the_server_bag_not_the_old_ledger_stacks(self):
        with open(os.path.join(ROOT, 'play', 'simulacion.js'), encoding='utf-8') as handle:
            sim = handle.read()
        self.assertIn('syncBolsa', sim)
        self.assertIn('vaultFromServer', sim)
        self.assertNotIn("ponerMetal('moneda_plata'", sim)
        self.assertNotIn("ponerMetal('moneda_cobre'", sim)
        self.assertIn('requestVault()', sim)


if __name__ == '__main__':
    unittest.main()
