# SPDX-License-Identifier: AGPL-3.0-or-later
"""Simonchis: las monedas de cobre.

Hay 333.000.000 y no habrá más. Cada Simonchi es una moneda entera:
no se parte, no se duplica y no se puede subir el tope.
"""
import hashlib
import hmac
import re
import secrets
import time

import topes as TOPES

MAX_SUPPLY = 333_000_000
DAY = 86400
DAILY = 200
CHALLENGE_TTL = 180
BITS = 12


def ensure(state):
    box = state.get('simonchis')
    if not isinstance(box, dict):
        box = {}
        state['simonchis'] = box
    if not box.get('secret'):
        box['secret'] = secrets.token_hex(32)
    box['max'] = MAX_SUPPLY
    box['minted'] = int(box.get('minted') or 0)
    box.setdefault('wallets', {})
    box.setdefault('used', {})
    box.setdefault('earnedDay', {})
    return box


def room(state):
    box = ensure(state)
    return max(0, MAX_SUPPLY - int(box['minted']))


def balance_of(state, name):
    box = state.get('simonchis') or {}
    return int((box.get('wallets') or {}).get(name) or 0)


def _payload(challenge):
    return '|'.join([
        'sch-pow-1',
        str(challenge['id']),
        str(challenge['account']),
        str(challenge['context']),
        str(int(challenge['bits'])),
        str(int(challenge['exp'])),
    ])


def _sign(secret, payload):
    return hmac.new(bytes.fromhex(secret), payload.encode('utf-8'), hashlib.sha256).hexdigest()


def _day_key(account, now):
    return f'{account}:{int(now) // DAY}'


def open_challenge(state, account, context, now=None):
    now = int(time.time() if now is None else now)
    box = ensure(state)
    if not account:
        return {'ok': False, 'reason': 'guest'}
    if room(state) <= 0:
        return {'ok': False, 'reason': 'supply'}
    challenge = {
        'id': secrets.token_hex(8),
        'account': str(account),
        'context': re.sub(r'[^A-Za-z0-9_.:-]', '', str(context or ''))[:80] or 'horno',
        'bits': BITS,
        'personal': 0,
        'exp': now + CHALLENGE_TTL,
        'coin': 'Simonchis',
    }
    challenge['payload'] = _payload(challenge)
    challenge['sig'] = _sign(box['secret'], challenge['payload'])
    return {'ok': True, 'challenge': challenge}


def _leading(hexdigest):
    n = 0
    for ch in str(hexdigest or ''):
        v = int(ch, 16)
        if v == 0:
            n += 4
            continue
        if v < 2:
            return n + 3
        if v < 4:
            return n + 2
        if v < 8:
            return n + 1
        return n
    return n


def redeem(state, account, context, proof, want, now=None, purse=None):
    """Acuña como máximo `want` Simonchis, sin pasar el tope ni el cupo del día."""
    now = int(time.time() if now is None else now)
    box = ensure(state)
    context = re.sub(r'[^A-Za-z0-9_.:-]', '', str(context or ''))[:80] or 'horno'
    if not account:
        return {'ok': False, 'reason': 'guest', 'qty': 0}
    if not isinstance(proof, dict):
        return {'ok': False, 'reason': 'signature', 'qty': 0}
    nonce = str(proof.get('nonce') if proof.get('nonce') is not None else '')
    if not re.fullmatch(r'[0-9]{1,20}', nonce):
        return {'ok': False, 'reason': 'signature', 'qty': 0}
    parsed = {
        'id': str(proof.get('id') or ''),
        'account': str(proof.get('account') or ''),
        'context': re.sub(r'[^A-Za-z0-9_.:-]', '', str(proof.get('context') or ''))[:80] or 'horno',
        'bits': int(proof.get('bits') or 0),
        'exp': int(proof.get('exp') or 0),
    }
    payload = _payload(parsed)
    secret = box.get('secret') or ''
    expected = _sign(secret, payload)
    if not hmac.compare_digest(expected, str(proof.get('sig') or '')):
        return {'ok': False, 'reason': 'signature', 'qty': 0}
    if parsed['exp'] < now:
        return {'ok': False, 'reason': 'expired', 'qty': 0}
    if parsed['id'] in box['used']:
        return {'ok': False, 'reason': 'replay', 'qty': 0}
    if parsed['account'] != str(account) or parsed['context'] != context:
        return {'ok': False, 'reason': 'account', 'qty': 0}
    digest = hashlib.sha256(f'{payload}|{nonce}'.encode('utf-8')).hexdigest()
    if _leading(digest) < parsed['bits']:
        return {'ok': False, 'reason': 'weak', 'qty': 0}
    left = room(state)
    if left <= 0:
        return {'ok': False, 'reason': 'supply', 'qty': 0}
    key = _day_key(account, now)
    earned = int(box['earnedDay'].get(key) or 0)
    today = max(0, TOPES.simonchis_daily() - earned)
    grant = min(max(0, int(want or 0)), left, today)
    if grant <= 0:
        return {'ok': False, 'reason': 'cap', 'qty': 0}
    box['used'][parsed['id']] = parsed['exp']
    box['minted'] = int(box['minted']) + grant
    who = str(purse or account)
    box['wallets'][who] = int(box['wallets'].get(who) or 0) + grant
    box['earnedDay'][key] = earned + grant
    if int(box['minted']) > MAX_SUPPLY:
        box['minted'] = MAX_SUPPLY
    return {'ok': True, 'reason': '', 'qty': grant}


def credit_named(state, name, qty):
    """Suma Simonchis ya concedidas a la billetera visible del jugador."""
    box = ensure(state)
    name = str(name or '')
    qty = int(qty or 0)
    if not name or qty <= 0:
        return 0
    box['wallets'][name] = int(box['wallets'].get(name) or 0) + qty
    return qty
