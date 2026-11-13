# SPDX-License-Identifier: AGPL-3.0-or-later
"""Filas legibles del libro mayor: fecha, tipo, monto, cuenta y saldo corrido.

Lee los bloques y la mempool. También incorpora, sin duplicar, los apuntes
de Plata que aún no tienen transacción en el libro (cambio y quinto al fondo).
No modifica el estado ni acuña.
"""
from collections import Counter

LABELS = {
    'mint': ('minado', 'Minado'),
    'mina': ('minado', 'Minado'),
    'migrate': ('minado', 'Minado'),
    'exchange': ('cambio', 'Cambio plata→oro'),
    'fusion': ('fusion', 'Fusión'),
    'genesis': ('reserva', 'Reserva'),
    'pool': ('fondo', 'Al fondo'),
    'grant': ('otro', 'Misión'),
    'pay': ('otro', 'Pago'),
    'bank': ('otro', 'Banquito'),
}


def _label(kind):
    return LABELS.get(kind, ('otro', 'Movimiento'))


def _events(state):
    found = []
    for block in state.get('blocks') or []:
        ts = int(block.get('ts') or 0)
        height = int(block.get('height') or 0)
        for index, tx in enumerate(block.get('txs') or []):
            found.append((ts, height, index, tx))
    for index, tx in enumerate(state.get('mempool') or []):
        found.append((int(tx.get('ts') or 0), 10 ** 9, index, tx))
    return found


def _extra(state, seen_exchange, seen_pool):
    box = state.get('plata') if isinstance(state.get('plata'), dict) else {}
    rows = []
    for index, tx in enumerate((box or {}).get('txs') or []):
        kind = tx.get('type')
        if kind == 'exchange':
            key = (str(tx.get('name') or ''), int(tx.get('gotSmh') or 0))
            if seen_exchange[key]:
                seen_exchange[key] -= 1
                continue
            rows.append((int(tx.get('t') or 0), 10 ** 8, index, {
                'type': 'exchange',
                'from': 'fondo_cambio',
                'to': tx.get('name') or '',
                'amountSubs': int(tx.get('gotSmh') or 0),
                'note': 'Cambio de plata por oro',
            }))
        elif kind == 'pool':
            key = (str(tx.get('from') or ''), int(tx.get('amountSmh') or 0))
            if seen_pool[key]:
                seen_pool[key] -= 1
                continue
            rows.append((int(tx.get('t') or 0), 10 ** 8, index, {
                'type': 'pool',
                'from': tx.get('from') or '',
                'to': 'fondo_cambio',
                'amountSubs': int(tx.get('amountSmh') or 0),
                'note': 'Un quinto al fondo de cambio',
            }))
    return rows


def filas(state):
    """Lista cronológica. El saldo es el de la cuenta que recibe, o el de quien envía si no hay destino."""
    events = _events(state or {})
    seen_exchange = Counter()
    seen_pool = Counter()
    for _ts, _height, _index, tx in events:
        amount = int(tx.get('amountSubs') or 0)
        if tx.get('type') == 'exchange':
            seen_exchange[(str(tx.get('to') or ''), amount)] += 1
        elif tx.get('type') == 'pool':
            seen_pool[(str(tx.get('from') or ''), amount)] += 1
    events.extend(_extra(state or {}, seen_exchange, seen_pool))
    events.sort(key=lambda item: (item[0], item[1], item[2]))
    balances = {}
    plata_balances = {}
    rows = []
    for ts, _height, _index, tx in events:
        amount = int(tx.get('amountSubs') or 0)
        coin = str(tx.get('coin') or '')
        sph = int(tx.get('amountSph') or 0)
        if coin == 'SMP' and sph > 0:
            kind, _label_text = _label('bank')
            origin = str(tx.get('from') or '')
            dest = str(tx.get('to') or '')
            if origin:
                plata_balances[origin] = int(plata_balances.get(origin) or 0) - sph
            if dest:
                plata_balances[dest] = int(plata_balances.get(dest) or 0) + sph
            account = dest or origin
            shown = origin + ' → ' + dest if origin and dest else account
            rows.append({
                'ts': int(ts),
                'type': kind,
                'label': 'Banquito Plata',
                'amountSubs': 0,
                'amountSph': sph,
                'coin': 'SMP',
                'account': shown,
                'balanceSubs': 0,
                'balanceSph': int(plata_balances.get(account) or 0),
                'note': str(tx.get('note') or ''),
            })
            continue
        if amount == 0:
            continue
        kind, label = _label(tx.get('type'))
        origin = str(tx.get('from') or '')
        dest = str(tx.get('to') or '')
        if origin:
            balances[origin] = int(balances.get(origin) or 0) - amount
        if dest:
            balances[dest] = int(balances.get(dest) or 0) + amount
        account = dest or origin
        if origin and dest:
            shown = origin + ' → ' + dest
        else:
            shown = account
        rows.append({
            'ts': int(ts),
            'type': kind,
            'label': label,
            'amountSubs': amount,
            'account': shown,
            'balanceSubs': int(balances.get(account) or 0),
            'note': str(tx.get('note') or ''),
        })
    return rows
