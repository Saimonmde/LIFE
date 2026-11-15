# SPDX-License-Identifier: AGPL-3.0-or-later
"""Movimientos de la cuenta y el serial de cada acuñación.

Cada moneda nueva recibe un serial que no se repite: SMC-00000001,
SMP-00000001 o SCH-00000001. El número sigue aunque la lista se acorte.
"""
import time

PREFIX = {'simoncoin': 'SMC', 'simonplata': 'SMP', 'simonchis': 'SCH'}
KEEP = 500


def _box(state):
    raw = state.get('historial')
    if not isinstance(raw, dict) or not isinstance(raw.get('rows'), list):
        raw = {'next': {}, 'rows': []}
        state['historial'] = raw
    raw.setdefault('next', {})
    return raw


def anotar(state, coin, base, name, note, now=None):
    coin = str(coin or '')
    prefix = PREFIX.get(coin)
    if not prefix:
        raise ValueError('moneda')
    base = int(base or 0)
    if base <= 0:
        raise ValueError('monto')
    box = _box(state)
    n = int(box['next'].get(coin) or 0) + 1
    box['next'][coin] = n
    row = {
        'serial': f'{prefix}-{n:08d}',
        'coin': coin,
        'base': base,
        'name': str(name or ''),
        'note': str(note or '')[:180],
        't': int(now if now is not None else time.time()),
    }
    box['rows'].append(row)
    del box['rows'][:-KEEP]
    return row


def para(state, name, limit=40):
    box = state.get('historial') if isinstance(state.get('historial'), dict) else {}
    rows = [r for r in (box.get('rows') or []) if r.get('name') == name]
    return list(reversed(rows[-int(limit):]))
