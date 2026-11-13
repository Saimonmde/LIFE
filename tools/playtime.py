# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tiempo jugado por jugador. El servidor es la autoridad.

Sólo cuenta una sesión activa: un latido cada ~30 s. Si el hueco supera el
corte de inactividad, ese tramo no se suma (una pestaña abierta no acumula
para siempre). state/players.json vive en el disco del proceso. En Render ese
disco se pierde al redeploy.
"""
import json
import os
import time

HEARTBEAT = 30
IDLE_CUTOFF = 90


def empty():
    return {'players': {}}


def load(path):
    if not os.path.isfile(path):
        state = empty()
        save(path, state)
        return state
    with open(path, encoding='utf-8') as handle:
        state = json.load(handle)
    state.setdefault('players', {})
    return state


def save(path, state):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(state, handle, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def ensure(state, name, now=None):
    now = int(now if now is not None else time.time())
    box = state.setdefault('players', {}).setdefault(name, {
        'createdAt': now,
        'playtime': 0,
        'lastBeat': now,
    })
    box.setdefault('createdAt', now)
    box.setdefault('playtime', 0)
    box.setdefault('lastBeat', now)
    return box


def beat(state, name, active=True, now=None):
    """Suma el tramo desde el latido anterior si la sesión sigue activa."""
    now = int(now if now is not None else time.time())
    box = ensure(state, name, now)
    gap = now - int(box.get('lastBeat') or now)
    added = 0
    if active and 0 < gap <= IDLE_CUTOFF:
        added = gap
        box['playtime'] = int(box.get('playtime') or 0) + added
    box['lastBeat'] = now
    return public(box, added)


def public(box, added=0):
    return {
        'createdAt': int(box.get('createdAt') or 0),
        'playtime': int(box.get('playtime') or 0),
        'added': int(added),
        'heartbeat': HEARTBEAT,
        'idleCutoff': IDLE_CUTOFF,
        'ephemeral': True,
    }
