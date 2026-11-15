# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pelaje del caballo en la cuenta. Bayo por defecto; gris y negro son variantes."""

COATS = ('bay', 'grey', 'black')
DEFAULT = 'bay'
ALIASES = {'bayo': 'bay', 'gris': 'grey', 'negro': 'black'}


class CoatError(Exception):
    pass


def normalize(coat):
    key = ALIASES.get(str(coat or '').strip().lower(), str(coat or '').strip().lower())
    return key if key in COATS else ''


def view(user):
    raw = user.get('caballo') if isinstance(user, dict) else None
    coat = normalize(raw.get('coat')) if isinstance(raw, dict) else ''
    return {'coat': coat or DEFAULT}


def apply(user, coat):
    key = normalize(coat)
    if not key:
        raise CoatError('Ese pelaje no existe. Elige bayo, gris o negro.')
    user['caballo'] = {'coat': key}
    return view(user)
