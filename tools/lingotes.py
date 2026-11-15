# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lingotes del Banco Central.

Una cuenta corriente no los funde. Sólo el dueño o un papel de personal,
y sólo dentro del Banco Central. Cada barra sale con serie y queda
encadenada al hash anterior. No se crea Simoncoin, Simonplata ni Simonchis.
El único llamador que puede pasar autorizado=True es server.lingote_for.
"""
import hashlib
import json

import monedas
import social

ZONE = 'central'
METALES = ('oro', 'plata', 'cobre')
ITEMS = {'oro': 'lingote_oro', 'plata': 'lingote_plata', 'cobre': 'lingote_cobre'}
PREFIX = {'oro': 'LGO', 'plata': 'LGP', 'cobre': 'LGC'}
MAX_QTY = 12
ROLES = ('simon', 'staff', 'admin')
GENESIS = '0' * 64
REFUSALS = []


def autorizado(user):
    return social.role_of(user) in ROLES


def rechazar(user, zone):
    if not autorizado(user):
        return 'Esta ventanilla no está abierta para esta cuenta.'
    if str(zone or '') != ZONE:
        return 'Los lingotes se funden en el Banco Central.'
    return ''


def anotar_rechazo(via, role, zone, reason):
    """Deja el rechazo en memoria y en el registro del proceso. Sin correo ni clave."""
    row = {
        'via': str(via or ''),
        'role': str(role or 'player'),
        'zone': str(zone or ''),
        'reason': str(reason or ''),
    }
    REFUSALS.append(row)
    del REFUSALS[:-80]
    print(
        '[lingotes] rechazo via=%s rol=%s zona=%s motivo=%s' % (
            row['via'], row['role'], row['zone'], row['reason'],
        ),
        flush=True,
    )
    return row


def _box(state):
    box = state.get('foundry')
    if not isinstance(box, dict):
        box = {}
        state['foundry'] = box
    box.setdefault('minted', {})
    box.setdefault('players', {})
    nxt = box.get('next')
    if not isinstance(nxt, dict):
        nxt = {}
        box['next'] = nxt
    for metal in METALES:
        nxt.setdefault(metal, 1)
    if not isinstance(box.get('serials'), list):
        box['serials'] = []
    if not isinstance(box.get('history'), list):
        box['history'] = []
    return box


def reserva(state):
    minted = {}
    box = state.get('foundry')
    if isinstance(box, dict) and isinstance(box.get('minted'), dict):
        minted = box['minted']
    return {metal: int(minted.get(ITEMS[metal]) or 0) for metal in METALES}


def vista(state):
    box = _box(state)
    return {
        'reserve': reserva(state),
        'history': list(box['history'])[-12:],
        'serials': list(box['serials'])[-12:],
    }


def publico(state):
    """Totales por metal para el Libro mayor. Sin nombres ni series."""
    counts = reserva(state)
    box = state.get('foundry') if isinstance(state.get('foundry'), dict) else {}
    return {
        'oro': counts['oro'],
        'plata': counts['plata'],
        'cobre': counts['cobre'],
        'head': str((box or {}).get('head') or ''),
    }


def _encadenar(box, row):
    prev = str(box.get('head') or GENESIS)
    body = dict(row)
    body['prev'] = prev
    raw = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    body['hash'] = digest
    chain = box.setdefault('chain', [])
    chain.append(body)
    box['chain'] = chain[-400:]
    box['head'] = digest
    return body


def fundir(state, name, metal, qty, now, autorizado=False):
    if not autorizado:
        raise PermissionError('lingote')
    metal = str(metal or '')
    if metal not in ITEMS:
        raise ValueError('metal')
    qty = int(qty)
    if qty < 1 or qty > MAX_QTY:
        raise ValueError('qty')
    box = _box(state)
    made = []
    for _ in range(qty):
        number = int(box['next'].get(metal) or 1)
        box['next'][metal] = number + 1
        serial = '%s-%06d' % (PREFIX[metal], number)
        entry = _encadenar(box, {
            'serial': serial,
            'metal': metal,
            'item': ITEMS[metal],
            'at': int(now or 0),
        })
        box['serials'].append({
            'serial': serial,
            'metal': metal,
            'item': ITEMS[metal],
            'at': int(now or 0),
            'by': str(name or ''),
            'hash': entry['hash'],
            'prev': entry['prev'],
        })
        made.append(serial)
    box['serials'] = box['serials'][-200:]
    monedas.anotar_lingotes(state, name, ITEMS[metal], qty)
    box['history'].append({
        'at': int(now or 0),
        'by': str(name or ''),
        'metal': metal,
        'qty': qty,
        'serials': made,
    })
    box['history'] = box['history'][-40:]
    return {
        'item': ITEMS[metal],
        'metal': metal,
        'qty': qty,
        'serials': made,
        'reserve': reserva(state),
        'history': list(box['history'])[-12:],
        'head': box.get('head') or '',
    }
