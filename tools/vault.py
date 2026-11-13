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
    if not os.path.isfile(path):
        state = empty()
        save(path, state)
        return state
    with open(path, encoding='utf-8') as handle:
        state = json.load(handle)
    state.setdefault('accounts', {})
    return state


def save(path, state):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(state, handle, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def account(state, name):
    box = state.setdefault('accounts', {}).setdefault(name, {'smcSubs': 0, 'items': {}})
    box.setdefault('smcSubs', 0)
    box.setdefault('items', {})
    return box


def public_account(box):
    return {'smcSubs': int(box.get('smcSubs') or 0), 'items': dict(box.get('items') or {})}


def add_smc(box, subs):
    box['smcSubs'] = int(box.get('smcSubs') or 0) + int(subs)


def take_smc(box, subs):
    have = int(box.get('smcSubs') or 0)
    if have < int(subs):
        return False
    box['smcSubs'] = have - int(subs)
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
