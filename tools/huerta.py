# SPDX-License-Identifier: AGPL-3.0-or-later
"""Huerta vacía de Las Palmas, aparte del cafetal y del cacaotal.

Ocho eras empiezan sin mata. La semilla sale de la mochila y el fruto
vuelve a la mochila. El reloj es el de la finca: siembra, crecimiento,
floración, fruto y cosecha. No crea kilos del Libro ni monedas.
"""
from __future__ import annotations

import mochila
import reloj

BEDS = 8
CROPS = {
    'manzana': {'seed': 'manzana_seed', 'item': 'manzana', 'qty': 2, 'name': 'Manzana'},
    'pera': {'seed': 'pera_seed', 'item': 'pera', 'qty': 2, 'name': 'Pera'},
    'naranja': {'seed': 'naranja_seed', 'item': 'naranja', 'qty': 2, 'name': 'Naranja'},
    'mango': {'seed': 'mango_seed', 'item': 'mango', 'qty': 2, 'name': 'Mango'},
    'banano': {'seed': 'banano_seed', 'item': 'banano', 'qty': 2, 'name': 'Banano'},
    'coco': {'seed': 'coco_seed', 'item': 'coco', 'qty': 1, 'name': 'Coco'},
    'cafe': {'seed': 'cafe_seed', 'item': 'cafe_cereza', 'qty': 1, 'name': 'Café'},
    'cacao': {'seed': 'cacao_seed', 'item': 'cacao_baba', 'qty': 1, 'name': 'Cacao'},
}
BY_SEED = {spec['seed']: crop for crop, spec in CROPS.items()}


def ripe_seconds(config):
    days = float((config or {}).get('ripeAfterDays') or 2)
    return days * float(reloj.REAL_SECONDS_PER_DAY)


def ensure(box):
    """Ocho eras vacías. No siembra nada solo."""
    beds = box.setdefault('huerta', {})
    if not isinstance(beds, dict):
        beds = {}
        box['huerta'] = beds
    for index in range(1, BEDS + 1):
        key = 'huerta-%d' % index
        row = beds.get(key)
        if not isinstance(row, dict):
            beds[key] = {'crop': '', 'plantedAt': 0}
            continue
        row['crop'] = str(row.get('crop') or '')
        if row['crop'] not in CROPS:
            row['crop'] = ''
        try:
            row['plantedAt'] = int(row.get('plantedAt') or 0)
        except (TypeError, ValueError):
            row['plantedAt'] = 0
        if not row['crop']:
            row['plantedAt'] = 0
    return beds


def seed_counts(bag):
    bag = bag or {}
    found = {}
    for crop, spec in CROPS.items():
        try:
            qty = int(bag.get(spec['seed']) or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty > 0:
            found[spec['seed']] = {'crop': crop, 'name': spec['name'], 'qty': qty}
    return found


def rows(box, now, config):
    import finca

    beds = ensure(box)
    ripe = ripe_seconds(config) or 1.0
    out = []
    for index in range(1, BEDS + 1):
        key = 'huerta-%d' % index
        plot = beds[key]
        crop = plot.get('crop') or ''
        planted = int(plot.get('plantedAt') or 0)
        if crop and planted:
            stage = finca.stage_of(plot, now, config)
            phase = finca.phase_of(plot, now, config)
            progress = max(0.0, min(1.0, (float(now) - planted) / ripe))
        else:
            stage = 'vacio'
            phase = 'vacio'
            progress = 0.0
        spec = CROPS.get(crop) or {}
        out.append({
            'id': key,
            'crop': crop,
            'name': spec.get('name') or '',
            'stage': stage,
            'phase': phase,
            'plantedAt': planted,
            'progress': round(progress, 4),
            'ready': phase == 'cosecha',
        })
    return out


def _bed(box, bed_id):
    import finca

    beds = ensure(box)
    key = str(bed_id or '')
    if key not in beds:
        raise finca.FincaError('Esa era no está en la huerta.')
    return beds[key]


def plant(state, config, account, bed_id, seed, bag, now):
    """Gasta una semilla de la mochila. La era tiene que estar vacía."""
    import finca

    if bag is None:
        raise finca.FincaError('Entra con tu cuenta para sembrar.')
    crop = BY_SEED.get(str(seed or ''))
    if not crop:
        raise finca.FincaError('Esa semilla no se siembra en la huerta.')
    box = state['accounts'].setdefault(account, {})
    row = _bed(box, bed_id)
    if row.get('crop') and row.get('plantedAt'):
        raise finca.FincaError('Esa era ya tiene una mata.')
    spec = CROPS[crop]
    have = int(bag.get(spec['seed']) or 0)
    if have < 1:
        raise finca.FincaError('No tienes esa semilla en la mochila.')
    left = have - 1
    if left:
        bag[spec['seed']] = left
    else:
        bag.pop(spec['seed'], None)
    row['crop'] = crop
    row['plantedAt'] = int(now)
    name = spec['name']
    return {
        'note': 'Sembraste %s en la huerta. El servidor lleva el reloj.' % name.lower(),
        'spent': {'item': spec['seed'], 'qty': 1},
    }


def harvest(state, config, account, bed_id, bag, now):
    """El fruto entra en la mochila y la era queda vacía."""
    import finca

    if bag is None:
        raise finca.FincaError('Entra con tu cuenta para cosechar.')
    box = state['accounts'].setdefault(account, {})
    row = _bed(box, bed_id)
    if not row.get('crop') or not row.get('plantedAt'):
        raise finca.FincaError('Esa era está vacía.')
    if finca.phase_of(row, now, config) != 'cosecha':
        raise finca.FincaError('Todavía no está para cosechar.')
    spec = CROPS[row['crop']]
    item = spec['item']
    qty = int(spec['qty'])
    snapshot = {key: int(value or 0) for key, value in bag.items()}
    if not mochila.fits(snapshot, item, qty):
        raise finca.FincaError(mochila.FULL)
    bag[item] = int(bag.get(item) or 0) + qty
    name = spec['name']
    row['crop'] = ''
    row['plantedAt'] = 0
    return {
        'note': 'Cosechaste %s. Quedó en la mochila y la era volvió a quedar vacía.' % name.lower(),
        'gained': {'item': item, 'qty': qty, 'name': name},
    }
