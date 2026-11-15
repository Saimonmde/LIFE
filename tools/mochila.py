# SPDX-License-Identifier: AGPL-3.0-or-later
"""Capacidad de la mochila. El servidor decide; el cliente sólo avisa.

Sesenta casillas. Cada objeto distinto ocupa una, y el montón de ese
objeto sigue el tope que ya tiene el intercambio. Si no entra, no se
suma nada: ni se pierde ni se duplica.
"""

SLOTS = 60
FULL = 'Tu mochila está llena'


def slots_used(items):
    return sum(1 for qty in (items or {}).values() if int(qty or 0) > 0)


def fits(items, item, qty):
    qty = int(qty or 0)
    item = str(item or '')
    if qty <= 0 or not item:
        return False
    have = int((items or {}).get(item) or 0)
    if have > 0:
        return True
    return slots_used(items) + 1 <= SLOTS


def add(items, item, qty):
    """Suma en el mismo diccionario. False si no cabe: el diccionario no cambia."""
    if not fits(items, item, qty):
        return False
    item = str(item)
    items[item] = int(items.get(item) or 0) + int(qty)
    return True
