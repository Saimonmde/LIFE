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
    'mina': 'Mina de Las Palmas',
    'cantera': 'Cantera',
    'rio_claro': 'Río Claro',
    'finca': 'Cafetal',
    'cafetal': 'Cafetal',
    'madera': 'Pinos',
    'banco': 'Banco Envigado',
    'skate': 'Skate',
    'parque_envigado': 'Parque de Envigado',
    'casa': 'Tu casa',
}
# Sitios con recurso. El cliente los dibuja; el servidor elige la casilla.
RECURSOS = {
    'mina': 'plata, cobre (pico)',
    'cantera': 'plata, cobre (pico)',
    'rio_claro': 'oro (río, batea)',
    'finca': 'café, cacao',
    'cafetal': 'café, cacao',
    'madera': 'madera',
    'banco': 'casa bancaria',
    'skate': 'skate',
    'parque_envigado': 'parque',
    'casa': 'hogar',
}
# La pista de skate la sella el cliente. No se aterriza encima.
SKATE_BLOCK = {(84, 273), (85, 273), (84, 274), (85, 274), (86, 273), (86, 274)}
BANK_OUT = (113, 257)
HOME_STAND = (94, 267)
RESTRICTED = {'central', 'banco_central'}
SAFE = {'cobble', 'path', 'grass', 'grass_worn', 'grass_flowers', 'bridge', 'asphalt', 'pavement'}
COOLDOWN = 2.5
# La misma marcha que play/caballo.js: 4.2 casillas/s a pie, × MOUNT_SPEED a caballo.
WALK_SPEED = 4.2
MOUNT_SPEED = 2.2
HORSE_SPEED = WALK_SPEED * MOUNT_SPEED
STEP_SLACK = 1.35
STEP_BURST = 1.25
# Puertas de salida. Coinciden con play/casa.js (PARK_STAND) y play/banco.js (OUTSIDE).
PORTALS = {
    'casa': (94, 267),
    'banco': (113, 257),
}


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


def beside(world, x, y, radius=3, blocked=()):
    """Casilla caminable junto al recurso. Nunca agua, muro ni una casilla sellada."""
    blocked = {(int(a), int(b)) for a, b in blocked}
    x, y = int(x), int(y)
    fallback = None
    for ring in range(0, radius + 1):
        for dy in range(-ring, ring + 1):
            for dx in range(-ring, ring + 1):
                if max(abs(dx), abs(dy)) != ring:
                    continue
                nx, ny = x + dx, y + dy
                if (nx, ny) in blocked:
                    continue
                if safe(world, nx, ny):
                    return nx, ny
                if fallback is None and walkable(world, nx, ny):
                    fallback = (nx, ny)
    if fallback:
        return fallback
    raise ViajeError('ahí no hay suelo caminable')


def _nodes(world, kind):
    return [node for node in world.get('nodes') or [] if node.get('type') == kind]


def _pack(dest_id, x, y):
    return {
        'id': dest_id,
        'name': NOMBRES[dest_id],
        'x': int(x),
        'y': int(y),
        'kind': 'recurso',
        'recurso': RECURSOS[dest_id],
    }


def _open(world, dest):
    x, y = dest['x'], dest['y']
    if not walkable(world, x, y) or _kind(world, x, y) == 'water':
        raise ViajeError('el destino no es caminable')
    return dest


def gold_stand(world):
    """Al lado de una veta de oro que ya está en el Río Claro. No crea oro en otro sitio."""
    river = {
        (int(a), int(b))
        for a, b in (((world.get('waterBodies') or {}).get('rio_claro') or {}).get('tiles') or [])
    }
    nodes = [node for node in _nodes(world, 'nodo_oro_fluvial') if (int(node['x']), int(node['y'])) in river]
    if not nodes:
        raise ViajeError('el oro sólo está en el río')
    node = nodes[0]
    blocked = {(int(item['x']), int(item['y'])) for item in nodes}
    x, y = beside(world, node['x'], node['y'], 3, blocked)
    return _pack('rio_claro', x, y)


def quarry_stand(world):
    nodes = [node for node in _nodes(world, 'mineral_rock') if node.get('mineral') in ('cobre', 'plata')]
    if not nodes:
        raise ViajeError('no hay cantera')
    blocked = {(int(node['x']), int(node['y'])) for node in nodes}
    x, y = beside(world, nodes[0]['x'], nodes[0]['y'], 2, blocked)
    return _pack('cantera', x, y)


def wood_stand(world):
    nodes = _nodes(world, 'wood_tree')
    if not nodes:
        raise ViajeError('no hay madera')
    blocked = {(int(node['x']), int(node['y'])) for node in nodes}
    x, y = beside(world, nodes[0]['x'], nodes[0]['y'], 2, blocked)
    return _pack('madera', x, y)


def finca_stand(world, dest_id='finca'):
    palmas = next((item for item in world.get('waypoints') or [] if item.get('id') == 'las_palmas'), None)
    if not palmas:
        raise ViajeError('no hay cafetal')
    x, y = beside(world, palmas['x'], palmas['y'], 4)
    made = _pack(dest_id, x, y)
    if dest_id == 'cafetal':
        made['recurso'] = RECURSOS['cafetal']
    return made


def skate_stand(world):
    x, y = beside(world, 84, 273, 2, SKATE_BLOCK)
    return _pack('skate', x, y)


def banco_stand(world):
    x, y = beside(world, BANK_OUT[0], BANK_OUT[1], 1)
    return _pack('banco', x, y)


def parque_stand(world):
    town = next((item for item in catalog(world) if item['id'] == 'envigado'), None)
    if not town:
        x, y = beside(world, HOME_STAND[0], HOME_STAND[1], 2)
    else:
        x, y = nearest_spawn(world, town['x'], town['y'])
    return _pack('parque_envigado', x, y)


def casa_stand(world):
    """Puerta de la casa en el parque. Salir de casa sigue en esa misma llegada."""
    x, y = beside(world, HOME_STAND[0], HOME_STAND[1], 1)
    return _pack('casa', x, y)


def named(world, dest_id):
    """Un destino con nombre, o None si no es de esta lista."""
    if dest_id == 'mina':
        spot = dict(mine_stand(world))
        spot['kind'] = 'recurso'
        spot['recurso'] = RECURSOS['mina']
        return spot
    if dest_id == 'cantera':
        return quarry_stand(world)
    if dest_id == 'rio_claro':
        return gold_stand(world)
    if dest_id == 'finca':
        return finca_stand(world, 'finca')
    if dest_id == 'cafetal':
        return finca_stand(world, 'cafetal')
    if dest_id == 'madera':
        return wood_stand(world)
    if dest_id == 'banco':
        return banco_stand(world)
    if dest_id == 'skate':
        return skate_stand(world)
    if dest_id == 'parque_envigado':
        return parque_stand(world)
    if dest_id == 'casa':
        return casa_stand(world)
    return None


def resolve(world, dest_id):
    dest_id = str(dest_id or '').strip().lower()
    if dest_id in RESTRICTED:
        raise ViajeError('ese sitio está restringido')
    extra = named(world, dest_id)
    if extra:
        return _open(world, extra)
    known = {item['id']: item for item in catalog(world)}
    if dest_id not in known:
        raise ViajeError('ese lugar no está en el mapa')
    spot = known[dest_id]
    x, y = nearest_spawn(world, spot['x'], spot['y'])
    made = {'id': dest_id, 'name': spot['name'], 'x': x, 'y': y, 'kind': spot['kind'], 'recurso': ''}
    return _open(world, made)


def mine_stand(world):
    """Casilla caminable frente a la entrada de la mina, junto a Las Palmas."""
    palmas = next((item for item in world.get('waypoints') or [] if item.get('id') == 'las_palmas'), None)
    if not palmas:
        raise ViajeError('no hay mina')
    px, py = int(palmas['x']), int(palmas['y'])
    for ring in range(2, 12):
        for dy in range(-ring, ring + 1):
            for dx in range(-ring, ring + 1):
                if max(abs(dx), abs(dy)) != ring:
                    continue
                x, y = px + dx, py + dy
                if walkable(world, x, y) and walkable(world, x, y + 1):
                    return {'id': 'mina', 'name': 'Mina de Las Palmas', 'x': x, 'y': y + 1}
    raise ViajeError('no hay acceso a la mina')


def step_allowed(step, dt):
    """Un paso de a pie o a caballo cabe. Un salto de decenas de casillas, no."""
    step = abs(float(step or 0))
    if step <= 0:
        return True
    dt = max(0.05, min(2.0, float(dt)))
    return step <= HORSE_SPEED * STEP_SLACK * dt + STEP_BURST


def _house_doors():
    """Cada municipio tiene su puerta. Salir de casa no es sólo la de Envigado."""
    try:
        import hogar
    except Exception:
        return []
    doors = []
    for item in hogar.CASAS.values():
        try:
            doors.append((float(item['x']), float(item['y'])))
        except (KeyError, TypeError, ValueError):
            continue
    return doors


def portal_arrival(zone, x, y, back=None):
    """La salida vale si caes en la puerta, en tu casa del municipio, o donde entraste."""
    try:
        fx, fy = float(x), float(y)
    except (TypeError, ValueError):
        return False
    points = []
    if zone == 'mine':
        if not back or back[0] is None or back[1] is None:
            return True
        points.append((float(back[0]), float(back[1])))
    else:
        if zone in PORTALS:
            points.append((float(PORTALS[zone][0]), float(PORTALS[zone][1])))
        if zone == 'casa':
            points.extend(_house_doors())
        if back and back[0] is not None and back[1] is not None:
            try:
                points.append((float(back[0]), float(back[1])))
            except (TypeError, ValueError):
                pass
        if not points:
            return True
    return any(max(abs(fx - ax), abs(fy - ay)) <= 3 for ax, ay in points)


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
