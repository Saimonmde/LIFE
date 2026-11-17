# SPDX-License-Identifier: AGPL-3.0-or-later
"""Soltar un objeto. Sale del inventario al momento y aparece en el piso a los 10 segundos.

Mientras espera, sólo hay un indicador. Cuando aparece, cualquiera lo recoge,
incluido quien lo soltó, sin otra espera. A los 30 minutos desaparece, igual
que el saco del puma. El Simoncoin no se suelta.
"""
import time

import crudo
import fauna
import purses
import vault

ESPERA = 10
VIDA = fauna.DROP_TTL
CERCA = 2
NO_SOLTAR = frozenset({
    'smc', 'simoncoin', 'smh', 'smp', 'sph', 'sai', 'moneda_oro',
})
COLORES = {
    'mineral_oro': '#e2b23c',
    'pepita_oro': '#ffe08a',
    'mineral_plata': '#d5dee8',
    'mineral_cobre': '#d08a52',
    'moneda_plata': '#e8eef4',
    'moneda_cobre': '#c46a32',
    'lingote_oro': '#e2b23c',
    'lingote_plata': '#d5dee8',
    'lingote_cobre': '#d08a52',
    'bolsa_cafe': '#6f4e37',
    'bolsa_cacao': '#c4a574',
}
NOMBRES = {
    'mineral_oro': 'Oro crudo',
    'pepita_oro': 'Pepita de oro',
    'mineral_plata': 'Plata cruda',
    'mineral_cobre': 'Cobre crudo',
    'moneda_plata': 'Moneda de plata',
    'moneda_cobre': 'Moneda de cobre',
    'lingote_oro': 'Lingote de oro',
    'lingote_plata': 'Lingote de plata',
    'lingote_cobre': 'Lingote de cobre',
    'bolsa_cafe': 'Café',
    'bolsa_cacao': 'Cacao',
    'piedra': 'Piedra',
    'madera': 'Madera',
}


def explicar(item):
    textos = {
        'mineral_oro': 'Oro crudo. En el horno se vuelve Simoncoin y esa acuñación sí entra al libro mayor.',
        'pepita_oro': 'Pepita de oro. El horno la cuenta como oro crudo para acuñar Simoncoin.',
        'mineral_plata': 'Plata cruda. Cuatro piezas hacen una moneda de plata, que se guarda en el inventario.',
        'mineral_cobre': 'Cobre crudo. Tres piezas hacen una moneda de cobre, que se guarda en el inventario.',
        'moneda_plata': 'Moneda de plata acuñada. Se guarda, se cambia o se suelta. No es Simoncoin.',
        'moneda_cobre': 'Moneda de cobre acuñada. Se guarda, se cambia o se suelta. No es Simoncoin.',
        'lingote_plata': 'Lingote de plata. En el horno equivale a una moneda de plata.',
        'lingote_cobre': 'Lingote de cobre. En el horno equivale a una moneda de cobre.',
        'lingote_oro': 'Lingote de oro. Lo guarda el Banco Central. No es Simoncoin suelto.',
        'bolsa_cafe': 'Café de la finca. Se lleva al taller y también se puede cambiar.',
        'bolsa_cacao': 'Cacao de la finca. Se lleva al taller y también se puede cambiar.',
        'piedra': 'Piedra de la mina. Sirve de material. No es una moneda.',
        'madera': 'Madera. Sirve de material. No es una moneda.',
    }
    return textos.get(item) or 'Objeto del inventario. Se puede guardar en el baúl o dejar en el piso.'


def _libro(state):
    rows = state.setdefault('piso', [])
    if not isinstance(rows, list):
        rows = []
        state['piso'] = rows
    return rows


def _tokens(state):
    box = state.setdefault('pisoTokens', [])
    if not isinstance(box, list):
        box = []
        state['pisoTokens'] = box
    return box


def _limpiar(state, now):
    rows = [row for row in _libro(state) if float(row.get('expires') or 0) > now]
    state['piso'] = rows
    return rows


def _debitar(econ, vault_state, account, name, item, qty):
    if purses.count(vault_state, name, item) >= qty and purses.debit(vault_state, name, item, qty):
        return {'donde': 'mochila'}
    box = vault.account(vault_state, name)
    if vault.take_item(box, item, qty):
        return {'donde': 'baul'}
    if item in crudo.CAPS and account:
        spent = crudo.debit(econ, account, (item,), qty)
        if spent is not None:
            return {'donde': 'crudo', 'spent': spent}
    return None


def _devolver(econ, vault_state, account, name, item, qty, tomado):
    donde = (tomado or {}).get('donde')
    if donde == 'mochila':
        purses.credit(vault_state, name, item, qty)
    elif donde == 'baul':
        vault.add_item(vault.account(vault_state, name), item, qty)
    elif donde == 'crudo':
        crudo.credit(econ, account, item, qty, cap=max(int(qty), 1))


def soltar(econ, vault_state, account, name, item, qty, x, y, zone, now=None, token=''):
    now = time.time() if now is None else float(now)
    item = str(item or '')
    token = str(token or '')[:48]
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        qty = 0
    if item in NO_SOLTAR or item.lower() in NO_SOLTAR:
        return {'ok': False, 'reason': 'El Simoncoin no se suelta. Se cambia con otra persona.'}
    if qty < 1 or qty > 999 or not item:
        return {'ok': False, 'reason': 'Esa cantidad no se suelta.'}
    vistos = _tokens(econ)
    if token and token in vistos:
        return {'ok': True, 'dup': True, 'reason': 'Ese soltar ya se aplicó.'}
    tomado = _debitar(econ, vault_state, account, name, item, qty)
    if tomado is None:
        return {'ok': False, 'reason': 'No tienes esa cantidad.'}
    seq = int(econ.get('pisoSeq') or 0) + 1
    econ['pisoSeq'] = seq
    drop = {
        'id': 'p%d' % seq,
        'item': item,
        'name': NOMBRES.get(item) or item,
        'qty': qty,
        'x': float(x),
        'y': float(y),
        'zone': str(zone or 'city'),
        'aparece': now + ESPERA,
        'expires': now + VIDA,
        'color': COLORES.get(item) or '#c4a574',
        'token': token,
    }
    _libro(econ).append(drop)
    if token:
        vistos.append(token)
        del vistos[:-80]
    return {'ok': True, 'drop': _fila(drop, now), 'donde': tomado['donde'], 'reason': 'Soltaste %d. Aparece en el piso en %d segundos.' % (qty, ESPERA)}


def _fila(drop, now):
    return {
        'id': drop['id'],
        'item': drop['item'],
        'name': drop.get('name') or drop['item'],
        'qty': int(drop.get('qty') or 0),
        'x': float(drop.get('x') or 0),
        'y': float(drop.get('y') or 0),
        'zone': drop.get('zone') or 'city',
        'aparece': float(drop.get('aparece') or 0),
        'expires': float(drop.get('expires') or 0),
        'espera': now < float(drop.get('aparece') or 0),
        'color': drop.get('color') or '#c4a574',
    }


def publicos(state, zone, now=None):
    now = time.time() if now is None else float(now)
    zone = str(zone or 'city')
    return [_fila(row, now) for row in _limpiar(state, now) if row.get('zone') == zone]


def alzar(econ, vault_state, name, drop_id, x, y, zone, now=None):
    now = time.time() if now is None else float(now)
    rows = _limpiar(econ, now)
    drop = next((row for row in rows if row.get('id') == str(drop_id or '')), None)
    if not drop:
        return {'ok': False, 'reason': 'Eso ya no está en el piso.'}
    if now < float(drop.get('aparece') or 0):
        return {'ok': False, 'reason': 'Todavía no aparece. Espera un momento.'}
    if str(zone or '') != str(drop.get('zone') or ''):
        return {'ok': False, 'reason': 'Eso está en otro lugar.'}
    if max(abs(float(x) - float(drop['x'])), abs(float(y) - float(drop['y']))) > CERCA:
        return {'ok': False, 'reason': 'Acércate para recogerlo.'}
    rows.remove(drop)
    before = purses.count(vault_state, name, drop['item'])
    after = purses.credit(vault_state, name, drop['item'], int(drop['qty']))
    if after != before + int(drop['qty']):
        rows.append(drop)
        return {'ok': False, 'reason': 'La mochila no acepta más. Sigue en el piso.'}
    return {
        'ok': True,
        'item': drop['item'],
        'qty': int(drop['qty']),
        'name': drop.get('name') or drop['item'],
        'reason': 'Recogiste %d %s.' % (int(drop['qty']), drop.get('name') or drop['item']),
    }
