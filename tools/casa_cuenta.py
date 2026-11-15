# SPDX-License-Identifier: AGPL-3.0-or-later
"""La casa vive en la cuenta: municipio, muebles, objetos y mascota.

El mismo documento se refleja en el almacén de vida (plano y mascota) para que
el juego que ya lee ese almacén no tenga otra copia distinta. Postgres entra
por tools/persist.py cuando la cuenta se guarda.
"""
import re

import hogar
import mascotas
import muebles

_ITEM = re.compile(r'^[a-z0-9_]{1,32}$')


class CasaError(Exception):
    pass


def blank():
    return {'municipio': '', 'layout': None, 'items': [], 'pet': None, 'migrated': False}


def _items(raw):
    if isinstance(raw, dict):
        raw = [{'item': key, 'qty': value} for key, value in raw.items()]
    if not isinstance(raw, list):
        return []
    found = []
    for row in raw[:40]:
        if not isinstance(row, dict):
            continue
        item = str(row.get('item') or '')
        if not _ITEM.match(item):
            continue
        try:
            qty = int(row.get('qty') or 0)
        except (TypeError, ValueError):
            continue
        if qty < 1:
            continue
        found.append({'item': item, 'qty': min(qty, 999)})
    return found


def view(user):
    raw = user.get('casa') if isinstance(user, dict) and isinstance(user.get('casa'), dict) else {}
    municipio = ''
    if isinstance(user, dict):
        municipio = user.get('municipio') or raw.get('municipio') or ''
    layout = raw.get('layout') if isinstance(raw.get('layout'), dict) else None
    pet = raw.get('pet') if isinstance(raw.get('pet'), dict) else None
    return {
        'municipio': municipio,
        'layout': layout,
        'items': _items(raw.get('items')),
        'pet': pet,
        'migrated': bool(raw.get('migrated')),
    }


def apply(user, payload, migrate=False):
    """Guarda lo que venga. La migración local sólo corre una vez."""
    payload = payload if isinstance(payload, dict) else {}
    current = view(user)
    if migrate and current['migrated']:
        return current
    casa = {
        'municipio': current['municipio'],
        'layout': current['layout'],
        'items': current['items'],
        'pet': current['pet'],
        'migrated': current['migrated'],
    }
    if payload.get('municipio'):
        key = str(payload.get('municipio') or '').strip().lower()
        if key not in hogar.ORDEN:
            raise CasaError('Ese municipio no está en el Valle de Aburrá.')
        casa['municipio'] = key
        user['municipio'] = key
    if payload.get('layout') is not None:
        casa['layout'] = muebles.sanitize(payload.get('layout'))
    if 'items' in payload:
        casa['items'] = _items(payload.get('items'))
    if 'pet' in payload and payload.get('pet') not in (None, '', {}):
        pet = mascotas.validate(payload.get('pet'))
        if not pet:
            if migrate:
                pet = None
            else:
                raise CasaError('Esa mascota no está en el catálogo.')
        if pet:
            casa['pet'] = pet
    elif 'pet' in payload and not migrate:
        casa['pet'] = None
    if migrate:
        casa['migrated'] = True
    user['casa'] = casa
    if casa['municipio']:
        user['municipio'] = casa['municipio']
    return view(user)


def mirror(state, key, user):
    """Copia el plano y la mascota de la cuenta al almacén que ya usa el juego."""
    casa = view(user)
    if not key:
        return casa
    state.setdefault('homes', {})
    state.setdefault('pets', {})
    if casa['layout']:
        state['homes'][key] = casa['layout']
    if casa['pet']:
        state['pets'][key] = casa['pet']
    return casa


def absorb(user, state, key):
    """Si la vida ya tenía mascota o plano, entran en la cuenta. Y al revés."""
    changed = False
    casa = dict(user.get('casa') or {})
    pet = (state.get('pets') or {}).get(key) if key else None
    home = (state.get('homes') or {}).get(key) if key else None
    if isinstance(pet, dict) and not isinstance(casa.get('pet'), dict):
        casa['pet'] = pet
        changed = True
    if isinstance(home, dict) and not isinstance(casa.get('layout'), dict):
        casa['layout'] = home
        changed = True
    if changed:
        user['casa'] = casa
    if isinstance(casa.get('pet'), dict) and key and not isinstance(pet, dict):
        state.setdefault('pets', {})[key] = casa['pet']
        changed = True
    if isinstance(casa.get('layout'), dict) and key and not isinstance(home, dict):
        state.setdefault('homes', {})[key] = casa['layout']
        changed = True
    return changed
