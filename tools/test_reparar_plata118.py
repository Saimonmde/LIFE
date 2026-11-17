# SPDX-License-Identifier: AGPL-3.0-or-later
"""La reparación del #118 acredita la diferencia en Simoncoin, una sola vez."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as eco
import ed25519
import libro
import reparar_plata118 as rep


def _econ():
    state = eco.empty_state()
    state['minedSmh'] = 0
    state['plata'] = {'wallets': {}, 'txs': [], 'minedSph': 0}
    return state


class RepairTests(unittest.TestCase):
    def test_dave_gets_the_floored_difference_and_a_second_run_does_nothing(self):
        econ = _econ()
        econ['plata']['txs'] = [
            {'type': 'mint', 'to': 'Dave', 'amountSph': 100},
            {'type': 'mint', 'to': 'Dave', 'amountSph': 250},
            {'type': 'mint', 'to': 'Ana', 'amountSph': 50},
            {'type': 'mint', 'to': 'Nico', 'amountSph': 100_000_000},
        ]
        preview = rep.plan(econ)
        self.assertTrue(preview['ok'])
        # 100+250 = 350 unidades. 350 // 100 = 3 centavos. 50 no llega a 0,01.
        # 1 SMP completo no es el bug.
        self.assertEqual(preview['cuentas'], [
            {'cuenta': 'Dave', 'unidades': 350, 'smh': 3, 'smc': 0.03},
        ])
        self.assertEqual(preview['totalSmc'], 0.03)
        antes = eco.issuance_room(econ)
        result = rep.aplicar(econ, now=20)
        self.assertEqual(result['estado'], 'hecha')
        self.assertEqual(econ['wallets']['Dave'], 3)
        self.assertNotIn('Ana', econ['wallets'])
        self.assertEqual(eco.issuance_room(econ), antes - 3)
        otra = rep.aplicar(econ, now=21)
        self.assertEqual(otra['estado'], 'ya')
        self.assertEqual(econ['wallets']['Dave'], 3)

    def test_one_hundred_units_are_one_cent_of_simoncoin(self):
        econ = _econ()
        econ['plata']['txs'] = [{'type': 'mint', 'to': 'Dave', 'amountSph': 100}]
        self.assertEqual(rep.plan(econ)['cuentas'][0]['smc'], 0.01)
        rep.aplicar(econ, now=1)
        self.assertEqual(econ['wallets']['Dave'], 1)

    def test_cap_blocks_every_account(self):
        econ = _econ()
        econ['minedSmh'] = (eco.MAX_SUPPLY - eco.TREASURY) * eco.SUBS
        econ['plata']['txs'] = [
            {'type': 'mint', 'to': 'Dave', 'amountSph': 100},
            {'type': 'mint', 'to': 'Ana', 'amountSph': 200},
        ]
        antes = dict(econ.get('wallets') or {})
        result = rep.aplicar(econ, now=1)
        self.assertEqual(result['estado'], 'bloqueada')
        self.assertFalse(result['changed'])
        self.assertEqual(econ.get('wallets') or {}, antes)
        self.assertNotIn('plata118', econ.get('meta') or {})

    def test_dry_run_file_and_public_book(self):
        econ = _econ()
        econ['plata']['txs'] = [{'type': 'mint', 'to': 'Dave', 'amountSph': 100}]
        with tempfile.TemporaryDirectory() as folder:
            result = rep.aplicar(econ, folder=folder, now=5)
            self.assertEqual(result['estado'], 'hecha')
            self.assertTrue(os.path.exists(os.path.join(folder, 'plata-118-respaldo.bin')))
            informe = open(os.path.join(folder, 'plata-118-informe.json'), encoding='utf-8').read()
            self.assertIn('dry-run', informe)
            self.assertIn('Dave', informe)
        seed = bytes(range(32))
        chain = libro.empty(ed25519.publickey(seed).hex())
        record = libro.acuñar(
            chain, seed, 'Dave', 1, 'Reparación de la plata del #118',
            kind='migracion', bits=1, presupuesto=2,
        )
        self.assertIsNotNone(record)
        public = libro.publico(record)
        self.assertEqual(public['owner'], 'Dave')
        self.assertEqual(public['amountSmh'], 1)
        self.assertEqual(public['kind'], 'migracion')


if __name__ == '__main__':
    unittest.main()
