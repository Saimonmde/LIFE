# SPDX-License-Identifier: AGPL-3.0-or-later
"""Etiquetas del mapa del valle: diez municipios, sin cajas encimadas.

Norte es -y. La medida de cada caja es la misma que usa play/game.js.
"""
CHAR_W = 7.4
PAD_X = 6
BOX_H = {'municipio': 22, 'poi': 18}
SIZE = 800
PAD = 42

# De norte a sur, como el Área Metropolitana del Valle de Aburrá.
MUNICIPIOS = (
    'barbosa', 'girardota', 'copacabana', 'bello', 'medellin',
    'itagui', 'envigado', 'sabaneta', 'la_estrella', 'caldas',
)
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
}


def project(width, height):
    scale = (SIZE - PAD * 2) / max(width, height)
    left = (SIZE - width * scale) / 2
    top = (SIZE - height * scale) / 2
    return scale, left, top


def anchor(scale, left, top, x, y):
    return left + (x + 0.5) * scale, top + (y + 0.5) * scale


def box_of(text, ax, ay, dx, dy, kind):
    width = len(text) * CHAR_W + PAD_X * 2
    height = BOX_H[kind]
    return (ax + dx - width / 2, ay + dy, width, height)


def hits(a, b, gap=3):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw + gap <= bx or bx + bw + gap <= ax or ay + ah + gap <= by or by + bh + gap <= ay)


def _shifts():
    found = []
    for dy in range(8, 80, 4):
        found.append((0, dy))
    for radius in range(4, 168, 4):
        for dy in range(0, radius + 1, 4):
            for dx in range(-radius, radius + 1, 4):
                found.append((dx, dy))
                if dy:
                    found.append((dx, -dy))
    seen = set()
    ordered = []
    for item in found:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


SHIFTS = _shifts()


def place(labels, width, height, obstacles=()):
    """Devuelve las etiquetas con dx, dy en píxeles del mapa de 800 px."""
    scale, left, top = project(width, height)
    placed = []
    out = []
    for label in labels:
        ax, ay = anchor(scale, left, top, label['x'], label['y'])
        kind = label.get('kind') or 'municipio'
        text = label['name']
        chosen = None
        for dx, dy in SHIFTS:
            rect = box_of(text, ax, ay, dx, dy, kind)
            if rect[0] < 8 or rect[1] < 28 or rect[0] + rect[2] > SIZE - 8 or rect[1] + rect[3] > SIZE - 28:
                continue
            if any(hits(rect, item['rect']) for item in placed):
                continue
            if any(hits(rect, obstacle) for obstacle in obstacles):
                continue
            if kind == 'municipio':
                center = rect[1] + rect[3] / 2
                if any(item['kind'] == 'municipio' and item['ay'] < ay and item['center'] >= center for item in placed):
                    continue
                if any(item['kind'] == 'municipio' and item['ay'] > ay and item['center'] <= center for item in placed):
                    continue
            chosen = (dx, dy, rect)
            break
        if chosen is None:
            raise RuntimeError('sin sitio para ' + text)
        placed.append({'rect': chosen[2], 'ay': ay, 'center': chosen[2][1] + chosen[2][3] / 2, 'kind': kind})
        out.append({**label, 'kind': kind, 'dx': chosen[0], 'dy': chosen[1]})
    return out


def stamp_obstacle(scale, left, top):
    """El bloque brillante del Parque de Envigado. Las etiquetas no se esconden debajo."""
    x0, y0, x1, y1 = 32, 245, 125, 291
    px = left + x0 * scale
    py = top + y0 * scale
    return (px, py, (x1 - x0) * scale, (y1 - y0) * scale)


def labels_for(world):
    by_id = {item['id']: item for item in world['waypoints']}
    labels = []
    for key in MUNICIPIOS:
        spot = by_id[key]
        x, y = spot['x'], spot['y']
        if key == 'copacabana':
            y = min(y, by_id['bello']['y'] - 10)
        if key == 'envigado':
            x, y = 138, 276
        labels.append({'id': key, 'name': NOMBRES[key], 'x': x, 'y': y, 'kind': 'municipio'})
    med = by_id['medellin']
    labels.append({
        'id': 'parque_bolivar', 'name': 'Parque de Bolívar', 'kind': 'poi',
        'x': med['x'] + 6, 'y': med['y'] + 10,
    })
    palmas = by_id['las_palmas']
    labels.append({'id': 'las_palmas', 'name': 'Las Palmas', 'kind': 'poi', 'x': palmas['x'], 'y': palmas['y']})
    labels.append({'id': 'mina', 'name': 'Mina', 'kind': 'poi', 'x': palmas['x'] - 2, 'y': palmas['y'] - 2})
    labels.append({'id': 'casa', 'name': 'Casa', 'kind': 'poi', 'x': 93, 'y': 267})
    scale, left, top = project(world['width'], world['height'])
    return place(labels, world['width'], world['height'], (stamp_obstacle(scale, left, top),))
