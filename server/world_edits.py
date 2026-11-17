# SPDX-License-Identifier: AGPL-3.0-or-later
"""Capa de ediciones del mundo. No toca el mapa base ni los guardados de cuentas.

LIFE_ENV=public (por defecto) escribe state/world-edits.json.
LIFE_ENV=preview escribe state/world-edits-preview.json.
"""
import copy
import json
import os
import re
import secrets
import time

SCHEMA = 1
PATH_STYLES = ('piedra', 'adoquin', 'carretera')
MATERIALS = ('grass', 'dirt', 'sand', 'stone', 'brick', 'asphalt', 'water')
PROP_TYPES = (
    'palma', 'guayacan', 'sombra', 'arbusto', 'flores', 'pasto',
    'roca', 'cerca', 'banca', 'farol', 'letrero', 'fuente', 'cafe', 'cacao',
)
EDIT_ROLES = ('admin', 'owner', 'dev', 'simon', 'staff')
SCALE_MIN = 0.25
SCALE_MAX = 4.0
DY_MIN = -12.0
DY_MAX = 12.0
COORD_MIN = -2000
COORD_MAX = 20000
CELL_LIMIT = 8000
PROP_LIMIT = 2000
OBJECT_LIMIT = 2000
DESIGN_LIMIT = 40
HISTORY_LIMIT = 24
NAME_LIMIT = 40
_HEX = re.compile(r'^#[0-9a-fA-F]{6}$')
_ID = re.compile(r'^[A-Za-z0-9_:\-]{1,64}$')


class EditError(Exception):
    def __init__(self, code, message):
        self.code = int(code)
        super().__init__(message)


def env_name(raw=None):
    """public o preview. Cualquier otro valor queda en public."""
    if raw is None:
        raw = os.environ.get('LIFE_ENV', 'public')
    value = str(raw or '').strip().lower()
    return 'preview' if value == 'preview' else 'public'


def storage_name(env=None):
    return 'world_edits_preview' if env_name(env) == 'preview' else 'world_edits'


def storage_filename(env=None):
    return 'world-edits-preview.json' if env_name(env) == 'preview' else 'world-edits.json'


def can_edit(user, role_of=None):
    """Administradores, el papel simon del dueño, o correos de ADMIN_USERS."""
    if not isinstance(user, dict):
        return False
    role = str(user.get('role') or '')
    if user.get('admin') or user.get('owner') or role in EDIT_ROLES:
        return True
    if role_of is not None:
        try:
            resolved = role_of(user)
        except TypeError:
            resolved = role_of(user, '')
        if resolved in ('admin', 'simon', 'owner', 'staff'):
            return True
    email = str(user.get('email') or '').strip().lower()
    allowed = {part.strip().lower() for part in os.environ.get('ADMIN_USERS', '').split(',') if part.strip()}
    return bool(email) and email in allowed


def empty_current():
    return {'paths': [], 'objects': [], 'props': [], 'terrain': [], 'surfaces': []}


def empty_doc(env=None):
    env = env_name(env)
    return {
        'schema': SCHEMA,
        'env': env,
        'version': 0,
        'updatedAt': 0,
        'updatedBy': '',
        'current': empty_current(),
        'designs': [],
        'history': [],
    }


def _num(value, lo, hi, fallback=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    if number != number or number in (float('inf'), float('-inf')):
        return float(fallback)
    return max(float(lo), min(float(hi), number))


def _cell(value, lo=0, hi=4096):
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    if number < lo or number > hi:
        return None
    return number


def _ident(value, fallback):
    text = str(value or '').strip()
    if _ID.match(text):
        return text
    return fallback


def _tint(value, fallback='#74875b'):
    text = str(value or '').strip()
    if _HEX.match(text):
        return text.lower()
    return fallback


def _name(value, fallback='Diseño'):
    text = re.sub(r'[\x00-\x1f<>]', '', str(value or '')).strip()
    text = text[:NAME_LIMIT]
    return text or fallback


def _limit(items, cap):
    return items[:cap]


def _reject_size(raw):
    if not isinstance(raw, dict):
        return
    pairs = (
        ('paths', CELL_LIMIT, 'caminos'),
        ('objects', OBJECT_LIMIT, 'objetos'),
        ('props', PROP_LIMIT, 'vegetación'),
        ('terrain', CELL_LIMIT, 'terreno'),
        ('surfaces', CELL_LIMIT, 'superficies'),
    )
    for key, cap, label in pairs:
        if isinstance(raw.get(key), list) and len(raw[key]) > cap:
            raise EditError(400, 'Demasiados elementos en ' + label + '.')


def normalize_current(raw):
    raw = raw if isinstance(raw, dict) else {}
    paths = []
    seen = set()
    for item in raw.get('paths') or []:
        if not isinstance(item, dict):
            continue
        x, z = _cell(item.get('x')), _cell(item.get('z'))
        style = str(item.get('style') or '')
        if x is None or z is None or style not in PATH_STYLES:
            continue
        key = (x, z)
        if key in seen:
            paths = [p for p in paths if (p['x'], p['z']) != key]
        seen.add(key)
        paths.append({'id': f'{x}:{z}', 'style': style, 'x': x, 'z': z})
    paths = _limit(paths, CELL_LIMIT)

    objects = []
    seen = set()
    for item in raw.get('objects') or []:
        if not isinstance(item, dict):
            continue
        ident = _ident(item.get('id'), '')
        if not ident or ident in seen:
            continue
        seen.add(ident)
        objects.append({
            'id': ident,
            'x': round(_num(item.get('x'), COORD_MIN, COORD_MAX), 3),
            'y': round(_num(item.get('y'), -80, 200), 3),
            'z': round(_num(item.get('z'), COORD_MIN, COORD_MAX), 3),
            'scale': round(_num(item.get('scale'), SCALE_MIN, SCALE_MAX, 1), 3),
            'rotY': round(_num(item.get('rotY'), -3600, 3600) % 360, 3),
            'deleted': bool(item.get('deleted')),
        })
    objects = _limit(objects, OBJECT_LIMIT)

    props = []
    seen = set()
    for item in raw.get('props') or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get('type') or '')
        if kind not in PROP_TYPES:
            continue
        ident = _ident(item.get('id'), 'p' + secrets.token_hex(3))
        if ident in seen:
            continue
        seen.add(ident)
        props.append({
            'id': ident,
            'type': kind,
            'x': round(_num(item.get('x'), COORD_MIN, COORD_MAX), 3),
            'y': round(_num(item.get('y'), -80, 200), 3),
            'z': round(_num(item.get('z'), COORD_MIN, COORD_MAX), 3),
            'scale': round(_num(item.get('scale'), SCALE_MIN, SCALE_MAX, 1), 3),
            'rotY': round(_num(item.get('rotY'), -3600, 3600) % 360, 3),
            'grounded': bool(item.get('grounded', True)),
        })
    props = _limit(props, PROP_LIMIT)

    terrain = []
    seen = set()
    for item in raw.get('terrain') or []:
        if not isinstance(item, dict):
            continue
        x, z = _cell(item.get('x')), _cell(item.get('z'))
        if x is None or z is None:
            continue
        key = (x, z)
        if key in seen:
            continue
        seen.add(key)
        dy = round(_num(item.get('dy'), DY_MIN, DY_MAX), 3)
        if abs(dy) < 0.001:
            continue
        terrain.append({'x': x, 'z': z, 'dy': dy})
    terrain = _limit(terrain, CELL_LIMIT)

    surfaces = []
    seen = set()
    for item in raw.get('surfaces') or []:
        if not isinstance(item, dict):
            continue
        x, z = _cell(item.get('x')), _cell(item.get('z'))
        material = str(item.get('material') or '')
        if x is None or z is None or material not in MATERIALS:
            continue
        key = (x, z)
        if key in seen:
            surfaces = [s for s in surfaces if (s['x'], s['z']) != key]
        seen.add(key)
        surfaces.append({
            'id': f'{x}:{z}',
            'x': x,
            'z': z,
            'material': material,
            'tint': _tint(item.get('tint')),
        })
    surfaces = _limit(surfaces, CELL_LIMIT)
    return {'paths': paths, 'objects': objects, 'props': props, 'terrain': terrain, 'surfaces': surfaces}


def _designs(raw):
    designs = []
    seen = set()
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        ident = _ident(item.get('id'), '')
        if not ident or ident in seen:
            continue
        seen.add(ident)
        designs.append({
            'id': ident,
            'name': _name(item.get('name')),
            'createdAt': int(_num(item.get('createdAt'), 0, 10**12)),
            'createdBy': _name(item.get('createdBy'), ''),
            'fromEnv': env_name(item.get('fromEnv')),
            'snapshot': normalize_current(item.get('snapshot')),
        })
    return designs[:DESIGN_LIMIT]


def _history(raw):
    history = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        history.append({
            'version': int(_num(item.get('version'), 0, 10**9)),
            'at': int(_num(item.get('at'), 0, 10**12)),
            'by': _name(item.get('by'), ''),
            'op': _name(item.get('op'), 'editar')[:24],
            'snapshot': normalize_current(item.get('snapshot')),
        })
    return history[-HISTORY_LIMIT:]


def normalize(raw, env=None):
    base = empty_doc(env)
    if not isinstance(raw, dict):
        return base
    base['version'] = int(_num(raw.get('version'), 0, 10**9))
    base['updatedAt'] = int(_num(raw.get('updatedAt'), 0, 10**12))
    base['updatedBy'] = _name(raw.get('updatedBy'), '')
    base['current'] = normalize_current(raw.get('current'))
    base['designs'] = _designs(raw.get('designs'))
    base['history'] = _history(raw.get('history'))
    base['env'] = env_name(env if env is not None else raw.get('env'))
    base['schema'] = SCHEMA
    return base


def dumps(doc):
    return json.dumps(normalize(doc), ensure_ascii=False, sort_keys=True)


def loads(text):
    return normalize(json.loads(text))


def seed_current(anchor=None):
    anchor = anchor or {}
    x = _cell(anchor.get('x'), 0, 4000)
    z = _cell(anchor.get('z'), 0, 4000)
    if x is None or z is None:
        raise EditError(400, 'El ancla de la muestra no cae en el mapa.')
    paths = []
    for i in range(6):
        paths.append({'id': f'{x + i}:{z}', 'style': 'piedra', 'x': x + i, 'z': z})
        paths.append({'id': f'{x + i}:{z + 2}', 'style': 'adoquin', 'x': x + i, 'z': z + 2})
        paths.append({'id': f'{x + i}:{z + 4}', 'style': 'carretera', 'x': x + i, 'z': z + 4})
    props = [
        {'id': 'muestra-palma', 'type': 'palma', 'x': (x + 1) * 2 + 1, 'y': 0, 'z': (z - 2) * 2 + 1,
         'scale': 1, 'rotY': 20, 'grounded': True},
        {'id': 'muestra-banca', 'type': 'banca', 'x': (x + 3) * 2 + 1, 'y': 0, 'z': (z + 1) * 2 + 1,
         'scale': 1, 'rotY': 90, 'grounded': True},
        {'id': 'muestra-cafe', 'type': 'cafe', 'x': (x + 5) * 2 + 1, 'y': 0, 'z': (z - 2) * 2 + 1,
         'scale': 1, 'rotY': 0, 'grounded': True},
    ]
    return normalize_current({'paths': paths, 'props': props, 'objects': [], 'terrain': [], 'surfaces': []})


def _actor(user):
    if not isinstance(user, dict):
        return 'admin'
    return _name(user.get('name') or user.get('wallet_name') or 'admin', 'admin')


def _commit(doc, current, user, now, op):
    history = list(doc['history'])
    if doc['version']:
        history.append({
            'version': doc['version'],
            'at': doc['updatedAt'],
            'by': doc['updatedBy'],
            'op': op,
            'snapshot': copy.deepcopy(doc['current']),
        })
    stored = normalize({
        **doc,
        'version': doc['version'] + 1,
        'updatedAt': int(now),
        'updatedBy': _actor(user),
        'current': current,
        'history': history[-HISTORY_LIMIT:],
    }, env=doc['env'])
    return stored


def _need_version(doc, message):
    if 'baseVersion' not in message or message.get('baseVersion') is None:
        return
    try:
        base = int(message.get('baseVersion'))
    except (TypeError, ValueError):
        raise EditError(400, 'La versión de base no es válida.')
    if base != doc['version']:
        raise EditError(409, 'El mundo cambió. Recarga antes de guardar.')


def _find_design(doc, ident):
    ident = _ident(ident, '')
    for item in doc['designs']:
        if item['id'] == ident:
            return item
    raise EditError(404, 'No está ese diseño.')


def public_designs(doc):
    return [{
        'id': item['id'], 'name': item['name'], 'createdAt': item['createdAt'],
        'createdBy': item['createdBy'], 'fromEnv': item['fromEnv'],
    } for item in doc.get('designs') or []]


def public_history(doc):
    return [{
        'version': item['version'], 'at': item['at'], 'by': item['by'], 'op': item['op'],
    } for item in doc.get('history') or []]


def packet(doc, user=None, role_of=None):
    doc = normalize(doc, env=doc.get('env') if isinstance(doc, dict) else None)
    return {
        'schema': SCHEMA,
        'env': doc['env'],
        'editor': can_edit(user, role_of=role_of),
        'version': doc['version'],
        'updatedAt': doc['updatedAt'],
        'updatedBy': doc['updatedBy'],
        'current': doc['current'],
        'designs': public_designs(doc),
        'history': public_history(doc),
    }


def export_package(doc, ident):
    item = _find_design(doc, ident)
    return {
        'kind': 'life-world-design',
        'schema': SCHEMA,
        'name': item['name'],
        'fromEnv': doc['env'],
        'snapshot': copy.deepcopy(item['snapshot']),
    }


def apply_request(doc, user, message, role_of=None, now=None):
    """Aplica una edición. code 403 si quien escribe no es administrador."""
    doc = normalize(doc, env=doc.get('env') if isinstance(doc, dict) else None)
    now = time.time() if now is None else float(now)
    message = message if isinstance(message, dict) else {}
    if not can_edit(user, role_of=role_of):
        return {
            'ok': False, 'code': 403, 'changed': False,
            'error': 'Sólo un administrador puede editar el mundo.',
            'doc': packet(doc, user, role_of=role_of),
        }
    op = str(message.get('op') or '')
    try:
        if op == 'export_design':
            package = export_package(doc, message.get('id'))
            return {'ok': True, 'code': 200, 'changed': False, 'package': package, 'doc': packet(doc, user, role_of=role_of), 'stored': doc}
        _need_version(doc, message)
        stored, extra = _mutate(doc, user, message, now)
    except EditError as exc:
        return {
            'ok': False, 'code': exc.code, 'changed': False, 'error': str(exc),
            'doc': packet(doc, user, role_of=role_of),
        }
    result = {
        'ok': True, 'code': 200, 'changed': True, 'stored': stored,
        'doc': packet(stored, user, role_of=role_of), 'error': '',
    }
    result.update(extra)
    return result


def _mutate(doc, user, message, now):
    op = str(message.get('op') or '')
    extra = {}
    if op == 'replace':
        _reject_size(message.get('current'))
        current = normalize_current(message.get('current'))
        return _commit(doc, current, user, now, 'guardar'), extra
    if op == 'save_design':
        raw_snapshot = message.get('snapshot') or doc['current']
        _reject_size(raw_snapshot)
        current = normalize_current(raw_snapshot)
        designs = list(doc['designs'])
        designs.append({
            'id': 'd' + secrets.token_hex(4),
            'name': _name(message.get('name')),
            'createdAt': int(now),
            'createdBy': _actor(user),
            'fromEnv': doc['env'],
            'snapshot': current,
        })
        if len(designs) > DESIGN_LIMIT:
            raise EditError(400, 'Demasiados diseños.')
        stored = normalize({**doc, 'designs': designs}, env=doc['env'])
        stored = _commit(stored, doc['current'], user, now, 'diseño')
        return stored, extra
    if op == 'apply_design':
        item = _find_design(doc, message.get('id'))
        return _commit(doc, item['snapshot'], user, now, 'aplicar'), extra
    if op == 'duplicate_design':
        item = _find_design(doc, message.get('id'))
        designs = list(doc['designs'])
        designs.append({
            'id': 'd' + secrets.token_hex(4),
            'name': _name(message.get('name') or (item['name'] + ' copia')),
            'createdAt': int(now),
            'createdBy': _actor(user),
            'fromEnv': item['fromEnv'],
            'snapshot': copy.deepcopy(item['snapshot']),
        })
        if len(designs) > DESIGN_LIMIT:
            raise EditError(400, 'Demasiados diseños.')
        stored = normalize({**doc, 'designs': designs}, env=doc['env'])
        return _commit(stored, doc['current'], user, now, 'duplicar'), extra
    if op == 'delete_design':
        ident = _ident(message.get('id'), '')
        designs = [item for item in doc['designs'] if item['id'] != ident]
        if len(designs) == len(doc['designs']):
            raise EditError(404, 'No está ese diseño.')
        stored = normalize({**doc, 'designs': designs}, env=doc['env'])
        return _commit(stored, doc['current'], user, now, 'borrar-diseño'), extra
    if op == 'import_design':
        if str(message.get('confirm') or '') != 'PROMOVER':
            raise EditError(400, 'Escribe PROMOVER para traer un diseño al mundo.')
        package = message.get('package') if isinstance(message.get('package'), dict) else {}
        if package.get('kind') not in (None, '', 'life-world-design'):
            raise EditError(400, 'Ese archivo no es un diseño de Saimon City.')
        raw_snapshot = package.get('snapshot') or package.get('current')
        _reject_size(raw_snapshot)
        snapshot = normalize_current(raw_snapshot)
        designs = list(doc['designs'])
        designs.append({
            'id': 'd' + secrets.token_hex(4),
            'name': _name(package.get('name') or message.get('name')),
            'createdAt': int(now),
            'createdBy': _actor(user),
            'fromEnv': env_name(package.get('fromEnv')),
            'snapshot': snapshot,
        })
        if len(designs) > DESIGN_LIMIT:
            raise EditError(400, 'Demasiados diseños.')
        stored = normalize({**doc, 'designs': designs}, env=doc['env'])
        current = snapshot if message.get('apply') else doc['current']
        return _commit(stored, current, user, now, 'importar'), extra
    if op == 'revert':
        if str(message.get('confirm') or '') != 'REVERTIR':
            raise EditError(400, 'Escribe REVERTIR para volver al mapa base.')
        return _commit(doc, empty_current(), user, now, 'revertir'), extra
    if op == 'rollback':
        try:
            version = int(message.get('version'))
        except (TypeError, ValueError):
            raise EditError(400, 'Falta el número de versión.')
        hit = next((item for item in doc['history'] if item['version'] == version), None)
        if not hit:
            raise EditError(404, 'Esa versión no está en el historial.')
        return _commit(doc, hit['snapshot'], user, now, 'rollback'), extra
    if op == 'reset_preview':
        if doc['env'] != 'preview':
            raise EditError(400, 'Restablecer sólo existe en la versión de muestras.')
        if str(message.get('confirm') or '') != 'RESTABLECER':
            raise EditError(400, 'Escribe RESTABLECER para vaciar las muestras.')
        return _commit(doc, empty_current(), user, now, 'restablecer'), extra
    if op == 'seed_preview':
        if doc['env'] != 'preview':
            raise EditError(400, 'Sembrar sólo existe en la versión de muestras.')
        return _commit(doc, seed_current(message.get('anchor')), user, now, 'sembrar'), extra
    raise EditError(400, 'Esa operación no existe.')
