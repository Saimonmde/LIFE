# SPDX-License-Identifier: AGPL-3.0-or-later
"""Casa del jugador: municipio de sur a norte y casilla donde aparece.

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
    import lugares
    fav = lugares.spot((user or {}).get('favorite_place'))
    if fav and walkable(fav[0], fav[1]):
        return float(fav[0]), float(fav[1])
    spot = stand((user or {}).get('municipio'))
    if spot and walkable(spot[0], spot[1]):
        return float(spot[0]), float(spot[1])
    return None
