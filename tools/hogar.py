# SPDX-License-Identifier: AGPL-3.0-or-later
"""Casa del jugador: municipio, plano, oficio, mascotas y código de visita.

La primera vez el modo es «ovni». Un ingreso posterior sólo usa la casilla
guardada. El plano y las mascotas de la cuenta viven aparte, con un código
CASA-XXXX. nft queda vacío: esta versión no acuña nada.

La primera vez el modo es «ovni». Un ingreso posterior sólo usa la casilla
guardada: no se encadena otra cinemática.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'data', 'hogares.json')

with open(PATH, encoding='utf-8') as handle:
    GEO = json.load(handle)

ORDEN = tuple(GEO['orden'])
CASAS = {item['id']: item for item in GEO['casas']}
NOMBRES = {item['id']: item['name'] for item in GEO['casas']}


def entry_mode(just_picked):
    """La primera elección es el ovni. Cada entrada siguiente baja en helicóptero."""
    return 'ovni' if just_picked else 'heli'


def casa(municipio):
    return CASAS.get(str(municipio or '').strip().lower())


def stand(municipio):
    item = casa(municipio)
    if not item:
        return None
    return int(item['x']), int(item['y'])


def arrival(user, resume, walkable):
    """Sin reanudación, la cuenta entra en su casa. Una reconexión conserva el sitio."""
    if isinstance(resume, dict):
        try:
            x, y = float(resume['x']), float(resume['y'])
            if walkable(int(x), int(y)) and x >= 0 and y >= 0:
                return x, y
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
    spot = stand((user or {}).get('municipio'))
    if spot and walkable(spot[0], spot[1]):
        return float(spot[0]), float(spot[1])
    return None

import secrets

ROLES = ('explorador', 'comerciante', 'artesano', 'inmobiliario', 'guardian')
ALFABETO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
CATALOG = {
    'bed': (2, 1, True),
    'altar': (1, 1, True),
    'bacenilla': (1, 1, True),
    'cocina': (2, 1, True),
    'ventana': (1, 1, True),
    'matica': (1, 1, True),
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
}
STYLES = {
    'bed': ('retazos', 'colonial', 'dosel', 'catre'),
    'altar': ('madera', 'velas', 'hornacina', 'familiar'),
    'cocina': ('lena', 'barro', 'carbon', 'estufa'),
    'matica': ('flores', 'helecho', 'sabila', 'orquidea', 'cinta'),
}
WALLS = {
    '#f4f0e6', '#efe2c4', '#e7d39a', '#d5ddc8',
    '#e4c48a', '#c9894a', '#f7f1e4', '#6f8f9a',
}
FLOORS = {'#c45c38', '#a84832', '#d4895c', '#b7a48a'}
DEFAULT_WALL = '#e4c48a'
DEFAULT_FLOOR = '#c45c38'
MAX_ITEMS = 36
PELOS = {
    'gato': ('naranja', 'negro', 'blanco', 'gris', 'tricolor'),
    'perro': ('cafe', 'negro', 'blanco', 'dorado', 'manchado'),
}
MAX_MASCOTAS = 3
DOOR = (4, 9)
SPAWN = (4, 6)
NFT_VACIO = {
    'enlace': '',
    'cadena': '',
    'token': '',
    'nota': 'Campo reservado para un enlace futuro. Esta versión no acuña ni escribe en ninguna cadena.',
}


class HogarError(Exception):
    def __init__(self, message, status='400 Bad Request'):
        self.status = status
        super().__init__(message)


def vacio():
    return {'por_cuenta': {}, 'por_codigo': {}}


def load(path):
    import persist
    doc = persist.load_named('hogar', path)
    if not isinstance(doc, dict):
        doc = vacio()
    if not isinstance(doc.get('por_cuenta'), dict):
        doc['por_cuenta'] = {}
    if not isinstance(doc.get('por_codigo'), dict):
        doc['por_codigo'] = {}
    return doc


def save(path, doc):
    import persist
    persist.save_named('hogar', path, doc)


def piso():
    celdas = {}
    for y in range(1, 9):
        for x in range(1, 9):
            celdas[(x, y)] = 'room'
    for y in (3, 4, 5):
        celdas[(9, y)] = 'hall'
    for y in range(2, 8):
        for x in range(10, 13):
            celdas[(x, y)] = 'patio'
    celdas[DOOR] = 'door'
    celdas[(DOOR[0], DOOR[1] - 1)] = 'threshold'
    celdas[(DOOR[0] - 1, DOOR[1] - 1)] = 'threshold'
    celdas[(DOOR[0] + 1, DOOR[1] - 1)] = 'threshold'
    return celdas


SUELO = piso()


def _tamano(tipo, rot):
    spec = CATALOG.get(tipo)
    if not spec:
        return None
    w, h, solid = spec
    if rot % 2:
        w, h = h, w
    return w, h, solid


def _celdas(item):
    tam = _tamano(item['type'], item['rot'])
    if not tam:
        return []
    w, h, _solid = tam
    return [(item['x'] + dx, item['y'] + dy) for dy in range(h) for dx in range(w)]


def _cabe(puestos, item, suelo=SUELO):
    spec = CATALOG.get(item['type'])
    if not spec:
        return False
    _w, _h, solid = _tamano(item['type'], item['rot'])
    for x, y in _celdas(item):
        clase = suelo.get((x, y))
        if not clase or clase in ('door', 'threshold'):
            return False
        if solid and (x, y) == SPAWN:
            return False
        previo = puestos.get((x, y))
        if solid and previo:
            return False
        if not solid and previo == 'soft':
            return False
    return True


def sanitizar_casa(data):
    data = data if isinstance(data, dict) else {}
    pared = data.get('wall') if data.get('wall') in WALLS else DEFAULT_WALL
    suelo = data.get('floor') if data.get('floor') in FLOORS else DEFAULT_FLOOR
    puestos = {}
    items = []
    vistos = set()
    for raw in data.get('items') or []:
        if not isinstance(raw, dict) or raw.get('type') not in CATALOG or len(items) >= MAX_ITEMS:
            continue
        tipo = raw['type']
        estilos = STYLES.get(tipo) or ()
        estilo = raw.get('style') if raw.get('style') in estilos else (estilos[0] if estilos else '')
        try:
            x, y = int(raw.get('x')), int(raw.get('y'))
            rot = int(raw.get('rot') or 0) % 4
        except (TypeError, ValueError):
            continue
        base = ''.join(ch for ch in str(raw.get('id') or tipo) if ch.isalnum() or ch in '-_')[:24] or tipo
        ident = base
        if ident in vistos:
            ident = tipo + '-' + str(len(items))
        item = {'id': ident, 'type': tipo, 'x': x, 'y': y, 'rot': rot, 'style': estilo}
        if not _cabe(puestos, item):
            continue
        for celda in _celdas(item):
            clase = 'solid' if CATALOG[tipo][2] else 'soft'
            if clase == 'solid' or celda not in puestos:
                puestos[celda] = clase
        vistos.add(ident)
        items.append(item)
    return {'v': 2, 'wall': pared, 'floor': suelo, 'items': items}


def _nombre_mascota(raw, especie):
    texto = ''.join(ch for ch in str(raw or '') if ch.isalnum() or ch in ' áéíóúñÁÉÍÓÚÑ').strip()
    texto = ' '.join(texto.split())[:16]
    if texto:
        return texto
    return 'Michi' if especie == 'gato' else 'Firulais'


def sanitizar_mascotas(raw):
    if not isinstance(raw, list):
        return []
    salida = []
    vistos = set()
    for item in raw:
        if not isinstance(item, dict) or len(salida) >= MAX_MASCOTAS:
            continue
        especie = item.get('especie') if item.get('especie') in PELOS else item.get('species')
        if especie not in PELOS:
            continue
        color = item.get('color') if item.get('color') in PELOS[especie] else PELOS[especie][0]
        ident = ''.join(ch for ch in str(item.get('id') or '') if ch.isalnum() or ch == '-')[:24]
        if not ident or ident in vistos:
            ident = especie + '-' + str(len(salida) + 1)
        vistos.add(ident)
        salida.append({
            'id': ident,
            'especie': especie,
            'color': color,
            'nombre': _nombre_mascota(item.get('nombre') or item.get('name'), especie),
        })
    return salida


def normalizar_codigo(raw):
    texto = str(raw or '').strip().upper()
    if len(texto) == 4 and all(ch in ALFABETO for ch in texto):
        texto = 'CASA-' + texto
    if len(texto) != 9 or not texto.startswith('CASA-'):
        return ''
    cuerpo = texto[5:]
    if len(cuerpo) != 4 or any(ch not in ALFABETO for ch in cuerpo):
        return ''
    return texto


def nuevo_codigo(ocupados):
    for _ in range(32):
        codigo = 'CASA-' + ''.join(secrets.choice(ALFABETO) for _ in range(4))
        if codigo not in ocupados:
            return codigo
    raise HogarError('No hay un código libre ahora.')


def _caja_nueva():
    return {
        'role': '',
        'casa': None,
        'mascotas': [],
        'codigo': '',
        'visitas': True,
        'nft': dict(NFT_VACIO),
    }


def asegurar(doc, user):
    uid = str((user or {}).get('id') or '')
    if not uid:
        raise HogarError('Entra con tu cuenta para guardar la casa.', '401 Unauthorized')
    box = doc['por_cuenta'].get(uid)
    if not isinstance(box, dict):
        box = _caja_nueva()
        doc['por_cuenta'][uid] = box
    box['nft'] = dict(NFT_VACIO)
    box['visitas'] = bool(box.get('visitas', True))
    codigo = normalizar_codigo(box.get('codigo'))
    if not codigo or doc['por_codigo'].get(codigo) not in (None, uid):
        if codigo and doc['por_codigo'].get(codigo) == uid:
            pass
        else:
            codigo = nuevo_codigo(doc['por_codigo'])
    if doc['por_codigo'].get(codigo) not in (None, uid):
        codigo = nuevo_codigo(doc['por_codigo'])
    box['codigo'] = codigo
    doc['por_codigo'][codigo] = uid
    return box


def publico(box, user, propio):
    casa = box.get('casa') if isinstance(box.get('casa'), dict) else None
    vista = {
        'ok': True,
        'codigo': box.get('codigo') or '',
        'visitas': bool(box.get('visitas', True)),
        'casa': casa,
        'mascotas': list(box.get('mascotas') or []),
        'dueno': str((user or {}).get('name') or 'Alguien')[:16],
        'nft': dict(NFT_VACIO),
        'enlace': '/play/?casa=' + (box.get('codigo') or ''),
    }
    if propio:
        vista['role'] = box.get('role') or ''
        vista['propia'] = True
    return vista


def aplicar(doc, user, payload):
    payload = payload if isinstance(payload, dict) else {}
    box = asegurar(doc, user)
    if 'role' in payload or 'oficio' in payload:
        role = str(payload.get('role') if 'role' in payload else payload.get('oficio') or '')
        if role not in ROLES:
            raise HogarError('Ese oficio no existe.')
        box['role'] = role
    if 'casa' in payload:
        box['casa'] = sanitizar_casa(payload.get('casa'))
    if 'mascotas' in payload or 'pets' in payload:
        crudo = payload.get('mascotas') if 'mascotas' in payload else payload.get('pets')
        box['mascotas'] = sanitizar_mascotas(crudo)
    return publico(box, user, True)


def regenerar(doc, user):
    box = asegurar(doc, user)
    anterior = box.get('codigo')
    if anterior:
        doc['por_codigo'].pop(anterior, None)
    codigo = nuevo_codigo(doc['por_codigo'])
    box['codigo'] = codigo
    doc['por_codigo'][codigo] = str(user.get('id'))
    return publico(box, user, True)


def fijar_visitas(doc, user, abiertas):
    box = asegurar(doc, user)
    box['visitas'] = bool(abiertas)
    return publico(box, user, True)


def visitar(doc, codigo, nombre):
    limpio = normalizar_codigo(codigo)
    if not limpio:
        return None, 'El código no tiene la forma CASA-XXXX.'
    uid = doc['por_codigo'].get(limpio)
    box = doc['por_cuenta'].get(uid) if uid else None
    if not uid or not isinstance(box, dict) or box.get('codigo') != limpio:
        return None, 'No hay una casa con ese código.'
    if not box.get('visitas', True):
        return None, 'Esta casa no recibe visitas.'
    return publico(box, {'name': nombre or 'Alguien'}, False), None


def oficio_de(doc, user_id):
    box = (doc or {}).get('por_cuenta', {}).get(str(user_id or ''))
    role = box.get('role') if isinstance(box, dict) else ''
    return role if role in ROLES else ''


def olvidar(doc, user_id):
    uid = str(user_id or '')
    box = doc['por_cuenta'].pop(uid, None)
    if isinstance(box, dict) and box.get('codigo') and doc['por_codigo'].get(box['codigo']) == uid:
        doc['por_codigo'].pop(box['codigo'], None)


def dueno_de(doc, accounts, codigo):
    limpio = normalizar_codigo(codigo)
    uid = doc['por_codigo'].get(limpio)
    if not uid:
        return None
    for user in (accounts or {}).get('users') or []:
        if user.get('id') == uid:
            return user
    return {'id': uid, 'name': 'Alguien'}
