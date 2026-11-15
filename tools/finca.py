# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cafetal y cacaotal de Las Palmas.

El café y el cacao crecen con el reloj del juego. El taller escribe cada
saco o cajón en el libro, con serie y hash. Los kilos cosechados son fruto
fresco y sólo suben: vender, guardar, pasar o procesar no los baja. El
taller tampoco crea kilos. Café: 5 kg de cereza dan 1 kg de pergamino seco
(Cenicafé, rango 4,7 a 5,3; se usa 5), 94 kg de pergamino dan un saco de
70 kg de excelso, y una carga son 125 kg de pergamino (FNC). Cacao: un
cajón de 1 × 1 × 0,9 m lleva 450 kg en baba y rinde 150 kg secos. Las
citas están en data/finca.json y en docs/unidades-finca.md.

Aquí no se acuñan monedas ni lingotes. Una venta sólo mueve monedas que
ya existen, desde la Casa de Contratación. Si no le alcanzan, no compra.
"""
import hashlib
import hmac
import json
import os
import secrets

import economy
import plata
import reloj

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_CONFIG = os.path.join(ROOT, 'data', 'finca.json')
CROPS = ('cafe', 'cacao')
COINS = ('simoncoin', 'simonplata', 'simonchis')
SUPPLY_NUMS = (
    'simoncoin', 'simonplata', 'simonchis',
    'simoncoinSum', 'simonplataSum', 'simonchisSum',
)
PRIVATE_ROLES = frozenset(('owner', 'admin', 'compliance'))
# Pesos que ya estaban guardados antes de cuadrar el rendimiento.
# No se reescriben: un saco viejo sigue pesando lo que decía su ficha.
LEGACY_SACK_KG = {'cafe': 70, 'cacao': 50}


class FincaError(ValueError):
    pass


def load_config(path=None):
    path = path or DEFAULT_CONFIG
    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    if int(data.get('realSecondsPerGameDay') or 0) != reloj.REAL_SECONDS_PER_DAY:
        raise FincaError('el día de la finca tiene que ser el del reloj')
    for crop in CROPS:
        if crop not in (data.get('crops') or {}):
            raise FincaError('falta el cultivo ' + crop)
    return data


def empty_state():
    return {
        'v': 1,
        'secret': secrets.token_hex(16),
        'seededSmh': 0,
        'seq': 0,
        'harvestedKg': {'cafe': 0, 'cacao': 0},
        'processedBags': {'cafe': 0, 'cacao': 0},
        'soldBags': {'cafe': 0, 'cacao': 0},
        'harvestPrev': {'cafe': '', 'cacao': ''},
        'lastBagHash': '',
        'accounts': {},
        'bags': {},
        'publicEvents': [],
        'privateEvents': [],
        'feed': [],
    }


def _keep_saved_mass(bag):
    """Un bulto ya guardado conserva sus kilos. No se inventan ni se bajan."""
    row = dict(bag)
    if not row.get('massRule'):
        row['massRule'] = 'legado'
        row['productKg'] = int(row.get('kg') or 0)
    return row


def normalize(state):
    base = empty_state()
    if not isinstance(state, dict):
        return base
    base['secret'] = str(state.get('secret') or base['secret'])
    base['seededSmh'] = int(state.get('seededSmh') or 0)
    base['seq'] = int(state.get('seq') or 0)
    base['lastBagHash'] = str(state.get('lastBagHash') or '')
    for crop in CROPS:
        base['harvestedKg'][crop] = int((state.get('harvestedKg') or {}).get(crop) or 0)
        base['processedBags'][crop] = int((state.get('processedBags') or {}).get(crop) or 0)
        base['soldBags'][crop] = int((state.get('soldBags') or {}).get(crop) or 0)
        base['harvestPrev'][crop] = str((state.get('harvestPrev') or {}).get(crop) or '')
    if isinstance(state.get('accounts'), dict):
        base['accounts'] = state['accounts']
        for box in base['accounts'].values():
            if not isinstance(box, dict):
                continue
            for crop, batch in (box.get('batches') or {}).items():
                if isinstance(batch, dict) and not batch.get('massRule'):
                    batch['massRule'] = 'legado'
                    batch['sackKg'] = LEGACY_SACK_KG.get(str(crop), int(batch.get('sackKg') or 0))
    bags = state.get('bags')
    if isinstance(bags, dict):
        base['bags'] = {
            serial: _keep_saved_mass(bag)
            for serial, bag in bags.items()
            if isinstance(bag, dict)
        }
    for key in ('publicEvents', 'privateEvents', 'feed'):
        if isinstance(state.get(key), list):
            base[key] = state[key]
    return base


def batch_balance(spec, config):
    """Kilos frescos del lote y kilos secos que salen. No crea masa.

    El tamaño de cada cosecha está elegido para llenar unidades reales
    con las mismas 10 cosechas y los mismos 2 resultados. Café: 94 kg de
    cereza por cosecha. Cacao: 90 kg en baba, un quinto de cajón.
    """
    need = int(config.get('harvestsPerBatch') or 0)
    bags = int(config.get('bagsPerBatch') or 0)
    per = int(spec.get('kgPerHarvest') or 0)
    sack = int(spec.get('bagKg') or 0)
    fresh = need * per
    ratio = spec.get('yield') or {}
    num = int(ratio.get('num') or 0)
    den = int(ratio.get('den') or 0)
    if min(need, bags, per, sack, num, den) <= 0:
        raise FincaError('falta el rendimiento del cultivo')
    if fresh * num % den:
        raise FincaError('la conversión no da kilos enteros')
    dry = fresh * num // den
    if dry != bags * sack:
        raise FincaError('el peso seco no cuadra con la unidad')
    if fresh % bags:
        raise FincaError('el peso fresco no se reparte')
    out = {
        'freshKg': fresh,
        'dryKg': dry,
        'sackKg': sack,
        'freshEach': fresh // bags,
        'bags': bags,
    }
    parchment = spec.get('parchment')
    if parchment:
        cherry = int(parchment.get('cherryKg') or 0)
        per_sack = int(parchment.get('perSackKg') or 0)
        carga = int(parchment.get('cargaKg') or 0)
        if min(cherry, per_sack, carga) <= 0 or fresh % cherry:
            raise FincaError('la cereza no da pergamino entero')
        pergamino = fresh // cherry
        if pergamino * sack % per_sack:
            raise FincaError('la trilla no da sacos enteros')
        excelso = pergamino * sack // per_sack
        if excelso != dry:
            raise FincaError('el excelso no cuadra con el pergamino')
        out['pergaminoKg'] = pergamino
        out['cargas'] = pergamino // carga
        out['cargaRestoKg'] = pergamino % carga
    box = spec.get('box')
    if box:
        baba = int(box.get('babaKg') or 0)
        box_dry = int(box.get('dryKg') or 0)
        if baba <= 0 or box_dry <= 0 or fresh != bags * baba or box_dry != sack:
            raise FincaError('el lote no llena cajones enteros')
        if baba * num // den != box_dry:
            raise FincaError('el cajón no respeta la merma')
        out['boxes'] = bags
    return out


def load(path):
    import persist
    doc = persist.load_named('finca', path)
    if doc is None:
        doc = empty_state()
        save(path, doc)
        return doc
    return normalize(doc)


def save(path, state):
    import persist
    persist.save_named('finca', path, state)


def owner_email():
    import fusion
    return fusion.owner_email()


def can_see_private(email, role=''):
    if str(email or '').strip().lower() == owner_email():
        return True
    return str(role or '').strip().lower() in PRIVATE_ROLES


def supply_fingerprint(snap):
    snap = snap or {}
    foundry = snap.get('foundry') or {}
    items = tuple(sorted((str(key), int(value or 0)) for key, value in foundry.items()))
    nums = tuple(int(snap.get(key) or 0) for key in SUPPLY_NUMS)
    return nums + (items,)


def same_supply(before, after):
    return supply_fingerprint(before) == supply_fingerprint(after)


def guarded_move(purse, coin, src, dst, amount):
    """Mueve monedas ya existentes. Si el movimiento crea monedas o lingotes, se deshace."""
    amount = int(amount or 0)
    if amount <= 0 or not src or not dst or src == dst or coin not in COINS:
        return False
    before = purse.supply()
    if not purse.move(coin, src, dst, amount):
        return False
    if same_supply(before, purse.supply()):
        return True
    purse.move(coin, dst, src, amount)
    return False


def _sha(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _pseudo(state, account):
    secret = bytes.fromhex(state.get('secret') or '')
    return hmac.new(secret, str(account or '').encode('utf-8'), hashlib.sha256).hexdigest()[:12]


def _next(state, prefix):
    state['seq'] = int(state.get('seq') or 0) + 1
    return f'{prefix}-{state["seq"]:06d}'


def _crop(config, crop):
    if crop not in CROPS:
        raise FincaError('ese cultivo no está en Las Palmas')
    return config['crops'][crop]


def _steps(spec):
    return list(spec.get('steps') or [])


def _price(spec, coin):
    raw = (spec.get('prices') or {}).get(coin)
    if coin == 'simonchis':
        return int(raw or 0)
    return economy.parse_amount(f'{raw} SMC')


def _account(state, config, account):
    box = state['accounts'].setdefault(account, {
        'goods': {}, 'batches': {}, 'soldDay': 0, 'soldCount': 0, 'plots': {},
    })
    box.setdefault('goods', {})
    box.setdefault('batches', {})
    plots = box.setdefault('plots', {})
    counts = config.get('plots') or {}
    for crop in CROPS:
        want = int(counts.get(crop) or 0)
        have = [key for key, row in plots.items() if row.get('crop') == crop]
        for index in range(len(have) + 1, want + 1):
            plots[f'{crop}-{index}'] = {'crop': crop, 'plantedAt': 0}
    return box


def _days(planted_at, now):
    elapsed = max(0.0, float(now) - float(planted_at or 0))
    return elapsed / float(reloj.REAL_SECONDS_PER_DAY)


def stage_of(plot, now, config):
    """Etapa que ya ve el juego: vacio, planton, verde, maduro. No cambia la cosecha."""
    if not plot or not plot.get('plantedAt'):
        return 'vacio'
    days = _days(plot['plantedAt'], now)
    if days >= float(config.get('ripeAfterDays') or 2):
        return 'maduro'
    if days >= float(config.get('greenAfterDays') or 1):
        return 'verde'
    return 'planton'


PHASES = ('siembra', 'crecimiento', 'floracion', 'fruto', 'cosecha')
_LEGACY_PHASE = {
    '': 'vacio', 'empty': 'vacio', 'vacio': 'vacio',
    'planted': 'siembra', 'planton': 'siembra', 'siembra': 'siembra',
    'growing': 'crecimiento', 'verde': 'crecimiento', 'crecimiento': 'crecimiento',
    'floracion': 'floracion', 'flower': 'floracion', 'flowering': 'floracion',
    'fruto': 'fruto', 'fruiting': 'fruto',
    'grown': 'cosecha', 'maduro': 'cosecha', 'cosecha': 'cosecha',
}


def legacy_phase(token):
    return _LEGACY_PHASE.get(str(token or '').strip().lower(), 'vacio')


def migrate_plot(plot, now, config):
    """Una parcela guardada como empty/planted/grown recibe reloj, sin tocar los kilos."""
    if not isinstance(plot, dict) or plot.get('plantedAt'):
        return plot
    phase = legacy_phase(plot.get('phase') or plot.get('stage') or '')
    if phase == 'vacio':
        return plot
    ripe = float(config.get('ripeAfterDays') or 2)
    along = {'siembra': 0.05, 'crecimiento': ripe * 0.30, 'floracion': ripe * 0.55, 'fruto': ripe * 0.80, 'cosecha': ripe + 0.05}
    plot['plantedAt'] = int(float(now) - along[phase] * reloj.REAL_SECONDS_PER_DAY)
    plot['phase'] = phase
    return plot


def phase_of(plot, now, config):
    """Cinco etapas de estudio. cosecha coincide con maduro: ahí se cosecha."""
    if not plot or not plot.get('plantedAt'):
        return legacy_phase((plot or {}).get('phase') or (plot or {}).get('stage') or '')
    days = _days(plot['plantedAt'], now)
    ripe = float(config.get('ripeAfterDays') or 2)
    if days >= ripe:
        return 'cosecha'
    grown = ('siembra', 'crecimiento', 'floracion', 'fruto')
    slot = int(days / ripe * len(grown)) if ripe else 0
    return grown[min(len(grown) - 1, max(0, slot))]


def _feed(state, text):
    state.setdefault('feed', []).insert(0, text)
    del state['feed'][40:]


def _log(state, kind, account, now, text, crop='', kg=0, total_kg=0, serial='', prev='', digest='', counterparty='', coin='', amount=0):
    event_id = _next(state, 'ev')
    public = {
        'id': event_id,
        'kind': kind,
        'ts': int(now),
        'crop': crop,
        'kg': int(kg or 0),
        'totalKg': int(total_kg or 0),
        'serial': serial or '',
        'prev': prev or '',
        'hash': digest or '',
        'note': text,
    }
    private = dict(public)
    private['account'] = account
    private['counterparty'] = counterparty or ''
    private['coin'] = coin or ''
    private['amount'] = int(amount or 0)
    state.setdefault('publicEvents', []).append(public)
    state.setdefault('privateEvents', []).append(private)
    del state['publicEvents'][:-200]
    del state['privateEvents'][:-400]
    _feed(state, text)
    return public


def _harvest_hash(crop, kg, total, prev):
    return _sha({'crop': crop, 'kg': int(kg), 'kind': 'cosecha', 'prev': prev or '', 'totalKg': int(total)})


def _bag_hash(serial, crop, kg, product, harvests, batch, steps, prev):
    return _sha({
        'batch': batch,
        'crop': crop,
        'harvests': list(harvests),
        'kg': int(kg),
        'prev': prev or '',
        'product': product,
        'serial': serial,
        'steps': list(steps),
    })


def fund_buyer(state, purse, config):
    """Pasa Simoncoin ya emitido del tesoro a la casa. No acuña."""
    want = economy.parse_amount(str(config.get('seedSimoncoin') or '0') + ' SMC')
    already = int(state.get('seededSmh') or 0)
    need = int(want) - already
    if need <= 0:
        return False
    buyer = config['buyer']
    have = int(purse.balance('simoncoin', 'tesoro_genesis') or 0)
    take = min(need, have)
    if take <= 0:
        return False
    if not guarded_move(purse, 'simoncoin', 'tesoro_genesis', buyer, take):
        return False
    state['seededSmh'] = already + take
    _log(
        state, 'fondo', 'tesoro_genesis', 0,
        'La Casa de Contratación apartó monedas que ya existían.',
        counterparty=buyer, coin='simoncoin', amount=take,
    )
    return True


def _tick(state, box, crop, now, config, account):
    batch = (box.get('batches') or {}).get(crop)
    if not batch or int(now) < int(batch.get('readyAt') or 0) or batch.get('settled'):
        return False
    spec = _crop(config, crop)
    steps = _steps(spec)
    index = int(batch.get('step') or 0)
    prev = batch.get('hash') or ''
    digest = _sha({'batch': batch['id'], 'crop': crop, 'prev': prev, 'step': steps[index]['id']})
    batch['hash'] = digest
    batch.setdefault('stepHashes', []).append(digest)
    batch['settled'] = True
    label = steps[index]['label']
    _log(state, 'taller', account, now, f'El taller de {spec["name"].lower()} terminó: {label.lower()}.', crop=crop, digest=digest, prev=prev)
    if index + 1 < len(steps):
        return False
    harvests = list(batch.get('harvests') or [])
    made = []
    kg = int(batch.get('sackKg') or 0)
    if kg <= 0:
        raise FincaError('el lote no tiene un peso')
    name = 'café' if crop == 'cafe' else 'cacao'
    if batch.get('massRule') == 'legado':
        phrase = f'Se procesó 1 bulto de {name}'
    else:
        phrase = spec.get('processPhrase') or f'Se procesó 1 unidad de {kg} kg de {name}.'
    for _ in range(int(config.get('bagsPerBatch') or 2)):
        serial = _next(state, spec.get('serialPrefix') or crop[:3].upper())
        prev_bag = state.get('lastBagHash') or ''
        step_hashes = list(batch.get('stepHashes') or [])
        bag_hash = _bag_hash(serial, crop, kg, spec.get('product') or '', harvests, batch['id'], step_hashes, prev_bag)
        bag = {
            'serial': serial,
            'crop': crop,
            'kg': kg,
            'productKg': kg,
            'freshKg': int(batch.get('freshKg') or 0),
            'massRule': batch.get('massRule') or 'rendimiento',
            'product': spec.get('product') or '',
            'harvests': harvests,
            'batch': batch['id'],
            'steps': [step['id'] for step in steps],
            'stepHashes': step_hashes,
            'prev': prev_bag,
            'hash': bag_hash,
            'owner': account,
            'place': 'mochila',
            'chain': [{'kind': 'origen', 'hash': bag_hash, 'prev': prev_bag}],
        }
        state['bags'][serial] = bag
        state['lastBagHash'] = bag_hash
        state['processedBags'][crop] = int(state['processedBags'].get(crop) or 0) + 1
        _log(state, 'proceso', account, now, phrase, crop=crop, serial=serial, prev=prev_bag, digest=bag_hash)
        made.append(serial)
    box['batches'].pop(crop, None)
    batch['made'] = made
    return True


def _tick_all(state, box, now, config, account):
    made = False
    for crop in CROPS:
        if _tick(state, box, crop, now, config, account):
            made = True
    return made


def plant(state, config, account, plot_id, now):
    box = _account(state, config, account)
    plot = box['plots'].get(plot_id)
    if not plot:
        raise FincaError('esa parcela no es tuya')
    if plot.get('plantedAt'):
        raise FincaError('ahí ya hay una mata')
    plot['plantedAt'] = int(now)
    spec = _crop(config, plot['crop'])
    _log(state, 'plantar', account, now, f'Se plantó {spec["name"].lower()}.', crop=plot['crop'])
    return plot_id


def harvest(state, config, account, plot_id, now):
    box = _account(state, config, account)
    plot = box['plots'].get(plot_id)
    migrate_plot(plot, now, config)
    if not plot or stage_of(plot, now, config) != 'maduro':
        raise FincaError('aún no está maduro')
    crop = plot['crop']
    spec = _crop(config, crop)
    kg = int(spec.get('kgPerHarvest') or 0)
    if kg <= 0:
        raise FincaError('la cosecha no tiene kilos')
    state['harvestedKg'][crop] = int(state['harvestedKg'].get(crop) or 0) + kg
    total = state['harvestedKg'][crop]
    prev = state['harvestPrev'].get(crop) or ''
    digest = _harvest_hash(crop, kg, total, prev)
    harvest_id = _next(state, 'cos')
    state['harvestPrev'][crop] = digest
    box.setdefault('openHarvests', {}).setdefault(crop, []).append(harvest_id)
    item = spec['harvestItem']
    box['goods'][item] = int(box['goods'].get(item) or 0) + 1
    plot['plantedAt'] = 0
    name = 'café' if crop == 'cafe' else 'cacao'
    _log(state, 'cosecha', account, now, f'Se cosecharon {kg} kg de {name}.', crop=crop, kg=kg, total_kg=total, prev=prev, digest=digest, serial=harvest_id)
    return {'kg': kg, 'totalKg': total, 'item': item, 'hash': digest, 'prev': prev}


def process(state, config, account, crop, now):
    box = _account(state, config, account)
    if _tick(state, box, crop, now, config, account):
        return {'done': True}
    spec = _crop(config, crop)
    steps = _steps(spec)
    if not steps:
        raise FincaError('el taller no tiene pasos')
    batch = box['batches'].get(crop)
    if batch and not batch.get('settled'):
        raise FincaError('espera un momento. El taller sigue trabajando.')
    if batch and batch.get('settled'):
        batch['step'] = int(batch.get('step') or 0) + 1
        batch['settled'] = False
        batch['readyAt'] = int(now) + int(config.get('stepSeconds') or 8)
        label = steps[batch['step']]['label']
        _log(state, 'taller', account, now, f'El taller de {spec["name"].lower()} empezó: {label.lower()}.', crop=crop)
        return {'done': False, 'step': label}
    need = int(config.get('harvestsPerBatch') or 10)
    balance = batch_balance(spec, config)
    item = spec['harvestItem']
    have = int(box['goods'].get(item) or 0)
    if have < need:
        raise FincaError(f'hacen falta {need} recolecciones. Llevas {have}.')
    box['goods'][item] = have - need
    harvests = box.setdefault('openHarvests', {}).setdefault(crop, [])
    used = harvests[:need]
    del harvests[:need]
    box['batches'][crop] = {
        'id': _next(state, 'lot'),
        'crop': crop,
        'step': 0,
        'settled': False,
        'readyAt': int(now) + int(config.get('stepSeconds') or 8),
        'harvests': used,
        'stepHashes': [],
        'hash': '',
        'massRule': 'rendimiento',
        'sackKg': balance['sackKg'],
        'freshKg': balance['freshEach'],
    }
    _log(state, 'taller', account, now, f'El taller de {spec["name"].lower()} empezó: {steps[0]["label"].lower()}.', crop=crop)
    return {'done': False, 'step': steps[0]['label']}


def _bag_owned(state, serial, account, place):
    bag = state['bags'].get(serial)
    if not bag or bag.get('owner') != account or bag.get('place') != place:
        raise FincaError('ese bulto no está en tu mano')
    return bag


def sell(state, purse, config, account, serial, coin, now):
    if coin not in COINS:
        raise FincaError('esa moneda no compra café ni cacao')
    bag = _bag_owned(state, serial, account, 'mochila')
    spec = _crop(config, bag['crop'])
    price = _price(spec, coin)
    if price <= 0:
        raise FincaError('ese bulto no tiene precio')
    day = int(now) // 86400
    box = _account(state, config, account)
    if int(box.get('soldDay') or 0) != day:
        box['soldDay'] = day
        box['soldCount'] = 0
    cap = int(config.get('dailySellCapBags') or 0)
    if int(box.get('soldCount') or 0) >= cap:
        raise FincaError('hoy ya vendiste el tope de bultos')
    buyer = config['buyer']
    if not guarded_move(purse, coin, buyer, account, price):
        raise FincaError('la Casa de Contratación no tiene monedas para comprar')
    prev = bag.get('hash') or ''
    digest = _sha({'kind': 'venta', 'place': 'vendido', 'prev': prev, 'serial': bag['serial'], 'who': _pseudo(state, buyer)})
    bag.setdefault('chain', []).append({'kind': 'venta', 'hash': digest, 'prev': prev, 'place': 'vendido'})
    bag['hash'] = digest
    bag['owner'] = buyer
    bag['place'] = 'vendido'
    box['soldCount'] = int(box.get('soldCount') or 0) + 1
    state['soldBags'][bag['crop']] = int(state['soldBags'].get(bag['crop']) or 0) + 1
    name = 'café' if bag['crop'] == 'cafe' else 'cacao'
    _log(state, 'venta', account, now, f'Se vendió 1 bulto de {name}.', crop=bag['crop'], serial=bag['serial'], prev=prev, digest=digest, counterparty=buyer, coin=coin, amount=price)
    return {'serial': serial, 'coin': coin, 'amount': price}


def deposit(state, config, account, serial, now):
    bag = _bag_owned(state, serial, account, 'mochila')
    _move_place(state, bag, account, 'banco', now, 'deposito', 'Se guardó 1 bulto en el banco.')
    return serial


def withdraw(state, config, account, serial, now):
    bag = state['bags'].get(serial)
    if not bag or bag.get('owner') != account or bag.get('place') != 'banco':
        raise FincaError('ese bulto no está en el banco')
    _move_place(state, bag, account, 'mochila', now, 'retiro', 'Se retiró 1 bulto del banco.')
    return serial


def _move_place(state, bag, account, place, now, kind, text):
    prev = bag.get('hash') or ''
    digest = _sha({'kind': kind, 'place': place, 'prev': prev, 'serial': bag['serial'], 'who': _pseudo(state, account)})
    bag.setdefault('chain', []).append({'kind': kind, 'hash': digest, 'prev': prev, 'place': place})
    bag['hash'] = digest
    bag['place'] = place
    name = 'café' if bag['crop'] == 'cafe' else 'cacao'
    if kind == 'deposito':
        text = f'Se guardó 1 bulto de {name}.'
    elif kind == 'retiro':
        text = f'Se retiró 1 bulto de {name}.'
    _log(state, kind, account, now, text, crop=bag['crop'], serial=bag['serial'], prev=prev, digest=digest)


def handoff_bag(state, serial, src, dst, now):
    """Pasa un bulto de una cuenta a otra. No crea monedas ni lingotes.

    tools/trades.py puede llamar esto cuando entre a main. Aquí no hay ofertas.
    """
    bag = _bag_owned(state, serial, src, 'mochila')
    if not dst or dst == src:
        raise FincaError('el pase necesita otra cuenta')
    prev = bag.get('hash') or ''
    digest = _sha({'kind': 'pase', 'place': 'mochila', 'prev': prev, 'serial': serial, 'who': _pseudo(state, dst)})
    bag.setdefault('chain', []).append({'kind': 'pase', 'hash': digest, 'prev': prev, 'place': 'mochila'})
    bag['hash'] = digest
    bag['owner'] = dst
    name = 'café' if bag['crop'] == 'cafe' else 'cacao'
    _log(state, 'pase', src, now, f'Se pasó 1 bulto de {name}.', crop=bag['crop'], serial=serial, prev=prev, digest=digest, counterparty=dst)
    return serial


def _balances(purse, config):
    buyer = config['buyer']
    out = {}
    for coin in COINS:
        out[coin] = int(purse.balance(coin, buyer) or 0)
    out['simoncoinText'] = economy.format_pair(out['simoncoin'])
    out['simonplataText'] = plata.format_pair(out['simonplata'])
    out['simonchisText'] = f'{out["simonchis"]} Simonchis'
    return out


def _circulation(state, crop):
    return sum(1 for bag in state['bags'].values() if bag.get('crop') == crop and bag.get('place') != 'vendido')


def public_payload(state, purse, config):
    """Totales y frases anónimas. Sin cuentas, sin contrapartes, sin series privadas de dueño."""
    crops = {}
    for crop in CROPS:
        spec = config['crops'][crop]
        crops[crop] = {
            'name': spec['name'],
            'freshName': spec.get('freshName') or spec.get('harvestName') or '',
            'kgPerHarvest': int(spec.get('kgPerHarvest') or 0),
            'sackKg': int(spec.get('bagKg') or 0),
            'unitCount': spec.get('unitCount') or 'bultos procesados',
            'harvestedKg': int(state['harvestedKg'].get(crop) or 0),
            'processedBags': int(state['processedBags'].get(crop) or 0),
            'circulation': _circulation(state, crop),
            'sold': int(state['soldBags'].get(crop) or 0),
        }
    feed = [str(line) for line in (state.get('feed') or [])[:40]]
    events = []
    for row in state.get('publicEvents') or []:
        events.append({
            'id': row.get('id'),
            'kind': row.get('kind'),
            'ts': row.get('ts'),
            'crop': row.get('crop') or '',
            'kg': int(row.get('kg') or 0),
            'totalKg': int(row.get('totalKg') or 0),
            'serial': row.get('serial') or '',
            'prev': row.get('prev') or '',
            'hash': row.get('hash') or '',
            'note': row.get('note') or '',
        })
    return {
        'buyerName': config.get('buyerName') or '',
        'buyerBalances': _balances(purse, config),
        'crops': crops,
        'harvestedKg': {crop: crops[crop]['harvestedKg'] for crop in CROPS},
        'processedBags': {crop: crops[crop]['processedBags'] for crop in CROPS},
        'feed': feed,
        'events': events[-40:],
    }


def attach_public(ledger, state, purse, config):
    """Suma la finca a los contadores que ya publica el libro. No toca la acuñación."""
    body = dict(ledger or {})
    body['finca'] = public_payload(state, purse, config)
    return body


def private_payload(state):
    return {
        'events': list(state.get('privateEvents') or []),
        'harvestedKg': dict(state.get('harvestedKg') or {}),
        'processedBags': dict(state.get('processedBags') or {}),
    }


def player_view(state, config, account, purse, now):
    box = _account(state, config, account)
    _tick_all(state, box, now, config, account)
    plots = []
    for plot_id, plot in box['plots'].items():
        migrate_plot(plot, now, config)
        plots.append({
            'id': plot_id,
            'crop': plot['crop'],
            'stage': stage_of(plot, now, config),
            'phase': phase_of(plot, now, config),
            'plantedAt': int(plot.get('plantedAt') or 0),
        })
    bags = []
    bank = []
    for bag in state['bags'].values():
        if bag.get('owner') != account:
            continue
        row = {
            'serial': bag['serial'],
            'crop': bag['crop'],
            'kg': bag['kg'],
            'product': bag['product'],
            'hash': bag['hash'],
            'place': bag['place'],
        }
        if bag.get('place') == 'banco':
            bank.append(row)
        elif bag.get('place') == 'mochila':
            bags.append(row)
    batches = {}
    for crop, batch in (box.get('batches') or {}).items():
        steps = _steps(config['crops'][crop])
        index = int(batch.get('step') or 0)
        batches[crop] = {
            'step': steps[index]['label'] if index < len(steps) else '',
            'readyAt': int(batch.get('readyAt') or 0),
            'settled': bool(batch.get('settled')),
        }
    day = int(now) // 86400
    sold = int(box.get('soldCount') or 0) if int(box.get('soldDay') or 0) == day else 0
    return {
        'plots': plots,
        'goods': {key: int(value) for key, value in (box.get('goods') or {}).items()},
        'bags': bags,
        'bank': bank,
        'batches': batches,
        'harvestedKg': dict(state['harvestedKg']),
        'processedBags': dict(state['processedBags']),
        'buyerName': config.get('buyerName') or '',
        'buyerBalances': _balances(purse, config),
        'soldToday': sold,
        'sellCap': int(config.get('dailySellCapBags') or 0),
        'harvestsPerBatch': int(config.get('harvestsPerBatch') or 10),
        'bagsPerBatch': int(config.get('bagsPerBatch') or 2),
        'stepSeconds': int(config.get('stepSeconds') or 8),
        'ripeningNote': ((config.get('ripening') or {}).get('note') or ''),
        'crops': {
            crop: {
                'name': spec['name'],
                'harvestName': spec['harvestName'],
                'freshName': spec.get('freshName') or '',
                'kgPerHarvest': int(spec.get('kgPerHarvest') or 0),
                'bagKg': int(spec.get('bagKg') or 0),
                'note': spec.get('note') or '',
                'steps': [step['label'] for step in _steps(spec)],
                'eduSteps': [step.get('label') or step.get('id') for step in ((config.get('edu') or {}).get(crop) or [])],
                'prices': spec.get('prices') or {},
            }
            for crop, spec in config['crops'].items()
        },
    }


def act(state, purse, config, account, op, args, now, present=True):
    args = args or {}
    if op != 'ver' and not present:
        return {'ok': False, 'error': 'Hay que estar en Las Palmas, junto a los talleres.', 'changed': False, 'movedCoins': False}
    if op != 'ver' and not account:
        return {'ok': False, 'error': 'Entra con tu cuenta para cultivar.', 'changed': False, 'movedCoins': False}
    moved = fund_buyer(state, purse, config) if purse else False
    changed = bool(moved)
    try:
        if account and op != 'procesar':
            box = _account(state, config, account)
            if _tick_all(state, box, now, config, account):
                changed = True
        if op == 'ver':
            pass
        elif op == 'plantar':
            plant(state, config, account, str(args.get('plot') or ''), now)
            changed = True
        elif op == 'cosechar':
            harvest(state, config, account, str(args.get('plot') or ''), now)
            changed = True
        elif op == 'procesar':
            process(state, config, account, str(args.get('crop') or ''), now)
            changed = True
        elif op == 'vender':
            sell(state, purse, config, account, str(args.get('serial') or ''), str(args.get('coin') or ''), now)
            changed = True
            moved = True
        elif op == 'depositar':
            deposit(state, config, account, str(args.get('serial') or ''), now)
            changed = True
        elif op == 'retirar':
            withdraw(state, config, account, str(args.get('serial') or ''), now)
            changed = True
        else:
            return {'ok': False, 'error': 'esa acción no existe', 'changed': changed, 'movedCoins': moved}
    except FincaError as exc:
        return {'ok': False, 'error': str(exc), 'changed': changed, 'movedCoins': moved, 'view': player_view(state, config, account, purse, now) if account else None}
    view = player_view(state, config, account, purse, now) if account else None
    return {'ok': True, 'error': '', 'changed': changed, 'movedCoins': moved, 'view': view}
