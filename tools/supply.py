# SPDX-License-Identifier: AGPL-3.0-or-later
"""Emisión de SMC con prueba de trabajo, tope diario y calendario público.

La unidad es el Simonchi (SMH). Este módulo no toca saldos ni bloques al
activarse: sólo añade la clave `supply` al libro. La reserva génesis sigue
en tesoro_genesis. No hay una rama de admin, dueño ni premine: esas marcas
se descartan antes de calcular nada.

La prueba de trabajo no basta contra un bot. El tope por cuenta, la actividad
en el juego y los límites por IP hacen el trabajo pesado.
"""
import hashlib
import hmac
import math
import re
import secrets
import time

import economy as eco

DAY = 86400
TARGET_INTERVAL = 600
PROOFS_PER_DAY = DAY // TARGET_INTERVAL  # 144
WINDOW_PROOFS = 12
WINDOW_SECONDS = 7200
START_BITS = 16
MIN_BITS = 12
MAX_BITS = 20
ABSOLUTE_BITS = 26
PERSONAL_STEP = 2
MAX_PROOFS_PER_HOUR = 4
CHALLENGE_TTL = 180
CLAIM_COOLDOWN = 60
ACTIVITY_TILES = 8
ACTIVITY_FRESH = 120
CHALLENGES_PER_10MIN = 6
IP_CHALLENGES_PER_10MIN = 12
IP_PROOFS_PER_HOUR = 8
PENALTY = 900
BASE_DAILY_SMH = eco.SUBS // 4          # 0,25 SMC
AGE_SMH = eco.SUBS // 20                # 0,05 SMC por día de cuenta, hasta 60
AGE_DAYS = 60
PLAY_SMH = eco.SUBS // 20               # 0,05 SMC por hora jugada, hasta 40
PLAY_HOURS = 40
QUEST_SMH = eco.SUBS // 10              # 0,10 SMC por misión, hasta 10
QUEST_CAP = 10
HINT = (
    'La prueba de trabajo sola no impide un bot. '
    'También hacen falta una cuenta, moverse en el juego, el tope del día y el cupo de la red.'
)
REASONS = {
    'guest': 'Entra con una cuenta para recibir SMC. Como invitado puedes jugar y recoger objetos, pero no monedas.',
    'replay': 'Esa prueba ya se usó.',
    'expired': 'La prueba caducó. Pide otra.',
    'weak': 'La prueba no alcanza la dificultad.',
    'signature': 'La prueba no es válida.',
    'account': 'La prueba es de otra cuenta.',
    'action': 'La prueba no corresponde a esta acción.',
    'fast': 'Vas más rápido de lo que esta cuenta puede minar. Pide otra prueba.',
    'cap': 'Llegaste al tope de SMC de hoy. Mañana se abre otro tramo.',
    'ceiling': 'La red ya emitió el cupo de este día.',
    'supply': 'Se alcanzó el tope de 21.000.000 SMC.',
    'activity': 'Muévete y juega un poco antes de reclamar SMC.',
    'cooldown': 'Espera un momento para volver a reclamar.',
    'rate': 'Demasiados intentos. Esta cuenta o esta red queda en pausa un rato.',
    'anomaly': 'Se detectó un ritmo anómalo. Esta cuenta o esta red queda en pausa un rato.',
    'partial': 'Ese lote pide más SMC de las que una prueba puede pagar hoy. El mineral sigue en la mochila.',
}


def reason_text(code):
    return REASONS.get(code, 'No se pudo emitir SMC.')


def ensure(state, now=None):
    """Añade el calendario si falta. No modifica billeteras, bloques ni minedSmh."""
    now = int(now if now is not None else time.time())
    box = state.get('supply')
    fresh = not isinstance(box, dict) or not box.get('secret')
    if not isinstance(box, dict):
        box = {}
        state['supply'] = box
    if not box.get('secret'):
        box['secret'] = secrets.token_hex(32)
    box['v'] = 1
    box.setdefault('bits', START_BITS)
    box['bits'] = int(box.get('bits') or START_BITS)
    if not box.get('windowStart'):
        box['windowStart'] = now
    box.setdefault('windowProofs', 0)
    epoch = now // DAY
    if 'epoch' not in box:
        box['epoch'] = epoch
        box['epochSubs'] = 0
    box.setdefault('used', {})
    box.setdefault('accounts', {})
    box.setdefault('ips', {})
    box.setdefault('flags', [])
    if fresh:
        box['_fresh'] = True
    return fresh


def daily_cap_smh(age_seconds, play_seconds, quests):
    """Tope del día UTC, en SMH. Crece con la cuenta, el tiempo jugado y las misiones."""
    days = min(AGE_DAYS, max(0, int(age_seconds)) // DAY)
    hours = min(PLAY_HOURS, max(0, int(play_seconds)) // 3600)
    done = min(QUEST_CAP, max(0, int(quests)))
    return BASE_DAILY_SMH + days * AGE_SMH + hours * PLAY_SMH + done * QUEST_SMH


def quest_count(state, name):
    raw = (state.get('questGrants') or {}).get(name)
    if raw is None:
        return 0
    if isinstance(raw, str):
        return 1
    if isinstance(raw, list):
        return len(raw)
    return 1


def quest_ids(state, name):
    raw = (state.get('questGrants') or {}).get(name)
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return [str(raw)]


def mark_quest(state, name, quest_id):
    done = quest_ids(state, name)
    if quest_id not in done:
        done.append(str(quest_id))
    state.setdefault('questGrants', {})[name] = done


def _clean_profile(profile):
    """Descarta admin, dueño, bypass y premine. Nadie tiene un cupo distinto."""
    data = dict(profile or {})
    for key in ('admin', 'owner', 'bypass', 'premine', 'role'):
        data.pop(key, None)
    data['account'] = str(data.get('account') or '')[:64]
    data['ip'] = str(data.get('ip') or '')[:64] or 'sin-ip'
    data['age'] = max(0, int(data.get('age') or 0))
    data['play'] = max(0, int(data.get('play') or 0))
    data['quests'] = max(0, int(data.get('quests') or 0))
    data['activity'] = float(data.get('activity') or 0)
    data['fresh'] = bool(data.get('fresh'))
    return data


def _roll(box, now):
    epoch = int(now) // DAY
    if int(box.get('epoch') or -1) != epoch:
        box['epoch'] = epoch
        box['epochSubs'] = 0
    return epoch


def _account(box, account, now):
    acc = box.setdefault('accounts', {}).setdefault(account, {})
    epoch = int(now) // DAY
    if int(acc.get('epoch') or -1) != epoch:
        acc['epoch'] = epoch
        acc['earned'] = 0
        acc['proofs'] = 0
    acc.setdefault('earned', 0)
    acc.setdefault('proofs', 0)
    acc.setdefault('lastClaim', 0)
    acc.setdefault('challenges', [])
    acc.setdefault('claims', [])
    acc.setdefault('penaltyUntil', 0)
    return acc


def _ip(box, ip, now):
    row = box.setdefault('ips', {}).setdefault(ip, {})
    row.setdefault('challenges', [])
    row.setdefault('claims', [])
    row.setdefault('penaltyUntil', 0)
    return row


def _prune(times, now, window):
    return [int(t) for t in (times or []) if now - int(t) < window]


def _flag(box, now, account, ip, reason):
    flags = box.setdefault('flags', [])
    flags.append({'t': int(now), 'account': account, 'ip': ip, 'reason': reason})
    del flags[:-40]


def _pause(box, acc, row, now, account, ip, reason):
    until = int(now) + PENALTY
    acc['penaltyUntil'] = max(int(acc.get('penaltyUntil') or 0), until)
    row['penaltyUntil'] = max(int(row.get('penaltyUntil') or 0), until)
    _flag(box, now, account, ip, reason)
    return reason


def _era_reward(state):
    return int(eco.reward_smh(int(state.get('minedSmh') or 0)))


def _diminished(reward, proofs_today):
    if reward <= 0 or proofs_today >= 63:
        return 0
    return int(reward) // (2 ** int(proofs_today))


def _ceiling(reward):
    return int(reward) * PROOFS_PER_DAY


def retarget_bits(bits, proofs, elapsed):
    """Sube o baja la dificultad hacia una prueba cada 10 minutos. Como mucho ±4 bits."""
    proofs = int(proofs or 0)
    elapsed = int(elapsed or 0)
    if proofs <= 0 or elapsed <= 0:
        return int(bits)
    actual = elapsed / proofs
    delta = math.log2(TARGET_INTERVAL / actual)
    delta = max(-4.0, min(4.0, delta))
    return int(max(MIN_BITS, min(MAX_BITS, round(int(bits) + delta))))


def leading_zero_bits(hexdigest):
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


def search_nonce(payload, bits, limit=2_000_000):
    """Busca un nonce. Lo usan las pruebas; el servidor del juego no mina."""
    bits = int(bits)
    for i in range(int(limit)):
        nonce = str(i)
        digest = hashlib.sha256(f'{payload}|{nonce}'.encode('utf-8')).hexdigest()
        if leading_zero_bits(digest) >= bits:
            return nonce
    return None


def _context(text):
    out = re.sub(r'[^A-Za-z0-9_.:-]', '', str(text or ''))[:80]
    return out or 'accion'


def _canonical(challenge):
    return '|'.join([
        'smc-pow-1',
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


def _personal(acc, now):
    recent = _prune(acc.get('claims'), now, 3600)
    acc['claims'] = recent
    return PERSONAL_STEP * len(recent), recent


def _ready(profile, acc, now, opening):
    if not profile['account']:
        return 'guest'
    if int(acc.get('penaltyUntil') or 0) > now:
        return 'anomaly'
    if opening and not profile['fresh']:
        return 'activity'
    if profile['activity'] < ACTIVITY_TILES:
        return 'activity'
    if now - int(acc.get('lastClaim') or 0) < CLAIM_COOLDOWN:
        return 'cooldown'
    _extra, recent = _personal(acc, now)
    if len(recent) >= MAX_PROOFS_PER_HOUR:
        return 'rate'
    return ''


def _view(state, profile, now):
    box = state['supply']
    _roll(box, now)
    reward = _era_reward(state)
    ceiling = _ceiling(reward)
    epoch_left = max(0, ceiling - int(box.get('epochSubs') or 0))
    guest = not profile['account']
    cap = daily_cap_smh(profile['age'], profile['play'], profile['quests'])
    earned = 0
    proofs = 0
    paused = False
    personal = 0
    if not guest:
        acc = _account(box, profile['account'], now)
        earned = int(acc.get('earned') or 0)
        proofs = int(acc.get('proofs') or 0)
        paused = int(acc.get('penaltyUntil') or 0) > now
        personal, _recent = _personal(acc, now)
    remaining = max(0, cap - earned)
    nxt = 0 if guest else min(_diminished(reward, proofs), remaining, epoch_left, eco.issuance_room(state))
    return {
        'bits': int(box.get('bits') or START_BITS),
        'personal': personal,
        'eraRewardSubs': reward,
        'nextSubs': int(nxt),
        'dailyCapSubs': cap,
        'earnedSubs': earned,
        'remainingSubs': remaining,
        'epochRemainingSubs': epoch_left,
        'proofsToday': proofs,
        'guest': guest,
        'paused': paused,
        'targetSeconds': TARGET_INTERVAL,
        'proofsPerDay': PROOFS_PER_DAY,
        'maxSupply': eco.MAX_SUPPLY,
        'treasury': eco.TREASURY,
        'hint': HINT,
    }


def public_view(state, profile=None, now=None):
    ensure(state, now=now)
    now = int(now if now is not None else time.time())
    return _view(state, _clean_profile(profile), now)


def open_challenge(state, profile, action, context, now=None):
    ensure(state, now=now)
    now = int(now if now is not None else time.time())
    profile = _clean_profile(profile)
    box = state['supply']
    _roll(box, now)
    view = _view(state, profile, now)
    if not profile['account']:
        return {'ok': False, 'reason': 'guest', 'view': view}
    acc = _account(box, profile['account'], now)
    row = _ip(box, profile['ip'], now)
    if int(row.get('penaltyUntil') or 0) > now or int(acc.get('penaltyUntil') or 0) > now:
        return {'ok': False, 'reason': 'anomaly', 'view': view}
    why = _ready(profile, acc, now, opening=True)
    if why:
        return {'ok': False, 'reason': why, 'view': view}
    acc['challenges'] = _prune(acc.get('challenges'), now, 600)
    row['challenges'] = _prune(row.get('challenges'), now, 600)
    if len(acc['challenges']) >= CHALLENGES_PER_10MIN or len(row['challenges']) >= IP_CHALLENGES_PER_10MIN:
        code = _pause(box, acc, row, now, profile['account'], profile['ip'], 'rate')
        return {'ok': False, 'reason': code, 'view': _view(state, profile, now)}
    personal, _recent = _personal(acc, now)
    bits = min(ABSOLUTE_BITS, int(box.get('bits') or START_BITS) + personal)
    challenge = {
        'id': secrets.token_hex(16),
        'account': profile['account'],
        'action': _context(action),
        'context': _context(context),
        'bits': bits,
        'personal': personal,
        'exp': now + CHALLENGE_TTL,
    }
    challenge['payload'] = _canonical(challenge)
    challenge['sig'] = _sign(box['secret'], challenge['payload'])
    acc['challenges'].append(now)
    row['challenges'].append(now)
    _prune_used(box, now)
    return {'ok': True, 'challenge': challenge, 'view': _view(state, profile, now)}


def _prune_used(box, now):
    used = box.setdefault('used', {})
    for ident, exp in list(used.items()):
        if int(exp) < now:
            used.pop(ident, None)


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


def redeem(state, profile, action, context, proof, want_smh=None, room_smh=None, exact=False, counts_as_mint=True, now=None):
    """Verifica la prueba y reserva los SMH que caben. No escribe la billetera."""
    ensure(state, now=now)
    now = int(now if now is not None else time.time())
    profile = _clean_profile(profile)
    box = state['supply']
    _roll(box, now)
    view = _view(state, profile, now)
    if not profile['account']:
        return {'ok': False, 'reason': 'guest', 'smh': 0, 'view': view}
    parsed = _read_proof(proof)
    if not parsed:
        return {'ok': False, 'reason': 'signature', 'smh': 0, 'view': view}
    payload = _canonical(parsed)
    secret = box.get('secret') or ''
    expected = _sign(secret, payload)
    if not hmac.compare_digest(expected, parsed['sig']):
        return {'ok': False, 'reason': 'signature', 'smh': 0, 'view': view}
    if parsed['exp'] < now:
        return {'ok': False, 'reason': 'expired', 'smh': 0, 'view': view}
    _prune_used(box, now)
    if parsed['id'] in box.get('used', {}):
        return {'ok': False, 'reason': 'replay', 'smh': 0, 'view': view}
    if parsed['account'] != profile['account']:
        return {'ok': False, 'reason': 'account', 'smh': 0, 'view': view}
    if parsed['action'] != _context(action) or parsed['context'] != _context(context):
        return {'ok': False, 'reason': 'action', 'smh': 0, 'view': view}
    acc = _account(box, profile['account'], now)
    row = _ip(box, profile['ip'], now)
    if int(row.get('penaltyUntil') or 0) > now:
        return {'ok': False, 'reason': 'anomaly', 'smh': 0, 'view': view}
    personal, recent = _personal(acc, now)
    if parsed['personal'] < personal:
        return {'ok': False, 'reason': 'fast', 'smh': 0, 'view': view}
    digest = hashlib.sha256(f'{payload}|{parsed["nonce"]}'.encode('utf-8')).hexdigest()
    if leading_zero_bits(digest) < parsed['bits']:
        return {'ok': False, 'reason': 'weak', 'smh': 0, 'view': view}
    why = _ready(profile, acc, now, opening=False)
    if why:
        if why == 'rate':
            _pause(box, acc, row, now, profile['account'], profile['ip'], 'rate')
        return {'ok': False, 'reason': why, 'smh': 0, 'view': _view(state, profile, now)}
    row['claims'] = _prune(row.get('claims'), now, 3600)
    if len(row['claims']) >= IP_PROOFS_PER_HOUR:
        _pause(box, acc, row, now, profile['account'], profile['ip'], 'rate')
        return {'ok': False, 'reason': 'rate', 'smh': 0, 'view': _view(state, profile, now)}
    reward = _era_reward(state)
    cap = daily_cap_smh(profile['age'], profile['play'], profile['quests'])
    earned = int(acc.get('earned') or 0)
    personal_left = max(0, cap - earned)
    diminished = _diminished(reward, int(acc.get('proofs') or 0))
    room = eco.issuance_room(state) if room_smh is None else max(0, int(room_smh))
    grant = min(diminished, personal_left, room)
    if counts_as_mint:
        epoch_left = max(0, _ceiling(reward) - int(box.get('epochSubs') or 0))
        grant = min(grant, epoch_left)
    if want_smh is not None:
        grant = min(grant, max(0, int(want_smh)))
    if grant <= 0:
        if room <= 0:
            code = 'supply'
        elif counts_as_mint and _ceiling(reward) - int(box.get('epochSubs') or 0) <= 0:
            code = 'ceiling'
        else:
            code = 'cap'
        return {'ok': False, 'reason': code, 'smh': 0, 'view': view}
    if exact and want_smh is not None and grant < int(want_smh):
        return {'ok': False, 'reason': 'partial', 'smh': 0, 'view': view}
    box.setdefault('used', {})[parsed['id']] = parsed['exp']
    acc['earned'] = earned + grant
    acc['proofs'] = int(acc.get('proofs') or 0) + 1
    acc['lastClaim'] = now
    acc.setdefault('claims', []).append(now)
    row['claims'].append(now)
    if counts_as_mint:
        box['epochSubs'] = int(box.get('epochSubs') or 0) + grant
        box['windowProofs'] = int(box.get('windowProofs') or 0) + 1
        elapsed = now - int(box.get('windowStart') or now)
        if box['windowProofs'] >= WINDOW_PROOFS or elapsed >= WINDOW_SECONDS:
            box['bits'] = retarget_bits(box.get('bits'), box['windowProofs'], max(elapsed, 1))
            box['windowProofs'] = 0
            box['windowStart'] = now
    return {'ok': True, 'reason': '', 'smh': int(grant), 'view': _view(state, profile, now), 'minted': bool(counts_as_mint)}


def restore(state, account, smh, minted=True, undo_claim=False):
    """Devuelve cupo si la emisión o el libro madre no pudieron anotar el monto."""
    box = state.get('supply') or {}
    acc = (box.get('accounts') or {}).get(account)
    smh = int(smh or 0)
    if not acc or smh <= 0:
        return
    acc['earned'] = max(0, int(acc.get('earned') or 0) - smh)
    if minted:
        box['epochSubs'] = max(0, int(box.get('epochSubs') or 0) - smh)
    if undo_claim:
        acc['proofs'] = max(0, int(acc.get('proofs') or 0) - 1)
        claims = acc.get('claims') or []
        if claims:
            claims.pop()
        if minted:
            box['windowProofs'] = max(0, int(box.get('windowProofs') or 0) - 1)
