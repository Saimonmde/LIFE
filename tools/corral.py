#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Corral de cada jugador, junto a su casa.

Ahí viven gallos y gallinas. La lista queda lista para otros animales
de granja. No se matan y no dan carne. La guacharaca no entra.
Sólo el dueño mete, saca o vende.
"""
from __future__ import annotations

CAP = 8
SPECIES = {
    'gallo': ('dorado', 'negro', 'blanco', 'rojo'),
    'gallina': ('blanca', 'pinta', 'negra', 'dorada'),
}
PROTECTED = ('guacharaca', 'ortalis')


class CorralError(ValueError):
    pass


def catchable(species):
    return str(species or '') in SPECIES


def sellable(species):
    return str(species or '') in SPECIES


def killable(species):
    return False


def empty():
    return {'v': 1, 'animals': [], 'caught': []}


def bounds(house, place='patio'):
    """Rectángulo del corral. El patio queda al lado de la casa, no encima de la puerta."""
    place = 'finca' if place == 'finca' else 'patio'
    if place == 'finca':
        return {'place': 'finca', 'x': 148, 'y': 209, 'w': 4, 'h': 3}
    try:
        x = int(house['x']) + 2
        y = int(house['y']) + 1
    except (TypeError, ValueError, KeyError):
        x, y = 0, 0
    return {'place': 'patio', 'x': x, 'y': y, 'w': 4, 'h': 3}


def inside(box, x, y):
    return box['x'] <= x < box['x'] + box['w'] and box['y'] <= y < box['y'] + box['h']


def _color(species, raw):
    colors = SPECIES[species]
    if raw in colors:
        return raw
    return colors[0]


def sanitize(raw):
    raw = raw if isinstance(raw, dict) else {}
    animals = []
    seen = set()
    for row in raw.get('animals') or []:
        if not isinstance(row, dict) or len(animals) >= CAP:
            continue
        species = str(row.get('species') or '')
        if species in PROTECTED or species not in SPECIES:
            continue
        ident = str(row.get('id') or '')[:24]
        if not ident or ident in seen:
            ident = '%s-%d' % (species, len(animals) + 1)
        seen.add(ident)
        place = 'finca' if row.get('place') == 'finca' else 'patio'
        animals.append({
            'id': ident,
            'species': species,
            'color': _color(species, str(row.get('color') or '')),
            'place': place,
        })
    caught = []
    for item in raw.get('caught') or []:
        ident = str(item or '')[:40]
        if ident and ident not in caught and len(caught) < 40:
            caught.append(ident)
    return {'v': 1, 'animals': animals, 'caught': caught}


def _box(user):
    data = sanitize(user.get('corral') if isinstance(user, dict) else {})
    user['corral'] = data
    return data


def _require_owner(user, actor_id):
    owner = str((user or {}).get('id') or '')
    if not owner or str(actor_id or '') != owner:
        raise CorralError('solo el dueño maneja este corral')


def catch(user, actor_id, species, world_id='', color=''):
    """Atrapa un animal suelto y lo deja en el corral. No mata."""
    _require_owner(user, actor_id)
    species = str(species or '')
    if species in PROTECTED or not catchable(species):
        raise CorralError('la guacharaca es fauna protegida y no se atrapa')
    data = _box(user)
    if len(data['animals']) >= CAP:
        raise CorralError('el corral está lleno')
    mark = str(world_id or '')[:40]
    if mark and mark in data['caught']:
        raise CorralError('ese animal ya fue atrapado')
    animal = {
        'id': '%s-%d' % (species, len(data['animals']) + 1),
        'species': species,
        'color': _color(species, color),
        'place': 'patio',
    }
    data['animals'].append(animal)
    if mark:
        data['caught'].append(mark)
    return animal


def kill(user, actor_id, animal_id=''):
    """No hay matanza: ni daño ni carne."""
    _require_owner(user, actor_id)
    raise CorralError('no se puede matar')


def take_out(user, actor_id, animal_id):
    _require_owner(user, actor_id)
    data = _box(user)
    kept = []
    found = None
    for animal in data['animals']:
        if found is None and animal['id'] == str(animal_id or ''):
            found = animal
        else:
            kept.append(animal)
    if not found:
        raise CorralError('ese animal no está en el corral')
    data['animals'] = kept
    return found


def sell_one(user, actor_id, animal_id, purse, buyer):
    """Saca un gallo del corral y lo pasa a otra cuenta. No crea monedas."""
    animal = take_out(user, actor_id, animal_id)
    if not sellable(animal['species']):
        user['corral']['animals'].append(animal)
        raise CorralError('ese animal no se vende')
    import gallos
    if animal['species'] != 'gallo':
        user['corral']['animals'].append(animal)
        raise CorralError('por ahora sólo se vende el gallo')
    owner = user.get('wallet_name') or user.get('name') or user.get('id')
    import purses
    before = purses.count(purse, owner, 'gallo')
    after = purses.credit(purse, owner, 'gallo', 1)
    if after != before + 1:
        user['corral']['animals'].append(animal)
        raise CorralError('no se pudo apartar el gallo para la venta')
    try:
        gallos.sell(purse, owner, buyer, 'gallo', 1)
    except gallos.GallosError as exc:
        purses.debit(purse, owner, 'gallo', 1)
        user['corral']['animals'].append(animal)
        raise CorralError(str(exc)) from exc
    return animal


def step(animal, box, dt=0.2):
    """Camina dentro del corral y no cruza la cerca."""
    animal = dict(animal)
    fx = float(animal.get('fx', box['x'] + 0.5))
    fy = float(animal.get('fy', box['y'] + 0.5))
    goal_x = float(animal.get('goalX', box['x'] + box['w'] / 2))
    goal_y = float(animal.get('goalY', box['y'] + box['h'] / 2))
    dx, dy = goal_x - fx, goal_y - fy
    dist = (dx * dx + dy * dy) ** 0.5
    if dist > 0.05:
        step_len = min(dist, 0.6 * float(dt or 0))
        fx += dx / dist * step_len
        fy += dy / dist * step_len
    margin = 0.15
    lo_x, hi_x = box['x'] + margin, box['x'] + box['w'] - margin
    lo_y, hi_y = box['y'] + margin, box['y'] + box['h'] - margin
    animal['fx'] = min(hi_x, max(lo_x, fx))
    animal['fy'] = min(hi_y, max(lo_y, fy))
    return animal
