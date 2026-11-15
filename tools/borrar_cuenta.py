# SPDX-License-Identifier: AGPL-3.0-or-later
"""Borrado de la propia cuenta.

Quita correo, teléfono, contraseña, vínculos de Google y Facebook, nickname,
sesiones y el perfil. El libro mayor conserva cada movimiento, con un
identificador anónimo en lugar del nombre. No toca founderFusion ni
tesoro_genesis. El SMC de la billetera y del depósito pasa al fondo de
cambio (economy.plata.smcPoolSmh). La Plata no tiene reserva: se quema
(burnedSph) y minedSph no cambia, así el tope de 84.000.000 sigue igual.
"""
import hashlib

import accounts as acc
import economy as eco
import ed25519
import fusion
import libro
import nft
import plata
import vault as VAULT

NOTE = 'Saldo de cuenta eliminada devuelto al fondo'
PROTEGIDOS = frozenset(('tesoro_genesis', 'fondo_cambio', 'puesto_frutas'))
IDENTIDAD = ('from', 'to', 'name', 'owner', 'account', 'miner', 'location')


def alias_de(user_id):
    digest = hashlib.sha256(str(user_id or '').encode('utf-8')).hexdigest()[:8]
    return 'cuenta-eliminada-' + digest


def es_fundador(user):
    return str((user or {}).get('email') or '').strip().lower() == fusion.owner_email()


def confirmacion_valida(user, confirm):
    text = str('' if confirm is None else confirm).strip()
    if text == 'ELIMINAR':
        return True
    key = acc.name_key(text)
    if not key:
        return False
    return key in {acc.name_key((user or {}).get('name')), acc.name_key((user or {}).get('wallet_name'))}


def _usuario(accounts, user_id):
    for user in (accounts or {}).get('users') or []:
        if user.get('id') == user_id:
            return user
    return None


def _nombres(user):
    names = []
    for raw in ((user or {}).get('name'), (user or {}).get('wallet_name')):
        name = str(raw or '').strip()
        if name and name not in names and name not in PROTEGIDOS:
            names.append(name)
    return names


def _mapa(names, alias):
    mapping = {}
    for name in names:
        mapping[name] = alias
        mapping['deposito:' + name] = alias
    return mapping


def _cambiar(value, mapping):
    if isinstance(value, str) and value in mapping:
        return mapping[value]
    return value


def _anonimizar(row, mapping):
    if not isinstance(row, dict):
        return False
    changed = False
    for key in IDENTIDAD:
        if key not in row:
            continue
        new = _cambiar(row.get(key), mapping)
        if new != row.get(key):
            row[key] = new
            changed = True
    return changed


def _rehash(state):
    prev = eco.GENESIS_PREV
    for index, block in enumerate(state.get('blocks') or []):
        block['prev'] = eco.GENESIS_PREV if index == 0 else prev
        block['hash'] = eco.hash_block(block['prev'], block['ts'], block['txs'])
        prev = block['hash']


def _resign_libro(chain, seed, mapping):
    blocks = (chain or {}).get('blocks') or []
    if not blocks or seed is None:
        for block in blocks:
            _anonimizar(block, mapping)
        return []
    start = None
    for index, block in enumerate(blocks):
        if _anonimizar(block, mapping) and start is None:
            start = index
    if start is None:
        return []
    new_ids = []
    ids = chain.setdefault('ids', [])
    prev = libro.GENESIS if start == 0 else blocks[start - 1]['hash']
    for index in range(start, len(blocks)):
        block = blocks[index]
        height = int(block.get('height') or (index + 1))
        bits = int(block.get('difficulty') or 0)
        bound_prev = prev

        def fields_of(nonce, used_bits, block=block, height=height, prev=bound_prev):
            return libro._fields(
                block.get('kind'), height, int(block.get('amountSmh') or 0),
                block.get('owner') or '', block.get('miner') or '', block.get('location') or '',
                int(block.get('ts') or 0), nonce, prev,
                block.get('from') or '', block.get('to') or '', used_bits,
            )

        if bits <= 0:
            payload = libro.canonico(fields_of(0, 0))
            digest = hashlib.sha256(payload).digest()
            nonce, used = 0, 0
        else:
            nonce, used, payload, digest = libro._probar(fields_of, bits, 0.25)
        ident = libro._codigo(block.get('kind'), height, digest)
        old = block.get('id')
        fresh = fields_of(nonce, used)
        block.clear()
        block.update(fresh)
        block['id'] = ident
        block['hash'] = digest.hex()
        block['sig'] = ed25519.sign(payload, seed).hex()
        if ident not in ids:
            ids.append(ident)
        if ident != old:
            new_ids.append(ident)
        prev = block['hash']
    return new_ids


def _resign_nft(chain, seed, mapping):
    tokens = (chain or {}).get('tokens') or []
    prev = nft.GENESIS
    dirty = False
    for token in tokens:
        if token.get('owner') in mapping:
            token['owner'] = mapping[token['owner']]
            dirty = True
        if dirty:
            token['prev'] = prev
            payload = nft.canonical(token)
            token['hash'] = hashlib.sha256(payload).hexdigest()
            if seed is not None:
                token['sig'] = ed25519.sign(payload, seed).hex()
        prev = token.get('hash')


def _pop(box, keys):
    if not isinstance(box, dict):
        return
    for key in keys:
        if key not in PROTEGIDOS:
            box.pop(key, None)


def _drop_flags(box, banned):
    if not isinstance(box, dict) or not isinstance(box.get('flags'), list):
        return
    box['flags'] = [row for row in box['flags'] if not (isinstance(row, dict) and row.get('account') in banned)]


def _retirar_smh(economy, vault_state, names):
    total = 0
    wallets = economy.setdefault('wallets', {})
    tokens = economy.get('walletTokens') if isinstance(economy.get('walletTokens'), dict) else None
    for name in names:
        have = int(wallets.get(name) or 0)
        if have > 0:
            if not eco.debit(economy, name, have):
                raise RuntimeError('no se pudo vaciar la billetera')
            total += have
        if name in wallets and int(wallets.get(name) or 0) == 0:
            wallets.pop(name, None)
        if tokens is not None:
            tokens.pop(name, None)
    accounts = (vault_state or {}).get('accounts') or {}
    for name in names:
        box = accounts.get(name)
        if not isinstance(box, dict):
            continue
        have = VAULT.smh_of(box)
        if have > 0:
            if not VAULT.take_smc(box, have):
                raise RuntimeError('no se pudo vaciar el depósito')
            total += have
    return total


def _retirar_sph(economy, vault_state, names):
    total = 0
    box = economy.get('plata') if isinstance(economy.get('plata'), dict) else None
    wallets = box.get('wallets') if isinstance(box, dict) and isinstance(box.get('wallets'), dict) else {}
    for name in names:
        have = int(wallets.get(name) or 0)
        if have > 0:
            if box is None or not plata._debit(box, name, have):
                raise RuntimeError('no se pudo vaciar la plata')
            total += have
        wallets.pop(name, None)
    accounts = (vault_state or {}).get('accounts') or {}
    for name in names:
        accbox = accounts.get(name)
        if not isinstance(accbox, dict):
            continue
        have = VAULT.sph_of(accbox)
        if have > 0:
            if not VAULT.take_smp(accbox, have):
                raise RuntimeError('no se pudo vaciar la plata del depósito')
            total += have
    return total


def _cerrar_migracion(economy, names):
    migrations = economy.get('migrations')
    if not isinstance(migrations, dict):
        return
    for name in names:
        prior = migrations.pop(name, None)
        if not isinstance(prior, dict) or int(prior.get('credited') or 0) <= 0:
            continue
        lock = eco.migration_lock(name)
        if not lock:
            continue
        migrations[lock] = {
            'done': True,
            'requested': int(prior.get('requested') or 0),
            'credited': int(prior.get('credited') or 0),
            'unit': 'SMH',
            'source': 'cuenta_eliminada',
        }


def _quitar_cuenta(accounts, found):
    user_id = found.get('id')
    email = str(found.get('email') or '').strip().lower()
    phone = str(found.get('phone') or '').strip()
    accounts['users'] = [user for user in (accounts.get('users') or []) if user.get('id') != user_id]
    sessions = accounts.get('sessions')
    if isinstance(sessions, dict):
        for token, row in list(sessions.items()):
            if isinstance(row, dict) and row.get('user_id') == user_id:
                sessions.pop(token, None)
    pending = accounts.get('pending')
    if isinstance(pending, dict) and email:
        pending.pop(email, None)
    rates = accounts.get('rates')
    if isinstance(rates, dict):
        for key in list(rates):
            text = str(key)
            if (email and email in text) or (phone and phone in text):
                rates.pop(key, None)


def aplicar(bundle, user, confirm, seed=None, now=None):
    """Muta bundle en memoria. No escribe disco ni Postgres.

    Devuelve ok, already, status, error, alias y new_ids.
    """
    now = int(now if now is not None else 0)
    accounts = bundle.get('accounts') or {}
    found = _usuario(accounts, (user or {}).get('id'))
    alias = alias_de((found or user or {}).get('id'))
    if not found:
        return {'ok': True, 'already': True, 'alias': alias, 'new_ids': [], 'status': '200 OK'}
    if not confirmacion_valida(found, confirm):
        return {
            'ok': False, 'already': False, 'alias': alias, 'new_ids': [],
            'status': '400 Bad Request',
            'error': 'Escribe tu nickname o la palabra ELIMINAR para confirmar.',
        }
    if es_fundador(found):
        return {
            'ok': False, 'already': False, 'alias': alias, 'new_ids': [],
            'status': '403 Forbidden',
            'error': 'La cuenta del fundador no se puede eliminar.',
        }

    economy = bundle.setdefault('economy', {})
    vault_state = bundle.setdefault('vault', {'accounts': {}})
    names = _nombres(found)
    mapping = _mapa(names, alias)
    smh = _retirar_smh(economy, vault_state, names)
    sph = _retirar_sph(economy, vault_state, names)
    if smh or sph:
        box = economy.setdefault('plata', {})
        if smh:
            box['smcPoolSmh'] = int(box.get('smcPoolSmh') or 0) + int(smh)
        if sph:
            box['burnedSph'] = int(box.get('burnedSph') or 0) + int(sph)
            txs = box.setdefault('txs', [])
            txs.append({'type': 'burn', 'from': alias, 'amountSph': int(sph), 'note': NOTE, 't': now})
            del txs[:-200]

    for block in economy.get('blocks') or []:
        for tx in block.get('txs') or []:
            _anonimizar(tx, mapping)
    for tx in economy.get('mempool') or []:
        _anonimizar(tx, mapping)
    plata_box = economy.get('plata') if isinstance(economy.get('plata'), dict) else None
    if plata_box is not None:
        for tx in plata_box.get('txs') or []:
            _anonimizar(tx, mapping)
    _rehash(economy)

    if smh or sph:
        row = {
            'type': 'return', 'from': alias, 'to': 'fondo_cambio',
            'amountSubs': int(smh), 'note': NOTE,
        }
        if sph:
            row['amountSph'] = int(sph)
        eco.append_tx(economy, row, now=now)

    _cerrar_migracion(economy, names)
    for key in ('questGrants', 'questOwed'):
        _pop(economy.get(key), names)
    supply = economy.get('supply') if isinstance(economy.get('supply'), dict) else None
    banned = set(names)
    banned.add(found.get('id'))
    if supply is not None:
        _pop(supply.get('accounts'), list(banned))
        _drop_flags(supply, banned)
    if plata_box is not None:
        _pop(plata_box.get('accounts'), list(banned))
        _drop_flags(plata_box, banned)

    vault_accounts = vault_state.get('accounts') if isinstance(vault_state, dict) else None
    _pop(vault_accounts, names)
    players = (bundle.get('players') or {}).get('players')
    _pop(players, names)

    new_ids = _resign_libro(bundle.get('libro'), seed, mapping)
    _resign_nft(bundle.get('nft'), seed, mapping)
    _quitar_cuenta(accounts, found)
    return {
        'ok': True, 'already': False, 'alias': alias, 'new_ids': new_ids,
        'status': '200 OK', 'smh': int(smh), 'sph': int(sph),
    }
