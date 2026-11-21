# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lee las galerías que dibuja el cliente. Una sola lista de vetas."""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PATH = os.path.join(ROOT, 'play', 'galerias.js')
_DATA = None


def data():
    global _DATA
    if _DATA is None:
        text = open(PATH, encoding='utf-8').read()
        start = text.index('root.GALERIAS_DATA =') + len('root.GALERIAS_DATA =')
        end = text.index('/* END DATA */', start)
        raw = text[start:end].strip().rstrip(';').strip()
        _DATA = json.loads(raw)
    return _DATA


def plan(kind):
    return data()[kind]


def veins(kind):
    """id -> (x, y, respawn ms, metal). El orden conserva los índices viejos."""
    found = {}
    prefix = 'ladera' if kind == 'ladera' else 'mina'
    layout = plan(kind)['veins']
    for metal in ('cobre', 'plata', 'oro'):
        ms = 32000 if metal == 'oro' else 18000
        for index, pair in enumerate(layout[metal]):
            found['%s_%s_%d' % (prefix, metal, index)] = (int(pair[0]), int(pair[1]), ms, metal)
    return found


def mine_clocks(kind):
    """La forma que ya usa el reloj de cada veta: id -> (x, y, ms)."""
    return {key: (row[0], row[1], row[2]) for key, row in veins(kind).items()}


def carve(kind):
    spec = plan(kind)
    width = int(spec['width'])
    height = int(spec['height'])
    grid = [[1 for _ in range(width)] for _ in range(height)]
    for rect in spec['open']:
        x0 = max(2, min(int(rect[0]), int(rect[2])))
        y0 = max(2, min(int(rect[1]), int(rect[3])))
        x1 = min(width - 3, max(int(rect[0]), int(rect[2])))
        y1 = min(height - 3, max(int(rect[1]), int(rect[3])))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                grid[y][x] = 0
    return grid


def reachable(kind):
    """Desde el nacimiento se llega a un lado de cada veta, del horno y del baúl."""
    spec = plan(kind)
    grid = carve(kind)
    blocked = set()
    for row in spec['fixtures']:
        if row['type'] != 'mine_sign':
            blocked.add((int(row['x']), int(row['y'])))
    for spots in spec['veins'].values():
        for pair in spots:
            blocked.add((int(pair[0]), int(pair[1])))
    for pair in spec['rocks']:
        blocked.add((int(pair[0]), int(pair[1])))
    width = int(spec['width'])
    height = int(spec['height'])
    start = (int(spec['spawn'][0]), int(spec['spawn'][1]))
    seen = {start}
    queue = [start]
    while queue:
        x, y = queue.pop(0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if grid[ny][nx] != 0 or (nx, ny) in blocked or (nx, ny) in seen:
                continue
            seen.add((nx, ny))
            queue.append((nx, ny))
    missing = []
    for key, (x, y, _ms, _metal) in veins(kind).items():
        if not any((x + dx, y + dy) in seen for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            missing.append(key)
    return seen, missing
