# SPDX-License-Identifier: AGPL-3.0-or-later
"""Oficio, plano de la casa, mascotas y dirección CASA-XXXX."""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import hogar

ROOT = pathlib.Path(__file__).resolve().parents[1]


def usuario(ident='u1', nombre='Ana'):
    return {'id': ident, 'name': nombre}


class HogarTests(unittest.TestCase):
    def test_codigo_y_visitas(self):
        doc = hogar.vacio()
        ana = usuario()
        vista = hogar.aplicar(doc, ana, {'role': 'guardian'})
        codigo = vista['codigo']
        self.assertTrue(codigo.startswith('CASA-') and len(codigo) == 9)
        self.assertEqual(hogar.visitar(doc, codigo, 'Ana')[0]['dueno'], 'Ana')
        hogar.fijar_visitas(doc, ana, False)
        publica, error = hogar.visitar(doc, codigo, 'Ana')
        self.assertIsNone(publica)
        self.assertIn('no recibe visitas', error)
        nuevo = hogar.regenerar(doc, ana)
        self.assertNotEqual(nuevo['codigo'], codigo)
        self.assertFalse(nuevo['visitas'])
        self.assertIsNone(hogar.visitar(doc, codigo, 'Ana')[0])
        self.assertIsNone(hogar.visitar(doc, nuevo['codigo'], 'Ana')[0])
        hogar.fijar_visitas(doc, ana, True)
        self.assertEqual(hogar.visitar(doc, nuevo['codigo'], 'Ana')[0]['codigo'], nuevo['codigo'])

    def test_nft_no_se_llena_desde_el_cliente(self):
        doc = hogar.vacio()
        vista = hogar.aplicar(doc, usuario(), {
            'role': 'explorador',
            'nft': {'enlace': 'https://ejemplo.invalid/token', 'token': '1'},
        })
        self.assertEqual(vista['nft']['enlace'], '')
        self.assertEqual(vista['nft']['token'], '')
        self.assertEqual(doc['por_cuenta']['u1']['nft']['cadena'], '')
        self.assertIn('no acuña', vista['nft']['nota'])

    def test_oficio_y_mascotas(self):
        doc = hogar.vacio()
        with self.assertRaises(hogar.HogarError):
            hogar.aplicar(doc, usuario(), {'role': 'rey'})
        hogar.aplicar(doc, usuario(), {'role': 'artesano', 'mascotas': [
            {'especie': 'gato', 'color': 'tricolor', 'nombre': 'Michi'},
            {'species': 'perro', 'color': 'dorado', 'nombre': '  Firu  '},
            {'especie': 'gato', 'color': 'no-existe', 'nombre': ''},
            {'especie': 'loro', 'color': 'verde', 'nombre': 'Loro'},
        ]})
        box = doc['por_cuenta']['u1']
        self.assertEqual(box['role'], 'artesano')
        self.assertEqual(len(box['mascotas']), 3)
        self.assertEqual(box['mascotas'][0]['nombre'], 'Michi')
        self.assertEqual(box['mascotas'][2]['color'], 'naranja')
        self.assertEqual(box['mascotas'][2]['nombre'], 'Michi')
        self.assertEqual(hogar.oficio_de(doc, 'u1'), 'artesano')

    def test_plano_estilos_y_solapes(self):
        casa = {
            'wall': '#e4c48a', 'floor': '#c45c38',
            'items': [
                {'id': 'bed', 'type': 'bed', 'x': 1, 'y': 1, 'rot': 0, 'style': 'dosel'},
                {'id': 'otra', 'type': 'bed', 'x': 1, 'y': 1, 'rot': 0, 'style': 'catre'},
                {'id': 'altar', 'type': 'altar', 'x': 5, 'y': 1, 'rot': 0, 'style': 'inventado'},
                {'id': 'fuera', 'type': 'silla-magica', 'x': 1, 'y': 2, 'rot': 0},
            ],
        }
        limpio = hogar.sanitizar_casa(casa)
        self.assertEqual([it['id'] for it in limpio['items']], ['bed', 'altar'])
        self.assertEqual(limpio['items'][0]['style'], 'dosel')
        self.assertEqual(limpio['items'][1]['style'], 'madera')
        self.assertEqual(limpio['wall'], '#e4c48a')

    def test_el_plano_del_juego_cabe(self):
        script = ROOT / 'tools' / 'test_casa_layout.mjs'
        hecho = subprocess.run(['node', str(script)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(hecho.returncode, 0, hecho.stderr or hecho.stdout)
        self.assertIn('PLANO OK', hecho.stdout)

    def test_borrar_la_cuenta_suelta_el_codigo(self):
        doc = hogar.vacio()
        vista = hogar.aplicar(doc, usuario(), {'role': 'comerciante'})
        hogar.olvidar(doc, 'u1')
        self.assertNotIn('u1', doc['por_cuenta'])
        self.assertIsNone(hogar.visitar(doc, vista['codigo'], 'Ana')[0])

    def test_archivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'hogar.json')
            doc = hogar.vacio()
            hogar.aplicar(doc, usuario('cuenta'), {'role': 'inmobiliario'})
            hogar.save(path, doc)
            otra = hogar.load(path)
            self.assertEqual(otra['por_cuenta']['cuenta']['role'], 'inmobiliario')


if __name__ == '__main__':
    unittest.main()
