# SPDX-License-Identifier: AGPL-3.0-or-later
"""Monedas físicas de plata y de cobre. No entran al libro mayor.

Cuatro minerales de plata hacen una moneda de plata.
Tres minerales de cobre hacen una moneda de cobre.
Un lingote hace una moneda: no hay otra receta de lingote, y ese es el supuesto.
Canjear usa el mineral que lleva la moneda (plata 0,01 SMC, cobre 0,001 SMC).
El piso es entero. Si no alcanza 0,01 SMC, no se quita ninguna moneda.
"""
import crudo
import purses
import topes
import vault

PLATA_POR_MONEDA = 'simonplata'
COBRE_POR_MONEDA = 'simonchis'
# 1 mineral de plata = 0,01 SMC = 1 unidad mínima. 1 mineral de cobre = un décimo de eso.
SMH_POR_PLATA = 1
SMH_POR_COBRE_NUM = 1
SMH_POR_COBRE_DEN = 10

METAL = {
    'plata': {
        'item': 'moneda_plata',
        'nombre': 'Moneda de plata',
        'mineral': 'mineral_plata',
        'lingote': 'lingote_plata',
        'tasa': PLATA_POR_MONEDA,
    },
    'cobre': {
        'item': 'moneda_cobre',
        'nombre': 'Moneda de cobre',
        'mineral': 'mineral_cobre',
        'lingote': 'lingote_cobre',
        'tasa': COBRE_POR_MONEDA,
    },
}


class PiezaError(ValueError):
    pass


def ficha(metal):
    row = METAL.get(str(metal or ''))
    if not row:
        raise PiezaError('Esa moneda no se acuña.')
    return row


def minerales_por_moneda(metal):
    row = ficha(metal)
    rate = int(topes.rate(row['tasa']) or 0)
    if rate < 1:
        raise PiezaError('La receta de esa moneda no está definida.')
    return rate


def smh_de(metal, monedas):
    """Unidades mínimas de Simoncoin que salen de esas monedas. El resto se descarta."""
    monedas = int(monedas or 0)
    if monedas < 1:
        return 0
    rate = minerales_por_moneda(metal)
    minerales = monedas * rate
    if metal == 'plata':
        return minerales * SMH_POR_PLATA
    if metal == 'cobre':
        return (minerales * SMH_POR_COBRE_NUM) // SMH_POR_COBRE_DEN
    return 0


def _acreditar(state, name, item, qty):
    before = purses.count(state, name, item)
    after = purses.credit(state, name, item, qty)
    if after != before + int(qty):
        return False
    return True


def _devolver_crudo(econ, account, spent):
    for item, qty in (spent or {}).items():
        amount = int(round(float(qty or 0)))
        if amount > 0:
            crudo.credit(econ, account, item, amount, cap=max(amount, 1))


def acuñar_crudo(econ, vault_state, account, name, metal, minerales):
    """Gasta minerales enteros y deja las monedas en la mochila. No toca el libro."""
    row = ficha(metal)
    try:
        minerales = int(minerales or 0)
    except (TypeError, ValueError):
        minerales = 0
    rate = minerales_por_moneda(metal)
    monedas = minerales // rate
    if monedas < 1:
        return {'ok': False, 'reason': 'Hacen falta %d de %s para una moneda.' % (rate, row['mineral'].replace('_', ' '))}
    gasta = monedas * rate
    if not account:
        return {'ok': False, 'reason': 'Entra con una cuenta para acuñar.'}
    spent = crudo.debit(econ, account, (row['mineral'],), gasta)
    if spent is None:
        return {'ok': False, 'reason': 'No hay suficiente mineral. No se acuñó nada.'}
    if not _acreditar(vault_state, name, row['item'], monedas):
        _devolver_crudo(econ, account, spent)
        return {'ok': False, 'reason': 'La mochila no acepta más monedas. El mineral sigue en la cuenta.'}
    return {
        'ok': True,
        'coin': row['tasa'],
        'item': row['item'],
        'name': row['nombre'],
        'qty': monedas,
        'total': purses.count(vault_state, name, row['item']),
        'gastados': gasta,
        'spent': spent,
        'fuente': 'mineral',
        'reason': 'Se acuñó %d %s. Quedó en el inventario. El libro mayor no la anota.' % (monedas, row['nombre'].lower()),
    }


def _tomar_lingote(vault_state, name, item, qty):
    de_mano = min(purses.count(vault_state, name, item), qty)
    if de_mano and not purses.debit(vault_state, name, item, de_mano):
        return None
    resto = qty - de_mano
    if resto:
        box = vault.account(vault_state, name)
        if not vault.take_item(box, item, resto):
            if de_mano:
                purses.credit(vault_state, name, item, de_mano)
            return None
    return {'mano': de_mano, 'baul': resto}


def _devolver_lingote(vault_state, name, item, tomado):
    if not tomado:
        return
    if tomado.get('mano'):
        purses.credit(vault_state, name, item, tomado['mano'])
    if tomado.get('baul'):
        vault.add_item(vault.account(vault_state, name), item, tomado['baul'])


def acuñar_lingote(vault_state, name, metal, monedas):
    """Un lingote, una moneda. El supuesto: no hay otra receta de lingote."""
    row = ficha(metal)
    try:
        monedas = int(monedas or 0)
    except (TypeError, ValueError):
        monedas = 0
    if monedas < 1:
        return {'ok': False, 'reason': 'Elige al menos un lingote.'}
    tomado = _tomar_lingote(vault_state, name, row['lingote'], monedas)
    if tomado is None:
        return {'ok': False, 'reason': 'No hay suficientes lingotes. No se acuñó nada.'}
    if not _acreditar(vault_state, name, row['item'], monedas):
        _devolver_lingote(vault_state, name, row['lingote'], tomado)
        return {'ok': False, 'reason': 'La mochila no acepta más monedas. El lingote sigue donde estaba.'}
    return {
        'ok': True,
        'coin': row['tasa'],
        'item': row['item'],
        'name': row['nombre'],
        'qty': monedas,
        'total': purses.count(vault_state, name, row['item']),
        'gastados': monedas,
        'spent': {row['lingote']: monedas},
        'fuente': 'lingote',
        'reason': 'Se acuñó %d %s a partir del lingote. El libro mayor no la anota.' % (monedas, row['nombre'].lower()),
    }


def preparar_canje(vault_state, name, metal, monedas):
    """Quita las monedas sólo si el canje llega al menos a 0,01 SMC."""
    row = ficha(metal)
    try:
        monedas = int(monedas or 0)
    except (TypeError, ValueError):
        monedas = 0
    smh = smh_de(metal, monedas)
    if smh < 1:
        return {'ok': False, 'reason': 'Con esa cantidad no llega a 0,01 SMC. Las monedas siguen en el inventario.'}
    if not purses.debit(vault_state, name, row['item'], monedas):
        return {'ok': False, 'reason': 'No tienes esas monedas.'}
    return {'ok': True, 'smh': smh, 'item': row['item'], 'qty': monedas, 'name': row['nombre']}


def devolver_canje(vault_state, name, item, qty):
    purses.credit(vault_state, name, item, qty)
