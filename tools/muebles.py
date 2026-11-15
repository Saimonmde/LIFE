# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plano de la casa. Las variantes de cama, altar, matera y cocina se guardan en el servidor."""
import mundos

MAP_W = 14
MAP_H = 12
DOOR = (4, 9)
SPAWN = (4, 6)
WALLS = ('#f4f0e6', '#efe2c4', '#e7d39a', '#d5ddc8')
FLOORS = ('#c45c38', '#a84832', '#d4895c', '#b7a48a')

# Huellas que ya conoce la casa, más el altar. El tamaño no cambia con la variante.
LEGACY = {
    'bed': (2, 1, True),
    'table': (2, 1, True),
    'chair': (1, 1, True),
    'chest': (1, 1, True),
    'stove': (1, 1, True),
    'pots': (1, 1, True),
    'plant': (1, 1, True),
    'rug': (2, 2, False),
    'candle': (1, 1, False),
    'painting': (1, 1, False),
    'shelf': (1, 1, True),
    'altar': (1, 1, True),
}


def floor_cells():
    cells = {}
    for y in range(1, 9):
        for x in range(1, 9):
            cells[(x, y)] = 'room'
    for x, y in ((9, 3), (9, 4), (9, 5)):
        cells[(x, y)] = 'hall'
    for y in range(2, 8):
        for x in range(10, 13):
            cells[(x, y)] = 'patio'
    cells[DOOR] = 'door'
    cells[(DOOR[0], DOOR[1] - 1)] = 'threshold'
    cells[(DOOR[0] - 1, DOOR[1] - 1)] = 'threshold'
    cells[(DOOR[0] + 1, DOOR[1] - 1)] = 'threshold'
    return cells


def variants_of(kind):
    spec = (mundos.catalog().get('furniture') or {}).get(kind) or {}
    return tuple(item['id'] for item in spec.get('variants') or [])


def size_of(item):
    spec = LEGACY.get(item.get('type'))
    if not spec:
        return None
    turn = int(item.get('rot') or 0) % 4
    width, height, solid = spec
    if turn % 2:
        width, height = height, width
    return width, height, solid


def cells_of(item):
    size = size_of(item)
    if not size:
        return []
    width, height, _solid = size
    return [(item['x'] + dx, item['y'] + dy) for dy in range(height) for dx in range(width)]


def can_place(items, item, ignore=None):
    size = size_of(item)
    if not size or item['x'] < 0 or item['y'] < 0:
        return False
    width, _height, solid = size
    if width < 1:
        return False
    cells = floor_cells()
    taken = {}
    for other in items:
        if other['id'] == ignore:
            continue
        other_solid = LEGACY[other['type']][2]
        for cell in cells_of(other):
            if other_solid or cell not in taken:
                taken[cell] = 'solid' if other_solid else 'soft'
    for cell in cells_of(item):
        kind = cells.get(cell)
        if not kind or kind in ('door', 'threshold'):
            return False
        if solid and cell == SPAWN:
            return False
        prev = taken.get(cell)
        if solid and prev:
            return False
        if not solid and prev == 'soft':
            return False
    return True


def default_layout():
    return {
        'v': 1, 'wall': WALLS[0], 'floor': FLOORS[0],
        'items': [
            {'id': 'bed', 'type': 'bed', 'x': 1, 'y': 1, 'rot': 0},
            {'id': 'stove', 'type': 'stove', 'x': 7, 'y': 1, 'rot': 0},
            {'id': 'pots', 'type': 'pots', 'x': 8, 'y': 1, 'rot': 0},
            {'id': 'table', 'type': 'table', 'x': 5, 'y': 3, 'rot': 0},
            {'id': 'chair-a', 'type': 'chair', 'x': 5, 'y': 4, 'rot': 0},
            {'id': 'chair-b', 'type': 'chair', 'x': 7, 'y': 3, 'rot': 0},
            {'id': 'shelf', 'type': 'shelf', 'x': 1, 'y': 4, 'rot': 0},
            {'id': 'candle', 'type': 'candle', 'x': 6, 'y': 4, 'rot': 0},
            {'id': 'painting', 'type': 'painting', 'x': 8, 'y': 5, 'rot': 0},
            {'id': 'rug', 'type': 'rug', 'x': 5, 'y': 6, 'rot': 0},
            {'id': 'chest', 'type': 'chest', 'x': 1, 'y': 7, 'rot': 0},
            {'id': 'plant-a', 'type': 'plant', 'x': 11, 'y': 3, 'rot': 0},
            {'id': 'plant-b', 'type': 'plant', 'x': 12, 'y': 5, 'rot': 0},
        ],
    }


def sanitize(data):
    base = default_layout()
    if not isinstance(data, dict):
        return base
    wall = data.get('wall') if data.get('wall') in WALLS else base['wall']
    tint = data.get('floor') if data.get('floor') in FLOORS else base['floor']
    items = []
    seen = set()
    for raw in data.get('items') or []:
        if not isinstance(raw, dict) or len(items) >= 30:
            continue
        kind = raw.get('type')
        if kind not in LEGACY:
            continue
        ident = ''.join(ch for ch in str(raw.get('id') or kind) if ch.isalnum() or ch in '-_')[:24] or kind
        if ident in seen:
            ident = f'{kind}-{len(items)}'
        try:
            item = {
                'id': ident,
                'type': kind,
                'x': int(raw.get('x') or 0),
                'y': int(raw.get('y') or 0),
                'rot': int(raw.get('rot') or 0) % 4,
            }
        except (TypeError, ValueError):
            continue
        allowed = variants_of(kind)
        if raw.get('variant') in allowed:
            item['variant'] = raw['variant']
        if not can_place(items, item):
            continue
        seen.add(ident)
        items.append(item)
    if not items:
        return base
    return {'v': 1, 'wall': wall, 'floor': tint, 'items': items}
