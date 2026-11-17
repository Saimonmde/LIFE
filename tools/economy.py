# SPDX-License-Identifier: AGPL-3.0-or-later
"""SaiMonCoins (SMC): emisión, halvings y libro mayor.

La unidad interna es el Simonchi (SMH): 1 SMC = 100 SMH.
Hasta 2026 la escala vieja fue 100.000.000. migrate_denomination la pasa una sola vez.
Los saldos, el libro y el tope se guardan como enteros SMH. No se usa coma flotante.

Nota histórica: hasta 2026 el nombre visible fue Saimon Coins (SAI), con alias Saimony.
Ese alias ya no se muestra. Un state/economy.json antiguo se sigue leyendo; no se reescriben los bloques.
El saimonito ya era esa unidad mínima: 1 saimonito = 1 SMH, así que esos enteros no se vuelven a multiplicar.
Un contador guardado en SMC (por ejemplo mined, antes de tener amountUnit) se pasa a SMH con la escala vigente, 100.

Simulación educativa. No es dinero real, no tiene valor de canje y no transfiere derechos.
Por ahora 1 SMC se parece, sólo como idea, a 1 BTC o a 1 USDT.
"""
import hashlib, json, os, time
from decimal import Decimal

# Una sola escala para el oro del juego. La Plata no usa este número.
SMH_PER_SMC = 100
OLD_SMH_PER_SMC = 100_000_000
DENOM_DIVISOR = OLD_SMH_PER_SMC // SMH_PER_SMC  # 1.000.000
DECIMALS = 2
SUBS = SMH_PER_SMC
MAX_SUPPLY = 21_000_000
MAX_SMH = MAX_SUPPLY * SMH_PER_SMC  # 2.100.000.000
INITIAL_REWARD = 1  # SMC por prueba aceptada. 50 por bateada se minaba demasiado rápido.
INITIAL_REWARD_SMH = INITIAL_REWARD * SUBS
SYMBOL = 'SMC'
SYMBOL_BASE = 'SMH'
UNIT = 'SaiMonCoin'
BASE_NAME = 'Simonchi'
DISCLAIMER = (
    'Las SaiMonCoins (SMC), o Simon Coins, son una simulación educativa. '
    'El saldo se muestra en SMC, con decimales cuando hace falta. '
    'Por ahora 1 SMC se parece, sólo como idea, a 1 BTC o a 1 USDT. '
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
    """Devuelve SMH enteros. Acepta SMC con hasta 2 decimales, o SMH enteros.

    '1,50 SMC' vale 150. '12.345 SMH' vale 12345.
    Más de 2 decimales se rechaza: no se redondea ni se crea ni se destruye un SMH.
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
        if len(frac) > DECIMALS:
            raise AmountError('como máximo 2 decimales: un SMH no se fracciona')
        frac = frac.ljust(DECIMALS, '0')
    else:
        frac = '0' * DECIMALS
    smh = int(whole) * SMH_PER_SMC + int(frac)
    if negative:
        smh = -smh
    return smh


def smc_to_smh(value):
    """Multiplica SMC × 100 y devuelve un entero. No pasa por float."""
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
    whole, frac = divmod(abs(smh), SMH_PER_SMC)
    grouped = f'{whole:,}'.replace(',', '.')
    if frac == 0:
        return f'{sign}{grouped} {SYMBOL}'
    decimals = f'{frac:0{DECIMALS}d}'.rstrip('0')
    return f'{sign}{grouped},{decimals} {SYMBOL}'


def format_smh(smh):
    smh = int(smh or 0)
    sign = '-' if smh < 0 else ''
    grouped = f'{abs(smh):,}'.replace(',', '.')
    return f'{sign}{grouped} {SYMBOL_BASE}'


def format_pair(smh):
    """Texto que ve el jugador: sólo SMC. El entero guardado sigue siendo un céntimo."""
    return format_smc(smh)


def migrate_smh_display(state, log=None):
    """Una vez: el entero guardado se lee como céntimo de SMC y no se vuelve a dividir.

    1 unidad = 0,01 SMC, exacto. 1250 sigue siendo 12,50 SMC. No se reescriben
    los bloques firmados ni el baúl: dividir el entero lo haría cien veces menor.
    La bandera meta.smhShownAsSmc impide repetirlo.
    """
    if not isinstance(state, dict):
        return False
    meta = state.setdefault('meta', {})
    if not isinstance(meta, dict):
        meta = {}
        state['meta'] = meta
    if meta.get('smhShownAsSmc') is True:
        return False
    wallets = state.get('wallets') if isinstance(state.get('wallets'), dict) else {}
    for name, value in list(wallets.items()):
        try:
            kept = int(value or 0)
        except (TypeError, ValueError):
            kept = smc_to_smh(value)
        wallets[name] = kept
        if log and kept != value:
            log(f'[smc] {name}: {value} paso a {kept} centimos de SMC')
    if 'minedSmh' in state:
        try:
            state['minedSmh'] = int(state.get('minedSmh') or 0)
        except (TypeError, ValueError):
            state['minedSmh'] = smc_to_smh(state.get('minedSmh') or 0)
    meta['smhShownAsSmc'] = True
    meta['smcCents'] = SMH_PER_SMC
    state['disclaimer'] = DISCLAIMER
    return True


def _soft_group(number, digits=2):
    """Entero con punto de miles y, si hace falta, coma decimal. No usa float para el saldo guardado."""
    text = f'{number:.{digits}f}'.rstrip('0').rstrip('.')
    whole, dot, frac = text.partition('.')
    grouped = f'{int(whole):,}'.replace(',', '.')
    if frac:
        return grouped + ',' + frac
    return grouped


def format_compact(amount):
    """Resumen corto: 950, 1,2 k, 3,45 k, 1,2 M. La coma es decimal (es-CO).

    El número exacto se muestra aparte. Esto no cambia el saldo guardado.
    """
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return '0'
    if amount != amount or amount in (float('inf'), float('-inf')):
        return '0'
    sign = '-' if amount < 0 else ''
    value = abs(amount)
    if value < 1000:
        if value == 0:
            return '0'
        if abs(value - round(value)) < 1e-9:
            return sign + f'{int(round(value)):,}'.replace(',', '.')
        if value >= 0.01:
            return sign + _soft_group(value, 2)
        text = f'{value:.8f}'.rstrip('0').rstrip('.')
        whole, _, frac = text.partition('.')
        return sign + whole + (',' + frac if frac else '')
    if value < 1_000_000:
        return sign + _soft_group(value / 1_000) + ' k'
    if value < 1_000_000_000:
        return sign + _soft_group(value / 1_000_000) + ' M'
    return sign + _soft_group(value / 1_000_000_000) + ' mil M'


def repair_smh(value):
    """Deshace un ×100 de más, ya en la escala nueva.

    No usa el divisor 1.000.000 de la migración. Un saldo que la migración
    acaba de convertir no entra aquí: haría falta que siguiera por encima
    de un millón de topes. Devuelve (smh, cambió).
    """
    try:
        smh = int(value)
    except (TypeError, ValueError):
        return 0, False
    if smh > MAX_SMH and smh % SMH_PER_SMC == 0:
        fixed = smh // SMH_PER_SMC
        if 0 <= fixed <= MAX_SMH:
            return int(fixed), True
    return smh, False


def repair_balances(state, log=None):
    """Repara billeteras imposibles ya migradas. No toca la plata ni el cobre.

    Si la denominación todavía no es 100, no hace nada: esa conversión es
    migrate_denomination y no se aplica dos veces.
    """
    logs = []
    if not isinstance(state, dict):
        return logs
    meta = state.get('meta') if isinstance(state.get('meta'), dict) else {}
    if int(meta.get('smhPerSmc') or 0) != SMH_PER_SMC or meta.get('denomJustMigrated'):
        return logs
    wallets = state.get('wallets')
    if not isinstance(wallets, dict):
        return logs
    for name, value in list(wallets.items()):
        fixed, changed = repair_smh(value)
        if not changed:
            continue
        line = f'[reparar] {name}: antes {value} SMH, después {fixed} SMH'
        logs.append(line)
        if log:
            log(line)
        wallets[name] = fixed
    return logs


def _scale_old_smh(value):
    """Pasa SMH viejos (1e8 por SMC) a la escala de 100. El SMC no cambia."""
    try:
        smh = int(value or 0)
    except (TypeError, ValueError):
        return 0
    sign = -1 if smh < 0 else 1
    smh = abs(smh)
    return sign * ((smh + DENOM_DIVISOR // 2) // DENOM_DIVISOR)


def _scale_tx_smh(tx):
    if not isinstance(tx, dict) or 'amountSubs' not in tx:
        return
    tx['amountSubs'] = _scale_old_smh(tx.get('amountSubs') or 0)


def migrate_denomination(state, log=None):
    """Una vez: new_smh = round(old_smh / 1_000_000). La bandera meta.smhPerSmc lo impide otra vez.

    No toca saldos de Plata (SPH). El fondo de cambio sí es SMC y se convierte.
    """
    if not isinstance(state, dict):
        return False
    meta = state.setdefault('meta', {})
    if int(meta.get('smhPerSmc') or 0) == SMH_PER_SMC:
        meta.pop('denomJustMigrated', None)
        return False
    def note(kind, name, before, after):
        line = f'[denominacion] {kind} {name}: antes {before} SMH, después {after} SMH'
        if log:
            log(line)
    for name, value in list((state.get('wallets') or {}).items()):
        after = _scale_old_smh(value)
        note('billetera', name, value, after)
        state['wallets'][name] = after
    if 'minedSmh' in state or state.get('mined') is None:
        before = int(state.get('minedSmh') or 0)
        after = _scale_old_smh(before)
        note('minado', 'mundo', before, after)
        state['minedSmh'] = after
    owed = state.get('questOwed')
    if isinstance(owed, dict):
        for name, value in list(owed.items()):
            after = _scale_old_smh(value)
            note('mision', name, value, after)
            owed[name] = after
    box = state.get('supply')
    if isinstance(box, dict):
        before = int(box.get('epochSubs') or 0)
        box['epochSubs'] = _scale_old_smh(before)
        if before:
            note('cupo-red', 'hoy', before, box['epochSubs'])
        for name, acc in list((box.get('accounts') or {}).items()):
            if not isinstance(acc, dict):
                continue
            before = int(acc.get('earned') or 0)
            acc['earned'] = _scale_old_smh(before)
            if before:
                note('cupo', name, before, acc['earned'])
    plata = state.get('plata')
    if isinstance(plata, dict) and 'smcPoolSmh' in plata:
        before = int(plata.get('smcPoolSmh') or 0)
        plata['smcPoolSmh'] = _scale_old_smh(before)
        if before:
            note('fondo', 'cambio', before, plata['smcPoolSmh'])
    for tx in state.get('mempool') or []:
        _scale_tx_smh(tx)
    prev = GENESIS_PREV
    for block in state.get('blocks') or []:
        for tx in block.get('txs') or []:
            _scale_tx_smh(tx)
        block['prev'] = prev
        block['hash'] = hash_block(prev, block.get('ts'), block.get('txs'))
        prev = block['hash']
    meta['smhPerSmc'] = SMH_PER_SMC
    meta['denomJustMigrated'] = True
    return True


def migrate_vault_smc(econ, vault_state, log=None):
    """Convierte el SMC del banco una sola vez. No toca la Plata del depósito."""
    if not isinstance(econ, dict) or not isinstance(vault_state, dict):
        return False
    meta = econ.setdefault('meta', {})
    if int(meta.get('smhPerSmc') or 0) != SMH_PER_SMC:
        return False
    if int(meta.get('vaultSmhPerSmc') or 0) == SMH_PER_SMC:
        return False
    accounts = vault_state.get('accounts') if isinstance(vault_state.get('accounts'), dict) else {}
    for name, box in list(accounts.items()):
        if not isinstance(box, dict):
            continue
        before = int(box.get('smh') if box.get('smh') is not None else box.get('smcSubs') or 0)
        after = _scale_old_smh(before)
        box['smh'] = after
        box['smcSubs'] = after
        if log:
            log(f'[denominacion] banco {name}: antes {before} SMH, después {after} SMH')
    meta['vaultSmhPerSmc'] = SMH_PER_SMC
    return True


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
    state = {
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
        'meta': {'smhPerSmc': SMH_PER_SMC, 'vaultSmhPerSmc': SMH_PER_SMC},
    }
    import supply
    supply.ensure(state)
    import plata
    plata.ensure(state)
    if isinstance(state.get('supply'), dict):
        state['supply'].pop('_fresh', None)
    if isinstance(state.get('plata'), dict):
        state['plata'].pop('_fresh', None)
    return state


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
    `mined`, si sigue en SMC, se pasa a SMH con SMH_PER_SMC (100).
    migrate_denomination recorta después la escala vieja, una sola vez.
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
    migrate_denomination(state, log=print)
    repair_balances(state, log=print)
    meta = state.get('meta')
    if isinstance(meta, dict):
        meta.pop('denomJustMigrated', None)
    return state


def normalize_state(state):
    """Ajusta el nombre visible y la unidad. Conserva bloques, saldos y la reserva génesis."""
    state['unit'] = UNIT
    state['symbol'] = SYMBOL
    state.pop('alias', None)
    state['disclaimer'] = DISCLAIMER
    migrate_amounts(state)
    migrate_smh_display(state, log=print)
    import supply
    supply.ensure(state)
    import plata
    plata.ensure(state)
    return state


def load_state(path):
    import persist
    state = persist.load_named('economy', path)
    if state is None:
        state = empty_state()
        save_state(path, state)
        return state
    normalize_state(state)
    fresh = False
    if state.get('supply', {}).get('_fresh'):
        state['supply'].pop('_fresh', None)
        fresh = True
    if state.get('plata', {}).get('_fresh'):
        state['plata'].pop('_fresh', None)
        fresh = True
    if fresh:
        save_state(path, state)
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


def migration_lock(name):
    """Clave opaca: una cuenta borrada no vuelve a emitir su conversión si el nickname se reutiliza."""
    key = ' '.join(str(name or '').strip().casefold().split())
    if not key:
        return ''
    return 'lock:' + hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]


def migrate_monedas(state, name, monedas, now=None, limit_smh=None):
    """Convierte monedas antiguas. 1 moneda = 1 SMC = 100 SMH.

    Sin límite, acredita de una vez lo que quepa en el tope (el comportamiento de siempre).
    Con limit_smh, acredita sólo ese trozo y deja el resto pendiente para otro día.
    Un registro viejo, sin la marca done, se trata como ya terminado.
    """
    record = state.setdefault('migrations', {})
    lock_key = migration_lock(name)
    locked = record.get(lock_key) if lock_key else None
    if isinstance(locked, dict) and locked.get('done', True):
        return {
            'already': True,
            'credited': 0,
            'requested': int(locked.get('requested') or 0),
            'rate': OLD_COIN_TO_SMC,
            'unit': 'SMH',
        }
    prior = record.get(name) if isinstance(record.get(name), dict) else None
    if prior and prior.get('done', True):
        return {
            'already': True,
            'credited': 0,
            'requested': int(prior.get('requested') or 0),
            'rate': OLD_COIN_TO_SMC,
            'unit': 'SMH',
        }
    if prior:
        requested = int(prior.get('requested') or 0)
        already = int(prior.get('credited') or 0)
    else:
        requested = smc_to_smh(monedas) * OLD_COIN_TO_SMC
        if requested < 0:
            requested = 0
        already = 0
    left = max(0, requested - already)
    chunk = left if limit_smh is None else min(left, max(0, int(limit_smh)))
    credited_now = issue(
        state, name, chunk,
        f'Conversión {OLD_COIN_TO_SMC}:1 de monedas antiguas del Jardín a SMC',
        'migrate', now=now,
    ) if chunk else 0
    total = already + int(credited_now)
    done = total >= requested or issuance_room(state) <= 0
    record[name] = {
        'source': 'monedas_jardin',
        'rate': OLD_COIN_TO_SMC,
        'requested': requested,
        'credited': total,
        'done': done,
        'unit': 'SMH',
    }
    return {
        'already': False,
        'credited': int(credited_now),
        'requested': requested,
        'rate': OLD_COIN_TO_SMC,
        'unit': 'SMH',
        'done': done,
    }
