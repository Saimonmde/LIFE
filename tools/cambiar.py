# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cambia objetos ya recogidos por Simoncoin. No inventa unidades.

1 SMC = 100 SMH. El cobre vale 0,001 SMC, así que hacen falta 10 para
llegar a 0,01. Si no alcanza, no se quita nada. El café y el cacao
valen 0,01 SMC por recolección. Los bultos de exportación no se tocan.
"""
import crudo
import economy as eco
import libro as LIBRO
import purses

# (numerador SMH, denominador de unidades, nombre, tarifa en SMC)
TARIFA = {
    'mineral_cobre': (1, 10, 'Mineral de cobre', '0,001'),
    'mineral_plata': (1, 1, 'Mineral de plata', '0,01'),
    'mineral_oro': (10, 1, 'Mineral de oro', '0,1'),
    'pepita_oro': (10, 1, 'Pepita de oro', '0,1'),
    'cafe_cereza': (1, 1, 'Café', '0,01'),
    'cacao_baba': (1, 1, 'Cacao', '0,01'),
}
COSECHA = {'cafe_cereza': 'cafe', 'cacao_baba': 'cacao'}


def ficha(item):
    return TARIFA.get(str(item or ''))


def smh_de(item, qty):
    row = ficha(item)
    qty = int(qty or 0)
    if not row or qty < 1:
        return 0
    return (qty * row[0]) // row[1]


def usable(item, qty):
    """Unidades que sí llegan a un céntimo. El resto se queda."""
    row = ficha(item)
    qty = int(qty or 0)
    if not row or qty < 1:
        return 0
    num, den = row[0], row[1]
    pagado = (qty * num) // den
    if pagado < 1:
        return 0
    return (pagado * den) // num


def _crudo(econ, account, item):
    if item not in crudo.CAPS:
        return 0
    return int(crudo.nuggets(econ, account, item))


def tener(econ, vault, finca, account, item):
    if not ficha(item):
        return 0
    total = purses.count(vault, account, item) + _crudo(econ, account, item)
    if item in COSECHA:
        goods = (((finca or {}).get('accounts') or {}).get(account) or {}).get('goods') or {}
        total += int(goods.get(item) or 0)
    return total


def _tomar(econ, vault, finca, account, item, qty):
    left = int(qty)
    taken = {'purse': 0, 'crudo': 0, 'finca': 0}
    if item in COSECHA:
        goods = (((finca or {}).get('accounts') or {}).get(account) or {}).setdefault('goods', {})
        have = int(goods.get(item) or 0)
        got = min(have, left)
        if got:
            goods[item] = have - got
            if goods[item] <= 0:
                goods.pop(item, None)
            taken['finca'] = got
            left -= got
    got = min(purses.count(vault, account, item), left)
    if got and purses.debit(vault, account, item, got):
        taken['purse'] = got
        left -= got
    if left and item in crudo.CAPS:
        row = crudo._row(econ, account)
        have = int(row.get(item) or 0) // crudo.SCALE
        got = min(have, left)
        if got:
            row[item] = int(row.get(item) or 0) - got * crudo.SCALE
            if row[item] <= 0:
                row.pop(item, None)
            taken['crudo'] = got
            left -= got
    return taken, int(qty) - left


def _devolver(econ, vault, finca, account, item, taken):
    if taken.get('finca'):
        goods = (((finca or {}).get('accounts') or {}).get(account) or {}).setdefault('goods', {})
        goods[item] = int(goods.get(item) or 0) + int(taken['finca'])
    if taken.get('purse'):
        purses.credit(vault, account, item, taken['purse'])
    if taken.get('crudo'):
        row = crudo._row(econ, account)
        row[item] = int(row.get(item) or 0) + int(taken['crudo']) * crudo.SCALE


def preparar(econ, vault, finca, account, item, qty):
    row = ficha(item)
    if not row:
        return {'ok': False, 'reason': 'Eso no se cambia por Simoncoin.'}
    qty = int(qty or 0)
    have = tener(econ, vault, finca, account, item)
    if qty < 1 or qty > have:
        return {'ok': False, 'reason': 'No tienes esa cantidad.'}
    use = usable(item, qty)
    smh = smh_de(item, use)
    if smh < 1:
        return {
            'ok': False,
            'reason': 'Con esa cantidad no llega a 0,01 SMC. Cada %s vale %s SMC. Sigue en tu inventario.' % (row[2].lower(), row[3]),
        }
    taken, got = _tomar(econ, vault, finca, account, item, use)
    if got != use:
        _devolver(econ, vault, finca, account, item, taken)
        return {'ok': False, 'reason': 'No se pudo apartar. No se cambió nada.'}
    return {'ok': True, 'item': item, 'qty': use, 'smh': smh, 'nombre': row[2], 'tarifa': row[3], 'taken': taken}


def cerrar(econ, chain, seed, name, smh, note, ahora=0):
    """Acredita el Simoncoin y lo anota. Si no cabe, no deja rastro."""
    smh = int(smh or 0)
    if smh < 1 or not name:
        return 0, None
    room = min(eco.issuance_room(econ), LIBRO.cupo_subs(chain))
    if smh > room:
        return 0, None
    granted = eco.issue(econ, name, smh, note, 'cambio', now=ahora)
    if granted != smh:
        if granted:
            eco.debit(econ, name, granted)
            econ['minedSmh'] = max(0, int(econ.get('minedSmh') or 0) - granted)
        return 0, None
    record = LIBRO.acuñar(
        chain, seed, name, granted, note, ts=int(ahora or 0), bits=1, presupuesto=2, kind='acuñacion',
    )
    if record is None:
        eco.debit(econ, name, granted)
        econ['minedSmh'] = max(0, int(econ.get('minedSmh') or 0) - granted)
        return 0, None
    return granted, record
