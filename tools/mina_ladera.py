# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mina de La Ladera: la segunda mina, con más vetas y pago sólo en SMC.

La Mina de Las Palmas no cambia. Allí picar deja mineral y el horno acuña
0,1 SMC por pieza de cobre, de plata o de oro (piezas × 10 SMH). El documento
docs/economia-smc.md habla del oro del río (50 SMC al día) y del cobre de
respaldo (150 SMC), no de estas tres tasas por veta. La conversión de saldos
viejos en tools/una_moneda.py sí usa 0,001 / 0,01 / 0,1, pero no es el pago
de picar.

Picar deja el mineral. El horno, junto al baúl, lo acuña a esas tasas y sólo
en SMC: cobre 0,001, plata 0,01, mineral de oro 0,1. El cobre se junta de a
milésimos hasta poder anotar 0,01 SMC. No se muestra SMH, SMP ni SPH. Siguen
el tope de 21.000.000 y los topes del día, los mismos de Las Palmas: el oro y
la plata comparten el de oro, el cobre usa el suyo. Una fundición los suma
una sola vez.
"""
import economy as eco
import supply as sup

NAME = 'Mina de La Ladera'
ZONE = 'mina2'
PLACE = 'mina-ladera'
TRAVEL = 'mina_ladera'
# El mismo horno de Las Palmas, puesto junto al baúl. El cliente usa estas casillas.
HORNO = (24, 16)
REACH = 1
MONEDA = {
    'simoncoin': 'oro',
    'simonplata': 'plata',
    'simonchis': 'cobre',
}
PIEZAS = {'oro': 10, 'plata': 100, 'cobre': 1000}
WIDTH = 48
HEIGHT = 40
SPAWN = (24.0, 35.0)
# Milésimos de SMC. 10 milésimos = 1 SMH = 0,01 SMC. El libro sigue en enteros.
MILLIS = {'cobre': 1, 'plata': 10, 'oro': 100}
RATES_SMC = {'cobre': 0.001, 'plata': 0.01, 'oro': 0.1}
RESPAWN_MS = {'cobre': 18000, 'plata': 18000, 'oro': 32000}
RECURSO = 'cobre 0,001 · plata 0,01 · oro 0,1 SMC'


def _grid(xs, ys):
    return [(x, y) for y in ys for x in xs]


def _spots():
    cobre = _grid((6, 11, 16), (6, 12, 20, 28))[:10]
    plata = _grid((34, 40), (6, 14, 22, 30))
    oro = _grid((22, 28), (6, 14, 24, 32)) + [(18, 10), (38, 18), (24, 28), (32, 20)]
    return {'cobre': cobre, 'plata': plata, 'oro': oro}


def veins():
    """id -> (x, y, respawn ms, metal). Una veta, un reloj."""
    found = {}
    for metal, spots in _spots().items():
        ms = RESPAWN_MS[metal]
        for index, (x, y) in enumerate(spots):
            found['ladera_%s_%d' % (metal, index)] = (x, y, ms, metal)
    return found


VEINS = veins()


def capacity():
    """Cuántas personas pueden picar a la vez: una veta cada una."""
    return len(VEINS)


def metal_of(node_id):
    row = VEINS.get(str(node_id or ''))
    return row[3] if row else ''


def _walk(world, x, y):
    width = int(world['width'])
    height = int(world['height'])
    if not (1 < x < width - 1 and 1 < y < height - 1):
        return False
    return world['collision'][y][x] == 0


def first_entrance(world, palmas):
    """La misma búsqueda que prepareCave para la Mina de Las Palmas."""
    px, py = int(palmas['x']), int(palmas['y'])
    for ring in range(2, 10):
        for dx in range(-ring, ring + 1):
            for dy in range(-ring, ring + 1):
                x, y = px + dx, py + dy
                if _walk(world, x, y) and _walk(world, x, y + 1):
                    return x, y
    return None


def finca_anchor(world, palmas):
    """El mismo claro del cafetal que usa el cliente junto a Las Palmas."""
    px, py = int(palmas['x']), int(palmas['y'])
    best = None
    for dy in range(6, 17):
        for dx in range(-8, 9):
            x, y = px + dx, py + dy
            opened = 0
            for iy in range(8):
                for ix in range(-6, 7):
                    if _walk(world, x + ix, y + iy):
                        opened += 1
            if best is None or opened > best[0]:
                best = (opened, x, y)
    if best and best[0] > 40:
        return best[1], best[2]
    return px, min(int(world['height']) - 4, py + 8)


def plot_tiles(anchor):
    """Las matas y los dos talleres. La boca no se sienta encima."""
    blocked = set()
    ax, ay = anchor
    for index in range(8):
        lx = -5.2 + index * 1.35
        lz = 5.6
        tx = int(round(ax + lx / 2.0))
        ty = int(round(ay + lz / 2.0))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                blocked.add((tx + dx, ty + dy))
    for lx, lz in ((-4.2, 3.6), (3.4, 3.6)):
        tx = int(round(ax + lx / 2.0))
        ty = int(round(ay + lz / 2.0))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                blocked.add((tx + dx, ty + dy))
    return blocked


def entrance(world):
    """Boca al lado del cafetal, no encima de las matas ni de la otra mina."""
    palmas = next((item for item in world.get('waypoints') or [] if item.get('id') == 'las_palmas'), None)
    if not palmas:
        return None
    first = first_entrance(world, palmas)
    if not first:
        return None
    anchor = finca_anchor(world, palmas)
    blocked = plot_tiles(anchor)
    ax, ay = anchor
    best = None
    for dy in range(-14, 15):
        for dx in range(-14, 15):
            x, y = ax + dx, ay + dy
            if (x, y) in blocked or (x, y + 1) in blocked:
                continue
            if not (_walk(world, x, y) and _walk(world, x, y + 1)):
                continue
            if max(abs(x - first[0]), abs(y - first[1])) < 8:
                continue
            dist = abs(dx) + abs(dy)
            if dist < 4 or dist > 10:
                continue
            rank = (dist, abs(dy), x, y)
            if best is None or rank < best:
                best = rank
    if not best:
        return None
    return {'x': best[2], 'y': best[3], 'name': NAME}


def _texto(metal, smh):
    nombre = {'cobre': 'Cobre', 'plata': 'Plata', 'oro': 'Mineral de oro'}[metal]
    tasa = {'cobre': '0,001', 'plata': '0,01', 'oro': '0,1'}[metal]
    if int(smh or 0) <= 0:
        return '%s: %s SMC. Se anota al juntar 0,01 SMC.' % (nombre, tasa)
    return '+%s (%s, %s SMC por veta).' % (eco.format_smc(smh), nombre.lower(), tasa)


def _cupo(econ, account, metal, now, age, play, quests):
    sup.ensure(econ, now=int(now))
    acc = sup._account(econ['supply'], account, int(now))
    if metal == 'cobre':
        cap = sup.copper_daily_smh()
        earned = int(acc.get('copperEarned') or 0)
        key = 'copperEarned'
    else:
        cap = sup.enforced_daily_smh(age, play, quests)
        earned = int(acc.get('earned') or 0)
        key = 'earned'
    return acc, key, max(0, cap - earned)


def cobrar(econ, name, account, metal, now, age=0, play=0, quests=0):
    """Anota el SMC de una veta. No crea más del tope ni del día.

    El cobre de 0,001 SMC se guarda en milésimos hasta completar 0,01.
    Devuelve ok False si no cabe: la veta no se gasta.
    """
    metal = str(metal or '')
    if metal not in MILLIS:
        return {'ok': False, 'smh': 0, 'texto': 'Esa veta no es de esta mina.', 'reason': 'veta'}
    account = str(account or '')
    name = str(name or '')
    if not account or not name:
        return {'ok': False, 'smh': 0, 'texto': 'Entra con una cuenta para recibir SMC.', 'reason': 'guest'}
    box = econ.setdefault('minaLadera', {})
    row = box.setdefault(account, {'millis': 0})
    pending = int(row.get('millis') or 0) + MILLIS[metal]
    smh = pending // 10
    keep = pending % 10
    if smh <= 0:
        row['millis'] = pending
        return {'ok': True, 'smh': 0, 'texto': _texto(metal, 0), 'reason': ''}
    acc, key, left = _cupo(econ, account, metal, now, age, play, quests)
    room = eco.issuance_room(econ)
    grant = min(smh, left, room)
    if grant <= 0:
        reason = 'supply' if room <= 0 else 'cap'
        text = 'Se alcanzó el tope de 21.000.000 SMC.' if reason == 'supply' else 'Llegaste al tope de SMC de hoy.'
        return {'ok': False, 'smh': 0, 'texto': text, 'reason': reason}
    row['millis'] = keep + (smh - grant) * 10
    acc[key] = int(acc.get(key) or 0) + grant
    granted = eco.issue(econ, name, grant, 'Veta de %s en la Mina de La Ladera' % metal, 'mint', now=now)
    if granted < grant:
        acc[key] = max(0, int(acc.get(key) or 0) - (grant - granted))
        row['millis'] = int(row.get('millis') or 0) + (grant - granted) * 10
    if granted <= 0:
        return {'ok': False, 'smh': 0, 'texto': 'Se alcanzó el tope de 21.000.000 SMC.', 'reason': 'supply'}
    return {'ok': True, 'smh': granted, 'texto': _texto(metal, granted), 'reason': ''}


def junto(zone, x, y):
    """Hay que estar en la mina de La Ladera y al lado del horno. Como el horno de Las Palmas: Chebyshev 1."""
    if str(zone or '') != ZONE:
        return False
    try:
        fx, fy = float(x), float(y)
    except (TypeError, ValueError):
        return False
    return max(abs(fx - HORNO[0]), abs(fy - HORNO[1])) <= REACH


def metal_moneda(coin):
    return MONEDA.get(str(coin or ''))


def millis_de(metal, piezas, previo=0):
    """Milésimos de SMC. 10 milésimos = 0,01 SMC = 1 unidad del libro."""
    if metal not in MILLIS:
        return 0
    return max(0, int(previo or 0)) + max(0, int(piezas or 0)) * MILLIS[metal]


def partir(millis):
    millis = max(0, int(millis or 0))
    return millis // 10, millis % 10


def migrar(econ):
    """No toca el SMC ya anotado ni borra los milésimos que todavía no llegaban a 0,01.

    El horno los suma en la próxima fundición.
    """
    if not isinstance(econ, dict):
        return False
    meta = econ.setdefault('meta', {})
    if meta.get('laderaHorno'):
        return False
    kept = 0
    box = econ.get('minaLadera') or {}
    if isinstance(box, dict):
        for row in box.values():
            if isinstance(row, dict):
                row['millis'] = max(0, int(row.get('millis') or 0))
                kept += row['millis']
    meta['laderaHorno'] = {'millis': kept}
    return True


def contar(econ, account, metal, smh, now, token, age=0, play=0, quests=0):
    """Suma el cupo del día una sola vez. El mismo contador que Las Palmas.

    Oro y plata usan el cupo de oro. El cobre usa el suyo. Un token repetido no suma.
    """
    metal = str(metal or '')
    account = str(account or '')
    token = str(token or '')
    smh = max(0, int(smh or 0))
    if metal not in MILLIS or not account or not token or smh <= 0:
        return 0
    row = econ.setdefault('minaLadera', {}).setdefault(account, {'millis': 0})
    seen = row.setdefault('fundiciones', [])
    if token in seen:
        return 0
    acc, key, left = _cupo(econ, account, metal, now, age, play, quests)
    room = eco.issuance_room(econ)
    grant = min(smh, left, room)
    if grant <= 0:
        return 0
    acc[key] = int(acc.get(key) or 0) + grant
    seen.append(token)
    del seen[:-40]
    return grant


def soltar_cupo(econ, account, metal, smh):
    """Quita del cupo del día lo que no llegó a anotarse. No toca la billetera."""
    smh = int(smh or 0)
    if smh <= 0 or str(metal or '') not in MILLIS:
        return
    acc = ((econ.get('supply') or {}).get('accounts') or {}).get(str(account or ''))
    if not isinstance(acc, dict):
        return
    key = 'copperEarned' if metal == 'cobre' else 'earned'
    acc[key] = max(0, int(acc.get(key) or 0) - smh)


def deshacer(econ, name, account, metal, smh, now):
    """Si el libro madre no anota, el SMC no se queda ni el cupo se gasta."""
    smh = int(smh or 0)
    if smh <= 0:
        return
    eco.debit(econ, name, smh)
    econ['minedSmh'] = max(0, int(econ.get('minedSmh') or 0) - smh)
    mem = econ.get('mempool') or []
    if mem and mem[-1].get('to') == name and int(mem[-1].get('amountSubs') or 0) == smh:
        mem.pop()
    account = str(account or '')
    if not account:
        return
    sup.ensure(econ, now=int(now))
    acc = sup._account(econ['supply'], account, int(now))
    key = 'copperEarned' if metal == 'cobre' else 'earned'
    acc[key] = max(0, int(acc.get(key) or 0) - smh)
    row = econ.setdefault('minaLadera', {}).setdefault(account, {'millis': 0})
    row['millis'] = int(row.get('millis') or 0) + smh * 10
