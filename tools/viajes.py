# SPDX-License-Identifier: AGPL-3.0-or-later
"""Viajes desde el mapa: sólo municipios y puntos conocidos, en suelo caminable.

El norte del valle no cambia. Un destino desconocido, un muro o el agua no sirven.
"""
MUNICIPIOS = (
    'barbosa', 'girardota', 'copacabana', 'bello', 'medellin',
    'itagui', 'envigado', 'sabaneta', 'la_estrella', 'caldas',
)
POIS = ('parque_bolivar', 'las_palmas')
NOMBRES = {
    'barbosa': 'Barbosa',
    'girardota': 'Girardota',
    'copacabana': 'Copacabana',
    'bello': 'Bello',
    'medellin': 'Medellín',
    'itagui': 'Itagüí',
    'envigado': 'Envigado',
    'sabaneta': 'Sabaneta',
    'la_estrella': 'La Estrella',
    'caldas': 'Caldas',
    'parque_bolivar': 'Parque de Bolívar',
    'las_palmas': 'Las Palmas',
}
SAFE = {'cobble', 'path', 'grass', 'grass_worn', 'grass_flowers', 'bridge', 'asphalt', 'pavement'}
COOLDOWN = 2.5


class ViajeError(Exception):
    pass


def _kind(world, x, y):
    return world['tiles'][str(world['ground'][y][x])]['kind']


def walkable(world, x, y):
    if not (0 <= int(x) < world['width'] and 0 <= int(y) < world['height']):
        return False
    x, y = int(x), int(y)
    if world['collision'][y][x] != 0:
        return False
    return _kind(world, x, y) != 'water'


def safe(world, x, y):
    return walkable(world, x, y) and _kind(world, int(x), int(y)) in SAFE


def nearest_spawn(world, x, y, radius=16):
    """Casilla caminable junto al centro. Prefiere plaza, camino o hierba; nunca agua ni muro."""
    x, y = int(x), int(y)
    if safe(world, x, y):
        return x, y
    fallback = None
    for ring in range(1, radius + 1):
        for dy in range(-ring, ring + 1):
            for dx in range(-ring, ring + 1):
                if max(abs(dx), abs(dy)) != ring:
                    continue
                nx, ny = x + dx, y + dy
                if safe(world, nx, ny):
                    return nx, ny
                if fallback is None and walkable(world, nx, ny):
                    fallback = (nx, ny)
    if fallback:
        return fallback
    raise ViajeError('ahí no hay suelo caminable')


def catalog(world):
    """Diez municipios por su centro real, y los puntos con posición (Parque de Bolívar, Las Palmas)."""
    labels = {item['id']: item for item in world.get('mapLabels') or [] if item.get('id')}
    points = {item['id']: item for item in world.get('waypoints') or []}
    found = []
    for key in MUNICIPIOS + POIS:
        src = points.get(key) or labels.get(key)
        if not src or 'x' not in src or 'y' not in src:
            continue
        found.append({
            'id': key,
            'name': (labels.get(key) or {}).get('name') or NOMBRES[key],
            'x': int(src['x']),
            'y': int(src['y']),
            'kind': 'poi' if key in POIS else 'municipio',
        })
    return found


def resolve(world, dest_id):
    dest_id = str(dest_id or '').strip().lower()
    known = {item['id']: item for item in catalog(world)}
    if dest_id not in known:
        raise ViajeError('ese lugar no está en el mapa')
    spot = known[dest_id]
    x, y = nearest_spawn(world, spot['x'], spot['y'])
    if not walkable(world, x, y) or _kind(world, x, y) == 'water':
        raise ViajeError('el destino no es caminable')
    return {'id': dest_id, 'name': spot['name'], 'x': x, 'y': y, 'kind': spot['kind']}


class Gate:
    def __init__(self, cooldown=COOLDOWN):
        self.cooldown = cooldown
        self.last = {}

    def allow(self, who, now):
        previous = self.last.get(who, -1e9)
        if now - previous < self.cooldown:
            return False
        self.last[who] = now
        return True
