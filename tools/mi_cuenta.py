# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lo que el jugador puede ver de su cuenta. No muestra claves ni crea monedas."""
import partida


PLACES = {
    'city': 'En el valle',
    'casa': 'En tu casa',
    'mine': 'En la mina',
    'banco': 'En el banco',
    'central': 'En el Banco Central',
}


def _minutes(rev, now_ms):
    try:
        stamp = int(rev or 0)
        now_ms = int(now_ms or 0)
    except (TypeError, ValueError):
        return ''
    if stamp < 10 ** 12 or now_ms < stamp:
        return ''
    mins = (now_ms - stamp) // 60000
    if mins < 1:
        return 'Guardado hace un momento'
    return 'Guardado hace %d min' % mins


def _place(saved):
    pos = saved.get('position') if isinstance(saved, dict) else None
    if not isinstance(pos, dict):
        return 'Sin lugar guardado'
    name = PLACES.get(pos.get('mapId'), 'En el valle')
    return '%s · %s, %s' % (name, pos.get('x'), pos.get('y'))


def _coins(econ, name):
    econ = econ if isinstance(econ, dict) else {}
    smh = int((econ.get('wallets') or {}).get(name) or 0)
    sph = int(((econ.get('plata') or {}).get('wallets') or {}).get(name) or 0)
    chis = int(((econ.get('simonchis') or {}).get('wallets') or {}).get(name) or 0)
    return {'simoncoinSmh': smh, 'simonplataSph': sph, 'simonchis': chis}


def _finca(accounts, name):
    box = (accounts or {}).get(name) or {}
    plots = box.get('plots') or {}
    crops = {}
    for plot in plots.values():
        if not isinstance(plot, dict):
            continue
        crop = str(plot.get('crop') or 'lote')
        crops[crop] = crops.get(crop, 0) + 1
    return crops


def _animals(user):
    rows = ((user.get('corral') or {}).get('animals') or []) if isinstance(user, dict) else []
    found = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        kind = str(row.get('species') or '')
        if not kind:
            continue
        found[kind] = found.get(kind, 0) + 1
    return found


def resumen(user, econ, finca_accounts, now_ms=0, vault_state=None):
    """Vista para el panel. No incluye contraseña, hash ni el identificador de Google."""
    user = user if isinstance(user, dict) else {}
    saved = partida.recall(user)
    name = str(user.get('wallet_name') or user.get('name') or '')
    import lugares
    import mundos
    import vault as vault_mod
    place = lugares.get(user.get('favorite_place'))
    coins = _coins(econ, name)
    bank = 0
    if isinstance(vault_state, dict):
        bank = vault_mod.smh_of((vault_state.get('accounts') or {}).get(name))
    coins['bankSmh'] = int(bank)
    coins['totalSmh'] = int(coins['simoncoinSmh']) + int(bank)
    return {
        'nick': name[:16],
        'google': bool((user.get('providers') or {}).get('google')),
        'place': _place(saved),
        'saved': _minutes(saved.get('rev'), now_ms),
        'inventory': list(saved.get('inv') or [])[:12],
        'coins': coins,
        'crops': _finca(finca_accounts, name),
        'animals': _animals(user),
        'favoritePlace': (place or {}).get('name') or '',
        'favoriteWorld': mundos.normalize(user.get('favorite_world')) or '',
    }
