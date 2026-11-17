# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lo que el jugador puede ver de su cuenta. No muestra claves ni crea monedas."""
import json
import os

import partida

_NOMBRES = None
_EXTRAS = {
    'mineral_oro': 'Mineral de oro',
    'moneda_oro': 'Moneda de oro',
    'moneda_plata': 'Moneda de plata',
    'moneda_cobre': 'Moneda de cobre',
    'lingote_oro': 'Lingote de oro',
    'lingote_plata': 'Lingote de plata',
    'lingote_cobre': 'Lingote de cobre',
    'cafe_cereza': 'Café cereza',
    'cacao_baba': 'Cacao en baba',
    'cafe_seed': 'Semilla de café',
    'cacao_seed': 'Semilla de cacao',
    'piel_puma': 'Piel de puma',
}


def nombre_de(item):
    """Nombre que se lee en Mi cuenta. El id interno no sale si ya tiene nombre."""
    global _NOMBRES
    if _NOMBRES is None:
        found = dict(_EXTRAS)
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'el-jardin.json')
        try:
            with open(path, encoding='utf-8') as handle:
                catalog = json.load(handle).get('items') or {}
        except (OSError, ValueError):
            catalog = {}
        for key, row in catalog.items():
            if isinstance(row, dict) and row.get('name'):
                found.setdefault(str(key), str(row['name']))
        _NOMBRES = found
    text = str(item or '')
    if text in _NOMBRES:
        return _NOMBRES[text]
    return text.replace('_', ' ')


PLACES = {
    'city': 'En el valle',
    'casa': 'En tu casa',
    'mine': 'En la mina',
    'mina2': 'En la Mina de La Ladera',
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


def _live_inventory(user, econ, vault_state, saved, finca_accounts, name):
    """La mochila guardada en el aparato no pisa lo que el servidor ya movió."""
    saved = [dict(row) for row in (saved or []) if isinstance(row, dict)]
    live = {}
    account = str((user or {}).get('id') or '')
    crudo_row = ((econ or {}).get('crudo') or {}).get(account) if account else None
    if isinstance(crudo_row, dict):
        import crudo
        for item in crudo.CAPS:
            live[item] = int(crudo.nuggets(econ, account, item))
    if isinstance(vault_state, dict) and name:
        import purses
        for item, qty in purses.inventory(vault_state, name).items():
            live[item] = int(qty or 0)
        box = (vault_state.get('accounts') or {}).get(name) or {}
        for item, qty in (box.get('items') or {}).items():
            extra = int(qty or 0)
            if extra > 0:
                live[item] = int(live.get(item) or 0) + extra
    goods = ((finca_accounts or {}).get(name) or {}).get('goods') or {}
    for item, qty in goods.items():
        extra = int(qty or 0)
        if extra > 0:
            live[item] = int(live.get(item) or 0) + extra
    if not live:
        return [
            {'item': row.get('item'), 'qty': int(row.get('qty') or 0), 'nombre': nombre_de(row.get('item'))}
            for row in saved[:12] if isinstance(row, dict)
        ]
    rows = []
    seen = set()
    for row in saved:
        item = row.get('item')
        if item in live:
            seen.add(item)
            if live[item] > 0:
                rows.append({'item': item, 'qty': live[item], 'nombre': nombre_de(item)})
        else:
            rows.append({'item': item, 'qty': int(row.get('qty') or 0), 'nombre': nombre_de(item)})
    for item, qty in live.items():
        if item not in seen and int(qty) > 0:
            rows.append({'item': item, 'qty': int(qty), 'nombre': nombre_de(item)})
    return [row for row in rows if int(row.get('qty') or 0) > 0][:24]


def resumen(user, econ, finca_accounts, now_ms=0, vault_state=None):
    """Vista para el panel. No incluye contraseña, hash ni el identificador de Google."""
    user = user if isinstance(user, dict) else {}
    saved = partida.recall(user)
    import billetera
    name = billetera.elegir(econ, vault_state, user, user.get('wallet_name') or user.get('name') or '')
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
        'nick': str(user.get('wallet_name') or user.get('name') or name)[:16],
        'billetera': name,
        'correo': billetera.correo_corto(user.get('email')),
        'google': bool((user.get('providers') or {}).get('google')),
        'place': _place(saved),
        'saved': _minutes(saved.get('rev'), now_ms),
        'inventory': _live_inventory(user, econ, vault_state, saved.get('inv') or [], finca_accounts, name),
        'enVivo': True,
        'coins': coins,
        'crops': _finca(finca_accounts, name),
        'animals': _animals(user),
        'favoritePlace': (place or {}).get('name') or '',
        'favoriteWorld': mundos.normalize(user.get('favorite_world')) or '',
    }
