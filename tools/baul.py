# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mueve objetos entre la mochila y el depósito de esa misma cuenta.

El baúl de la casa, el de la Casa bancaria y el de la mina leen este
depósito. No hay una copia por lugar. Un mismo pase no se aplica dos veces.
"""
import time

import purses
import vault


def mover(state, name, op, item, qty, token='', now=None):
    name = str(name or '')
    item = str(item or '')[:32]
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        qty = 0
    now = time.time() if now is None else float(now)
    if not name or not item or qty < 1 or qty > 999 or op not in ('deposit', 'withdraw'):
        return {'ok': False, 'reason': 'Nada que mover.', 'qty': 0}
    box = vault.account(state, name)
    ops = box.setdefault('ops', [])
    token = str(token or '')[:48]
    if token and token in ops:
        return {'ok': True, 'dup': True, 'op': op, 'item': item, 'qty': 0, 'account': vault.public_account(box)}
    last = box.get('lastMove') or {}
    sig = '%s:%s:%s' % (op, item, qty)
    if last.get('sig') == sig and now - float(last.get('at') or 0) < 0.45:
        return {'ok': True, 'dup': True, 'op': op, 'item': item, 'qty': 0, 'account': vault.public_account(box)}
    if op == 'deposit':
        if not purses.debit(state, name, item, qty):
            return {'ok': False, 'reason': 'No llevas esa cantidad.', 'qty': 0}
        vault.add_item(box, item, qty)
    else:
        if not vault.take_item(box, item, qty):
            return {'ok': False, 'reason': 'El depósito no tiene esa cantidad.', 'qty': 0}
        before = purses.count(state, name, item)
        after = purses.credit(state, name, item, qty)
        if after != before + qty:
            vault.add_item(box, item, qty)
            return {'ok': False, 'reason': 'La mochila no acepta más.', 'qty': 0}
    if token:
        ops.append(token)
        del ops[:-32]
    box['lastMove'] = {'sig': sig, 'at': now}
    log = box.setdefault('log', [])
    log.append({'op': op, 'item': item, 'qty': qty, 'at': int(now)})
    del log[:-40]
    return {'ok': True, 'dup': False, 'op': op, 'item': item, 'qty': qty, 'account': vault.public_account(box)}
