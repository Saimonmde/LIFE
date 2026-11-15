# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy
import fichas
from fichas import FichaError


class FichaTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop('FICHAS_FISICAS', None)
        self.econ = economy.empty_state()
        self.econ['wallets']['Ana'] = 5 * economy.SUBS
        self.econ['wallets']['Luis'] = 0
        self.mined = self.econ['minedSmh']

    def test_flag_off_by_default(self):
        self.assertFalse(fichas.activas())
        code, payload, kind = fichas.responder(self.econ, 'GET', '/ficha/FIC-1', {}, {}, None)
        self.assertEqual(code, 404)
        self.assertEqual(kind, 'json')
        self.assertEqual(payload['error'], 'no existe')

    def test_issue_locks_existing_balance_and_does_not_mint(self):
        issued = fichas.emitir(self.econ, 'Ana', 'simoncoin', economy.SUBS, '12 g', 'serie A', ahora=10)
        self.assertEqual(self.econ['wallets']['Ana'], 4 * economy.SUBS)
        self.assertEqual(self.econ['wallets'][fichas.RESERVA], economy.SUBS)
        self.assertEqual(self.econ['minedSmh'], self.mined)
        self.assertTrue(issued['url'].startswith('/ficha/' + issued['id'] + '?m='))
        with self.assertRaises(FichaError):
            fichas.emitir(self.econ, 'Ana', 'simoncoin', 10 * economy.SUBS, '12 g', 'serie A')
        self.assertEqual(self.econ['wallets'][fichas.RESERVA], economy.SUBS)

    def test_public_page_hides_people_and_bad_mac_matches_unknown(self):
        issued = fichas.emitir(self.econ, 'Ana', 'simoncoin', economy.SUBS, '12 g', 'serie A', ahora=10)
        mac = issued['url'].split('m=')[1]
        page = fichas.vista_publica(self.econ, issued['id'], mac)
        shown = json.dumps(page)
        self.assertNotIn('Ana', shown)
        self.assertNotIn('clave', shown)
        self.assertEqual(page['estado'], 'circulando')
        self.assertEqual(page['peso_g'], '12 g')
        unknown = fichas.vista_publica(self.econ, issued['id'], 'mal')
        missing = fichas.vista_publica(self.econ, 'FIC-NO', mac)
        self.assertEqual(unknown, missing)
        self.assertFalse(unknown['comprobada'])

    def test_scan_starts_nothing_and_four_steps_move_the_holder_only(self):
        issued = fichas.emitir(self.econ, 'Ana', 'simoncoin', economy.SUBS, '12 g', 'serie A', ahora=10)
        mac = issued['url'].split('m=')[1]
        ident = issued['id']
        before = self.econ['wallets']['Ana']
        scanned = fichas.leer(self.econ, ident, mac, 'medellin', ahora=20)
        self.assertFalse(scanned['transferencia'])
        self.assertEqual(self.econ['fichas']['piezas'][ident]['titular'], 'Ana')
        self.assertEqual(self.econ['wallets']['Ana'], before)
        intent = scanned['intencion']
        fichas.aceptar(self.econ, 'Ana', intent)
        fichas.aceptar(self.econ, 'Luis', intent)
        mid = fichas.confirmar(self.econ, 'Ana', intent)
        self.assertFalse(mid['transferencia'])
        self.assertEqual(self.econ['fichas']['piezas'][ident]['titular'], 'Ana')
        done = fichas.confirmar(self.econ, 'Luis', intent)
        self.assertTrue(done['transferencia'])
        self.assertEqual(self.econ['fichas']['piezas'][ident]['titular'], 'Luis')
        self.assertEqual(self.econ['wallets']['Ana'], before)
        self.assertEqual(self.econ['wallets']['Luis'], 0)
        self.assertEqual(self.econ['wallets'][fichas.RESERVA], economy.SUBS)
        public = json.dumps(fichas.vista_publica(self.econ, ident, mac))
        self.assertNotIn('Ana', public)
        self.assertNotIn('Luis', public)
        self.assertNotIn('reserva_fichas', public)

    def test_lost_status_blocks_transfer_and_duplicate_places_flag(self):
        issued = fichas.emitir(self.econ, 'Ana', 'simoncoin', economy.SUBS, '12 g', 'serie A', ahora=10)
        mac = issued['url'].split('m=')[1]
        ident = issued['id']
        fichas.marcar(self.econ, 'Ana', ident, 'robada')
        scanned = fichas.leer(self.econ, ident, mac, 'bello', ahora=30)
        with self.assertRaises(FichaError):
            fichas.aceptar(self.econ, 'Ana', scanned['intencion'])
        self.assertEqual(self.econ['fichas']['piezas'][ident]['titular'], 'Ana')
        other = fichas.emitir(self.econ, 'Ana', 'simoncoin', economy.SUBS, '8 g', 'serie B', ahora=11)
        other_mac = other['url'].split('m=')[1]
        fichas.leer(self.econ, other['id'], other_mac, 'medellin', ahora=100)
        fichas.leer(self.econ, other['id'], other_mac, 'bello', ahora=200)
        self.assertIn('sitios distintos', self.econ['fichas']['piezas'][other['id']]['alerta'])
        blocked = fichas.leer(self.econ, other['id'], other_mac, 'bello', ahora=210)
        with self.assertRaises(FichaError):
            fichas.aceptar(self.econ, 'Ana', blocked['intencion'])

    def test_second_code_stays_out_of_the_qr_and_redeem_returns_the_lock(self):
        issued = fichas.emitir(self.econ, 'Ana', 'simoncoin', 100, '10 g', 'serie C', ahora=10, segundo='oculto')
        self.assertNotIn('oculto', issued['url'])
        mac = issued['url'].split('m=')[1]
        shown = json.dumps(fichas.vista_publica(self.econ, issued['id'], mac))
        self.assertNotIn('oculto', shown)
        self.assertNotIn('segundo', shown)
        with self.assertRaises(FichaError):
            fichas.retirar(self.econ, 'Ana', issued['id'], 'mal')
        self.assertEqual(self.econ['wallets'][fichas.RESERVA], 100)
        fichas.retirar(self.econ, 'Ana', issued['id'], 'oculto')
        self.assertEqual(self.econ['fichas']['piezas'][issued['id']]['estado'], 'retirada')
        self.assertEqual(self.econ['wallets'].get(fichas.RESERVA, 0), 0)
        self.assertEqual(self.econ['minedSmh'], self.mined)


if __name__ == '__main__':
    unittest.main()
