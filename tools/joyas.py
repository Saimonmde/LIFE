# SPDX-License-Identifier: AGPL-3.0-or-later
"""Receta Simon Jewels: 5 de oro, 3 de cobre y 2 de plata hacen 1,00 SMC.

El cambio directo de esos minerales sigue en 0,523 SMC. Esta receta entrega
1,00 SMC y no mueve esas tarifas. Si no cabe en el día o en los 21.000.000,
no se quita metal.
"""
import crudo
import purses

RECETA = (
    ('mineral_oro', 5),
    ('mineral_cobre', 3),
    ('mineral_plata', 2),
)
SMC = 1
SMH = 100
# 5 × 0,1 + 3 × 0,001 + 2 × 0,01. No es la tarifa de esta receta.
VALOR_CAMBIO = 0.523
NOTA = 'Inspirada en la moneda Simon Jewels · 100 g · 12K (50 oro · 30 cobre · 20 plata)'
NOMBRE = {
    'mineral_oro': 'oro',
    'mineral_cobre': 'cobre',
    'mineral_plata': 'plata',
}


def falta(stock):
    """Lo que no alcanza, en el orden de la receta."""
    missing = []
    for item, need in RECETA:
        have = int((stock or {}).get(item) or 0)
        if have < need:
            missing.append((item, need - have, need))
    return missing


def texto_falta(stock):
    missing = falta(stock)
    if not missing:
        return ''
    partes = ['%d de %s' % (gap, NOMBRE[item]) for item, gap, _need in missing]
    if len(partes) == 1:
        return 'Te falta ' + partes[0] + '.'
    return 'Te falta ' + ', '.join(partes[:-1]) + ' y ' + partes[-1] + '.'


def cabe(daily_left, room):
    """Hace falta cupo para el SMC entero. Un resto menor no se acuña."""
    return int(daily_left or 0) >= SMH and int(room or 0) >= SMH


def tener(econ, vault, account, name, item):
    crudo_n = int(crudo.nuggets(econ, account, item) or 0) if account else 0
    purse_n = purses.count(vault, name, item) if name else 0
    return max(crudo_n, purse_n)


def stock(econ, vault, account, name):
    return {item: tener(econ, vault, account, name, item) for item, _qty in RECETA}


def tomar(econ, vault, account, name):
    """Quita la receta. None si no alcanza, y en ese caso no deja el metal a medias."""
    have = stock(econ, vault, account, name)
    if falta(have):
        return None
    taken = []
    for item, qty in RECETA:
        crudo_n = int(crudo.nuggets(econ, account, item) or 0) if account else 0
        purse_n = purses.count(vault, name, item) if name else 0
        if crudo_n >= qty:
            if crudo.debit(econ, account, (item,), qty) is None:
                _devolver(econ, vault, account, name, taken)
                return None
            taken.append(('crudo', item, qty))
        if purse_n >= qty:
            if not purses.debit(vault, name, item, qty):
                _devolver(econ, vault, account, name, taken)
                return None
            taken.append(('purse', item, qty))
        if crudo_n < qty and purse_n < qty:
            _devolver(econ, vault, account, name, taken)
            return None
    return {'spent': {item: qty for item, qty in RECETA}, 'taken': taken}


def devolver(econ, vault, account, name, taken):
    _devolver(econ, vault, account, name, taken or [])


def _devolver(econ, vault, account, name, taken):
    for where, item, qty in taken:
        if where == 'crudo' and account:
            crudo.credit(econ, account, item, qty, cap=max(int(qty), 1))
        elif where == 'purse' and name:
            purses.credit(vault, name, item, qty)
