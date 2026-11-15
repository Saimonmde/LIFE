#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Puente de la 4 Sur, jugable. La colocación es ilustrativa, no un levantamiento.

Se aplica en memoria sobre el valle ya cargado. No reescribe el JSON del mapa
ni copia partidas. Volver a llamarlo no duplica accesos.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
X0, X1, Y0, Y1 = 82, 138, 238, 242


class BridgeError(RuntimeError):
    pass


def install(world):
    if world.get('bridge4Sur'):
        return world['bridge4Sur']
    nodes = world.get('nodes') or []
    if any(X0 - 1 <= n.get('x', -1) <= X1 + 1 and Y0 - 1 <= n.get('y', -1) <= Y1 for n in nodes):
        raise BridgeError('Hay un recurso en el vano del puente; no se pisa.')
    west = world['elevation'][240][X0 - 1]
    east = world['elevation'][240][X1]
    deck = max(west, east) + 2
    cfg = {
        'id': 'puente_4_sur',
        'name': 'Puente de la 4 Sur · Gilberto Echeverri Mejía',
        'kind': 'procedural-reconstruction',
        'surveyed': False,
        'x0': X0, 'x1': X1, 'y0': Y0, 'y1': Y1,
        'nominalMeters': {
            'length': 560, 'width': 40.5, 'pylon': 47,
            'pylonSpacing': 108, 'stayedSpan': 213,
        },
        'renderUnitsPerNominalMeter': 0.2,
        'rendererUnitsPerTile': 2,
        'profile': {'west': west, 'east': east, 'deck': deck, 'rampTiles': 15},
        'pylonTiles': [104, 115],
        'scan': {
            'status': 'not-loaded',
            'url': 'https://poly.cam/capture/0B952B36-D202-4FC6-A4F9-8FAE632DABD8',
            'segments': [],
            'transform': {'translation': [220, deck, 480], 'rotationY': 0, 'scale': 1},
            'required': 'GLB/glTF with textures, local units and three matched control points; collisions separate',
        },
        'sources': [
            {
                'url': 'https://conconcreto.com/proyectos/puente-gilberto-echeverri-mejia/',
                'lengthMeters': 580, 'widthMeters': 40.5, 'towerMeters': 37,
            },
            {
                'url': 'https://www.scielo.cl/scielo.php?pid=S0718-50732012000300004&script=sci_arttext',
                'lengthMeters': 560, 'widthMeters': 40.5, 'pylonMeters': 47,
            },
        ],
        'note': (
            '560/580 m y 37/47 m no coinciden entre fuentes. Proporciones nominales '
            'ajustables en un valle esquemático, no una reconstrucción georreferenciada.'
        ),
    }
    asphalt = next(int(key) for key, tile in world['tiles'].items() if tile.get('kind') == 'asphalt')

    def height_at(x):
        if x < X0 + 15:
            return west + (deck - west) * (x - X0) / 15
        if x > X1 - 15:
            return east + (deck - east) * (X1 - x) / 15
        return deck

    for x in range(X0, X1):
        for y in range(Y0, Y1):
            world['ground'][y][x] = asphalt
            world['collision'][y][x] = 0
            world['elevation'][y][x] = round(height_at(x + 0.5), 4)
        if X0 < x < X1 - 1:
            world['collision'][Y0 - 1][x] = 1
            world['collision'][Y1][x] = 1
    for x in cfg['pylonTiles']:
        world['collision'][Y0 + 1][x] = 1
    river = ((world.get('waterBodies') or {}).get('rio_medellin') or {}).get('tiles') or []
    water = []
    for cell in river:
        if isinstance(cell, (list, tuple)) and len(cell) >= 2:
            cx, cy = cell[0], cell[1]
        elif isinstance(cell, dict):
            cx, cy = cell.get('x'), cell.get('y')
        else:
            continue
        if X0 <= cx < X1 and Y0 <= cy < Y1:
            water.append([cx, cy])
    cfg['waterCells'] = water
    world.setdefault('waypoints', [])
    world.setdefault('signs3d', [])
    for ident, x, name in (
        ('puente_4_sur', X1 - 1, 'Puente de la 4 Sur · acceso El Poblado'),
        ('puente_4_sur_guayabal', X0, 'Puente de la 4 Sur · acceso Guayabal'),
    ):
        if not any(point.get('id') == ident for point in world['waypoints']):
            world['waypoints'].append({'id': ident, 'name': name, 'x': x, 'y': Y0 + 2})
    if not any(sign.get('text') == 'PUENTE 4 SUR · RECREACIÓN' for sign in world['signs3d']):
        world['signs3d'].append({'text': 'PUENTE 4 SUR · RECREACIÓN', 'x': X1 + 1, 'y': Y0 + 2})
    world['bridge4Sur'] = cfg
    return cfg


if __name__ == '__main__':
    path = ROOT / 'data' / 'el-jardin.json'
    world = json.loads(path.read_text())
    install(world)
    print(world['bridge4Sur']['name'])
