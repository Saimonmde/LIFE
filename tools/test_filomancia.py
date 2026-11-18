# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import unittest

import filomancia as F


class FilomanciaTest(unittest.TestCase):
    def test_la_linea_empieza_en_hacer_fuego_y_el_maestro_lanza_fuegos(self):
        self.assertEqual(F.rango(0), 'Hacer fuego')
        self.assertEqual(F.nivel(0), 1)
        self.assertEqual(F.rango(25), 'Mantener la llama')
        self.assertEqual(F.rango(100), 'Brasas')
        self.assertEqual(F.rango(225), 'Chispa alta')
        self.assertEqual(F.nivel(399), 4)
        self.assertFalse(F.puede_fuegos(399))
        self.assertEqual(F.rango(400), 'Fuegos artificiales')
        self.assertTrue(F.puede_fuegos(400))
        self.assertIsNone(F.lanzar(100)[0])
        self.assertEqual(F.lanzar(400)[0]['segundos'], 8)

    def test_prender_gasta_una_madera_y_exige_encendedor(self):
        self.assertIsNone(F.preparar(False, 3, False)[0])
        self.assertIsNone(F.preparar(True, 0, False)[0])
        self.assertIsNone(F.preparar(True, 2, True)[0])
        hecho = F.preparar(True, 2, False)[0]
        self.assertEqual(hecho['madera'], 1)
        self.assertEqual(hecho['segundos'], 60)
        self.assertEqual(F.fase(60), 'llama')
        self.assertEqual(F.fase(8), 'brasas')
        self.assertEqual(F.fase(0), 'apagada')

    def test_solo_la_ve_quien_esta_cerca_y_en_la_misma_zona(self):
        self.assertTrue(F.ve(10, 10, 'city', 20, 12, 'city'))
        self.assertFalse(F.ve(10, 10, 'city', 80, 10, 'city'))
        self.assertFalse(F.ve(10, 10, 'city', 12, 12, 'casa'))

    def test_el_cliente_nombra_la_linea_y_el_encendedor(self):
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        texto = open(os.path.join(raiz, 'play', 'filomancia.js'), encoding='utf-8').read()
        self.assertIn('Filomancia', texto)
        self.assertIn('Fuegos artificiales', texto)
        self.assertIn('Encendedor', texto)
        self.assertIn('madera', texto)
