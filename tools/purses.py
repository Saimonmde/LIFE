# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mochila de objetos en el servidor, distinta del depósito del banquito.

La cosecha (café, cacao u otro oficio) acredita aquí. El intercambio lee
esta mochila: no acepta un inventario que sólo exista en el navegador.

Identificadores acordados para el oficio de café y cacao:

- bolsa_cafe
- bolsa_cacao

Cualquier otro id que cumpla ^[a-z][a-z0-9_]{0,31}$ también se puede
acreditar. No hace falta editar este archivo para sumar un objeto nuevo.
"""

import mochila

CATALOG = {
    'bolsa_cafe': 'Bolsa de café',
    'bolsa_cacao': 'Bolsa de cacao',
    'cafe_cereza': 'Café cereza',
    'cafe_lavado': 'Café lavado',
    'cafe_pergamino': 'Pergamino seco',
    'cafe_tostado': 'Café tostado',
    'gallo': 'Gallo',
}
MAX_STACK = 9999


def _box(state, name):
    purses = state.setdefault('purses', {})
    bag = purses.setdefault(str(name or ''), {})
    return bag


def inventory(state, name):
    bag = (state.get('purses') or {}).get(str(name or '')) or {}
    out = {}
    for key, qty in bag.items():
        have = int(qty or 0)
        if have > 0:
            out[str(key)] = have
    return out


def count(state, name, item):
    return int(inventory(state, name).get(str(item or '')) or 0)


def credit(state, name, item, qty):
    """Suma objetos ya obtenidos. No crea moneda. Devuelve el nuevo total.

    No recorta en silencio: si no cabe en la mochila o en el montón,
    deja el saldo igual y devuelve lo que ya había.
    """
    item = str(item or '')
    qty = int(qty or 0)
    name = str(name or '')
    have = count(state, name, item)
    if not name or not item or qty <= 0:
        return have
    if have + qty > MAX_STACK:
        return have
    bag = inventory(state, name)
    if not mochila.fits(bag, item, qty):
        return have
    stored = _box(state, name)
    stored[item] = have + qty
    return stored[item]


def debit(state, name, item, qty):
    item = str(item or '')
    qty = int(qty or 0)
    if qty <= 0:
        return True
    bag = _box(state, str(name or ''))
    have = int(bag.get(item) or 0)
    if have < qty:
        return False
    left = have - qty
    if left:
        bag[item] = left
    else:
        bag.pop(item, None)
    return True


def public(state, name):
    return {'items': inventory(state, name), 'catalog': dict(CATALOG)}
