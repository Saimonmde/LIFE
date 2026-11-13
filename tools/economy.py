# SPDX-License-Identifier: AGPL-3.0-or-later
"""SaiMonCoins (SMC): emisión, halvings y libro mayor.

Nota histórica: hasta 2026 el nombre visible fue Saimon Coins (SAI), con alias Saimony.
Ese alias ya no se muestra. Un state/economy.json antiguo se sigue leyendo; no se reescriben los bloques.

Simulación educativa. No es dinero real, no tiene valor de canje y no transfiere derechos.
"""
import hashlib, json, os, time

SUBS = 100_000_000
MAX_SUPPLY = 21_000_000
INITIAL_REWARD = 50  # SMC por bateada de oro fluvial
SYMBOL = 'SMC'
UNIT = 'SaiMonCoin'
DISCLAIMER = (
    'Las SaiMonCoins (SMC) son sólo una moneda del juego. '
    'No son dinero real, no se pueden retirar ni vender, no tienen valor ni canje.'
)
HALVING_MINED = 10_500_000
TREASURY = 210_000  # reserva inicial (recompensas de misión); no es emisión nueva
GENESIS_PREV = '0' * 64
BLOCK_SECONDS = 60


def subunits(sai):
    return int(round(float(sai) * SUBS))


def sai_of(subs):
    return subs / SUBS


def format_sai(subs):
    s = sai_of(int(subs))
    if abs(s - round(s)) < 1e-12:
        return f'{int(round(s)):,} {SYMBOL}'.replace(',', '.')
    t = f'{s:.8f}'.rstrip('0').rstrip('.')
    return t.replace('.', ',') + ' ' + SYMBOL


def reward_sai(mined_sai):
    """Premio actual por bateada según el total ya minado."""
    mined_sai = float(mined_sai or 0)
    if mined_sai >= MAX_SUPPLY - TREASURY:
        return 0
    era = int(mined_sai // HALVING_MINED)
    r = INITIAL_REWARD / (2 ** era)
    remaining = (MAX_SUPPLY - TREASURY) - mined_sai
    if r > remaining:
        r = max(0, remaining)
    return r


def hash_block(prev_hash, ts, txs):
    payload = prev_hash + '\n' + str(ts) + '\n' + json.dumps(txs, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def empty_state():
    genesis_txs = [{
        'type': 'genesis',
        'to': 'tesoro_genesis',
        'amountSubs': subunits(TREASURY),
        'note': 'Reserva inicial de SaiMonCoins (no es dinero real).',
    }]
    ts = 0
    h = hash_block(GENESIS_PREV, ts, genesis_txs)
    return {
        'unit': UNIT,
        'symbol': SYMBOL,
        'smallestUnit': 'saimonito',
        'subunitsPerUnit': SUBS,
        'maxSupply': MAX_SUPPLY,
        'treasury': TREASURY,
        'mined': 0,
        'wallets': {'tesoro_genesis': subunits(TREASURY), 'puesto_frutas': 0},
        'blocks': [{
            'height': 0,
            'ts': ts,
            'prev': GENESIS_PREV,
            'hash': h,
            'txs': genesis_txs,
        }],
        'mempool': [],
        'disclaimer': DISCLAIMER,
    }


def verify_block(block, prev_hash=None):
    if prev_hash is not None and block.get('prev') != prev_hash:
        return False
    return block.get('hash') == hash_block(block['prev'], block['ts'], block['txs'])


def seal_if_due(state, now=None, force=False):
    now = int(now if now is not None else time.time())
    mem = state.get('mempool') or []
    if not mem:
        return None
    last = state['blocks'][-1]
    if not force and now - int(last.get('ts') or 0) < BLOCK_SECONDS:
        return None
    txs = list(mem)
    state['mempool'] = []
    block = {'height': last['height'] + 1, 'ts': now, 'prev': last['hash'], 'txs': txs}
    block['hash'] = hash_block(block['prev'], block['ts'], block['txs'])
    state['blocks'].append(block)
    return block


def append_tx(state, tx, now=None):
    state.setdefault('mempool', []).append(tx)
    return seal_if_due(state, now=now)


def credit(state, name, subs):
    w = state.setdefault('wallets', {})
    w[name] = int(w.get(name) or 0) + int(subs)


def debit(state, name, subs):
    w = state.setdefault('wallets', {})
    if int(w.get(name) or 0) < int(subs):
        return False
    w[name] = int(w[name]) - int(subs)
    return True


def normalize_state(state):
    """Ajusta el nombre visible. Conserva bloques, saldos y un archivo guardado con el símbolo SAI."""
    state['unit'] = UNIT
    state['symbol'] = SYMBOL
    state.pop('alias', None)
    state['disclaimer'] = DISCLAIMER
    state.setdefault('smallestUnit', 'saimonito')
    return state


def load_state(path):
    import persist
    state = persist.load_named('economy', path)
    if state is None:
        state = empty_state()
        save_state(path, state)
        return state
    normalize_state(state)
    return state


def save_state(path, state):
    import persist
    persist.save_named('economy', path, state)


# 1 moneda antigua del Jardín (el contador que no era SMC) = 1 SMC. El SAI ya guardado
# sigue 1:1 porque normalize_state sólo cambia el nombre, no el saldo.
OLD_COIN_TO_SMC = 1


def issuance_room(state):
    """SMC que todavía se pueden emitir. La reserva génesis no cuenta como emisión nueva."""
    mined = float(state.get('mined') or 0)
    return max(0.0, (MAX_SUPPLY - TREASURY) - mined)


def issue(state, name, amount, note, kind='mint', now=None):
    """Emite SMC nuevas contra el tope de 21.000.000. Devuelve las que cupieron."""
    requested = float(amount or 0)
    if requested <= 0:
        return 0.0
    room = issuance_room(state)
    if room <= 0:
        return 0.0
    granted = min(requested, room)
    subs = subunits(granted)
    granted = sai_of(subs)
    if granted <= 0:
        return 0.0
    state['mined'] = float(state.get('mined') or 0) + granted
    credit(state, name, subs)
    append_tx(state, {'type': kind, 'to': name, 'amountSubs': subs, 'note': note}, now=now)
    return granted


def migrate_monedas(state, name, monedas, now=None):
    """Convierte una sola vez las monedas antiguas. Si el tope no alcanza, acredita el resto."""
    record = state.setdefault('migrations', {})
    if name in record:
        return {'already': True, 'credited': 0.0, 'requested': float(record[name].get('requested') or 0), 'rate': OLD_COIN_TO_SMC}
    requested = max(0.0, float(monedas or 0)) * OLD_COIN_TO_SMC
    credited = issue(
        state, name, requested,
        f'Conversión {OLD_COIN_TO_SMC}:1 de monedas antiguas del Jardín a SMC',
        'migrate', now=now,
    ) if requested else 0.0
    record[name] = {
        'source': 'monedas_jardin',
        'rate': OLD_COIN_TO_SMC,
        'requested': requested,
        'credited': credited,
    }
    return {'already': False, 'credited': credited, 'requested': requested, 'rate': OLD_COIN_TO_SMC}
