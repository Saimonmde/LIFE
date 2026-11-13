# SPDX-License-Identifier: AGPL-3.0-or-later
"""Libro madre: cada acuñación de SMC es un registro único e irrepetible.

Simulación educativa. No es dinero real, no tiene valor ni se canjea.
La cadena vive en Postgres (almacén libro_madre) o, sin DATABASE_URL, en state/libro-madre.json.
Los códigos reservados no se reutilizan: en Postgres hay una clave única; en disco, un conjunto.
"""
import hashlib
import json
import os
import time

import economy
import ed25519
import persist

GENESIS = '0' * 64
KINDS_MINT = ('acuñacion', 'genesis', 'migracion')
KIND_MOVE = 'transferencia'
DISCLAIMER = (
    'Libro madre de SaiMonCoins (SMC): simulación educativa. '
    'Cada acuñación es un registro único e irrepetible, como una pieza de minería. '
    'No es dinero real, no tiene valor ni se puede canjear.'
)
MAX_SUBS = economy.subunits(economy.MAX_SUPPLY)


class LibroError(Exception):
    pass


def dificultad():
    raw = os.environ.get('LIBRO_DIFICULTAD', '').strip()
    try:
        value = int(raw) if raw else 12
    except ValueError:
        value = 12
    return max(1, min(20, value))


def bits_cero(digest):
    n = 0
    for byte in digest:
        if byte == 0:
            n += 8
            continue
        return n + (8 - byte.bit_length())
    return n


def empty(pubkey_hex):
    return {
        'pubkey': pubkey_hex,
        'blocks': [],
        'ids': [],
        'disclaimer': DISCLAIMER,
        'symbol': economy.SYMBOL,
        'maxSupply': economy.MAX_SUPPLY,
    }


def load(path, pubkey_hex):
    doc = persist.load_named('libro_madre', path)
    if not isinstance(doc, dict):
        doc = empty(pubkey_hex)
    doc['pubkey'] = pubkey_hex
    doc['disclaimer'] = DISCLAIMER
    doc['symbol'] = economy.SYMBOL
    doc['maxSupply'] = economy.MAX_SUPPLY
    blocks = doc.get('blocks') or []
    ids = []
    for block in blocks:
        ident = block.get('id')
        if ident and ident not in ids:
            ids.append(ident)
    doc['blocks'] = blocks
    doc['ids'] = ids
    persist.remember_ids(os.path.dirname(path) or '.', ids)
    return doc


def save(path, chain, new_ids):
    persist.save_reserved('libro_madre', path, chain, new_ids)


def cupo_subs(chain):
    return max(0, MAX_SUBS - _emitido(chain))


def _emitido(chain):
    total = 0
    for block in chain.get('blocks') or []:
        if block.get('kind') in KINDS_MINT:
            total += int(block.get('amountSmh') or 0)
    return total


def balances(chain):
    """Saldo = acuñaciones cuya dueña es la cuenta + transferencias recibidas − enviadas."""
    got = {}

    def add(name, delta):
        if not name:
            return
        got[name] = got.get(name, 0) + int(delta)

    for block in chain.get('blocks') or []:
        if block.get('kind') == KIND_MOVE:
            add(block.get('from'), -int(block.get('amountSmh') or 0))
            add(block.get('to'), int(block.get('amountSmh') or 0))
        else:
            add(block.get('owner'), int(block.get('amountSmh') or 0))
    return got


def _fields(kind, height, amount_subs, owner, miner, location, ts, nonce, prev, origen, destino, bits):
    return {
        'kind': kind,
        'height': int(height),
        'amountSmh': int(amount_subs),
        'owner': owner or '',
        'miner': miner or '',
        'location': location or '',
        'ts': int(ts),
        'nonce': int(nonce),
        'prev': prev,
        'from': origen or '',
        'to': destino or '',
        'difficulty': int(bits),
    }


def canonico(fields):
    return json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _probar(fields_of, bits, presupuesto):
    """Busca un nonce. Si se acaba el tiempo, baja un bit para no frenar el servidor."""
    bits = max(1, int(bits))
    inicio = time.perf_counter()
    nonce = 0
    while True:
        payload = canonico(fields_of(nonce, bits))
        digest = hashlib.sha256(payload).digest()
        if bits_cero(digest) >= bits:
            return nonce, bits, payload, digest
        nonce += 1
        if nonce % 1024 == 0 and time.perf_counter() - inicio > presupuesto and bits > 1:
            bits -= 1
        if nonce > 2_000_000:
            raise LibroError('la prueba de trabajo no encontró nonce a tiempo')


def _codigo(kind, height, digest):
    short = digest.hex()[:8].upper()
    prefix = 'SMC' if kind in KINDS_MINT else 'MOV'
    return f'{prefix}-{int(height)}-{short}'


def _firmar(chain, seed, kind, amount_subs, owner, miner, location, origen, destino, ts, bits, presupuesto):
    blocks = chain.setdefault('blocks', [])
    height = len(blocks) + 1
    prev = blocks[-1]['hash'] if blocks else GENESIS
    ts = int(ts if ts is not None else time.time())

    def fields_of(nonce, used_bits):
        return _fields(kind, height, amount_subs, owner, miner, location, ts, nonce, prev, origen, destino, used_bits)

    if bits <= 0:
        payload = canonico(fields_of(0, 0))
        digest = hashlib.sha256(payload).digest()
        nonce, used = 0, 0
    else:
        nonce, used, payload, digest = _probar(fields_of, bits, presupuesto)
    ident = _codigo(kind, height, digest)
    if ident in set(chain.get('ids') or []):
        raise LibroError('ese código ya existe y no se vuelve a emitir')
    record = fields_of(nonce, used)
    record['id'] = ident
    record['hash'] = digest.hex()
    record['sig'] = ed25519.sign(payload, seed).hex()
    chain.setdefault('ids', []).append(ident)
    blocks.append(record)
    return record


def acuñar(chain, seed, owner, amount_subs, location, ts=None, bits=None, presupuesto=0.025, kind='acuñacion'):
    """Crea una acuñación. None si no cabe en el tope de 21.000.000 SMC."""
    amount_subs = int(amount_subs or 0)
    if amount_subs <= 0:
        return None
    if kind not in KINDS_MINT:
        raise LibroError('tipo de acuñación desconocido')
    if amount_subs > cupo_subs(chain):
        return None
    bits = dificultad() if bits is None else int(bits)
    if bits < 1:
        raise LibroError('la acuñación necesita prueba de trabajo')
    return _firmar(
        chain, seed, kind, amount_subs, owner, owner, location, '', '', ts, bits, presupuesto,
    )


def transferir(chain, seed, origen, destino, amount_subs, note, ts=None):
    amount_subs = int(amount_subs or 0)
    if amount_subs <= 0:
        raise LibroError('la transferencia tiene que ser mayor que cero')
    if not origen or not destino or origen == destino:
        raise LibroError('la transferencia necesita dos cuentas distintas')
    have = balances(chain).get(origen, 0)
    if have < amount_subs:
        raise LibroError('el libro madre no tiene saldo para esa transferencia')
    return _firmar(
        chain, seed, KIND_MOVE, amount_subs, destino, '', note or 'transferencia',
        origen, destino, ts, 0, 0.025,
    )


def revertir(chain, record):
    if not record:
        return
    blocks = chain.get('blocks') or []
    if blocks and blocks[-1].get('id') == record.get('id'):
        blocks.pop()
    ids = chain.get('ids') or []
    if record.get('id') in ids:
        ids.remove(record.get('id'))


def migrar(chain, seed, wallets, vault_accounts, ts=None, bits=None, presupuesto=0.025):
    """Crea registros de génesis o migración por la diferencia, sin cambiar los saldos dados."""
    explained = balances(chain)
    holdings = {}
    for name, subs in (wallets or {}).items():
        holdings[str(name)] = int(subs or 0)
    for name, box in (vault_accounts or {}).items():
        box = box or {}
        holdings['deposito:' + str(name)] = int(box.get('smh') if box.get('smh') is not None else (box.get('smcSubs') or 0))
    created = []
    base = int(ts if ts is not None else time.time())
    for index, (name, subs) in enumerate(sorted(holdings.items())):
        delta = subs - int(explained.get(name) or 0)
        if delta <= 0:
            continue
        if name == 'tesoro_genesis' and not any(b.get('kind') == 'genesis' for b in chain.get('blocks') or []):
            kind, place = 'genesis', 'Génesis del tesoro'
        elif name.startswith('deposito:'):
            kind, place = 'migracion', 'Migración del depósito'
        else:
            kind, place = 'migracion', 'Migración de saldos'
        record = acuñar(
            chain, seed, name, delta, place, ts=base + index, bits=bits, presupuesto=presupuesto, kind=kind,
        )
        if record is None:
            raise LibroError('la migración no cabe en el tope de 21.000.000 SMC')
        created.append(record)
        explained[name] = explained.get(name, 0) + delta
    return created


def publico(record):
    if not record:
        return None
    return {
        'id': record.get('id'),
        'kind': record.get('kind'),
        'height': record.get('height'),
        'amountSmh': int(record.get('amountSmh') or 0),
        'amountText': economy.format_pair(record.get('amountSmh') or 0),
        'miner': record.get('miner') or '',
        'owner': record.get('owner') or '',
        'location': record.get('location') or '',
        'from': record.get('from') or '',
        'to': record.get('to') or '',
        'ts': record.get('ts'),
        'nonce': record.get('nonce'),
        'difficulty': record.get('difficulty'),
        'prev': record.get('prev'),
        'hash': record.get('hash'),
        'sig': record.get('sig'),
    }


def _payload(record):
    return canonico(_fields(
        record.get('kind'), record.get('height'), record.get('amountSmh'),
        record.get('owner'), record.get('miner'), record.get('location'),
        record.get('ts'), record.get('nonce'), record.get('prev'),
        record.get('from'), record.get('to'), record.get('difficulty'),
    ))


def _firma_ok(record, pubkey):
    payload = _payload(record)
    digest = hashlib.sha256(payload).digest()
    if digest.hex() != record.get('hash'):
        return False, 'el hash no coincide'
    ident = _codigo(record.get('kind'), record.get('height'), digest)
    if ident != record.get('id'):
        return False, 'el código no corresponde al hash'
    bits = int(record.get('difficulty') or 0)
    if record.get('kind') in KINDS_MINT and bits < 1:
        return False, 'la acuñación no tiene prueba de trabajo'
    if bits_cero(digest) < bits:
        return False, 'la prueba de trabajo no alcanza'
    try:
        sig = bytes.fromhex(record.get('sig') or '')
    except ValueError:
        return False, 'firma ilegible'
    if not ed25519.verify(sig, payload, pubkey):
        return False, 'firma inválida'
    return True, 'válido'


def verificar(chain, pubkey_hex=None):
    pubkey_hex = pubkey_hex or chain.get('pubkey')
    try:
        pubkey = bytes.fromhex(pubkey_hex or '')
    except ValueError:
        return False, 'clave pública ilegible'
    if len(pubkey) != 32:
        return False, 'clave pública inválida'
    prev = GENESIS
    seen = set()
    total = 0
    blocks = chain.get('blocks') or []
    for index, record in enumerate(blocks):
        ident = record.get('id')
        if not ident or ident in seen:
            return False, f'código repetido o vacío en la altura {record.get("height")}'
        seen.add(ident)
        if int(record.get('height') or 0) != index + 1:
            return False, f'altura rota en {ident}'
        if record.get('prev') != prev:
            return False, f'eslabón roto en {ident}'
        ok, why = _firma_ok(record, pubkey)
        if not ok:
            return False, f'{why} en {ident}'
        if record.get('kind') in KINDS_MINT:
            total += int(record.get('amountSmh') or 0)
        prev = record.get('hash')
    if total > MAX_SUBS:
        return False, 'la emisión supera 21.000.000 SMC'
    return True, f'{len(blocks)} bloques, {economy.format_smc(total)} emitidas'


def verificar_uno(chain, ident, pubkey_hex=None):
    pubkey_hex = pubkey_hex or chain.get('pubkey')
    try:
        pubkey = bytes.fromhex(pubkey_hex or '')
    except ValueError:
        pubkey = b''
    want = str(ident or '')
    found = None
    prev = GENESIS
    for record in chain.get('blocks') or []:
        if str(record.get('id') or '').lower() == want.lower():
            found = record
            break
        prev = record.get('hash')
    if not found:
        return None
    if found.get('prev') != prev:
        ok, why = False, 'eslabón roto'
    elif len(pubkey) != 32:
        ok, why = False, 'clave pública inválida'
    else:
        ok, why = _firma_ok(found, pubkey)
    pub = publico(found)
    pub['verificado'] = bool(ok)
    pub['motivo'] = why
    return pub


def pagina(chain, pagina=1, limite=20):
    try:
        pagina = max(1, int(pagina or 1))
    except (TypeError, ValueError):
        pagina = 1
    try:
        limite = min(50, max(1, int(limite or 20)))
    except (TypeError, ValueError):
        limite = 20
    blocks = list(reversed(chain.get('blocks') or []))
    start = (pagina - 1) * limite
    chunk = blocks[start:start + limite]
    pages = max(1, (len(blocks) + limite - 1) // limite)
    items = []
    for record in chunk:
        uno = verificar_uno(chain, record.get('id'))
        items.append(uno or publico(record))
    return {
        'disclaimer': DISCLAIMER,
        'symbol': economy.SYMBOL,
        'maxSupply': economy.MAX_SUPPLY,
        'supplySmh': _emitido(chain),
        'supply': economy.format_smc(_emitido(chain)),
        'height': len(chain.get('blocks') or []),
        'pagina': pagina,
        'paginas': pages,
        'limite': limite,
        'blocks': items,
    }


def _consulta(query, keys, default):
    for key in keys:
        if key not in (query or {}):
            continue
        value = query[key]
        if isinstance(value, list):
            value = value[0] if value else default
        return value
    return default


def api_get(path, query, chain):
    """Respuesta pública. path es /api/libro, /api/libro/verificar o /api/libro/<id>."""
    clean = path.rstrip('/') or '/api/libro'
    if clean == '/api/libro':
        return 200, pagina(chain, _consulta(query, ('pagina', 'page'), 1), _consulta(query, ('limite', 'limit'), 20))
    if clean == '/api/libro/verificar':
        ok, message = verificar(chain)
        return 200, {
            'ok': ok,
            'mensaje': message,
            'height': len(chain.get('blocks') or []),
            'supplySmh': _emitido(chain),
            'supply': economy.format_smc(_emitido(chain)),
            'disclaimer': DISCLAIMER,
            'pubkey': chain.get('pubkey'),
        }
    ident = clean.split('/')[-1]
    found = verificar_uno(chain, ident)
    if not found:
        return 404, {'error': 'no existe', 'disclaimer': DISCLAIMER}
    found['disclaimer'] = DISCLAIMER
    found['pubkey'] = chain.get('pubkey')
    return 200, found
