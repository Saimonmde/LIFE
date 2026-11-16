# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lugares para empezar. Sólo parques y pueblos que ya están en el valle.

Parque de Envigado usa la casilla de la casa colonial. Los demás parques
usan el punto que ya tiene el mapa. No se inventa ningún sitio.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    with open(os.path.join(ROOT, 'data', name), encoding='utf-8') as handle:
        return json.load(handle)


def catalog():
    homes = _load('hogares.json')
    world = _load('el-jardin.json')
    points = {item.get('id'): item for item in world.get('waypoints') or [] if item.get('id')}
    labels = {item.get('id'): item for item in world.get('mapLabels') or [] if item.get('id')}
    found = []
    for casa in homes['casas']:
        mark = points.get(casa['id']) or {}
        if casa['id'] == 'envigado':
            name, x, y = 'Parque de Envigado', int(casa['x']), int(casa['y'])
        else:
            name = mark.get('name') or casa['name']
            x, y = int(mark.get('x', casa['x'])), int(mark.get('y', casa['y']))
        found.append({
            'id': casa['id'], 'name': name, 'x': x, 'y': y,
            'kind': 'parque', 'municipio': casa['id'],
        })
    park = labels.get('parque_bolivar')
    if park:
        found.append({
            'id': 'parque_bolivar', 'name': park.get('name') or 'Parque de Bolívar',
            'x': int(park['x']), 'y': int(park['y']), 'kind': 'poi', 'municipio': 'medellin',
        })
    palms = points.get('las_palmas')
    if palms:
        found.append({
            'id': 'las_palmas', 'name': 'Las Palmas',
            'x': int(palms['x']), 'y': int(palms['y']), 'kind': 'poi', 'municipio': '',
        })
    return found


def get(place_id):
    key = str(place_id or '').strip().lower()
    for item in catalog():
        if item['id'] == key:
            return item
    return None


def spot(place_id):
    item = get(place_id)
    if not item:
        return None
    return int(item['x']), int(item['y'])
