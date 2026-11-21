# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cambiar
import crudo
import joyas


class JoyasTest(unittest.TestCase):
    def test_la_receta_pide_los_tres_metales_y_entrega_un_smc(self):
        self.assertEqual(joyas.RECETA, (('mineral_oro', 5), ('mineral_cobre', 3), ('mineral_plata', 2)))
        self.assertEqual(joyas.SMH, 100)
        self.assertEqual(joyas.VALOR_CAMBIO, 0.523)
        self.assertIn('Simon Jewels', joyas.NOTA)
        self.assertIn('100 g', joyas.NOTA)
        self.assertIn('12K', joyas.NOTA)
        vacio = {}
        self.assertIn('oro', joyas.texto_falta(vacio))
        self.assertFalse(joyas.cabe(99, 1000))
        self.assertFalse(joyas.cabe(100, 99))
        self.assertTrue(joyas.cabe(100, 100))
        self.assertEqual(cambiar.TARIFA['mineral_oro'][3], '0,1')
        self.assertEqual(cambiar.TARIFA['mineral_plata'][3], '0,01')
        self.assertEqual(cambiar.TARIFA['mineral_cobre'][3], '0,001')
        self.assertEqual(cambiar.TARIFA['cafe_cereza'][3], '0,01')
        self.assertEqual(cambiar.TARIFA['cacao_baba'][3], '0,01')

    def test_sin_el_metal_completo_no_quita_nada(self):
        econ = {'crudo': {}}
        vault = {'purses': {}}
        for item, qty in (('mineral_oro', 5), ('mineral_cobre', 3), ('mineral_plata', 1)):
            crudo.credit(econ, 'ana', item, qty, cap=qty)
        self.assertIsNone(joyas.tomar(econ, vault, 'ana', 'Ana'))
        self.assertEqual(int(crudo.nuggets(econ, 'ana', 'mineral_plata')), 1)
        self.assertEqual(int(crudo.nuggets(econ, 'ana', 'mineral_oro')), 5)

    def test_con_la_receta_quita_el_metal_y_se_puede_devolver(self):
        econ = {'crudo': {}}
        vault = {'purses': {}}
        for item, qty in joyas.RECETA:
            crudo.credit(econ, 'ana', item, qty, cap=qty)
        tomado = joyas.tomar(econ, vault, 'ana', 'Ana')
        self.assertEqual(tomado['spent']['mineral_oro'], 5)
        self.assertEqual(int(crudo.nuggets(econ, 'ana', 'mineral_oro')), 0)
        self.assertEqual(int(crudo.nuggets(econ, 'ana', 'mineral_cobre')), 0)
        self.assertEqual(int(crudo.nuggets(econ, 'ana', 'mineral_plata')), 0)
        joyas.devolver(econ, vault, 'ana', 'Ana', tomado['taken'])
        self.assertEqual(int(crudo.nuggets(econ, 'ana', 'mineral_oro')), 5)
        self.assertEqual(int(crudo.nuggets(econ, 'ana', 'mineral_cobre')), 3)

    def test_la_pantalla_muestra_la_receta_y_la_marca(self):
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        texto = open(os.path.join(raiz, 'play', 'acunar.js'), encoding='utf-8').read()
        self.assertIn('Inspirada en la moneda Simon Jewels · 100 g · 12K (50 oro · 30 cobre · 20 plata)', texto)
        self.assertIn('acunar-joyas-ok', texto)
        self.assertIn("t: 'joyas'", texto)
        self.assertIn('mineral_oro.svg', texto)
        pagina = open(os.path.join(raiz, 'server.py'), encoding='utf-8').read()
        self.assertIn('def joyas_for', pagina)
        self.assertIn("t == 'joyas'", pagina)
