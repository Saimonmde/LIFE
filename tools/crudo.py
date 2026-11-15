# SPDX-License-Identifier: AGPL-3.0-or-later
"""Metal crudo por cuenta. El servidor lo guarda; el cliente no lo inventa."""
SCALE = 1000
CAPS = {
    'pepita_oro': 200,
    'mineral_oro': 200,
    'mineral_plata': 400,
    'mineral_cobre': 800,
}
ACTION_CAP = 4
ORO = ('pepita_oro', 'mineral_oro')


def items_for(coin):
    if coin == 'simoncoin':
        return ORO
    if coin == 'simonplata':
        return ('mineral_plata',)
    if coin == 'simonchis':
        return ('mineral_cobre',)
    return ()


def _row(state, account):
    return state.setdefault('crudo', {}).setdefault(str(account or ''), {})


def nuggets(state, account, item):
    return int(_row(state, account).get(item) or 0) / SCALE


def total(state, account, items):
    return sum(nuggets(state, account, item) for item in items)


def credit(state, account, item, qty, cap=ACTION_CAP):
    if item not in CAPS or not account:
        return 0
    qty = max(0, min(int(qty or 0), int(cap)))
    if qty <= 0:
        return 0
    row = _row(state, account)
    row[item] = int(row.get(item) or 0) + qty * SCALE
    return qty


def migrar(state, account, counts):
    """Una sola vez. Lo que ya estaba en el aparato entra, con tope."""
    if not account:
        return False
    done = state.setdefault('crudoMig', {})
    if done.get(account):
        return False
    done[account] = True
    counts = counts if isinstance(counts, dict) else {}
    for item, cap in CAPS.items():
        qty = max(0, min(int(counts.get(item) or 0), cap))
        if qty:
            credit(state, account, item, qty, cap=cap)
    return True


def debit(state, account, items, amount):
    """Gasta pepita y luego mineral de oro, en ese orden. None si no alcanza."""
    need = int(round(float(amount or 0) * SCALE))
    if need <= 0:
        return {}
    row = _row(state, account)
    if sum(int(row.get(item) or 0) for item in items) < need:
        return None
    spent = {}
    for item in items:
        got = min(int(row.get(item) or 0), need)
        if got <= 0:
            continue
        row[item] = int(row.get(item) or 0) - got
        spent[item] = got / SCALE
        need -= got
    return spent
