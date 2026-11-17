# SPDX-License-Identifier: AGPL-3.0-or-later
"""El céntimo guardado no se vuelve a dividir, y la pantalla no dice SMH ni Simonchis."""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as eco
import ed25519
import libro

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = bytes(range(32))
UI_SKIP = {'three.module.js'}
BANNED = re.compile(r'\bSMH\b|Simonchis')


class MigrationTests(unittest.TestCase):
    def test_keeps_every_cent_and_runs_once(self):
        state = eco.empty_state()
        state['meta'].pop('smhShownAsSmc', None)
        state['wallets']['Ana'] = 1250
        state['wallets']['Luz'] = 1
        before = dict(state['wallets'])
        block = state['blocks'][0]['hash']
        self.assertTrue(eco.migrate_smh_display(state))
        self.assertEqual(state['wallets']['Ana'], before['Ana'])
        self.assertEqual(state['wallets']['Luz'], 1)
        self.assertEqual(eco.format_smc(state['wallets']['Ana']), '12,5 SMC')
        self.assertEqual(eco.format_smc(state['wallets']['Luz']), '0,01 SMC')
        self.assertEqual(state['blocks'][0]['hash'], block)
        self.assertNotIn('SMH', state['disclaimer'])
        self.assertNotIn('Simonchis', state['disclaimer'])
        self.assertFalse(eco.migrate_smh_display(state))
        self.assertEqual(state['wallets'], before)
        self.assertTrue(state['meta']['smhShownAsSmc'])
        self.assertEqual(state['meta']['smcCents'], 100)

    def test_signed_ledger_stays_valid(self):
        state = eco.empty_state()
        chain = libro.empty(ed25519.publickey(SEED).hex())
        record = libro.acuñar(
            chain, SEED, 'Ana', 1250, 'Río', ts=3, bits=4, presupuesto=2,
        )
        self.assertEqual(record['amountSmh'], 1250)
        eco.migrate_smh_display(state)
        ok, why = libro.verificar(chain)
        self.assertTrue(ok, why)
        page = libro.pagina(chain, jugador='Ana')
        self.assertEqual(page['mintedText'], page['supply'])
        self.assertEqual(page['capText'], '21.000.000 SMC')
        self.assertEqual(page['playerMintedText'], '12,5 SMC')
        self.assertEqual(page['player'], 'Ana')
        other = libro.pagina(chain, jugador='Luz')
        self.assertEqual(other['playerMintedText'], '0 SMC')


class UiTests(unittest.TestCase):
    def test_play_screens_do_not_name_the_old_subunit(self):
        root = os.path.join(ROOT, 'play')
        hits = []
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if not name.endswith(('.js', '.html', '.css')) or name in UI_SKIP:
                    continue
                path = os.path.join(dirpath, name)
                text = open(path, encoding='utf-8').read()
                if BANNED.search(text):
                    hits.append(os.path.relpath(path, ROOT))
        self.assertEqual(hits, [])
        chest = open(os.path.join(root, 'baul.js'), encoding='utf-8').read()
        self.assertIn('0 SMC', chest)
        self.assertNotIn('SMH', chest)
        doc = open(os.path.join(ROOT, 'docs', 'economia-smc.md'), encoding='utf-8').read()
        self.assertIn('meta.smhShownAsSmc', doc)
        self.assertIn('21.000.000', doc)
        self.assertIn('Tus Simon Coins', open(os.path.join(root, 'libro-madre.js'), encoding='utf-8').read())


if __name__ == '__main__':
    unittest.main()
