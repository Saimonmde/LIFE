# SPDX-License-Identifier: AGPL-3.0-or-later
"""Depósito compartido: el banquito de la Casa bancaria y el baúl de la casa son la misma cuenta.

Lo guardado aquí no sale del depósito cuando se pierde la mochila. Mover SMC entre la
billetera y el depósito no emite monedas nuevas.
"""
import json
import os


def empty():
    return {'accounts': {}}


def load(path):
    import persist
    state = persist.load_named('vault', path)
    if state is None:
        state = empty()
        save(path, state)
        return state
    state.setdefault('accounts', {})
    return state


def save(path, state):
    import persist
    persist.save_named('vault', path, state)


def smh_of(box):
    if not isinstance(box, dict):
        return 0
    if box.get('smh') is not None:
        return int(box.get('smh') or 0)
    return int(box.get('smcSubs') or 0)


def _sync(box, smh):
    box['smh'] = int(smh)
    box['smcSubs'] = int(smh)
    return box


def account(state, name):
    box = state.setdefault('accounts', {}).setdefault(name, {'smh': 0, 'smcSubs': 0, 'items': {}})
    box.setdefault('items', {})
    _sync(box, smh_of(box))
    return box


def sph_of(box):
    if not isinstance(box, dict):
        return 0
    return int(box.get('sph') or 0)


def add_smp(box, sph):
    box['sph'] = sph_of(box) + int(sph)
    return box['sph']


def take_smp(box, sph):
    have = sph_of(box)
    if have < int(sph):
        return False
    box['sph'] = have - int(sph)
    return True


def public_account(box):
    smh = smh_of(box)
    return {'smh': smh, 'smcSubs': smh, 'sph': sph_of(box), 'items': dict(box.get('items') or {})}


def add_smc(box, smh):
    _sync(box, smh_of(box) + int(smh))


def take_smc(box, smh):
    have = smh_of(box)
    if have < int(smh):
        return False
    _sync(box, have - int(smh))
    return True


def add_item(box, item, qty):
    items = box.setdefault('items', {})
    items[item] = int(items.get(item) or 0) + int(qty)
    return items[item]


def take_item(box, item, qty):
    items = box.setdefault('items', {})
    have = int(items.get(item) or 0)
    if have < int(qty):
        return False
    left = have - int(qty)
    if left:
        items[item] = left
    else:
        items.pop(item, None)
    return True
