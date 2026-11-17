# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mueve objetos entre la mochila y el depósito de esa misma cuenta.

El baúl de la casa, el de la Casa bancaria y el de la mina leen este
depósito. No hay una copia por lugar. Un mismo pase no se aplica dos veces.
"""
import time

import economy
import purses
import vault

# El café y el cacao viven en la finca. El baúl no los copia a otro sitio.
MIRROR = {'bolsa_cafe': 'cafe', 'bolsa_cacao': 'cacao'}
MINERAL = {
    'mineral_oro': 'Oro',
    'mineral_plata': 'Plata',
    'mineral_cobre': 'Cobre',
    'pepita_oro': 'Pepita de oro',
    'piedra': 'Piedra',
    'mineral_piedra': 'Piedra',
}
RECURSO = {
    'madera': 'Madera',
    'bolsa_cafe': 'Café',
    'bolsa_cacao': 'Cacao',
    'carne': 'Carne',
    'piel': 'Piel',
    'pluma': 'Pluma',
    'mango': 'Mango',
    'banano': 'Banano',
    'coco': 'Coco',
    'manzana': 'Manzana',
    'pera': 'Pera',
    'naranja': 'Naranja',
    'trucha': 'Trucha',
    'bocachico': 'Bocachico',
    'mojarra': 'Mojarra',
}


def mover(state, name, op, item, qty, token='', now=None):
    name = str(name or '')
    item = str(item or '')[:32]
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        qty = 0
    now = time.time() if now is None else float(now)
    if item in MIRROR:
        return {'ok': False, 'reason': 'Ese bulto se guarda con la finca, sin copiarlo.', 'qty': 0}
    if not name or not item or qty < 1 or qty > 999 or op not in ('deposit', 'withdraw'):
        return {'ok': False, 'reason': 'Nada que mover.', 'qty': 0}
    box = vault.account(state, name)
    ops = box.setdefault('ops', [])
    token = str(token or '')[:48]
    if token and token in ops:
        return {'ok': True, 'dup': True, 'op': op, 'item': item, 'qty': 0, 'account': vault.public_account(box)}
    last = box.get('lastMove') or {}
    sig = '%s:%s:%s' % (op, item, qty)
    if last.get('sig') == sig and now - float(last.get('at') or 0) < 0.45:
        return {'ok': True, 'dup': True, 'op': op, 'item': item, 'qty': 0, 'account': vault.public_account(box)}
    if op == 'deposit':
        if not purses.debit(state, name, item, qty):
            return {'ok': False, 'reason': 'No llevas esa cantidad.', 'qty': 0}
        vault.add_item(box, item, qty)
    else:
        if not vault.take_item(box, item, qty):
            return {'ok': False, 'reason': 'El depósito no tiene esa cantidad.', 'qty': 0}
        before = purses.count(state, name, item)
        after = purses.credit(state, name, item, qty)
        if after != before + qty:
            vault.add_item(box, item, qty)
            return {'ok': False, 'reason': 'La mochila no acepta más.', 'qty': 0}
    if token:
        ops.append(token)
        del ops[:-32]
    box['lastMove'] = {'sig': sig, 'at': now}
    log = box.setdefault('log', [])
    log.append({'op': op, 'item': item, 'qty': qty, 'at': int(now)})
    del log[:-40]
    return {'ok': True, 'dup': False, 'op': op, 'item': item, 'qty': qty, 'account': vault.public_account(box)}


def _now(now):
    return time.time() if now is None else float(now)


def _seen(box, token, sig, now):
    ops = box.setdefault('ops', [])
    token = str(token or '')[:48]
    if token and token in ops:
        return token, True
    last = box.get('lastMove') or {}
    if last.get('sig') == sig and now - float(last.get('at') or 0) < 0.45:
        return token, True
    return token, False


def _remember(box, token, sig, now, rows):
    if token:
        ops = box.setdefault('ops', [])
        ops.append(token)
        del ops[:-32]
    box['lastMove'] = {'sig': sig, 'at': now}
    log = box.setdefault('log', [])
    for row in rows:
        log.append({'op': row['op'], 'item': row['item'], 'qty': row['qty'], 'at': int(now)})
    del log[:-40]


def _all(qty):
    return qty in (None, 'all', 'todo', '*')


def _take_qty(have, qty):
    have = int(have or 0)
    if _all(qty):
        return have
    try:
        asked = int(qty)
    except (TypeError, ValueError):
        return 0
    if asked < 1 or asked > have:
        return 0
    return asked


def _plan(state, name, op, item, qty):
    box = vault.account(state, name)
    if item:
        if op == 'deposit':
            have = purses.count(state, name, item)
        else:
            have = int((box.get('items') or {}).get(item) or 0)
        take = _take_qty(have, qty)
        return {} if take < 1 else {item: take}
    source = purses.inventory(state, name) if op == 'deposit' else dict(box.get('items') or {})
    found = {}
    for key, have in source.items():
        if key in MIRROR:
            continue
        have = int(have or 0)
        if have > 0:
            found[str(key)] = have
    return found


def _undo(state, name, box, op, moved):
    for row in reversed(moved):
        key, n = row['item'], row['qty']
        if op == 'deposit':
            if vault.take_item(box, key, n):
                purses.credit(state, name, key, n)
        else:
            if purses.debit(state, name, key, n):
                vault.add_item(box, key, n)


def mover_lote(state, name, op, item='', qty=1, token='', now=None):
    """Mueve lo que ya está. qty 'all' usa la cantidad real. No crea objetos."""
    import mochila
    name = str(name or '')
    item = str(item or '')[:32]
    now = _now(now)
    if not name or op not in ('deposit', 'withdraw'):
        return {'ok': False, 'reason': 'Nada que mover.', 'moved': []}
    if item in MIRROR:
        return {'ok': False, 'reason': 'Ese bulto se guarda con la finca, sin copiarlo.', 'moved': []}
    box = vault.account(state, name)
    sig = '%s:%s:%s' % (op, item or '*', 'all' if _all(qty) else qty)
    token, dup = _seen(box, token, sig, now)
    if dup:
        return {'ok': True, 'dup': True, 'moved': [], 'account': vault.public_account(box)}
    plan = _plan(state, name, op, item, qty)
    if not plan:
        return {'ok': False, 'reason': 'No hay esa cantidad.', 'moved': []}
    if op == 'withdraw':
        projected = purses.inventory(state, name)
        for key, n in plan.items():
            if not mochila.fits(projected, key, n):
                return {'ok': False, 'reason': mochila.FULL, 'moved': []}
            projected[key] = int(projected.get(key) or 0) + n
    moved = []
    for key, n in plan.items():
        if op == 'deposit':
            if not purses.debit(state, name, key, n):
                _undo(state, name, box, op, moved)
                return {'ok': False, 'reason': 'No llevas esa cantidad.', 'moved': []}
            vault.add_item(box, key, n)
        else:
            if not vault.take_item(box, key, n):
                _undo(state, name, box, op, moved)
                return {'ok': False, 'reason': 'El depósito no tiene esa cantidad.', 'moved': []}
            before = purses.count(state, name, key)
            after = purses.credit(state, name, key, n)
            if after != before + n:
                vault.add_item(box, key, n)
                _undo(state, name, box, op, moved)
                return {'ok': False, 'reason': mochila.FULL, 'moved': []}
        moved.append({'op': op, 'item': key, 'qty': n})
    _remember(box, token, sig, now, moved)
    return {'ok': True, 'dup': False, 'moved': moved, 'account': vault.public_account(box)}


def _units(amount):
    """Lee SMC con el lector que ya existe. 'all' lo decide quien llama."""
    if _all(amount):
        return None
    if isinstance(amount, str):
        text = amount.strip()
        if not text or text.lower() in ('all', 'todo', '*'):
            return None
        return economy.parse_amount(text)
    if isinstance(amount, bool) or amount is None:
        return 0
    if isinstance(amount, int):
        return economy.smc_to_smh(amount)
    if isinstance(amount, float):
        return economy.parse_amount(format(amount, 'f'))
    return economy.parse_amount(str(amount))


def mover_smc(econ, state, name, op, amount, token='', now=None):
    """Pasa SMC que ya existen. No acuña y no cambia el total de esa cuenta."""
    name = str(name or '')
    now = _now(now)
    econ = econ if isinstance(econ, dict) else {}
    if not name or op not in ('deposit', 'withdraw'):
        return {'ok': False, 'reason': 'Nada que mover.', 'units': 0}
    box = vault.account(state, name)
    wallets = econ.setdefault('wallets', {})
    wallets.setdefault(name, 0)
    wallet = int(wallets.get(name) or 0)
    chest = vault.smh_of(box)
    before = wallet + chest
    mined = econ.get('minedSmh')
    try:
        units = _units(amount)
    except economy.AmountError:
        return {'ok': False, 'reason': 'Monto no válido. Ejemplo: 1 o 1,5.', 'units': 0}
    if units is None:
        units = wallet if op == 'deposit' else chest
    if units < 1:
        return {'ok': False, 'reason': 'Nada que mover.', 'units': 0}
    sig = 'smc:%s:%s' % (op, units)
    token, dup = _seen(box, token, sig, now)
    if dup:
        return {'ok': True, 'dup': True, 'units': 0, 'account': vault.public_account(box)}
    if op == 'deposit':
        if wallet < units or not economy.debit(econ, name, units):
            return {'ok': False, 'reason': 'No hay tantas SMC en la billetera.', 'units': 0}
        vault.add_smc(box, units)
    else:
        if chest < units or wallet + units > economy.MAX_SMH:
            return {'ok': False, 'reason': 'Pasaría el tope de 21.000.000 SMC.' if chest >= units else 'El baúl no tiene tantas SMC.', 'units': 0}
        if not vault.take_smc(box, units):
            return {'ok': False, 'reason': 'El baúl no tiene tantas SMC.', 'units': 0}
        economy.credit(econ, name, units)
    after = int(econ['wallets'].get(name) or 0) + vault.smh_of(box)
    if after != before or econ.get('minedSmh') != mined:
        if op == 'deposit':
            if vault.take_smc(box, units):
                economy.credit(econ, name, units)
        elif vault.add_smc(box, units) or True:
            economy.debit(econ, name, units)
        return {'ok': False, 'reason': 'No se movió nada.', 'units': 0}
    _remember(box, token, sig, now, [{'op': op, 'item': 'smc', 'qty': units}])
    return {'ok': True, 'dup': False, 'op': op, 'units': units, 'account': vault.public_account(box)}


def contar_bultos(finca_state, name, place):
    counts = {}
    bags = (finca_state or {}).get('bags') or {}
    for bag in bags.values():
        if not isinstance(bag, dict):
            continue
        if bag.get('owner') != name or bag.get('place') != place:
            continue
        item = 'bolsa_' + str(bag.get('crop') or '')
        if item not in MIRROR:
            continue
        counts[item] = counts.get(item, 0) + 1
    return counts


def mover_bultos(finca_state, config, name, op, item, qty=1, now=None):
    """Pasa bultos que ya existen entre la mano y el banco. No crea bultos."""
    import finca
    import mochila
    name = str(name or '')
    item = str(item or '')
    crop = MIRROR.get(item)
    now = _now(now)
    if not name or not crop or op not in ('deposit', 'withdraw'):
        return {'ok': False, 'reason': 'Nada que mover.', 'qty': 0}
    place_from = 'mochila' if op == 'deposit' else 'banco'
    serials = [
        serial for serial, bag in (finca_state.get('bags') or {}).items()
        if isinstance(bag, dict) and bag.get('owner') == name and bag.get('place') == place_from and bag.get('crop') == crop
    ]
    if _all(qty):
        take = serials
    else:
        try:
            asked = int(qty)
        except (TypeError, ValueError):
            asked = 0
        take = serials[:asked] if asked > 0 else []
    if not take:
        return {'ok': False, 'reason': 'No hay esa cantidad.', 'qty': 0}
    if op == 'withdraw':
        held = contar_bultos(finca_state, name, 'mochila')
        if not mochila.fits(held, item, len(take)):
            return {'ok': False, 'reason': mochila.FULL, 'qty': 0}
    moved = 0
    try:
        for serial in take:
            if op == 'deposit':
                finca.deposit(finca_state, config, name, serial, now)
            else:
                finca.withdraw(finca_state, config, name, serial, now)
            moved += 1
    except finca.FincaError as exc:
        return {'ok': False, 'reason': str(exc), 'qty': moved}
    return {'ok': True, 'dup': False, 'op': op, 'item': item, 'qty': moved}


def _texto(units):
    units = int(units or 0)
    whole, frac = divmod(abs(units), economy.SMH_PER_SMC)
    number = whole + (frac / economy.SMH_PER_SMC)
    if units < 0:
        number = -number
    return {
        'exacto': economy.format_smc(units),
        'compacto': economy.format_compact(number) + ' SMC',
    }


def vista(state, econ, name, bultos_encima=None, bultos_baul=None):
    """Lo que el servidor tiene de esa cuenta. El texto visible es sólo SMC."""
    import supply
    name = str(name or '')
    econ = econ if isinstance(econ, dict) else {}
    box = vault.account(state, name) if name else {'items': {}, 'smh': 0}
    carried = dict(purses.inventory(state, name))
    stored = {key: int(qty or 0) for key, qty in (box.get('items') or {}).items() if int(qty or 0) > 0}
    if bultos_encima is not None:
        for key in MIRROR:
            carried[key] = int((bultos_encima or {}).get(key) or 0)
    if bultos_baul is not None:
        for key in MIRROR:
            oficial = int((bultos_baul or {}).get(key) or 0)
            if oficial:
                stored[key] = oficial
    order = []
    for key in list(MINERAL) + list(RECURSO):
        if key not in order:
            order.append(key)
    for key in list(carried) + list(stored):
        if key not in order:
            order.append(key)
    filas = []
    for key in order:
        encima = int(carried.get(key) or 0)
        en_baul = int(stored.get(key) or 0)
        if encima < 1 and en_baul < 1:
            continue
        grupo = 'mineral' if key in MINERAL else 'recurso'
        filas.append({
            'id': key,
            'name': MINERAL.get(key) or RECURSO.get(key) or key,
            'grupo': grupo,
            'encima': encima,
            'baul': en_baul,
            'total': encima + en_baul,
        })
    wallet = int((econ.get('wallets') or {}).get(name) or 0)
    chest = vault.smh_of(box) if name else 0
    total = wallet + chest
    return {
        'smc': {
            'billetera': _texto(wallet),
            'baul': _texto(chest),
            'total': _texto(total),
            'escala': 'Las cantidades se muestran en SMC.',
            'topes': 'Oro: hasta %d SMC al día. Si se acaba, el cobre paga hasta %d SMC. El baúl no acuña.' % (
                int(supply.GOLD_DAILY_SMC), int(supply.COPPER_DAILY_SMC),
            ),
            'tope': '21.000.000 SMC',
        },
        'filas': filas,
        'totales': {
            'encima': sum(row['encima'] for row in filas),
            'baul': sum(row['baul'] for row in filas),
            'mineral': sum(row['total'] for row in filas if row['grupo'] == 'mineral'),
            'recurso': sum(row['total'] for row in filas if row['grupo'] == 'recurso'),
        },
    }


def migrate(state):
    """Una sola vez. No borra saldos ni objetos. Lo nuevo es opcional."""
    if not isinstance(state, dict):
        return False
    meta = state.get('meta') if isinstance(state.get('meta'), dict) else {}
    if int(meta.get('baul') or 0) >= 1:
        return False
    if not isinstance(state.get('accounts'), dict):
        state['accounts'] = {}
    if not isinstance(state.get('purses'), dict):
        if state.get('purses') not in (None, ''):
            state['pursesLegacy'] = state.get('purses')
        state['purses'] = {}
    for name, box in list(state['accounts'].items()):
        if not isinstance(box, dict):
            state['accounts'][name] = {'smh': 0, 'smcSubs': 0, 'items': {}}
            continue
        items = box.get('items')
        if isinstance(items, list):
            merged = {}
            for row in items:
                if not isinstance(row, dict):
                    continue
                key = str(row.get('item') or '')[:32]
                try:
                    qty = int(row.get('qty') or 0)
                except (TypeError, ValueError):
                    continue
                if key and qty > 0:
                    merged[key] = merged.get(key, 0) + qty
            box['items'] = merged
        elif not isinstance(items, dict):
            box['items'] = {}
    fresh = dict(meta)
    fresh['baul'] = 1
    state['meta'] = fresh
    return True
