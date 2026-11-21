# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cada veta tiene su propio reloj y la pica una sola persona a la vez.

Las posiciones, las cantidades y los tiempos son los que ya usa el juego.
Aquí no se inventa una veta ni se cambia un respawn. El estado vive en
memoria del proceso: no toca el archivo de la economía.
"""
HOLD = 0.8

# La misma grilla que play/galerias.js. Oro 32 s, plata y cobre 18 s.
import galerias as _galerias
MINE = _galerias.mine_clocks('palmas')


def empty():
    return {'ready': {}, 'hold': {}, 'who': {}, 'told': {}}


def _key(world, node_id):
    return '%s:%s' % (int(world), str(node_id or '')[:40])


def millis(world_nodes, node_id):
    """Milisegundos de respawn ya definidos. None si esa veta no se controla aquí."""
    node_id = str(node_id or '')
    if node_id in MINE:
        return MINE[node_id][2]
    if node_id.startswith('ladera_'):
        import mina_ladera as _ladera
        row = _ladera.VEINS.get(node_id)
        if row:
            return row[2]
    for node in world_nodes or []:
        if not isinstance(node, dict) or node.get('id') != node_id:
            continue
        if node.get('type') not in ('mineral_rock', 'nodo_oro_fluvial'):
            return None
        try:
            return int(node.get('respawnMs') or 0)
        except (TypeError, ValueError):
            return None
    return None


def claim(state, world, node_id, player, now, world_nodes=()):
    ms = millis(world_nodes, node_id)
    if ms is None:
        return {'ok': True, 'tracked': False}
    if ms <= 0:
        return {'ok': True, 'tracked': False}
    key = _key(world, node_id)
    ready = float(state['ready'].get(key) or 0)
    if ready > now:
        return {'ok': False, 'reason': 'agotada', 'until': ready}
    owner = state['who'].get(player)
    if owner and float(owner.get('until') or 0) > now and owner.get('key') != key:
        return {'ok': False, 'reason': 'una'}
    held = state['hold'].get(key)
    if held and float(held.get('until') or 0) > now and held.get('player') != player:
        return {'ok': False, 'reason': 'ocupado', 'until': float(held.get('until') or 0)}
    until = now + HOLD
    state['hold'][key] = {'player': player, 'until': until}
    state['who'][player] = {'key': key, 'until': until}
    return {'ok': True, 'tracked': True, 'key': key}


def finish(state, world, node_id, player, now, world_nodes=()):
    """Cierra esa veta sola. No toca el reloj de ninguna otra."""
    ms = millis(world_nodes, node_id)
    if not ms:
        return None
    key = _key(world, node_id)
    held = state['hold'].get(key)
    if held and held.get('player') != player:
        return None
    state['hold'].pop(key, None)
    until = now + (ms / 1000.0)
    state['ready'][key] = until
    state['told'].pop(key, None)
    return until


def release_player(state, player, now=None):
    row = state['who'].pop(player, None)
    if not row:
        return None
    key = row.get('key')
    held = state['hold'].get(key)
    if held and held.get('player') == player:
        state['hold'].pop(key, None)
    return key


def cooling(state, world, now):
    prefix = '%s:' % int(world)
    rows = []
    for key, until in state['ready'].items():
        if not str(key).startswith(prefix):
            continue
        if float(until) <= now:
            continue
        rows.append({'id': str(key).split(':', 1)[1], 'until': float(until)})
    rows.sort(key=lambda row: row['id'])
    return rows


def revive(state, now):
    """Las que ya cumplieron su propio tiempo, una vez cada una."""
    back = []
    for key, until in list(state['ready'].items()):
        if float(until) > now or state['told'].get(key):
            continue
        state['told'][key] = True
        world, _, node_id = str(key).partition(':')
        try:
            world = int(world)
        except ValueError:
            continue
        back.append({'world': world, 'id': node_id})
    return back
