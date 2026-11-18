# SPDX-License-Identifier: AGPL-3.0-or-later
"""El cambio por Simoncoin respeta la tarifa, el libro y el tope."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import cambiar
import economy as eco
import ed25519
import libro
import purses

SEED = bytes(range(32))


def cadena():
    return libro.empty(ed25519.publickey(SEED).hex())


class CambiarTests(unittest.TestCase):
    def setUp(self):
        self.econ = eco.empty_state()
        self.vault = {'accounts': {}, 'purses': {}}
        self.finca = {'accounts': {'Ana': {'goods': {}}}}
        self.chain = cadena()

    def _pagar(self, item, qty):
        plan = cambiar.preparar(self.econ, self.vault, self.finca, 'Ana', item, qty)
        self.assertTrue(plan['ok'], plan)
        granted, record = cambiar.cerrar(self.econ, self.chain, SEED, 'Ana', plan['smh'], 'cambio', ahora=10)
        self.assertEqual(granted, plan['smh'])
        self.assertEqual(record['kind'], 'acuñacion')
        return plan

    def test_rates_and_the_copper_floor(self):
        purses.credit(self.vault, 'Ana', 'mineral_cobre', 9)
        short = cambiar.preparar(self.econ, self.vault, self.finca, 'Ana', 'mineral_cobre', 9)
        self.assertFalse(short['ok'])
        self.assertEqual(purses.count(self.vault, 'Ana', 'mineral_cobre'), 9)
        purses.credit(self.vault, 'Ana', 'mineral_cobre', 1)
        plan = self._pagar('mineral_cobre', 10)
        self.assertEqual(plan['smh'], 1)
        self.assertEqual(purses.count(self.vault, 'Ana', 'mineral_cobre'), 0)
        purses.credit(self.vault, 'Ana', 'mineral_plata', 2)
        self.assertEqual(self._pagar('mineral_plata', 2)['smh'], 2)
        purses.credit(self.vault, 'Ana', 'mineral_oro', 1)
        self.assertEqual(self._pagar('mineral_oro', 1)['smh'], 10)
        self.finca['accounts']['Ana']['goods']['cafe_cereza'] = 3
        self.finca['accounts']['Ana']['goods']['cacao_baba'] = 1
        self.assertEqual(self._pagar('cafe_cereza', 3)['smh'], 3)
        self.assertEqual(self._pagar('cacao_baba', 1)['smh'], 1)
        self.assertEqual(self.econ['wallets']['Ana'], 1 + 2 + 10 + 3 + 1)
        self.assertEqual(self.econ['minedSmh'], 17)
        self.assertNotIn('cafe_cereza', self.finca['accounts']['Ana']['goods'])
        self.assertTrue(all(block['kind'] == 'acuñacion' for block in self.chain['blocks']))

    def test_cap_debits_nothing(self):
        self.econ['minedSmh'] = eco.MAX_SMH
        purses.credit(self.vault, 'Ana', 'cafe_cereza', 4)
        plan = cambiar.preparar(self.econ, self.vault, self.finca, 'Ana', 'cafe_cereza', 4)
        granted, record = cambiar.cerrar(self.econ, self.chain, SEED, 'Ana', plan['smh'], 'cambio', ahora=3)
        self.assertEqual(granted, 0)
        self.assertIsNone(record)
        cambiar._devolver(self.econ, self.vault, self.finca, 'Ana', 'cafe_cereza', plan['taken'])
        self.assertEqual(purses.count(self.vault, 'Ana', 'cafe_cereza'), 4)
        self.assertEqual(self.chain['blocks'], [])
        self.assertEqual(self.econ['minedSmh'], eco.MAX_SMH)

    def test_export_bags_are_not_this_exchange(self):
        self.assertIsNone(cambiar.ficha('bolsa_cafe'))
        self.assertIsNone(cambiar.ficha('bolsa_cacao'))


if __name__ == '__main__':
    unittest.main()
