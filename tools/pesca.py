# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pesca con red. El servidor elige el pez, el cupo y el descanso.

Trucha y bocachico salen del río. Mojarra sale del estanque. La red
vive en la barra del jugador; la pieza pescada entra en la mochila.
"""
from __future__ import annotations

import mochila

WATERS = ('rio_claro', 'estanque', 'rio_medellin')
RIVER = ('rio_claro', 'rio_medellin')


def _node(world, spot_id):
    want = str(spot_id or '')[:40]
    if not want:
        return None
    for node in (world or {}).get('nodes') or []:
        if isinstance(node, dict) and node.get('id') == want and node.get('type') == 'fishing_spot':
            return node
    return None


def _roll(table, rng):
    weights = []
    for row in table or []:
        if not isinstance(row, dict):
            continue
        item = str(row.get('item') or '')
        try:
            weight = int(row.get('weight') or 0)
        except (TypeError, ValueError):
            weight = 0
        if item and weight > 0:
            weights.append((item, weight))
    if not weights:
        return ''
    total = sum(weight for _item, weight in weights)
    pick = rng.randrange(total)
    for item, weight in weights:
        if pick < weight:
            return item
        pick -= weight
    return weights[-1][0]


def cast(world, bag, name, x, y, spot_id, now, ready, world_n=1, rng=None):
    """Un lance. Si no cabe o el agua descansa, la mochila no cambia."""
    import random

    node = _node(world, spot_id)
    if not node:
        return {'ok': False, 'reason': 'Ahí no hay un puesto de pesca.'}
    water = str(node.get('waterBody') or '')
    if water not in WATERS:
        return {'ok': False, 'reason': 'La red se usa en el río o en el estanque.'}
    try:
        dist = max(abs(float(x) - float(node['x'])), abs(float(y) - float(node['y'])))
    except (TypeError, ValueError):
        dist = 99
    if dist > 2.5:
        return {'ok': False, 'reason': 'Acércate al agua para lanzar la red.'}
    if bag is None or not name:
        return {'ok': False, 'reason': 'Entra con tu cuenta para guardar el pescado.'}
    try:
        world_n = int(world_n)
    except (TypeError, ValueError):
        world_n = 1
    key = '%d:%s:%s' % (world_n, str(name)[:40], node['id'])
    until = float((ready or {}).get(key) or 0)
    now = float(now)
    if now < until:
        return {'ok': False, 'reason': 'El agua está tranquila. Los peces vuelven en un momento.', 'until': until}
    table = ((node.get('yield') or {}).get('table')) or []
    rng = rng or random.Random()
    item = _roll(table, rng)
    if water in RIVER and item == 'mojarra':
        item = 'trucha'
    if water == 'estanque' and item in ('trucha', 'bocachico'):
        item = 'mojarra'
    if item not in ('trucha', 'bocachico', 'mojarra'):
        return {'ok': False, 'reason': 'Ese puesto no tiene peces.'}
    try:
        qty = int((node.get('yield') or {}).get('qty') or 1)
    except (TypeError, ValueError):
        qty = 1
    qty = max(1, min(4, qty))
    snapshot = {}
    for raw_item, raw_qty in (bag or {}).items():
        try:
            have = int(raw_qty or 0)
        except (TypeError, ValueError):
            continue
        if have > 0:
            snapshot[str(raw_item)] = have
    if not mochila.fits(snapshot, item, qty):
        return {'ok': False, 'reason': mochila.FULL, 'full': True}
    bag[item] = int(bag.get(item) or 0) + qty
    try:
        wait = int(node.get('respawnMs') or 15000) / 1000.0
    except (TypeError, ValueError):
        wait = 15.0
    if wait < 5:
        wait = 5.0
    if ready is not None:
        ready[key] = now + wait
    return {
        'ok': True,
        'item': item,
        'qty': qty,
        'spot': node['id'],
        'water': water,
        'until': now + wait,
        'reason': 'La red sacó %s.' % item,
    }
