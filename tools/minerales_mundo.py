# SPDX-License-Identifier: AGPL-3.0-or-later
"""Minerales de cada mundo y arena de oro en el Río Medellín.

El oro sigue saliendo sólo del río, con el respawn de 30 s que ya tenía
la batea y el tope de 50 SMC al día. Cada mundo tiene su propio reloj de
esa arena: lavar en el Mundo 1 no apaga el río del Mundo 2.

Las rocas nuevas no acuñan otra moneda. Caen en la mochila como el resto
de los minerales. El cobre sigue en 150 SMC al día y el libro no cambia.
"""
import json
import os

GOLD_MS = 30000
ROCK_MS = 18000


def catalog_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'minerales-mundo.json')


def catalog():
    with open(catalog_path(), encoding='utf-8') as handle:
        return json.load(handle)


def clock_key(world, node_id):
    """Una arena, un mundo. El mismo id en otro mundo es otra veta."""
    try:
        number = int(world)
    except (TypeError, ValueError):
        number = 0
    return '%s:%s' % (number, str(node_id or '')[:40])


def resting(ready, world, node_id, now):
    return float(now) < float((ready or {}).get(clock_key(world, node_id), 0) or 0)


def mark(ready, world, node_id, until):
    ready[clock_key(world, node_id)] = float(until)


def rivers_rest(ready, world, nodes, now):
    """Sin mundo no se declara el río en descanso: el aviso es del jugador."""
    if world is None or not nodes:
        return False
    return all(resting(ready, world, node.get('id'), now) for node in nodes)


def _gold(spec):
    return {
        'id': spec['id'],
        'type': 'nodo_oro_fluvial',
        'waterBody': spec['water'],
        'x': int(spec['x']),
        'y': int(spec['y']),
        'skill': 'mining',
        'method': 'fluvial',
        'tool': 'batea',
        'solid': True,
        'states': ['active', 'depleted'],
        'initialState': 'active',
        'sprites': {'active': 'spot_oro', 'depleted': 'spot_oro_lavado'},
        'successChance': 0.75,
        'yield': {'item': 'pepita_oro', 'min': 1, 'max': 1},
        'xp': 25,
        'respawnMs': GOLD_MS,
    }


def _rock(world_id, spec):
    return {
        'id': spec['id'],
        'type': 'mineral_rock',
        'mineral': spec['item'],
        'nombre': spec['name'],
        'mundo': int(world_id),
        'x': int(spec['x']),
        'y': int(spec['y']),
        'skill': 'mining',
        'method': 'terrestre',
        'tool': 'pico',
        'solid': True,
        'states': ['active', 'depleted'],
        'initialState': 'active',
        'sprites': {'active': 'rock_piedra', 'depleted': 'rock_depleted'},
        'yield': {'item': spec['item'], 'min': 1, 'max': 1},
        'xp': 12,
        'respawnMs': ROCK_MS,
    }


def gold_nodes():
    return [_gold(spec) for spec in catalog()['gold']]


def rock_nodes():
    found = []
    for row in catalog()['worlds']:
        for spec in row['rocks']:
            found.append(_rock(row['id'], spec))
    return found


def rock_by_id():
    return {node['id']: node for node in rock_nodes()}


def attach(world):
    """Suma las vetas que faltan. No mueve las que ya estaban en el río."""
    nodes = world.setdefault('nodes', [])
    have = {node.get('id') for node in nodes}
    for node in gold_nodes() + rock_nodes():
        if node['id'] in have:
            continue
        nodes.append(node)
        have.add(node['id'])
    return [node for node in nodes if str(node.get('id') or '').startswith('oro_medellin')]


RIVER_WATERS = ('rio_claro', 'rio_medellin')


def gold_spot(nodes, spot, world_n):
    """La pepita sólo sale de una arena de oro del río, mundos 1 a 5."""
    try:
        number = int(world_n)
    except (TypeError, ValueError):
        number = 0
    if number < 1 or number > 5:
        return None, 'El oro del Río Medellín está en los mundos 1 a 5.'
    want = str(spot or '')[:40]
    node = next((row for row in nodes or [] if isinstance(row, dict) and row.get('id') == want), None)
    if not node or node.get('type') != 'nodo_oro_fluvial':
        return None, 'El oro sólo sale del río, con la batea.'
    if str(node.get('waterBody') or '') not in RIVER_WATERS:
        return None, 'El oro sólo sale del río, con la batea.'
    return node, ''


def reject(world, spot, item):
    """Vacío si se puede picar. Si no, el aviso en español."""
    rock = rock_by_id().get(str(spot or '')[:40])
    if not rock:
        return ''
    try:
        here = int(world)
    except (TypeError, ValueError):
        here = 0
    if here != int(rock['mundo']):
        return 'Ese mineral es del Mundo %s.' % rock['mundo']
    want = ((rock.get('yield') or {}).get('item')) or ''
    if item and want and str(item) != want:
        return 'Esa veta no da ese mineral.'
    return ''


def names_for(world_id):
    for row in catalog()['worlds']:
        if int(row['id']) == int(world_id):
            return [spec['name'] for spec in row['rocks']]
    return []
