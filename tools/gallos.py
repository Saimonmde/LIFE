#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Gallos de la finca y de los patios.

Se pueden guardar y pasar de una cuenta a otra. No se acuñan monedas.
La guacharaca no entra por aquí: es fauna protegida.
Cantan al amanecer real de Bogotá y en cada día nuevo del reloj de 1777.
"""
from __future__ import annotations

import json
import math
import os
import struct
import wave

import purses
import reloj

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLD = os.path.join(ROOT, 'data', 'el-jardin.json')
HOMES = os.path.join(ROOT, 'data', 'hogares.json')
OUT_JS = os.path.join(ROOT, 'data', 'gallos.js')

ITEM = 'gallo'
CAP = 8
DAY_SECONDS = reloj.REAL_SECONDS_PER_DAY
REAL_START = 5 * 60
REAL_END = 6 * 60
SONG = {
    'strong': [
        {'name': 'qui', 'at': 0.00, 'dur': 0.09, 'freq': 640, 'slide': 700},
        {'name': 'qui', 'at': 0.12, 'dur': 0.09, 'freq': 860, 'slide': 920},
        {'name': 'riqui', 'at': 0.24, 'dur': 0.62, 'freq': 1180, 'slide': 460},
    ],
    'strongGap': 0.98,
    'strongRepeats': 2,
    'short': [
        {'name': 'qui', 'at': 0.00, 'dur': 0.08, 'freq': 700, 'slide': 760},
        {'name': 'qui', 'at': 0.10, 'dur': 0.08, 'freq': 900, 'slide': 980},
        {'name': 'riqui', 'at': 0.20, 'dur': 0.42, 'freq': 1100, 'slide': 520},
    ],
}


class GallosError(ValueError):
    pass


def sellable(item):
    return str(item or '') == ITEM


def killable(item):
    return False


def crows_real(hour, minute):
    """Canto fuerte entre las 5:00 inclusive y las 6:00 exclusive, hora de Bogotá."""
    try:
        hour = int(hour)
        minute = int(minute)
    except (TypeError, ValueError):
        return False
    if minute < 0 or minute > 59 or hour < 0:
        return False
    clock = hour * 60 + minute
    return REAL_START <= clock < REAL_END


def game_day(now, epoch):
    """Día 1 es el 1 de enero de 1777. Cada 20 minutos reales empieza otro."""
    try:
        elapsed = max(0.0, float(now) - float(epoch))
    except (TypeError, ValueError):
        return 1
    return int(elapsed // DAY_SECONDS) + 1


def notice(day):
    try:
        number = int(day)
    except (TypeError, ValueError):
        number = 1
    if number < 1:
        number = 1
    return 'Amaneció: día %d' % number


def game_dawn(previous, current):
    """Verdadero cuando el índice del día de juego avanza."""
    try:
        return int(current) > int(previous)
    except (TypeError, ValueError):
        return False


def count_inv(inv):
    total = 0
    for row in inv or []:
        if isinstance(row, dict) and row.get('item') == ITEM:
            try:
                total += int(row.get('qty') or 0)
            except (TypeError, ValueError):
                continue
    return max(0, total)


def clamp_inv(inv):
    """Deja como máximo CAP gallos. No toca el resto de la mochila."""
    left = CAP
    kept = []
    for row in inv or []:
        if not isinstance(row, dict) or row.get('item') != ITEM:
            kept.append(row)
            continue
        if left <= 0:
            continue
        try:
            qty = int(row.get('qty') or 0)
        except (TypeError, ValueError):
            continue
        if qty < 1:
            continue
        take = min(qty, left)
        left -= take
        kept.append({'item': ITEM, 'qty': take})
    return kept


def sell(state, src, dst, item=ITEM, qty=1):
    """Pasa gallos de una mochila a otra. No crea monedas. Rechaza la guacharaca."""
    item = str(item or '')
    if item != ITEM:
        raise GallosError('la guacharaca es fauna protegida y no se vende')
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        raise GallosError('la cantidad no sirve')
    if qty < 1:
        raise GallosError('la cantidad no sirve')
    src = str(src or '')
    dst = str(dst or '')
    if not src or not dst or src == dst:
        raise GallosError('la venta necesita dos cuentas')
    before = purses.count(state, dst, ITEM)
    if not purses.debit(state, src, ITEM, qty):
        raise GallosError('no tienes ese gallo')
    after = purses.credit(state, dst, ITEM, qty)
    if after != before + qty:
        purses.credit(state, src, ITEM, qty)
        raise GallosError('la otra mochila no tiene espacio')
    return {'item': ITEM, 'qty': qty, 'from': src, 'to': dst}


def sync_purse(state, name, count):
    """Iguala la mochila del intercambio con los gallos guardados. No crea monedas."""
    name = str(name or '')
    if not name:
        return 0
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 0
    count = max(0, min(CAP, count))
    have = purses.count(state, name, ITEM)
    if count > have:
        purses.credit(state, name, ITEM, count - have)
    elif have > count:
        purses.debit(state, name, ITEM, have - count)
    return purses.count(state, name, ITEM)


def _kind(world, x, y):
    return world['tiles'][str(world['ground'][y][x])]['kind']


def _open(world, x, y):
    width, height = world['width'], world['height']
    if not (0 <= x < width and 0 <= y < height):
        return False
    if world['collision'][y][x] != 0:
        return False
    kind = _kind(world, x, y)
    return kind not in ('water', 'creek', 'bridge')


def _plot_tiles(anchor):
    blocked = set()
    ax, ay = anchor
    for i in range(8):
        lx = -5.2 + i * 1.35
        lz = 5.6
        tx = int(round(ax + lx / 2.0))
        ty = int(round(ay + lz / 2.0))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                blocked.add((tx + dx, ty + dy))
    for lx, lz in ((-4.2, 3.6), (3.4, 3.6)):
        tx = int(round(ax + lx / 2.0))
        ty = int(round(ay + lz / 2.0))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                blocked.add((tx + dx, ty + dy))
    return blocked


def _finca_anchor(world, palmas):
    def walk(x, y):
        return _open(world, x, y)

    best = None
    for dy in range(6, 17):
        for dx in range(-8, 9):
            x = palmas['x'] + dx
            y = palmas['y'] + dy
            open_count = 0
            for iy in range(8):
                for ix in range(-6, 7):
                    if walk(x + ix, y + iy):
                        open_count += 1
            if best is None or open_count > best[0]:
                best = (open_count, x, y)
    if best and best[0] > 40:
        return best[1], best[2]
    return palmas['x'], min(world['height'] - 4, palmas['y'] + 8)


def place(world, homes):
    roosters = []
    used = set()
    order = ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1), (0, 2), (2, 0))
    for house in (homes or {}).get('casas') or []:
        hx, hy = int(house['x']), int(house['y'])
        spot = None
        for dx, dy in order:
            x, y = hx + dx, hy + dy
            if (x, y) in used or (x, y) == (hx, hy):
                continue
            if not _open(world, x, y):
                continue
            spot = (x, y)
            break
        if not spot:
            continue
        used.add(spot)
        roosters.append({
            'id': 'gallo-' + str(house['id']),
            'x': spot[0],
            'y': spot[1],
            'where': 'patio',
            'house': house['id'],
            'species': 'gallo',
            'loose': False,
        })
    palmas = next((item for item in world.get('waypoints') or [] if item.get('id') == 'las_palmas'), None)
    if palmas:
        anchor = _finca_anchor(world, palmas)
        plots = _plot_tiles(anchor)
        found = []
        ax, ay = anchor
        for dy in range(-6, 9):
            for dx in range(-6, 7):
                x, y = ax + dx, ay + dy
                if (x, y) in used or (x, y) in plots:
                    continue
                if not _open(world, x, y):
                    continue
                if _kind(world, x, y) not in ('grass', 'grass_worn', 'grass_flowers', 'path', 'cobble'):
                    continue
                found.append((abs(dx) + abs(dy), x, y))
        found.sort()
        for _score, x, y in found:
            if len([item for item in roosters if item['where'] == 'finca']) >= 4:
                break
            if any(max(abs(x - item['x']), abs(y - item['y'])) < 3 for item in roosters if item['where'] == 'finca'):
                continue
            used.add((x, y))
            kind = 'gallina' if len([item for item in roosters if item.get('species') == 'gallina']) < 2 else 'gallo'
            roosters.append({
                'id': '%s-finca-%d' % (kind, len([item for item in roosters if item['where'] == 'finca']) + 1),
                'x': x,
                'y': y,
                'where': 'finca',
                'house': '',
                'species': kind,
                'loose': True,
            })
    houses = [(int(house['x']), int(house['y'])) for house in (homes or {}).get('casas') or []]
    loose = 0
    for y in range(16, world['height'] - 16, 10):
        if loose >= 3:
            break
        for x in range(16, world['width'] - 16, 12):
            if loose >= 3:
                break
            if (x, y) in used or not _open(world, x, y) or _kind(world, x, y) != 'mountain':
                continue
            edge = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < world['width'] and 0 <= ny < world['height'] and _kind(world, nx, ny).startswith('grass'):
                    edge = True
            if not edge:
                continue
            if any(max(abs(x - hx), abs(y - hy)) < 12 for hx, hy in houses):
                continue
            used.add((x, y))
            loose += 1
            roosters.append({
                'id': 'gallo-monte-%d' % loose,
                'x': x,
                'y': y,
                'where': 'monte',
                'house': '',
                'species': 'gallo',
                'loose': True,
            })
    return {
        'roosters': roosters,
        'cap': CAP,
        'item': ITEM,
        'plots': [{'x': x, 'y': y} for x, y in sorted(_plot_tiles(_finca_anchor(world, palmas)) if palmas else [])],
    }


def load():
    with open(WORLD, encoding='utf-8') as handle:
        world = json.load(handle)
    with open(HOMES, encoding='utf-8') as handle:
        homes = json.load(handle)
    return place(world, homes)


def dump_js(doc, path=OUT_JS):
    slim = {'roosters': doc['roosters'], 'cap': doc['cap'], 'item': doc['item']}
    body = json.dumps(slim, ensure_ascii=False, separators=(',', ':'))
    text = '/* SPDX-License-Identifier: AGPL-3.0-or-later */\nwindow.GALLOS=' + body + ';\n'
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    return path


def _voice(samples, rate, notes, start, gain):
    for note in notes:
        at = start + note['at']
        dur = note['dur']
        i0 = int(at * rate)
        n = int(dur * rate)
        freq = note['freq']
        slide = note['slide']
        hold = 0.0
        for i in range(n):
            pos = i0 + i
            if pos < 0 or pos >= len(samples):
                continue
            t = i / rate
            env = min(1.0, i / max(1, rate * 0.01)) * math.exp(-2.4 * t / dur)
            white = (((i * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff) * 2 - 1
            hold = hold * 0.6 + white * 0.4
            phase = freq * t + (slide - freq) * t * t / max(dur, 0.01)
            tone = math.sin(2 * math.pi * phase)
            samples[pos] += (tone * 0.8 + hold * 0.25) * env * gain


def render_song(path, rate=16000):
    seconds = SONG['strongGap'] + 0.9
    samples = [0.0] * int(seconds * rate)
    for repeat in range(SONG['strongRepeats']):
        _voice(samples, rate, SONG['strong'], repeat * SONG['strongGap'], 0.9)
    peak = max(1e-6, max(abs(sample) for sample in samples))
    with wave.open(path, 'w') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        frames = b''.join(
            struct.pack('<h', max(-32767, min(32767, int(sample / peak * 26000))))
            for sample in samples
        )
        handle.writeframes(frames)
    return {'path': path, 'seconds': round(seconds, 2), 'bytes': os.path.getsize(path)}


if __name__ == '__main__':
    doc = load()
    dump_js(doc)
    print('roosters', len(doc['roosters']), 'finca', sum(1 for item in doc['roosters'] if item['where'] == 'finca'))
    for item in doc['roosters']:
        print(item['id'], item['where'], item['x'], item['y'])
