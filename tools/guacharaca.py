#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Guacharaca (Ortalis): hábitat, grupos y la ventana del canto.

Vive sólo en el monte, el borde del bosque, los árboles y las quebradas.
No entra a casas, potreros, corrales, la mina ni la finca.
Canta de 4:30 a 6:00, hora de Bogotá, y calla en punto a las 6:00.
"""
from __future__ import annotations

import json
import math
import os
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLD = os.path.join(ROOT, 'data', 'el-jardin.json')
HOMES = os.path.join(ROOT, 'data', 'hogares.json')
OUT_JS = os.path.join(ROOT, 'data', 'guacharacas.js')

DAWN_START = 4 * 60 + 30
DAWN_END = 6 * 60
FLOCKS = 10
FLOCK_GAP = 26
REACH = {'quebrada': 3, 'arbol': 3, 'borde': 3, 'monte': 8}
NATURAL = ('arbol', 'borde', 'quebrada', 'monte')
# La misma frase que arma el Web Audio del juego.
SONG = {
    'syllables': [
        {'name': 'gua', 'at': 0.00, 'dur': 0.16, 'freq': 340, 'slide': 190},
        {'name': 'cha', 'at': 0.22, 'dur': 0.11, 'freq': 460, 'slide': 280},
        {'name': 'ra', 'at': 0.38, 'dur': 0.11, 'freq': 510, 'slide': 300},
        {'name': 'ca', 'at': 0.54, 'dur': 0.15, 'freq': 420, 'slide': 220},
    ],
    'phrase': 0.78,
    'gap': 0.08,
    'repeats': 3,
    'duetDelay': 0.36,
    'duetRepeats': 3,
    'duetPitch': 1.14,
    'thirdAt': 1.20,
    'thirdRepeats': 2,
    'thirdPitch': 0.86,
}


def sings(hour, minute):
    """Verdadero sólo entre las 4:30 inclusive y las 6:00 exclusive."""
    try:
        hour = int(hour)
        minute = int(minute)
    except (TypeError, ValueError):
        return False
    if hour < 0 or minute < 0 or minute > 59:
        return False
    clock = hour * 60 + minute
    return DAWN_START <= clock < DAWN_END


def song_seconds():
    """Cuánto dura el coro completo, con el dúo y la tercera voz."""
    lead = SONG['repeats'] * SONG['phrase'] + (SONG['repeats'] - 1) * SONG['gap']
    duet = SONG['duetDelay'] + SONG['duetRepeats'] * SONG['phrase'] + (SONG['duetRepeats'] - 1) * SONG['gap']
    third = SONG['thirdAt'] + SONG['thirdRepeats'] * SONG['phrase'] + max(0, SONG['thirdRepeats'] - 1) * SONG['gap']
    return round(max(lead, duet, third), 2)


def _rect(x, y, w, h, kind):
    return {'x': int(x), 'y': int(y), 'w': int(max(1, w)), 'h': int(max(1, h)), 'kind': kind}


def forbidden(world, homes):
    """Rectángulos donde la guacharaca no puede posarse ni caminar."""
    zones = []
    for house in (homes or {}).get('casas') or []:
        zones.append(_rect(house['x'] - 6, house['y'] - 6, 13, 13, 'casa'))
        zones.append(_rect(house['x'] - 5, house['y'] - 5, 11, 11, 'potrero'))
    for region in world.get('regions') or []:
        if region.get('id') in ('valle', 'jardin'):
            continue
        kind = 'finca' if region.get('id') == 'las_palmas' else 'casa'
        zones.append(_rect(region['x'], region['y'], region['w'], region['h'], kind))
        if region.get('id') == 'las_palmas':
            zones.append(_rect(region['x'] - 2, region['y'] - 2, region['w'] + 4, region['h'] + 4, 'mina'))
    for area in world.get('areas') or []:
        name = area.get('id') or ''
        if name == 'huerto':
            kind = 'corral'
            zones.append(_rect(area['x'] - 1, area['y'] - 1, area['w'] + 2, area['h'] + 2, kind))
        elif name == 'cantera':
            zones.append(_rect(area['x'] - 1, area['y'] - 1, area['w'] + 2, area['h'] + 2, 'mina'))
        elif name in ('pueblo', 'plaza') or name.startswith('parque_'):
            zones.append(_rect(area['x'], area['y'], area['w'], area['h'], 'casa'))
    for deco in world.get('decorations') or []:
        typ = deco.get('type') or ''
        if typ in ('building', 'casa_envigado'):
            zones.append(_rect(deco['x'] - 1, deco['y'] - 1, (deco.get('w') or 1) + 2, (deco.get('h') or 1) + 2, 'casa'))
        elif typ == 'mine_entrance':
            zones.append(_rect(deco['x'] - 4, deco['y'] - 4, (deco.get('w') or 2) + 8, (deco.get('h') or 2) + 8, 'mina'))
    for mark in world.get('landmarks') or []:
        zones.append(_rect(mark['x'] - 1, mark['y'] - 1, (mark.get('w') or 4) + 2, (mark.get('h') or 4) + 2, 'casa'))
    palmas = next((item for item in world.get('waypoints') or [] if item.get('id') == 'las_palmas'), None)
    if palmas:
        zones.append(_rect(palmas['x'] - 16, palmas['y'] - 8, 36, 40, 'finca'))
        zones.append(_rect(palmas['x'] - 12, palmas['y'] - 12, 25, 25, 'mina'))
    return zones


def inside(zones, x, y):
    ix, iy = math.floor(x), math.floor(y)
    for zone in zones:
        if zone['x'] <= ix < zone['x'] + zone['w'] and zone['y'] <= iy < zone['y'] + zone['h']:
            return zone['kind']
    return ''


def _kind_at(world, x, y):
    tiles = world['tiles']
    tile = world['ground'][y][x]
    return tiles[str(tile)]['kind']


def place(world, homes):
    """Grupos de 2 a 6 en quebrada, árboles o monte. Nada de pueblo."""
    zones = forbidden(world, homes)
    width, height = world['width'], world['height']

    def blocked(x, y):
        return not (0 <= x < width and 0 <= y < height) or bool(inside(zones, x, y))

    def ground_kind(x, y):
        if not (0 <= x < width and 0 <= y < height):
            return ''
        return _kind_at(world, x, y)

    def open_ground(x, y):
        kind = ground_kind(x, y)
        if kind in ('water', 'bridge', 'cobble', 'path', 'asphalt', 'pavement', 'creek'):
            return False
        return kind.startswith('grass') or kind in ('mountain', 'rocky', 'shore', 'cliff')

    candidates = []
    seen = set()

    def add(x, y, habitat, perch):
        if x < 8 or y < 8 or x >= width - 8 or y >= height - 8:
            return
        if (x, y) in seen or blocked(x, y) or not open_ground(x, y):
            return
        if habitat == 'monte' and ground_kind(x, y) == 'rocky':
            return
        seen.add((x, y))
        candidates.append({'x': x, 'y': y, 'habitat': habitat, 'perch': bool(perch)})

    trees = []
    for deco in world.get('decorations') or []:
        if deco.get('type') in ('tree_roble', 'bush') or str(deco.get('type') or '').startswith('tree'):
            trees.append((deco['x'], deco['y']))
    for prop in world.get('scenery3d') or []:
        if prop.get('kind') == 'tree':
            trees.append((prop['x'], prop['y']))
    for node in world.get('nodes') or []:
        if node.get('type') in ('fruit_tree', 'wood_tree'):
            trees.append((node['x'], node['y']))
    for x, y in trees:
        add(x, y, 'arbol', True)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1)):
            add(x + dx, y + dy, 'borde', False)

    claro = ((world.get('waterBodies') or {}).get('rio_claro') or {}).get('tiles') or []
    for x, y in claro:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            add(x + dx, y + dy, 'quebrada', False)

    for y in range(2, height - 2, 6):
        for x in range(2, width - 2, 6):
            if ground_kind(x, y) != 'mountain':
                continue
            edge = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if ground_kind(x + dx, y + dy).startswith('grass'):
                    edge = True
                    break
            if edge:
                add(x, y, 'monte', False)

    by_hab = {name: [] for name in NATURAL}
    for item in candidates:
        by_hab[item['habitat']].append(item)
    for rows in by_hab.values():
        rows.sort(key=lambda item: (item['y'], item['x']))

    flocks = []
    used = set()
    cursor = {name: 0 for name in NATURAL}
    order = ('quebrada', 'arbol', 'monte', 'borde')
    while len(flocks) < FLOCKS:
        grew = False
        for habitat in order:
            rows = by_hab[habitat]
            while cursor[habitat] < len(rows):
                seed = rows[cursor[habitat]]
                cursor[habitat] += 1
                key = (seed['x'], seed['y'])
                if key in used:
                    continue
                if any(flock['habitat'] == habitat and flock['y'] // 48 == seed['y'] // 48 for flock in flocks):
                    continue
                if any(max(abs(seed['x'] - flock['x']), abs(seed['y'] - flock['y'])) < FLOCK_GAP for flock in flocks):
                    continue
                reach = REACH[habitat]
                near = [
                    item for item in candidates
                    if (item['x'], item['y']) not in used
                    and max(abs(item['x'] - seed['x']), abs(item['y'] - seed['y'])) <= reach
                ]
                near.sort(key=lambda item: (item['x'] != seed['x'] or item['y'] != seed['y'], abs(item['x'] - seed['x']) + abs(item['y'] - seed['y'])))
                want = 2 + ((seed['x'] + seed['y']) % 5)
                group = []
                spots = set()
                for item in near:
                    spot = (item['x'], item['y'])
                    if spot in spots:
                        continue
                    spots.add(spot)
                    group.append(item)
                    if len(group) == want:
                        break
                if len(group) < 2:
                    continue
                for item in group:
                    used.add((item['x'], item['y']))
                birds = []
                for index, item in enumerate(group):
                    birds.append({
                        'id': 'guacha-%d-%d' % (len(flocks) + 1, index),
                        'x': item['x'],
                        'y': item['y'],
                        'perch': bool(item['perch']),
                        'habitat': item['habitat'],
                    })
                flocks.append({
                    'id': 'guacha-%d' % (len(flocks) + 1),
                    'x': seed['x'],
                    'y': seed['y'],
                    'habitat': habitat,
                    'birds': birds,
                })
                grew = True
                break
        if not grew:
            break
    return {'flocks': flocks, 'zones': zones}


def load():
    with open(WORLD, encoding='utf-8') as handle:
        world = json.load(handle)
    with open(HOMES, encoding='utf-8') as handle:
        homes = json.load(handle)
    return place(world, homes)


def dump_js(doc, path=OUT_JS):
    body = json.dumps(doc, ensure_ascii=False, separators=(',', ':'))
    text = '/* SPDX-License-Identifier: AGPL-3.0-or-later */\nwindow.GUACHARACAS=' + body + ';\n'
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    return path


def _voice(samples, rate, start, pitch):
    phrase = SONG['phrase']
    gap = SONG['gap']
    for repeat, syllable in (
        (repeat, syllable)
        for repeat in range(SONG['repeats'] if pitch == 1 else SONG['duetRepeats'] if pitch > 1 else SONG['thirdRepeats'])
        for syllable in SONG['syllables']
    ):
        at = start + repeat * (phrase + gap) + syllable['at']
        dur = syllable['dur']
        i0 = int(at * rate)
        n = int(dur * rate)
        freq = syllable['freq'] * pitch
        slide = syllable['slide'] * pitch
        hold = 0.0
        for i in range(n):
            pos = i0 + i
            if pos < 0 or pos >= len(samples):
                continue
            t = i / rate
            env = min(1.0, i / max(1, rate * 0.012)) * math.exp(-3.2 * t / dur)
            white = (((i * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff) * 2 - 1
            hold = hold * 0.84 + white * 0.16
            phase = freq * t + (slide - freq) * t * t / max(dur, 0.01)
            tone = math.sin(2 * math.pi * phase) * 0.35
            samples[pos] += (hold * 0.75 + tone) * env * 0.55


def render_song(path, rate=16000):
    """Muestra del coro, generada aquí. No es una grabación."""
    seconds = song_seconds() + 0.15
    samples = [0.0] * int(seconds * rate)
    _voice(samples, rate, 0.0, 1)
    _voice(samples, rate, SONG['duetDelay'], SONG['duetPitch'])
    _voice(samples, rate, SONG['thirdAt'], SONG['thirdPitch'])
    peak = max(1e-6, max(abs(sample) for sample in samples))
    with wave.open(path, 'w') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        frames = b''.join(struct.pack('<h', max(-32767, min(32767, int(sample / peak * 28000)))) for sample in samples)
        handle.writeframes(frames)
    return {'path': path, 'seconds': round(seconds, 2), 'bytes': os.path.getsize(path)}


if __name__ == '__main__':
    doc = load()
    dump_js(doc)
    birds = [bird for flock in doc['flocks'] for bird in flock['birds']]
    print('flocks', len(doc['flocks']), 'birds', len(birds), 'song', song_seconds())
    for flock in doc['flocks']:
        print(flock['id'], flock['habitat'], flock['x'], flock['y'], len(flock['birds']),
              'perch', sum(1 for bird in flock['birds'] if bird['perch']))
