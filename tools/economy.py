# SPDX-License-Identifier: AGPL-3.0-or-later
"""SaiMonCoins (SMC): emisión, halvings y libro mayor.

La unidad interna es el Simonchi (SMH): 1 SMC = 100.000.000 SMH, como un satoshi.
Los saldos, el libro y el tope se guardan como enteros SMH. No se usa coma flotante.

Nota histórica: hasta 2026 el nombre visible fue Saimon Coins (SAI), con alias Saimony.
Ese alias ya no se muestra. Un state/economy.json antiguo se sigue leyendo; no se reescriben los bloques.
El saimonito ya era esa unidad mínima: 1 saimonito = 1 SMH, así que esos enteros no se vuelven a multiplicar.
Los contadores guardados en SMC (por ejemplo mined) sí se multiplican por 100.000.000 una sola vez.

Simulación educativa. No es dinero real, no tiene valor de canje y no transfiere derechos.
Por ahora 1 SMC se parece, sólo como idea, a 1 BTC o a 1 USDT.
"""
import hashlib, json, os, time
from decimal import Decimal

SUBS = 100_000_000
MAX_SUPPLY = 21_000_000
MAX_SMH = MAX_SUPPLY * SUBS  # 2.100.000.000.000.000
INITIAL_REWARD = 50  # SMC por bateada de oro fluvial
INITIAL_REWARD_SMH = INITIAL_REWARD * SUBS
SYMBOL = 'SMC'
SYMBOL_BASE = 'SMH'
UNIT = 'SaiMonCoin'
BASE_NAME = 'Simonchi'
DISCLAIMER = (
    'Las SaiMonCoins (SMC) son una simulación educativa. '
    '1 SMC = 100.000.000 Simonchis (SMH). Por ahora 1 SMC se parece, sólo como idea, a 1 BTC o a 1 USDT. '
    'No son dinero real, no se pueden retirar ni vender, no tienen valor ni canje.'
)
HALVING_MINED = 10_500_000
HALVING_SMH = HALVING_MINED * SUBS
TREASURY = 210_000  # reserva inicial en SMC (recompensas de misión); no es emisión nueva
TREASURY_SMH = TREASURY * SUBS
GENESIS_PREV = '0' * 64
BLOCK_SECONDS = 60


class AmountError(ValueError):
    pass


def _digits(text):
    if not text.isdigit():
        raise AmountError('monto ilegible')
    return text


def parse_amount(text):
    """Devuelve SMH enteros. Acepta SMC con hasta 8 decimales, o SMH enteros.

    '0.00012345' y '0,00012345 SMC' valen 12345. '12.345 SMH' vale 12345.
    Más de 8 decimales se rechaza: no se redondea ni se crea ni se destruye un SMH.
    """
    raw = str(text if text is not None else '').strip().lower()
    if not raw:
        raise AmountError('monto vacío')
    unit = 'smc'
    for name, kind in (
        ('simonchis', 'smh'), ('simonchi', 'smh'), ('smh', 'smh'),
        ('saimoncoins', 'smc'), ('saimoncoin', 'smc'), ('smc', 'smc'),
    ):
        if raw.endswith(name):
            unit = kind
            raw = raw[: -len(name)].strip()
            break
    raw = raw.replace(' ', '')
    if not raw:
        raise AmountError('monto vacío')
    if unit == 'smh':
        if raw.count(',') and raw.count('.'):
            grouped = raw.replace('.', '').replace(',', '')
        elif ',' in raw or '.' in raw:
            parts = raw.replace(',', '.').split('.')
            if not all(parts) or any(len(part) != 3 for part in parts[1:]) or len(parts[-1]) != 3:
                raise AmountError('un Simonchi no se parte')
            grouped = ''.join(parts)
        else:
            grouped = raw
        if grouped.startswith('+'):
            grouped = grouped[1:]
        if not grouped.isdigit():
            raise AmountError('monto ilegible')
        return int(grouped)
    if raw.count(',') and raw.count('.'):
        if raw.rfind(',') > raw.rfind('.'):
            raw = raw.replace('.', '').replace(',', '.')
        else:
            raw = raw.replace(',', '')
    elif ',' in raw:
        left, _, right = raw.partition(',')
        if raw.count(',') > 1 and all(len(part) == 3 for part in raw.split(',')[1:]):
            raw = raw.replace(',', '')
        else:
            raw = left + '.' + right
    elif raw.count('.') > 1:
        parts = raw.split('.')
        if all(len(part) == 3 for part in parts[1:]):
            raw = ''.join(parts)
        else:
            raise AmountError('monto ilegible')
    if raw.startswith('+'):
        raw = raw[1:]
    negative = raw.startswith('-')
    if negative:
        raw = raw[1:]
    whole, dot, frac = raw.partition('.')
    if whole == '':
        whole = '0'
    _digits(whole)
    if dot:
        _digits(frac)
        if len(frac) > 8:
            raise AmountError('como máximo 8 decimales: un SMH no se fracciona')
        frac = frac.ljust(8, '0')
    else:
        frac = '00000000'
    smh = int(whole) * SUBS + int(frac)
    if negative:
        smh = -smh
    return smh


def smc_to_smh(value):
    """Multiplica SMC × 100.000.000 y devuelve un entero. No pasa por float."""
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value * SUBS
    if isinstance(value, str):
        return parse_amount(value)
    text = format(Decimal(str(value)), 'f')
    return parse_amount(text)


def subunits(sai):
    """SMC → SMH. Conserva el nombre antiguo."""
    return smc_to_smh(sai)


def format_smc(smh):
    smh = int(smh or 0)
    sign = '-' if smh < 0 else ''
    whole, frac = divmod(abs(smh), SUBS)
    grouped = f'{whole:,}'.replace(',', '.')
    if frac == 0:
        return f'{sign}{grouped} {SYMBOL}'
    decimals = f'{frac:08d}'.rstrip('0')
    return f'{sign}{grouped},{decimals} {SYMBOL}'


def format_smh(smh):
    smh = int(smh or 0)
    sign = '-' if smh < 0 else ''
    grouped = f'{abs(smh):,}'.replace(',', '.')
    return f'{sign}{grouped} {SYMBOL_BASE}'


def format_pair(smh):
    return f'{format_smc(smh)} = {format_smh(smh)}'


def format_sai(subs):
    return format_smc(subs)


def sai_of(subs):
    """Sólo para textos heredados. El valor que se guarda es el entero SMH."""
    return int(subs) / SUBS


def reward_smh(mined_smh):
    """Premio de la bateada, en SMH enteros. El resto menor que 1 SMH no se crea."""
    mined_smh = int(mined_smh or 0)
    cap = (MAX_SUPPLY - TREASURY) * SUBS
    if mined_smh >= cap:
        return 0
    era = mined_smh // HALVING_SMH
    if era >= 63:
        reward = 0
    else:
        reward = INITIAL_REWARD_SMH // (2 ** era)
    remaining = cap - mined_smh
    if reward > remaining:
        reward = remaining
    return int(reward)


def reward_sai(mined_smc):
    """Premio expresado en SMC enteros cuando cae justo. La emisión usa reward_smh."""
    smh = reward_smh(smc_to_smh(mined_smc))
    if smh % SUBS == 0:
        return smh // SUBS
    return smh / SUBS


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
        'smallestUnit': SYMBOL_BASE,
        'smallestName': BASE_NAME,
        'subunitsPerUnit': SUBS,
        'amountUnit': 'SMH',
        'maxSupply': MAX_SUPPLY,
        'maxSupplySmh': MAX_SMH,
        'treasury': TREASURY,
        'minedSmh': 0,
        'wallets': {'tesoro_genesis': TREASURY_SMH, 'puesto_frutas': 0},
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


def _as_base_units(value):
    """Un entero ya es SMH (antes, saimonito). Un decimal está en SMC y se multiplica."""
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value
    return smc_to_smh(value)


def migrate_amounts(state):
    """Pasa el estado a SMH enteros sin reescribir los bloques ya sellados.

    Los saldos enteros no se multiplican: ya estaban en la unidad mínima.
    `mined`, si sigue en SMC, se multiplica una vez por 100.000.000.
    """
    wallets = state.setdefault('wallets', {})
    for name, value in list(wallets.items()):
        wallets[name] = _as_base_units(value)
    if state.get('amountUnit') == 'SMH' and 'minedSmh' in state:
        state['minedSmh'] = int(state.get('minedSmh') or 0)
    else:
        state['minedSmh'] = smc_to_smh(state.get('mined') or 0)
    state.pop('mined', None)
    state['amountUnit'] = 'SMH'
    state['smallestUnit'] = SYMBOL_BASE
    state['smallestName'] = BASE_NAME
    state['maxSupplySmh'] = MAX_SMH
    migrations = state.get('migrations') or {}
    for record in migrations.values():
        if not isinstance(record, dict) or record.get('unit') == 'SMH':
            continue
        if 'requested' in record:
            record['requested'] = smc_to_smh(record.get('requested') or 0)
        if 'credited' in record:
            record['credited'] = smc_to_smh(record.get('credited') or 0)
        record['unit'] = 'SMH'
    return state


def normalize_state(state):
    """Ajusta el nombre visible y la unidad. Conserva bloques y un archivo guardado con el símbolo SAI."""
    state['unit'] = UNIT
    state['symbol'] = SYMBOL
    state.pop('alias', None)
    state['disclaimer'] = DISCLAIMER
    migrate_amounts(state)
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
    """SMH que todavía se pueden emitir. La reserva génesis no cuenta como emisión nueva."""
    mined = int(state.get('minedSmh') or 0)
    return max(0, (MAX_SUPPLY - TREASURY) * SUBS - mined)


def issue(state, name, amount_smh, note, kind='mint', now=None):
    """Emite SMH nuevos contra el tope de 21.000.000 SMC. Devuelve los que cupieron, enteros."""
    requested = int(amount_smh or 0)
    if requested <= 0:
        return 0
    room = issuance_room(state)
    if room <= 0:
        return 0
    granted = min(requested, room)
    state['minedSmh'] = int(state.get('minedSmh') or 0) + granted
    credit(state, name, granted)
    append_tx(state, {'type': kind, 'to': name, 'amountSubs': granted, 'note': note}, now=now)
    return granted


def migrate_monedas(state, name, monedas, now=None):
    """Convierte una sola vez las monedas antiguas. 1 moneda = 1 SMC = 100.000.000 SMH."""
    record = state.setdefault('migrations', {})
    if name in record:
        return {
            'already': True,
            'credited': 0,
            'requested': int(record[name].get('requested') or 0),
            'rate': OLD_COIN_TO_SMC,
            'unit': 'SMH',
        }
    requested = smc_to_smh(monedas) * OLD_COIN_TO_SMC
    if requested < 0:
        requested = 0
    credited = issue(
        state, name, requested,
        f'Conversión {OLD_COIN_TO_SMC}:1 de monedas antiguas del Jardín a SMC',
        'migrate', now=now,
    ) if requested else 0
    record[name] = {
        'source': 'monedas_jardin',
        'rate': OLD_COIN_TO_SMC,
        'requested': requested,
        'credited': credited,
        'unit': 'SMH',
    }
    return {'already': False, 'credited': credited, 'requested': requested, 'rate': OLD_COIN_TO_SMC, 'unit': 'SMH'}
