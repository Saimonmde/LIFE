# SPDX-License-Identifier: AGPL-3.0-or-later
"""Proxy de cajas de la banca de Envigado, con las medidas del escaneo.

El GLB final lo reemplaza el mismo archivo. Este proxy solo existe para que
el juego tenga una banca del tamaño real mientras ese modelo no está.
Origen en el centro del suelo, lado largo en X, frente hacia +Z, Y hacia arriba.
"""
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'graphics' / 'models' / 'banca_envigado.glb'
SPEC = ROOT / 'graphics' / 'models' / 'banca_envigado.json'

# Nube densa del SPZ (577726 gaussianas, v3, 12 bits fraccionarios).
# La losa superior, ya separado el piso y la baranda: percentiles 1–99.
LENGTH = 1.63
WIDTH = 0.51
SEAT = 0.48
SLANT = 0.01
SLAB = 0.10
WEDGE_L = 1.40
WEDGE_W = 0.28
WEDGE_BACK = 0.38
WEDGE_FRONT = 0.16

TOP = (0.91, 0.88, 0.82)
SIDE = (0.56, 0.52, 0.48)
EDGE = (0.40, 0.37, 0.34)
DARK = (0.28, 0.26, 0.24)


def quad(positions, colors, a, b, c, d, color):
    for tri in ((a, b, c), (a, c, d)):
        for vertex in tri:
            positions.extend(vertex)
            colors.extend(color)


def box(positions, colors, x0, x1, y0, y1, z0, z1, top, side, edge, bottom):
    quad(positions, colors, (x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0), top)
    quad(positions, colors, (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), bottom)
    quad(positions, colors, (x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0), side)
    quad(positions, colors, (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (x0, y0, z1), side)
    quad(positions, colors, (x0, y0, z1), (x0, y1, z1), (x0, y1, z0), (x0, y0, z0), edge)
    quad(positions, colors, (x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1), edge)


def wedge(positions, colors):
    x0, x1 = -WEDGE_L / 2, WEDGE_L / 2
    z0, z1 = -WEDGE_W / 2, WEDGE_W / 2
    a, b = (x0, 0, z0), (x1, 0, z0)
    c, d = (x1, 0, z1), (x0, 0, z1)
    e, f = (x0, WEDGE_BACK, z0), (x1, WEDGE_BACK, z0)
    g, h = (x1, WEDGE_FRONT, z1), (x0, WEDGE_FRONT, z1)
    quad(positions, colors, d, c, b, a, DARK)
    quad(positions, colors, a, b, f, e, SIDE)
    quad(positions, colors, c, d, h, g, EDGE)
    quad(positions, colors, a, e, h, d, DARK)
    quad(positions, colors, b, c, g, f, DARK)
    quad(positions, colors, e, f, g, h, SIDE)


def mesh():
    positions, colors = [], []
    box(
        positions, colors,
        -LENGTH / 2, LENGTH / 2, SEAT - SLAB, SEAT, -WIDTH / 2, WIDTH / 2,
        TOP, SIDE, EDGE, DARK,
    )
    wedge(positions, colors)
    return positions, colors


def glb_bytes():
    positions, colors = mesh()
    count = len(positions) // 3
    blob = struct.pack('<' + 'f' * len(positions), *positions)
    blob += struct.pack('<' + 'f' * len(colors), *colors)
    pad = (4 - len(blob) % 4) % 4
    blob += b'\x00' * pad
    pos_bytes = count * 12
    color_off = pos_bytes

    def accessor(view, acc_type, minimum, maximum):
        return {
            'bufferView': view, 'componentType': 5126, 'count': count,
            'type': acc_type, 'min': minimum, 'max': maximum,
        }

    xs, ys, zs = positions[0::3], positions[1::3], positions[2::3]
    gltf = {
        'asset': {'version': '2.0', 'generator': 'banca_proxy.py'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'mesh': 0, 'name': 'banca_envigado'}],
        'meshes': [{
            'name': 'banca',
            'primitives': [{
                'attributes': {'POSITION': 0, 'COLOR_0': 1},
                'material': 0,
            }],
        }],
        'materials': [{
            'name': 'concreto',
            'pbrMetallicRoughness': {
                'baseColorFactor': [0.84, 0.81, 0.75, 1],
                'metallicFactor': 0,
                'roughnessFactor': 0.92,
            },
        }],
        'accessors': [
            accessor(0, 'VEC3', [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]),
            accessor(1, 'VEC3', [0, 0, 0], [1, 1, 1]),
        ],
        'bufferViews': [
            {'buffer': 0, 'byteOffset': 0, 'byteLength': pos_bytes, 'target': 34962},
            {'buffer': 0, 'byteOffset': color_off, 'byteLength': count * 12, 'target': 34962},
        ],
        'buffers': [{'byteLength': len(blob)}],
    }
    js = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    js += b' ' * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    out = struct.pack('<III', 0x46546C67, 2, total)
    out += struct.pack('<II', len(js), 0x4E4F534A) + js
    out += struct.pack('<II', len(blob), 0x004E4942) + blob
    return out


def spec():
    return {
        'id': 'banca_envigado',
        'units': 'meters',
        'up': 'Y',
        'origin': 'floor center',
        'longAxis': 'X',
        'front': '+Z',
        'length_m': LENGTH,
        'width_m': WIDTH,
        'seat_height_m': SEAT,
        'top_slant_m': SLANT,
        'slab_thickness_m': SLAB,
        'support': {
            'kind': 'wedge',
            'length_m': WEDGE_L,
            'width_m': WEDGE_W,
            'back_height_m': WEDGE_BACK,
            'front_height_m': WEDGE_FRONT,
        },
        'triangles': 24,
        'source': {
            'scan': 'https://scaniverse.com/scan/7bneqnib2f5mf6pg',
            'gaussians': 'https://scaniverse.com/api/media/7bneqnib2f5mf6pg/gaussians.spz',
            'preview': 'https://scaniverse.com/api/media/7bneqnib2f5mf6pg/preview.jpg',
            'format': 'SPZ v3 gzip, 577726 gaussians, fractional_bits 12',
            'author': 'Simón / @Saimon888',
            'license': 'CC-BY-SA-4.0',
        },
        'note': (
            'Medido en la nube densa, ya separado el piso de baldosa y la baranda. '
            'La losa de asiento mide 1.63 m por 0.51 m y queda a 0.48 m del piso. '
            'La superficie superior es casi horizontal: 1 cm de caída en todo el ancho. '
            'Debajo, la cuña se abre: el centro queda hueco y los apoyos bajan hacia el suelo. '
            'El GLB de al lado es un proxy de caja y cuña con esas medidas. '
            'El modelo estilizado final lo reemplaza sin cambiar la ruta.'
        ),
    }


def main():
    MODEL.write_bytes(glb_bytes())
    SPEC.write_text(json.dumps(spec(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote', MODEL, MODEL.stat().st_size)


if __name__ == '__main__':
    main()
