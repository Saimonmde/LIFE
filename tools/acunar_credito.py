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
    if stock <= 0:
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
    """Suma las monedas enteras ya acuñadas a la mochila. No emite saldo nuevo."""
    row = piezas(coin, recibes)
    if not row:
        return None
    total = purses.credit(vault, name, row['item'], row['qty'])
    if total < row['qty']:
        return None
    row['total'] = total
    return row


def vista(vault, econ, name, account=None):
    """Lo que la mochila muestra. El saldo fino vive aquí aunque no llegue a una moneda entera.

    No acuña: sólo lee la billetera y las piezas que ya se guardaron.
    """
    import monedas
    purse = purses.public(vault, name)
    book = monedas.ledger(econ, name, account)
    balances = book.get('balances') or {}
    purse['monedas'] = {
        'moneda_oro': int(balances.get('simoncoin') or 0),
        'moneda_plata': int(balances.get('simonplata') or 0),
        'moneda_cobre': int(balances.get('simonchis') or 0),
    }
    return purse
