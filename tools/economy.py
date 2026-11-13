# SPDX-License-Identifier: AGPL-3.0-or-later
"""Saimon Coins (SAI, alias Saimony): emisión, halvings y libro mayor.

Simulación educativa. No es dinero real, no tiene valor de canje y no transfiere derechos.
"""
import hashlib, json, os, time

SUBS = 100_000_000
MAX_SUPPLY = 21_000_000
INITIAL_REWARD = 50  # SAI por bateada de oro fluvial
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
        return f'{int(round(s)):,} SAI'.replace(',', '.')
    t = f'{s:.8f}'.rstrip('0').rstrip('.')
    return t.replace('.', ',') + ' SAI'


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
        'note': 'Reserva inicial de Saimon Coins (no es dinero real).',
    }]
    ts = 0
    h = hash_block(GENESIS_PREV, ts, genesis_txs)
    return {
        'unit': 'Saimon Coin',
        'symbol': 'SAI',
        'alias': ['Saimony'],
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
        'disclaimer': 'Las Saimon Coins (SAI, alias Saimony) son sólo una moneda del juego. No son dinero real, no se pueden retirar ni vender, no tienen valor ni canje.',
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


def load_state(path):
    if not os.path.isfile(path):
        st = empty_state()
        save_state(path, st)
        return st
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_state(path, state):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
