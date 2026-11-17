# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mundos al estilo RuneScape y lugares públicos.

La arquitectura reserva los mundos 1 a 333. Al publicar sólo abren el 1 al 5.
Dos jugadores se ven si comparten mundo y lugar público. La casa es privada.
"""
import json
import os

CAP = 333
# Al entrar no hay lista: el jugador aparece en este mundo.
# El favorito se guarda aparte y no cambia esta entrada.
DEFAULT_WORLD = 3
OWNER_FAVORITE_WORLD = 5
PRIVATE = frozenset({'casa'})
# La mina, el banco y la casa son otros mapas. El valle y los parques son la misma ciudad.
INTERIOR = frozenset({'casa', 'mina-palmas', 'mina-ladera', 'casa-bancaria', 'banco-central'})
# Las dos minas se comparten. La casa, la casa bancaria y el Banco Central siguen privados.
SHARED_INTERIOR = frozenset({'mina-palmas', 'mina-ladera'})
FIXED_NAMES = {
    'valle': 'Valle de Aburrá',
    'mina-palmas': 'Mina de Las Palmas',
    'mina-ladera': 'Mina de La Ladera',
    'casa-bancaria': 'Casa bancaria',
    'banco-central': 'Banco Central',
    'casa': 'Tu casa',
}
_CATALOG = None


def catalog_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'vida.json')


def catalog():
    global _CATALOG
    if _CATALOG is None:
        with open(catalog_path(), encoding='utf-8') as handle:
            _CATALOG = json.load(handle)
    return _CATALOG


def open_ids():
    values = []
    for raw in catalog()['worlds']['open']:
        number = int(raw)
        if 1 <= number <= CAP and number not in values:
            values.append(number)
    return tuple(values)


def known(number):
    try:
        number = int(number)
    except (TypeError, ValueError):
        return False
    return 1 <= number <= CAP


def normalize(value):
    """Un mundo jugable ahora, o None si está cerrado o no existe."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number in open_ids():
        return number
    return None


def boxes(world):
    """Lugares con nombre. El Parque de Envigado del catálogo gana al área corta del mapa."""
    found = []
    seen = set()
    for raw in catalog().get('places') or []:
        box = {
            'id': str(raw['id']),
            'name': str(raw.get('name') or raw['id']),
            'x': int(raw['x']), 'y': int(raw['y']), 'w': int(raw['w']), 'h': int(raw['h']),
        }
        found.append(box)
        seen.add(box['id'])
    for area in (world or {}).get('areas') or []:
        aid = str(area.get('id') or '')
        if not aid.startswith('parque_'):
            continue
        pid = aid.replace('_', '-')
        if pid in seen:
            continue
        found.append({
            'id': pid,
            'name': str(area.get('name') or pid),
            'x': int(area['x']), 'y': int(area['y']), 'w': int(area['w']), 'h': int(area['h']),
        })
        seen.add(pid)
    return found


def place_of(x, y, zone, boxes_):
    if zone == 'casa':
        return 'casa'
    if zone == 'mine':
        return 'mina-palmas'
    if zone == 'mina2':
        return 'mina-ladera'
    if zone == 'banco':
        return 'casa-bancaria'
    if zone == 'central':
        return 'banco-central'
    try:
        ix, iy = int(float(x)), int(float(y))
    except (TypeError, ValueError):
        return 'valle'
    for box in boxes_:
        if box['x'] <= ix < box['x'] + box['w'] and box['y'] <= iy < box['y'] + box['h']:
            return box['id']
    return 'valle'


def place_name(place, boxes_):
    if place in FIXED_NAMES:
        return FIXED_NAMES[place]
    for box in boxes_:
        if box['id'] == place:
            return box['name']
    return place or 'Valle de Aburrá'


def poste():
    raw = catalog().get('poste') or {}
    return {
        'id': str(raw.get('id') or 'poste-envigado'),
        'place': str(raw.get('place') or 'parque-envigado'),
        'name': str(raw.get('name') or 'Poste de notas'),
        'x': int(raw.get('x') or 0),
        'y': int(raw.get('y') or 0),
    }


def same_world(a, b):
    return getattr(a, 'world', None) == getattr(b, 'world', None)


def same_room(a, b):
    """Misma sala de chat. La casa nunca se comparte."""
    if getattr(a, 'world', None) != getattr(b, 'world', None):
        return False
    place_a = getattr(a, 'place', '')
    place_b = getattr(b, 'place', '')
    if place_a in PRIVATE or place_b in PRIVATE:
        return False
    return bool(place_a) and place_a == place_b


def outdoors(person):
    """En la ciudad compartida. Un parque no es otra instancia."""
    zone = getattr(person, 'zone', None)
    if zone and zone != 'city':
        return False
    place = getattr(person, 'place', '')
    return bool(place) and place not in INTERIOR


def same_sight(a, b):
    """Se ven los avatares. Mismo mundo y los dos afuera, o los dos en la misma mina.

    La casa y el Banco Central no se comparten.
    """
    if not same_world(a, b):
        return False
    if outdoors(a) and outdoors(b):
        return True
    place_a = getattr(a, 'place', '')
    place_b = getattr(b, 'place', '')
    return bool(place_a) and place_a == place_b and place_a in SHARED_INTERIOR


def presence(people, boxes_=None):
    """Cuántos hay por mundo, y quién está en línea con su lugar."""
    body = counts(people)
    boxes_ = boxes_ or []
    rows = []
    for person in people:
        if not getattr(person, 'hello', False) or getattr(person, 'bot', False):
            continue
        place = getattr(person, 'place', '') or 'valle'
        nick = getattr(person, 'nick', None) or getattr(person, 'name', '') or 'Viajero'
        rows.append({
            'id': getattr(person, 'id', 0),
            'nick': str(nick)[:16],
            'world': getattr(person, 'world', DEFAULT_WORLD),
            'place': place,
            'placeName': place_name(place, boxes_),
            'zone': getattr(person, 'zone', 'city') or 'city',
            'key': getattr(person, 'identity', '') or '',
            'pace': 'casa' if getattr(person, 'zone', '') == 'casa' else (getattr(person, 'pace', '') or ''),
        })
    rows.sort(key=lambda row: (row['world'], str(row['nick']).lower(), row['id']))
    body['players'] = rows
    return body


def counts(people):
    opened = open_ids()
    per = {number: 0 for number in opened}
    total = 0
    for person in people:
        if not getattr(person, 'hello', False) or getattr(person, 'bot', False):
            continue
        total += 1
        world = getattr(person, 'world', None)
        if world in per:
            per[world] += 1
    return {
        't': 'presence',
        'total': total,
        'worlds': {str(key): value for key, value in per.items()},
        'cap': CAP,
        'open': list(opened),
    }


def public_worlds(people):
    body = counts(people)
    worlds = []
    for number in open_ids():
        worlds.append({
            'id': number,
            'name': f'Mundo {number}',
            'open': True,
            'players': body['worlds'][str(number)],
        })
    return {
        'cap': CAP,
        'open': list(open_ids()),
        'closedFrom': (max(open_ids()) + 1) if open_ids() else 1,
        'closedTo': CAP,
        'total': body['total'],
        'worlds': worlds,
    }
