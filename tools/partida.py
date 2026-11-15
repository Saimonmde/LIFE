# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lo que el jugador puede guardar, sin saldos y sin la finca.

Las tres monedas y el Libro Mayor viven en el libro del servidor.
La finca vive en su propio almacén. Esta partida no los escribe.
"""
import re

import caballo_cuenta
import casa_cuenta
import mascotas
import muebles

_ITEM = re.compile(r'^[a-z0-9_]{1,32}$')
_SKILL = re.compile(r'^[a-z0-9_]{1,24}$')
_PANEL = re.compile(r'^[A-Za-z0-9_-]{1,40}$')
BANNED_ITEMS = {
    'smc', 'smp', 'smh', 'sph', 'simoncoin', 'simonplata', 'simonchis',
    'sai', 'plata', 'cobre_moneda',
}
MAPS = {'city', 'casa', 'mine', 'banco', 'central'}
DIRS = {'up', 'down', 'left', 'right'}
HUD_KEYS = (
    'lifeinc.hud.layout.desktop.horizontal',
    'lifeinc.hud.layout.desktop.vertical',
    'lifeinc.hud.layout.movil.horizontal',
    'lifeinc.hud.layout.movil.vertical',
)


def _inv(raw):
    if not isinstance(raw, list):
        return []
    found = []
    for row in raw[:40]:
        if not isinstance(row, dict):
            continue
        item = str(row.get('item') or '')
        if not _ITEM.match(item) or item in BANNED_ITEMS:
            continue
        try:
            qty = int(row.get('qty') or 0)
        except (TypeError, ValueError):
            continue
        if qty < 1:
            continue
        found.append({'item': item, 'qty': min(qty, 999)})
    return found


def _xp(raw):
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key, value in list(raw.items())[:40]:
        if not _SKILL.match(str(key)):
            continue
        try:
            xp = int(value)
        except (TypeError, ValueError):
            continue
        if xp < 0:
            continue
        out[str(key)] = min(xp, 1_000_000)
    return out


def _quest(raw):
    if not isinstance(raw, dict):
        return {}
    steps = {}
    if isinstance(raw.get('steps'), dict):
        for key, value in list(raw['steps'].items())[:40]:
            if not _SKILL.match(str(key)):
                continue
            try:
                steps[str(key)] = max(0, min(999, int(value)))
            except (TypeError, ValueError):
                continue
    try:
        stage = max(0, min(99, int(raw.get('stage') or 0)))
    except (TypeError, ValueError):
        stage = 0
    return {
        'stage': stage,
        'steps': steps,
        'done': bool(raw.get('done')),
        'turnedIn': bool(raw.get('turnedIn')),
    }


def _libro(raw):
    if not isinstance(raw, dict):
        return {}
    steps = {}
    if isinstance(raw.get('steps'), dict):
        for key, value in list(raw['steps'].items())[:20]:
            if not _SKILL.match(str(key)):
                continue
            try:
                steps[str(key)] = max(0, min(999, int(value)))
            except (TypeError, ValueError):
                continue
    return {
        'started': bool(raw.get('started')),
        'done': bool(raw.get('done')),
        'turnedIn': bool(raw.get('turnedIn')),
        'steps': steps,
    }


def _studied(raw):
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key, value in list(raw.items())[:40]:
        if _SKILL.match(str(key)) and value:
            out[str(key)] = True
    return out


def _num(value, lo, hi, default):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:
        return default
    return max(lo, min(hi, number))


def _position(raw):
    if not isinstance(raw, dict):
        return None
    map_id = str(raw.get('mapId') or '')
    if map_id not in MAPS:
        return None
    direction = raw.get('dir') if raw.get('dir') in DIRS else 'down'
    return {
        'mapId': map_id,
        'x': round(_num(raw.get('x'), 0, 400, 0), 2),
        'y': round(_num(raw.get('y'), 0, 400, 0), 2),
        'dir': direction,
    }


def _hud(raw):
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key in HUD_KEYS:
        panels = raw.get(key)
        if not isinstance(panels, dict):
            continue
        clean = {}
        for pid, entry in list(panels.items())[:40]:
            if not isinstance(entry, dict) or not _PANEL.match(str(pid)):
                continue
            item = {}
            if 'x' in entry:
                item['x'] = round(_num(entry.get('x'), -2000, 4000, 0), 2)
            if 'y' in entry:
                item['y'] = round(_num(entry.get('y'), -2000, 4000, 0), 2)
            if 'scale' in entry:
                item['scale'] = round(_num(entry.get('scale'), 0.55, 1.8, 1), 2)
            if entry.get('minimized'):
                item['minimized'] = True
            if entry.get('closed'):
                item['closed'] = True
            clean[str(pid)] = item
        out[key] = clean
    if 'pantallaLimpia' in raw:
        out['pantallaLimpia'] = bool(raw.get('pantallaLimpia'))
    return out


def _horse(raw):
    if not isinstance(raw, dict):
        return None
    coat = caballo_cuenta.normalize(raw.get('coat'))
    try:
        x = float(raw.get('x'))
        y = float(raw.get('y'))
    except (TypeError, ValueError):
        return {'coat': coat} if coat else None
    if x != x or y != y:
        return {'coat': coat} if coat else None
    direction = raw.get('dir') if raw.get('dir') in DIRS else 'down'
    found = {
        'x': round(max(0, min(400, x)), 2),
        'y': round(max(0, min(400, y)), 2),
        'dir': direction,
    }
    if coat:
        found['coat'] = coat
    return found


def pack(raw):
    """Deja sólo lo que se puede volver a cargar. Ignora monedas y finca."""
    raw = raw if isinstance(raw, dict) else {}
    data = {
        'v': 1,
        'inv': _inv(raw.get('inv')),
        'xp': _xp(raw.get('xp')),
        'quest': _quest(raw.get('quest')),
        'libro': _libro(raw.get('libro')),
        'studied': _studied(raw.get('studied')),
        'hp': round(_num(raw.get('hp'), 0, 100, 100), 2),
        'energy': round(_num(raw.get('energy'), 0, 100, 100), 2),
        'hud': _hud(raw.get('hud')),
    }
    position = _position(raw.get('position'))
    if position:
        data['position'] = position
    if raw.get('layout') is not None:
        data['layout'] = muebles.sanitize(raw.get('layout'))
    if raw.get('pet') not in (None, '', {}):
        pet = mascotas.validate(raw.get('pet'))
        if pet:
            data['pet'] = pet
    coat = caballo_cuenta.normalize(raw.get('coat'))
    horse = _horse(raw.get('horse'))
    if horse and horse.get('coat'):
        coat = horse['coat']
    if coat:
        data['coat'] = coat
    if horse:
        if coat and not horse.get('coat'):
            horse['coat'] = coat
        data['horse'] = horse
    return data


def remember(user, raw):
    """Guarda en la cuenta. No crea monedas ni toca la finca."""
    data = pack(raw)
    user['partida'] = data
    casa_payload = {}
    if data.get('layout'):
        casa_payload['layout'] = data['layout']
    if data.get('pet'):
        casa_payload['pet'] = data['pet']
    if casa_payload:
        casa_cuenta.apply(user, casa_payload)
    if data.get('coat'):
        caballo_cuenta.apply(user, data['coat'])
    return recall(user)


def recall(user):
    saved = pack(user.get('partida') if isinstance(user, dict) else {})
    casa = casa_cuenta.view(user if isinstance(user, dict) else {})
    horse = caballo_cuenta.view(user if isinstance(user, dict) else {})
    if not saved.get('layout') and casa.get('layout'):
        saved['layout'] = casa['layout']
    if not saved.get('pet') and casa.get('pet'):
        saved['pet'] = casa['pet']
    if not saved.get('coat'):
        saved['coat'] = horse.get('coat') or 'bay'
    saved['saved'] = isinstance(user, dict) and isinstance(user.get('partida'), dict)
    nick = ''
    if isinstance(user, dict):
        nick = str(user.get('wallet_name') or user.get('name') or '')[:16]
    saved['nick'] = nick
    return saved
