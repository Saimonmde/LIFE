# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lo que ve el jugador al acuñar. No crea monedas por sí mismo."""
import purses

ITEMS = {
    'simoncoin': 'moneda_oro',
    'simonplata': 'moneda_plata',
    'simonchis': 'moneda_cobre',
}


def motivo(stock, rate, left, room, metal, name):
    """Frase clara. El metal y el tope del día no se mezclan."""
    stock = float(stock or 0)
    rate = max(1, int(rate or 1))
    left = float(left or 0)
    room = float(room or 0)
    if stock < rate:
        return f'No tienes {metal} suficiente para acuñar {name}. Hacen falta {rate}.'
    if left <= 0:
        return 'Hoy ya llegaste al tope. Se reinicia a las 7:00 p. m.'
    if room <= 0:
        return f'Ya no se puede crear más {name}.'
    return ''


def piezas(coin, recibes):
    """Monedas enteras que entran en la mochila. El saldo fino vive en el libro."""
    try:
        qty = int(recibes or 0)
    except (TypeError, ValueError):
        qty = 0
    if coin not in ITEMS or qty < 1:
        return None
    return {'item': ITEMS[coin], 'qty': qty}


def acreditar_mochila(vault, name, coin, recibes):
    """Suma las monedas ya acuñadas a la mochila. No emite saldo nuevo."""
    row = piezas(coin, recibes)
    if not row:
        return None
    total = purses.credit(vault, name, row['item'], row['qty'])
    if total < row['qty']:
        return None
    row['total'] = total
    return row
