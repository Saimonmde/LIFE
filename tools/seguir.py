# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seguir a otra persona. No mueve monedas ni crea saldo."""

PACES = ('quieto', 'caminando', 'corriendo', 'caballo', 'casa')
LABELS = {
    'quieto': 'quieto',
    'caminando': 'caminando',
    'corriendo': 'corriendo',
    'caballo': 'a caballo',
    'casa': 'en casa',
}


def allow(user):
    """Si la cuenta no dice lo contrario, se puede seguir."""
    if not isinstance(user, dict):
        return True
    return user.get('followable', True) is not False


def pace_of(raw, zone, moving):
    if zone == 'casa':
        return 'casa'
    if raw in PACES and raw != 'casa':
        return raw
    return 'caminando' if moving else 'quieto'


def label(pace):
    return LABELS.get(pace, 'caminando')


def pedir(target_user, online, same):
    """Decide si el aviso puede salir. No toca saldos."""
    if not online or not same:
        return {'ok': False, 'reason': 'Esa persona ya no está en línea.'}
    if not allow(target_user):
        return {'ok': False, 'reason': 'Esa persona prefiere no ser seguida.'}
    return {'ok': True, 'reason': ''}
