# SPDX-License-Identifier: AGPL-3.0-or-later
"""Certificados educativos de SMC: cadena de hashes firmada con Ed25519.

No es una cadena pública, no hay gas y el disco de Render no conserva state/.
Cada emisión nueva recibe un código único. Mover SMC al banco no crea certificado.
"""
import hashlib
import json
import os
import time

import ed25519

GENESIS = '0' * 64


def empty_chain(pubkey_hex):
    return {'pubkey': pubkey_hex, 'tokens': [], 'disclaimer': (
        'Certificado educativo de SaiMonCoins. No es un token de una cadena pública, '
        'no se puede vender y no tiene valor real.'
    )}


def load_chain(path, pubkey_hex):
    if not os.path.isfile(path):
        chain = empty_chain(pubkey_hex)
        save_chain(path, chain)
        return chain
    with open(path, encoding='utf-8') as handle:
        chain = json.load(handle)
    chain['pubkey'] = pubkey_hex
    chain.setdefault('tokens', [])
    return chain


def save_chain(path, chain):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(chain, handle, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def load_seed(path):
    """Semilla de 32 bytes. NFT_PRIVATE_KEY (hex) o un archivo en state/, nunca en git."""
    env = os.environ.get('NFT_PRIVATE_KEY', '').strip()
    if env:
        seed = bytes.fromhex(env)
        if len(seed) != 32:
            raise ValueError('NFT_PRIVATE_KEY debe ser 32 bytes en hexadecimal')
        return seed
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as handle:
            seed = bytes.fromhex(json.load(handle)['seed'])
        if len(seed) != 32:
            raise ValueError('la semilla guardada no mide 32 bytes')
        return seed
    seed = os.urandom(32)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump({'seed': seed.hex()}, handle)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return seed


def canonical(token):
    body = {
        'id': token['id'],
        'code': token['code'],
        'owner': token['owner'],
        'amount': token['amount'],
        'ts': token['ts'],
        'tile': token['tile'],
        'foundry': token['foundry'],
        'prev': token['prev'],
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _code_for(owner, amount, prev, ts):
    digest = hashlib.sha256(f'{owner}|{amount}|{prev}|{ts}|{os.urandom(8).hex()}'.encode()).hexdigest()
    return 'SMC-' + digest[:10].upper()


def issue(chain, seed, owner, amount, foundry, tile, now=None):
    """Añade un certificado. amount es SMC (número). Devuelve el registro público."""
    amount = float(amount)
    if amount <= 0:
        return None
    tokens = chain.setdefault('tokens', [])
    prev = tokens[-1]['hash'] if tokens else GENESIS
    ts = int(now if now is not None else time.time())
    token = {
        'id': len(tokens) + 1,
        'code': _code_for(owner, amount, prev, ts),
        'owner': owner,
        'amount': amount,
        'ts': ts,
        'tile': tile,
        'foundry': foundry,
        'prev': prev,
    }
    payload = canonical(token)
    token['hash'] = hashlib.sha256(payload).hexdigest()
    token['sig'] = ed25519.sign(payload, seed).hex()
    tokens.append(token)
    return public_token(token)


def public_token(token):
    return {
        'id': token['id'],
        'code': token['code'],
        'owner': token['owner'],
        'amount': token['amount'],
        'ts': token['ts'],
        'tile': token['tile'],
        'foundry': token['foundry'],
        'prev': token['prev'],
        'hash': token['hash'],
        'sig': token['sig'],
    }


def metadata(token):
    """JSON compatible con los metadatos de ERC-721, por si más adelante se ancla."""
    pub = public_token(token)
    return {
        'name': f"Certificado SMC #{pub['id']}",
        'description': (
            'Certificado educativo de SaiMonCoins (SMC). No es un activo de una cadena pública, '
            'no paga gas y no tiene valor real. El código es único dentro de esta simulación.'
        ),
        'image': None,
        'external_url': None,
        'attributes': [
            {'trait_type': 'code', 'value': pub['code']},
            {'trait_type': 'amount_smc', 'value': pub['amount']},
            {'trait_type': 'owner', 'value': pub['owner']},
            {'trait_type': 'foundry', 'value': pub['foundry']},
            {'trait_type': 'tile', 'value': pub['tile']},
            {'trait_type': 'prev', 'value': pub['prev']},
        ],
        'certificate': pub,
    }


def verify_chain(chain, pubkey_hex=None):
    """Recorre la cadena. Devuelve (ok, mensaje)."""
    pubkey_hex = pubkey_hex or chain.get('pubkey')
    try:
        pubkey = bytes.fromhex(pubkey_hex or '')
    except ValueError:
        return False, 'clave pública ilegible'
    if len(pubkey) != 32:
        return False, 'clave pública inválida'
    prev = GENESIS
    seen = set()
    total = 0.0
    for token in chain.get('tokens') or []:
        code = token.get('code')
        if not code or code in seen:
            return False, f"código repetido o vacío en #{token.get('id')}"
        seen.add(code)
        if token.get('prev') != prev:
            return False, f"eslabón roto en #{token.get('id')}"
        payload = canonical(token)
        if hashlib.sha256(payload).hexdigest() != token.get('hash'):
            return False, f"hash distinto en #{token.get('id')}"
        try:
            sig = bytes.fromhex(token.get('sig') or '')
        except ValueError:
            return False, f"firma ilegible en #{token.get('id')}"
        if not ed25519.verify(sig, payload, pubkey):
            return False, f"firma inválida en #{token.get('id')}"
        total += float(token.get('amount') or 0)
        prev = token['hash']
    return True, f'{len(seen)} certificados, {total} SMC'
