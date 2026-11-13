# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plata (SMP): segunda moneda del libro, con tope fijo y cambio hacia SMC.

1 SMP = 100.000.000 platicas (SPH), el mismo corte que 1 SMC = 100.000.000 SMH.
Todo el libro se guarda en enteros. No hay premine ni reserva inicial.

El tope es 84.000.000 SMP, cuatro veces el de SMC. Cabe en un entero exacto
de JavaScript (2^53): 84 millones × 100.000.000 SPH sigue por debajo de ese
límite. 210 millones de SMP no cabrían sin redondear el saldo en el navegador.

El cambio Plata → SMC no acuña oro. Paga con SMC que ya salieron por prueba
de trabajo y que el servidor apartó (un quinto de cada emisión nueva). La
Plata gastada se quema y no vuelve al cupo minable.
"""
import hashlib
import hmac
import re
import secrets
import time

import economy as eco
import supply as sup

SUBS = eco.SUBS
MAX_SUPPLY = 84_000_000
MAX_SPH = MAX_SUPPLY * SUBS
HALVING_MINED = 42_000_000
HALVING_SPH = HALVING_MINED * SUBS
INITIAL_REWARD = 5
INITIAL_REWARD_SPH = INITIAL_REWARD * SUBS
SYMBOL = 'SMP'
SYMBOL_BASE = 'SPH'
UNIT = 'Plata'
BASE_NAME = 'platica'
POOL = 'fondo_cambio'
POOL_DEN = 5
RATE_SPH_PER_SMH = 100
EXCHANGE_DEN = 5
NETWORK_OUT_DEN = 2
ACCOUNT_SLICE_DEN = 10
BASE_DAILY_SPH = 5 * SUBS
AGE_SPH = SUBS
AGE_DAYS = 60
PLAY_SPH = SUBS
PLAY_HOURS = 40
QUEST_SPH = 2 * SUBS
QUEST_CAP = 10
PREMINE_SPH = 0
HINT = (
    'La Plata se mina con la misma prueba de trabajo, también después del tope de SMC. '
    '100 SMP = 1 SMC. Ese oro sale de un fondo ya emitido: no se crean SMC nuevas. '
    'La prueba sola no frena a un bot.'
)
REASONS = {
    'guest': 'Entra con una cuenta para recibir Plata. Como invitado puedes jugar y recoger objetos, pero no monedas.',
    'replay': 'Esa prueba ya se usó.',
    'expired': 'La prueba caducó. Pide otra.',
    'weak': 'La prueba no alcanza la dificultad.',
    'signature': 'La prueba no es válida.',
    'account': 'La prueba es de otra cuenta.',
    'action': 'La prueba no corresponde a esta acción.',
    'fast': 'Vas más rápido de lo que esta cuenta puede minar. Pide otra prueba.',
    'cap': 'Llegaste al tope de Plata de hoy. Mañana se abre otro tramo.',
    'ceiling': 'La red ya emitió el cupo de Plata de este día.',
    'supply': 'Se alcanzó el tope de 84.000.000 SMP.',
    'activity': 'Muévete y juega un poco antes de reclamar Plata.',
    'cooldown': 'Espera un momento para volver a intentarlo.',
    'rate': 'Demasiados intentos. Esta cuenta o esta red queda en pausa un rato.',
    'anomaly': 'Se detectó un ritmo anómalo. Esta cuenta o esta red queda en pausa un rato.',
    'pool': 'El fondo de cambio no tiene SMC. Nadie crea oro nuevo al cambiar.',
    'exchange_cap': 'Llegaste al tope de cambio de hoy.',
    'slice': 'Hoy ya tomaste tu parte del fondo. Mañana hay otro tramo.',
    'exchange_ceiling': 'Hoy el fondo ya soltó la mitad que puede soltar. El resto sigue guardado.',
    'dust': 'Hace falta al menos 100 platicas (SPH) para recibir 1 Simonchi (SMH).',
    'funds': 'No tienes tanta Plata.',
    'wallet': 'Esta billetera se creó en otro aparato.',
}


def reason_text(code):
    return REASONS.get(code, 'No se pudo mover Plata.')


def reserved_name(name):
    return str(name or '').strip().lower() == POOL


def reward_sph(mined_sph):
    """Premio de la era, en SPH enteros. Se parte a la mitad cada 42 millones."""
    mined_sph = int(mined_sph or 0)
    if mined_sph >= MAX_SPH:
        return 0
    era = mined_sph // HALVING_SPH
    if era >= 63:
        reward = 0
    else:
        reward = INITIAL_REWARD_SPH // (2 ** era)
    remaining = MAX_SPH - mined_sph
    if reward > remaining:
        reward = remaining
    return int(reward)


def issuance_room(state):
    box = state.get('plata') or {}
    return max(0, MAX_SPH - int(box.get('minedSph') or 0))


def daily_cap_sph(age_seconds, play_seconds, quests):
    """Tope del día UTC, en SPH. Crece con la cuenta, el tiempo jugado y las misiones."""
    days = min(AGE_DAYS, max(0, int(age_seconds)) // sup.DAY)
    hours = min(PLAY_HOURS, max(0, int(play_seconds)) // 3600)
    done = min(QUEST_CAP, max(0, int(quests)))
    return BASE_DAILY_SPH + days * AGE_SPH + hours * PLAY_SPH + done * QUEST_SPH


def exchange_cap_smh(age_seconds, play_seconds, quests):
    """Tope de SMC que esta cuenta puede sacar del fondo hoy: un quinto de su tope de SMC."""
    return int(sup.daily_cap_smh(age_seconds, play_seconds, quests)) // EXCHANGE_DEN


def ensure(state, now=None):
    """Añade el libro de Plata si falta. No toca billeteras SMC, bloques ni minedSmh."""
    now = int(now if now is not None else time.time())
    box = state.get('plata')
    fresh = not isinstance(box, dict) or not box.get('secret')
    if not isinstance(box, dict):
        box = {}
        state['plata'] = box
    if not box.get('secret'):
        box['secret'] = secrets.token_hex(32)
    box['v'] = 1
    box['symbol'] = SYMBOL
    box['symbolBase'] = SYMBOL_BASE
    box['unit'] = UNIT
    box['smallestName'] = BASE_NAME
    box['subunitsPerUnit'] = SUBS
    box['maxSupply'] = MAX_SUPPLY
    box['premineSph'] = PREMINE_SPH
    box.setdefault('bits', sup.START_BITS)
    box['bits'] = int(box.get('bits') or sup.START_BITS)
    if not box.get('windowStart'):
        box['windowStart'] = now
    box.setdefault('windowProofs', 0)
    box.setdefault('minedSph', 0)
    box.setdefault('burnedSph', 0)
    box.setdefault('smcPoolSmh', 0)
    box['minedSph'] = int(box.get('minedSph') or 0)
    box['burnedSph'] = int(box.get('burnedSph') or 0)
    box['smcPoolSmh'] = max(0, int(box.get('smcPoolSmh') or 0))
    epoch = now // sup.DAY
    if 'epoch' not in box:
        box['epoch'] = epoch
        box['epochSubs'] = 0
    box.setdefault('used', {})
    box.setdefault('accounts', {})
    box.setdefault('ips', {})
    box.setdefault('wallets', {})
    box.setdefault('txs', [])
    box.setdefault('flags', [])
    if fresh:
        box['_fresh'] = True
    return fresh


def _profile(profile):
    data = sup._clean_profile(profile)
    data['name'] = str((profile or {}).get('name') or '')[:32]
    return data


def _roll_mine(box, now):
    epoch = int(now) // sup.DAY
    if int(box.get('epoch') or -1) != epoch:
        box['epoch'] = epoch
        box['epochSubs'] = 0
    return epoch


def _roll_exchange(box, now):
    epoch = int(now) // sup.DAY
    if int(box.get('xEpoch') or -1) != epoch:
        box['xEpoch'] = epoch
        box['opening'] = int(box.get('smcPoolSmh') or 0)
        box['inflow'] = 0
        box['outflow'] = 0
    box.setdefault('opening', int(box.get('smcPoolSmh') or 0))
    box.setdefault('inflow', 0)
    box.setdefault('outflow', 0)
    return epoch


def _account(box, account, now):
    acc = box.setdefault('accounts', {}).setdefault(account, {})
    epoch = int(now) // sup.DAY
    if int(acc.get('epoch') or -1) != epoch:
        acc['epoch'] = epoch
        acc['earned'] = 0
        acc['proofs'] = 0
        acc['exchanged'] = 0
    acc.setdefault('earned', 0)
    acc.setdefault('proofs', 0)
    acc.setdefault('exchanged', 0)
    acc.setdefault('lastClaim', 0)
    acc.setdefault('lastExchange', 0)
    acc.setdefault('challenges', [])
    acc.setdefault('claims', [])
    acc.setdefault('xclaims', [])
    acc.setdefault('penaltyUntil', 0)
    return acc


def _ip(box, ip, now):
    row = box.setdefault('ips', {}).setdefault(ip, {})
    row.setdefault('challenges', [])
    row.setdefault('claims', [])
    row.setdefault('xclaims', [])
    row.setdefault('penaltyUntil', 0)
    return row


def _prune(times, now, window):
    return [int(t) for t in (times or []) if now - int(t) < window]


def _flag(box, now, account, ip, reason):
    flags = box.setdefault('flags', [])
    flags.append({'t': int(now), 'account': account, 'ip': ip, 'reason': reason})
    del flags[:-40]


def _pause(box, acc, row, now, account, ip, reason):
    until = int(now) + sup.PENALTY
    acc['penaltyUntil'] = max(int(acc.get('penaltyUntil') or 0), until)
    row['penaltyUntil'] = max(int(row.get('penaltyUntil') or 0), until)
    _flag(box, now, account, ip, reason)
    return reason


def _note(box, row):
    txs = box.setdefault('txs', [])
    txs.append(row)
    del txs[:-200]


def _wallet(box, name):
    wallets = box.setdefault('wallets', {})
    if name not in wallets:
        wallets[name] = 0
    wallets[name] = int(wallets[name] or 0)
    return wallets


def balance_of(state, name):
    box = state.get('plata') or {}
    return int((box.get('wallets') or {}).get(name) or 0)


def _credit(box, name, sph):
    sph = int(sph or 0)
    if sph <= 0 or not name:
        return 0
    wallets = _wallet(box, name)
    wallets[name] += sph
    return sph


def _debit(box, name, sph):
    sph = int(sph or 0)
    wallets = _wallet(box, name)
    if sph <= 0 or int(wallets.get(name) or 0) < sph:
        return False
    wallets[name] -= sph
    return True


def _ceiling(reward):
    return int(reward) * sup.PROOFS_PER_DAY


def _context(text):
    out = re.sub(r'[^A-Za-z0-9_.:-]', '', str(text or ''))[:80]
    return out or 'libre'


def _canonical(challenge):
    return '|'.join([
        'smp-pow-1',
        str(challenge['id']),
        str(challenge['account']),
        str(challenge['action']),
        str(challenge['context']),
        str(int(challenge['bits'])),
        str(int(challenge['personal'])),
        str(int(challenge['exp'])),
    ])


def _sign(secret, payload):
    return hmac.new(bytes.fromhex(secret), payload.encode('utf-8'), hashlib.sha256).hexdigest()


def _personal(acc, now, key):
    recent = _prune(acc.get(key), now, 3600)
    acc[key] = recent
    return sup.PERSONAL_STEP * len(recent), recent


def _ready(profile, acc, now, opening, claim_key, last_key):
    if not profile['account']:
        return 'guest'
    if int(acc.get('penaltyUntil') or 0) > now:
        return 'anomaly'
    if opening and not profile['fresh']:
        return 'activity'
    if profile['activity'] < sup.ACTIVITY_TILES:
        return 'activity'
    if now - int(acc.get(last_key) or 0) < sup.CLAIM_COOLDOWN:
        return 'cooldown'
    _extra, recent = _personal(acc, now, claim_key)
    if len(recent) >= sup.MAX_PROOFS_PER_HOUR:
        return 'rate'
    return ''


def _budgets(box):
    base = int(box.get('opening') or 0) + int(box.get('inflow') or 0)
    network = max(0, base // NETWORK_OUT_DEN - int(box.get('outflow') or 0))
    return base, network


def _view(state, profile, now):
    box = state['plata']
    _roll_mine(box, now)
    _roll_exchange(box, now)
    reward = reward_sph(box.get('minedSph'))
    ceiling = _ceiling(reward)
    epoch_left = max(0, ceiling - int(box.get('epochSubs') or 0))
    guest = not profile['account']
    cap = daily_cap_sph(profile['age'], profile['play'], profile['quests'])
    earned = 0
    proofs = 0
    exchanged = 0
    paused = False
    personal_bits = 0
    if not guest:
        acc = _account(box, profile['account'], now)
        earned = int(acc.get('earned') or 0)
        proofs = int(acc.get('proofs') or 0)
        exchanged = int(acc.get('exchanged') or 0)
        paused = int(acc.get('penaltyUntil') or 0) > now
        personal_bits, _recent = _personal(acc, now, 'claims')
    remaining = max(0, cap - earned)
    room = issuance_room(state)
    nxt = 0 if guest else min(reward, remaining, epoch_left, room)
    xcap = 0 if guest else exchange_cap_smh(profile['age'], profile['play'], profile['quests'])
    _base, network = _budgets(box)
    slice_total = _base // ACCOUNT_SLICE_DEN
    exchange_left = 0 if guest else min(
        max(0, xcap - exchanged),
        max(0, slice_total - exchanged),
        network,
        int(box.get('smcPoolSmh') or 0),
    )
    return {
        'symbol': SYMBOL,
        'symbolBase': SYMBOL_BASE,
        'unit': UNIT,
        'subunitsPerUnit': SUBS,
        'bits': int(box.get('bits') or sup.START_BITS),
        'personal': personal_bits,
        'eraRewardSph': reward,
        'nextSph': int(nxt),
        'dailyCapSph': cap,
        'earnedSph': earned,
        'remainingSph': remaining,
        'epochRemainingSph': epoch_left,
        'proofsToday': proofs,
        'minedSph': int(box.get('minedSph') or 0),
        'burnedSph': int(box.get('burnedSph') or 0),
        'maxSupply': MAX_SUPPLY,
        'premineSph': PREMINE_SPH,
        'guest': guest,
        'paused': paused,
        'poolSmh': int(box.get('smcPoolSmh') or 0),
        'rateSphPerSmh': RATE_SPH_PER_SMH,
        'rateText': '100 SMP = 1 SMC',
        'shareText': 'Un quinto de cada SMC nueva queda en el fondo.',
        'exchangeCapSmh': xcap,
        'exchangedSmh': exchanged,
        'exchangeLeftSmh': int(exchange_left),
        'targetSeconds': sup.TARGET_INTERVAL,
        'proofsPerDay': sup.PROOFS_PER_DAY,
        'hint': HINT,
        'balanceSph': balance_of(state, profile['name']) if profile.get('name') else 0,
    }


def public_view(state, profile=None, now=None):
    ensure(state, now=now)
    now = int(now if now is not None else time.time())
    view = _view(state, _profile(profile), now)
    view['balanceSph'] = balance_of(state, _profile(profile)['name']) if _profile(profile)['name'] else 0
    return view


def _prune_used(box, now):
    used = box.setdefault('used', {})
    for ident, exp in list(used.items()):
        if int(exp) < now:
            used.pop(ident, None)


def open_challenge(state, profile, action, context, now=None):
    ensure(state, now=now)
    now = int(now if now is not None else time.time())
    profile = _profile(profile)
    box = state['plata']
    _roll_mine(box, now)
    view = _view(state, profile, now)
    if not profile['account'] or not profile['name']:
        return {'ok': False, 'reason': 'guest', 'view': view}
    acc = _account(box, profile['account'], now)
    row = _ip(box, profile['ip'], now)
    if int(row.get('penaltyUntil') or 0) > now or int(acc.get('penaltyUntil') or 0) > now:
        return {'ok': False, 'reason': 'anomaly', 'view': view}
    why = _ready(profile, acc, now, True, 'claims', 'lastClaim')
    if why:
        return {'ok': False, 'reason': why, 'view': view}
    acc['challenges'] = _prune(acc.get('challenges'), now, 600)
    row['challenges'] = _prune(row.get('challenges'), now, 600)
    if len(acc['challenges']) >= sup.CHALLENGES_PER_10MIN or len(row['challenges']) >= sup.IP_CHALLENGES_PER_10MIN:
        code = _pause(box, acc, row, now, profile['account'], profile['ip'], 'rate')
        return {'ok': False, 'reason': code, 'view': _view(state, profile, now)}
    personal, _recent = _personal(acc, now, 'claims')
    bits = min(sup.ABSOLUTE_BITS, int(box.get('bits') or sup.START_BITS) + personal)
    challenge = {
        'id': secrets.token_hex(16),
        'account': profile['account'],
        'action': _context(action),
        'context': _context(context),
        'bits': bits,
        'personal': personal,
        'exp': now + sup.CHALLENGE_TTL,
    }
    challenge['payload'] = _canonical(challenge)
    challenge['sig'] = _sign(box['secret'], challenge['payload'])
    challenge['coin'] = SYMBOL
    acc['challenges'].append(now)
    row['challenges'].append(now)
    _prune_used(box, now)
    return {'ok': True, 'challenge': challenge, 'view': _view(state, profile, now)}


def _read_proof(proof):
    if not isinstance(proof, dict):
        return None
    try:
        nonce = str(proof.get('nonce') if proof.get('nonce') is not None else '')
        if not re.fullmatch(r'[0-9]{1,20}', nonce):
            return None
        return {
            'id': str(proof.get('id') or ''),
            'account': str(proof.get('account') or ''),
            'action': _context(proof.get('action')),
            'context': _context(proof.get('context')),
            'bits': int(proof.get('bits')),
            'personal': int(proof.get('personal')),
            'exp': int(proof.get('exp')),
            'sig': str(proof.get('sig') or ''),
            'nonce': nonce,
        }
    except (TypeError, ValueError):
        return None


def redeem(state, profile, action, context, proof, now=None):
    """Verifica la prueba y acredita SPH. No escribe billeteras SMC."""
    ensure(state, now=now)
    now = int(now if now is not None else time.time())
    profile = _profile(profile)
    box = state['plata']
    _roll_mine(box, now)
    view = _view(state, profile, now)
    if not profile['account'] or not profile['name']:
        return {'ok': False, 'reason': 'guest', 'sph': 0, 'view': view}
    parsed = _read_proof(proof)
    if not parsed:
        return {'ok': False, 'reason': 'signature', 'sph': 0, 'view': view}
    payload = _canonical(parsed)
    expected = _sign(box.get('secret') or '', payload)
    if len(parsed['sig']) != len(expected) or not hmac.compare_digest(expected, parsed['sig']):
        return {'ok': False, 'reason': 'signature', 'sph': 0, 'view': view}
    if parsed['exp'] < now:
        return {'ok': False, 'reason': 'expired', 'sph': 0, 'view': view}
    _prune_used(box, now)
    if parsed['id'] in box.get('used', {}):
        return {'ok': False, 'reason': 'replay', 'sph': 0, 'view': view}
    if parsed['account'] != profile['account']:
        return {'ok': False, 'reason': 'account', 'sph': 0, 'view': view}
    if parsed['action'] != _context(action) or parsed['context'] != _context(context):
        return {'ok': False, 'reason': 'action', 'sph': 0, 'view': view}
    acc = _account(box, profile['account'], now)
    row = _ip(box, profile['ip'], now)
    if int(row.get('penaltyUntil') or 0) > now:
        return {'ok': False, 'reason': 'anomaly', 'sph': 0, 'view': view}
    personal, _recent = _personal(acc, now, 'claims')
    if parsed['personal'] < personal:
        return {'ok': False, 'reason': 'fast', 'sph': 0, 'view': view}
    digest = hashlib.sha256(f'{payload}|{parsed["nonce"]}'.encode('utf-8')).hexdigest()
    if sup.leading_zero_bits(digest) < parsed['bits']:
        return {'ok': False, 'reason': 'weak', 'sph': 0, 'view': view}
    why = _ready(profile, acc, now, False, 'claims', 'lastClaim')
    if why:
        if why == 'rate':
            _pause(box, acc, row, now, profile['account'], profile['ip'], 'rate')
        return {'ok': False, 'reason': why, 'sph': 0, 'view': _view(state, profile, now)}
    row['claims'] = _prune(row.get('claims'), now, 3600)
    if len(row['claims']) >= sup.IP_PROOFS_PER_HOUR:
        _pause(box, acc, row, now, profile['account'], profile['ip'], 'rate')
        return {'ok': False, 'reason': 'rate', 'sph': 0, 'view': _view(state, profile, now)}
    reward = reward_sph(box.get('minedSph'))
    cap = daily_cap_sph(profile['age'], profile['play'], profile['quests'])
    earned = int(acc.get('earned') or 0)
    personal_left = max(0, cap - earned)
    room = issuance_room(state)
    epoch_left = max(0, _ceiling(reward) - int(box.get('epochSubs') or 0))
    grant = min(reward, personal_left, room, epoch_left)
    if grant <= 0:
        if room <= 0 or reward <= 0:
            code = 'supply'
        elif epoch_left <= 0:
            code = 'ceiling'
        else:
            code = 'cap'
        return {'ok': False, 'reason': code, 'sph': 0, 'view': view}
    box.setdefault('used', {})[parsed['id']] = parsed['exp']
    acc['earned'] = earned + grant
    acc['proofs'] = int(acc.get('proofs') or 0) + 1
    acc['lastClaim'] = now
    acc.setdefault('claims', []).append(now)
    row['claims'].append(now)
    box['minedSph'] = int(box.get('minedSph') or 0) + grant
    box['epochSubs'] = int(box.get('epochSubs') or 0) + grant
    box['windowProofs'] = int(box.get('windowProofs') or 0) + 1
    elapsed = now - int(box.get('windowStart') or now)
    if box['windowProofs'] >= sup.WINDOW_PROOFS or elapsed >= sup.WINDOW_SECONDS:
        box['bits'] = sup.retarget_bits(box.get('bits'), box['windowProofs'], max(elapsed, 1))
        box['windowProofs'] = 0
        box['windowStart'] = now
    _credit(box, profile['name'], grant)
    _note(box, {'type': 'mint', 'to': profile['name'], 'amountSph': int(grant), 't': now})
    return {'ok': True, 'reason': '', 'sph': int(grant), 'view': _view(state, profile, now)}


def pool_share(granted):
    """Un quinto, en SMH enteros. El resto menor que 5 SMH se queda en la billetera."""
    return max(0, int(granted or 0)) // POOL_DEN


def apartar(state, name, granted, now=None):
    """Mueve un quinto de una emisión ya hecha al fondo. No crea SMC."""
    ensure(state, now=now)
    now = int(now if now is not None else time.time())
    granted = int(granted or 0)
    pooled = pool_share(granted)
    if pooled <= 0 or not name or reserved_name(name):
        return granted, 0
    if not eco.debit(state, name, pooled):
        return granted, 0
    box = state['plata']
    _roll_exchange(box, now)
    box['smcPoolSmh'] = int(box.get('smcPoolSmh') or 0) + pooled
    box['inflow'] = int(box.get('inflow') or 0) + pooled
    _note(box, {'type': 'pool', 'from': name, 'amountSmh': pooled, 't': now})
    return granted - pooled, pooled


def devolver(state, name, pooled, now=None):
    """Deshace un aporte si el libro madre no pudo anotarlo."""
    pooled = int(pooled or 0)
    box = state.get('plata') or {}
    if pooled <= 0 or not name:
        return
    have = int(box.get('smcPoolSmh') or 0)
    take = min(pooled, have)
    box['smcPoolSmh'] = have - take
    box['inflow'] = max(0, int(box.get('inflow') or 0) - take)
    if take:
        eco.credit(state, name, take)


def _parse_sph(value):
    if isinstance(value, bool) or value is None:
        raise eco.AmountError('monto vacío')
    if isinstance(value, int):
        if value < 0:
            raise eco.AmountError('monto ilegible')
        return value
    raw = str(value).strip().lower()
    if not raw:
        raise eco.AmountError('monto vacío')
    unit = 'smp'
    for name, kind in (('platicas', 'sph'), ('platica', 'sph'), ('sph', 'sph'), ('plata', 'smp'), ('smp', 'smp')):
        if raw.endswith(name):
            unit = kind
            raw = raw[: -len(name)].strip()
            break
    if unit == 'sph':
        return eco.parse_amount(raw + ' SMH')
    return eco.parse_amount(raw + ' SMC')


def exchange(state, profile, sph=None, now=None):
    """Quema Plata y paga SMC del fondo. No aumenta minedSmh ni el tope de 21 millones."""
    ensure(state, now=now)
    now = int(now if now is not None else time.time())
    profile = _profile(profile)
    box = state['plata']
    _roll_exchange(box, now)
    view = _view(state, profile, now)
    if not profile['account'] or not profile['name']:
        return {'ok': False, 'reason': 'guest', 'smh': 0, 'sph': 0, 'view': view}
    acc = _account(box, profile['account'], now)
    row = _ip(box, profile['ip'], now)
    if int(row.get('penaltyUntil') or 0) > now or int(acc.get('penaltyUntil') or 0) > now:
        return {'ok': False, 'reason': 'anomaly', 'smh': 0, 'sph': 0, 'view': view}
    why = _ready(profile, acc, now, True, 'xclaims', 'lastExchange')
    if why:
        if why == 'rate':
            _pause(box, acc, row, now, profile['account'], profile['ip'], 'rate')
            view = _view(state, profile, now)
        return {'ok': False, 'reason': why, 'smh': 0, 'sph': 0, 'view': view}
    row['xclaims'] = _prune(row.get('xclaims'), now, 3600)
    if len(row['xclaims']) >= sup.IP_PROOFS_PER_HOUR:
        _pause(box, acc, row, now, profile['account'], profile['ip'], 'rate')
        return {'ok': False, 'reason': 'rate', 'smh': 0, 'sph': 0, 'view': _view(state, profile, now)}
    have = balance_of(state, profile['name'])
    try:
        requested = have if sph is None else min(have, _parse_sph(sph))
    except (TypeError, ValueError, eco.AmountError):
        return {'ok': False, 'reason': 'dust', 'smh': 0, 'sph': 0, 'view': view}
    if requested > have:
        return {'ok': False, 'reason': 'funds', 'smh': 0, 'sph': 0, 'view': view}
    xcap = exchange_cap_smh(profile['age'], profile['play'], profile['quests'])
    exchanged = int(acc.get('exchanged') or 0)
    personal_left = max(0, xcap - exchanged)
    base, network = _budgets(box)
    slice_left = max(0, base // ACCOUNT_SLICE_DEN - exchanged)
    pool = int(box.get('smcPoolSmh') or 0)
    affordable = requested // RATE_SPH_PER_SMH
    smh = min(affordable, personal_left, slice_left, network, pool)
    if smh <= 0:
        if pool <= 0:
            code = 'pool'
        elif personal_left <= 0:
            code = 'exchange_cap'
        elif slice_left <= 0:
            code = 'slice'
        elif network <= 0:
            code = 'exchange_ceiling'
        elif have < RATE_SPH_PER_SMH:
            code = 'funds' if requested <= 0 else 'dust'
        else:
            code = 'dust'
        return {'ok': False, 'reason': code, 'smh': 0, 'sph': 0, 'view': view}
    spent = int(smh) * RATE_SPH_PER_SMH
    if not _debit(box, profile['name'], spent):
        return {'ok': False, 'reason': 'funds', 'smh': 0, 'sph': 0, 'view': view}
    box['smcPoolSmh'] = pool - int(smh)
    box['burnedSph'] = int(box.get('burnedSph') or 0) + spent
    box['outflow'] = int(box.get('outflow') or 0) + int(smh)
    acc['exchanged'] = exchanged + int(smh)
    acc['lastExchange'] = now
    acc.setdefault('xclaims', []).append(now)
    row['xclaims'].append(now)
    eco.credit(state, profile['name'], int(smh))
    _note(box, {
        'type': 'exchange', 'name': profile['name'], 'spentSph': spent,
        'gotSmh': int(smh), 't': now,
    })
    return {
        'ok': True, 'reason': '', 'smh': int(smh), 'sph': spent,
        'view': _view(state, profile, now),
    }


def undo_exchange(state, profile, smh, sph, now=None):
    """Devuelve la Plata y el fondo si el libro madre rechazó el pase."""
    smh = int(smh or 0)
    sph = int(sph or 0)
    if smh <= 0:
        return
    profile = _profile(profile)
    box = state.get('plata') or {}
    if not eco.debit(state, profile['name'], smh):
        return
    box['smcPoolSmh'] = int(box.get('smcPoolSmh') or 0) + smh
    box['burnedSph'] = max(0, int(box.get('burnedSph') or 0) - sph)
    box['outflow'] = max(0, int(box.get('outflow') or 0) - smh)
    _credit(box, profile['name'], sph)
    acc = (box.get('accounts') or {}).get(profile['account'])
    if acc:
        acc['exchanged'] = max(0, int(acc.get('exchanged') or 0) - smh)


def format_smp(sph):
    sph = int(sph or 0)
    sign = '-' if sph < 0 else ''
    whole, frac = divmod(abs(sph), SUBS)
    grouped = f'{whole:,}'.replace(',', '.')
    if frac == 0:
        return f'{sign}{grouped} {SYMBOL}'
    decimals = f'{frac:08d}'.rstrip('0')
    return f'{sign}{grouped},{decimals} {SYMBOL}'


def format_sph(sph):
    sph = int(sph or 0)
    sign = '-' if sph < 0 else ''
    grouped = f'{abs(sph):,}'.replace(',', '.')
    return f'{sign}{grouped} {SYMBOL_BASE}'


def format_pair(sph):
    return f'{format_smp(sph)} = {format_sph(sph)}'
