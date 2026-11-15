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

CATALOG = {
    'bolsa_cafe': 'Bolsa de café',
    'bolsa_cacao': 'Bolsa de cacao',
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
    """Suma objetos ya obtenidos. No crea moneda. Devuelve el nuevo total."""
    item = str(item or '')
    qty = int(qty or 0)
    name = str(name or '')
    if not name or not item or qty <= 0:
        return count(state, name, item)
    bag = _box(state, name)
    bag[item] = min(MAX_STACK, int(bag.get(item) or 0) + qty)
    return bag[item]


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
