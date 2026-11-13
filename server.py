#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""LIFE INC · El Jardín — servidor local (sólo biblioteca estándar de Python, sin npm ni pip).

- Sirve la vista previa jugable (HTTP) y el chat/presencia multijugador (WebSocket en /ws) en el MISMO puerto.
- Uso:  python3 server.py              -> http://127.0.0.1:$PORT/play/  (PORT, o 8765)
        python3 server.py --port 8765 --host 0.0.0.0 --sin-bots
- Canales de chat: Global, Proximidad (≤ 30 m = 15 casillas), Clan, Grupo.
"""
import secrets, sys, uuid
import argparse, asyncio, base64, hashlib, json, mimetypes, os, random, re, socket, struct, time, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
import economy as ECO
import supply as SUP
import plata as PLATA
import ed25519
import libro as LIBRO
import nft as NFT
import payout as PAYOUT
import playtime as PLAY
import vault as VAULT
import viajes as VIAJES
import accounts as ACC
import fusion as FUSION
import historia as HISTORIA

ROOT = os.path.dirname(os.path.abspath(__file__))
GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
BLOCKED = ('/references', '/tools', '/server.py', '/state')
LEGAL_PAGES = {
    '/privacidad': 'legal/privacidad.html',
    '/terminos': 'legal/terminos.html',
}
PROX_TILES = 15           # 30 m con 2 m por casilla
MAX_TEXT = 160
CHANNELS = ('global', 'proximidad', 'clan', 'grupo')
SERVER_ID = uuid.uuid4().hex[:12]

with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as f:
    WORLD = json.load(f)
COLL = WORLD['collision']
SPAWN = (WORLD['spawn']['x'], WORLD['spawn']['y'])
_pl = next((a for a in WORLD.get('areas', []) if a['id'] == 'plaza'), None)
PLAZA_C = (_pl['x'] + _pl['w'] // 2, _pl['y'] + _pl['h'] // 2) if _pl else SPAWN
COLORS = list(WORLD.get('playerVariants', {}).keys()) or ['azul']
ECON_PATH = os.path.join(ROOT, 'state', 'economy.json')
ECON = ECO.load_state(ECON_PATH)
NFT_PATH = os.path.join(ROOT, 'state', 'nft.json')
NFT_KEY_PATH = os.path.join(ROOT, 'state', 'nft-key.json')
VAULT_PATH = os.path.join(ROOT, 'state', 'vault.json')
PLAY_PATH = os.path.join(ROOT, 'state', 'players.json')
PLAYERS = PLAY.load(PLAY_PATH)
ACCOUNTS_PATH = os.path.join(ROOT, 'state', 'accounts.json')
ACCOUNTS = ACC.load(ACCOUNTS_PATH)
NFT_SEED = NFT.load_seed(NFT_KEY_PATH)
NFT_PUB = ed25519.publickey(NFT_SEED)
NFT_CHAIN = NFT.load_chain(NFT_PATH, NFT_PUB.hex())
VAULT_STATE = VAULT.load(VAULT_PATH)
LIBRO_PATH = os.path.join(ROOT, 'state', 'libro-madre.json')
LIBRO_CHAIN = LIBRO.load(LIBRO_PATH, NFT_PUB.hex())
FOUNDRY = {
    'mineral_cobre': (3, 4),
    'mineral_plata': (4, 12),
    'mineral_oro': (5, 30),
    'pepita_oro': (5, 30),
}
SHIFT_SWINGS = 8
SHIFT_PAY = 10
QUEST_GRANTS = {'primeros_pasos': 250, 'el_libro_mayor': 50}

def save_econ():
    ECO.save_state(ECON_PATH, ECON)

def save_nft():
    NFT.save_chain(NFT_PATH, NFT_CHAIN)

def save_vault():
    VAULT.save(VAULT_PATH, VAULT_STATE)

def save_play():
    PLAY.save(PLAY_PATH, PLAYERS)

def save_accounts():
    ACC.save(ACCOUNTS_PATH, ACCOUNTS)

def save_libro(records):
    if not records:
        return
    try:
        LIBRO.save(LIBRO_PATH, LIBRO_CHAIN, [r['id'] for r in records])
    except persist_duplicate:
        for record in records:
            LIBRO.revertir(LIBRO_CHAIN, record)
        raise

def persist_duplicate_type():
    import persist
    return persist.DuplicateId

persist_duplicate = persist_duplicate_type()

def anotar_emision(owner, smh, location, kind='acuñacion'):
    smh = int(smh or 0)
    if smh <= 0:
        return None
    record = LIBRO.acuñar(LIBRO_CHAIN, NFT_SEED, owner, smh, location, kind=kind)
    if record is None:
        return None
    save_libro([record])
    return LIBRO.publico(record)

def anotar_pase(origen, destino, smh, note):
    record = LIBRO.transferir(LIBRO_CHAIN, NFT_SEED, origen, destino, int(smh), note)
    save_libro([record])
    return LIBRO.publico(record)

def river_label(node):
    key = node.get('waterBody') or ''
    body = (WORLD.get('waterBodies') or {}).get(key) or {}
    name = body.get('name') or 'Río'
    return f"{name} · {node.get('x')},{node.get('y')}"

_migrados = LIBRO.migrar(LIBRO_CHAIN, NFT_SEED, ECON.get('wallets') or {}, VAULT_STATE.get('accounts') or {})
save_libro(_migrados)

def maybe_fuse():
    """Pasa el SMC ya emitido a la cuenta del fundador, una sola vez."""
    result = FUSION.apply(ECON, ACCOUNTS, VAULT_STATE)
    if not result.get('changed'):
        return result
    fresh = result.get('fresh') or []
    dest = (result.get('record') or {}).get('wallet') or ''
    records = []
    for item in fresh:
        origen = item.get('libroFrom') or item.get('from')
        amount = int(item.get('amountSubs') or 0)
        have = int(LIBRO.balances(LIBRO_CHAIN).get(origen) or 0)
        take = min(amount, have)
        if take <= 0 or not dest or origen == dest:
            continue
        try:
            records.append(LIBRO.transferir(
                LIBRO_CHAIN, NFT_SEED, origen, dest, take, FUSION.NOTE,
            ))
        except LIBRO.LibroError as exc:
            print('[fusion] el libro madre no anotó', origen, exc, flush=True)
    if records:
        try:
            save_libro(records)
        except persist_duplicate:
            print('[fusion] el libro madre ya tenía ese código; el libro mayor sí quedó', flush=True)
    save_econ()
    save_vault()
    if result.get('status') == 'pending':
        print('[fusion] pendiente hasta que entre saimon888oficial@gmail.com', flush=True)
    elif fresh:
        moved = sum(int(item.get('amountSubs') or 0) for item in fresh)
        print(f'[fusion] {len(fresh)} pases, {moved} SMH hacia {dest}. {FUSION.NOTE}', flush=True)
    elif result.get('changed'):
        print('[fusion] depósito ya anotado; no se acreditó otra vez', flush=True)
    return result

maybe_fuse()

def play_for(name, active=True):
    info = PLAY.beat(PLAYERS, name, active=active)
    save_play()
    return info

def certify(owner, amount_smh, foundry, tile):
    token = NFT.issue(NFT_CHAIN, NFT_SEED, owner, int(amount_smh or 0), foundry, tile)
    if token:
        save_nft()
    return token

LEDGER_PAGE = 20
GOLD_NODES = [n for n in WORLD.get('nodes', []) if n.get('type') == 'nodo_oro_fluvial']
NODE_READY = {}
RESET_NOTE = ' El libro de esta simulación se reinicia cuando el servidor se apaga o se vuelve a desplegar.'

def block_page(before=None):
    blocks = ECON.get('blocks') or []
    if before is None:
        return blocks[-LEDGER_PAGE:]
    older = [b for b in blocks if int(b.get('height') or 0) < int(before)]
    return older[-LEDGER_PAGE:]

def econ_msg(who=None, before=None, reveal_token=None, locked=False, profile=None):
    page = block_page(before)
    m = {'t': 'economy', 'state': {
        'minedSmh': int(ECON.get('minedSmh') or 0), 'blocks': page, 'blockCount': len(ECON.get('blocks') or []),
        'mempool': ECON.get('mempool', []), 'disclaimer': (ECON.get('disclaimer') or '') + RESET_NOTE,
        'ledgerResets': True, 'symbol': 'SMC', 'symbolBase': 'SMH', 'unit': 'SaiMonCoin',
        'smallestName': 'Simonchi', 'subunitsPerUnit': ECO.SUBS,         'maxSupply': ECO.MAX_SUPPLY,
        'maxSupplySmh': ECO.MAX_SMH,
        'historia': HISTORIA.filas(ECON),
    }}
    if who:
        m['balanceSubs'] = 0 if locked else int((ECON.get('wallets') or {}).get(who) or 0)
        m['walletLocked'] = bool(locked)
    if reveal_token:
        m['walletToken'] = reveal_token
    view = SUP.public_view(ECON, profile)
    if who:
        view['owedSubs'] = int((ECON.get('questOwed') or {}).get(who) or 0)
    m['supply'] = view
    plata_profile = dict(profile or {})
    if who and not locked:
        plata_profile['name'] = who
    pview = PLATA.public_view(ECON, plata_profile)
    pview['balanceSph'] = 0 if locked or not who else PLATA.balance_of(ECON, who)
    m['plata'] = pview
    m['balanceSph'] = pview['balanceSph']
    return m

def token_matches(stored, presented):
    if not stored or not presented or len(stored) != len(str(presented)):
        return False
    return secrets.compare_digest(stored, str(presented))

def bind_wallet(name, presented):
    """Crea la billetera o reconoce a quien guarda el token. No revela el secreto ajeno."""
    wallets = ECON.setdefault('wallets', {})
    tokens = ECON.setdefault('walletTokens', {})
    if name not in wallets:
        wallets[name] = 0
    if name not in tokens:
        token = secrets.token_hex(16)
        tokens[name] = token
        save_econ()
        return token
    if token_matches(tokens[name], presented):
        return tokens[name]
    return None

def gold_node_for(x, y, node_id):
    node = next((n for n in GOLD_NODES if n.get('id') == node_id), None)
    if not node:
        return None
    if max(abs(float(x) - node['x']), abs(float(y) - node['y'])) > 1.25:
        return None
    return node

def leer_smh(message):
    """Lee un monto en SMH. amountSmh es entero; sin eso, el número va en SMC."""
    if not isinstance(message, dict):
        return ECO.smc_to_smh(message)
    if message.get('amountSmh') is not None:
        return int(message.get('amountSmh'))
    unit = str(message.get('unit') or '').strip()
    if unit:
        return ECO.parse_amount(f"{message.get('amount')} {unit}")
    if isinstance(message.get('amount'), str):
        return ECO.parse_amount(message.get('amount'))
    raw = message.get('amountSai') if message.get('amountSai') is not None else message.get('amount')
    return ECO.smc_to_smh(raw or 0)


def pagar(sender, dest, smh, note='Transferencia /pagar'):
    if not getattr(sender, 'wallet_ok', False):
        send(sender, {'t': 'pay_result', 'ok': False, 'to': dest})
        return send(sender, {'t': 'system', 'text': 'Esta billetera SMC se creó en otro aparato. Puedes jugar con este nombre, pero no gastar esas monedas.'})
    bind_wallet(sender.name, getattr(sender, 'wallet_token', ''))
    dests = {c.name: c.name for c in clients.values() if c.hello}
    dests['puesto_frutas'] = 'puesto_frutas'
    hit = next((dests[n] for n in dests if n.lower() == str(dest or '').strip().lower()), None)
    if not hit:
        send(sender, {'t': 'pay_result', 'ok': False, 'to': dest})
        return send(sender, {'t': 'system', 'text': f'No encuentro a «{dest}». Usa un jugador conectado o puesto_frutas.'})
    try:
        smh = int(smh)
    except (TypeError, ValueError):
        return send(sender, {'t': 'system', 'text': 'El monto no es válido.'})
    if smh <= 0:
        send(sender, {'t': 'pay_result', 'ok': False, 'to': hit})
        return send(sender, {'t': 'system', 'text': 'El monto debe ser mayor que cero.'})
    if not ECO.debit(ECON, sender.name, smh):
        send(sender, {'t': 'pay_result', 'ok': False, 'to': hit})
        return send(sender, {'t': 'system', 'text': 'No tienes saldo suficiente en SMC.'})
    ECO.credit(ECON, hit, smh)
    ECO.append_tx(ECON, {'type': 'pay', 'from': sender.name, 'to': hit, 'amountSubs': smh, 'note': note})
    try:
        anotar_pase(sender.name, hit, smh, note)
    except (LIBRO.LibroError, persist_duplicate):
        ECO.credit(ECON, sender.name, smh)
        ECO.debit(ECON, hit, smh)
        mem = ECON.get('mempool') or []
        if mem and mem[-1].get('from') == sender.name and int(mem[-1].get('amountSubs') or 0) == smh:
            mem.pop()
        return send(sender, {'t': 'system', 'text': 'El libro madre no pudo anotar ese pago.'})
    save_econ()
    broadcast_econ()
    send(sender, {'t': 'pay_result', 'ok': True, 'to': hit, 'note': note, 'amountSmh': smh, 'amountText': ECO.format_pair(smh)})
    broadcast({'t': 'system', 'text': f'{sender.name} pagó {ECO.format_pair(smh)} a {hit}. Sólo es una simulación, sin valor real.'})

def client_ip(headers, writer):
    forwarded = (headers.get('x-forwarded-for') or '').split(',')[0].strip()
    if forwarded:
        return forwarded[:64]
    peer = writer.get_extra_info('peername') if writer else None
    if peer:
        return str(peer[0])[:64]
    return ''

def note_motion(sender, step):
    step = float(step or 0)
    if step <= 0:
        return
    sender.activity_tiles = float(getattr(sender, 'activity_tiles', 0) or 0) + min(step, 4.0)
    sender.last_activity_at = time.time()

def account_profile(sender, now=None):
    """Edad, juego y misiones. Las marcas de admin se pasan y supply las tira."""
    now = time.time() if now is None else now
    user = getattr(sender, 'user', None) or {}
    name = getattr(sender, 'name', '') or ''
    box = PLAY.ensure(PLAYERS, name, now=int(now)) if name else {}
    created = int(user.get('createdAt') or box.get('createdAt') or now)
    role = str(user.get('role') or '')
    return {
        'account': str(user.get('id') or ''),
        'name': name,
        'ip': str(getattr(sender, 'ip', '') or ''),
        'age': max(0, int(now - created)),
        'play': int(box.get('playtime') or 0),
        'quests': SUP.quest_count(ECON, name),
        'activity': float(getattr(sender, 'activity_tiles', 0) or 0),
        'fresh': (now - float(getattr(sender, 'last_activity_at', 0) or 0)) <= SUP.ACTIVITY_FRESH,
        'admin': bool(user.get('admin') or user.get('owner') or role in ('admin', 'owner', 'dev')),
        'bypass': bool(user.get('bypass') or user.get('premine')),
    }

def fail_claim(sender, code, channel='system'):
    text = SUP.reason_text(code)
    try:
        view = SUP.public_view(ECON, account_profile(sender))
    except Exception:
        view = {}
    name = getattr(sender, 'name', '') or ''
    if isinstance(view, dict):
        view['owedSubs'] = int((ECON.get('questOwed') or {}).get(name) or 0)
    send(sender, {'t': 'pow_result', 'ok': False, 'reason': text, 'code': code, 'supply': view})
    if channel == 'smelt':
        send(sender, {'t': 'smelt_result', 'ok': False, 'needPow': False, 'reason': text, 'supply': view})
    else:
        send(sender, {'t': 'system', 'text': text})
    return {'ok': False, 'reason': code, 'smh': 0}

def take_proof(sender, action, context, proof, resume, want_smh=None, exact=False, counts_as_mint=True, room_smh=None):
    if getattr(sender, 'bot', False):
        return fail_claim(sender, 'guest', channel='smelt' if action == 'fundicion' else 'system')
    if not getattr(sender, 'wallet_ok', False):
        send(sender, {'t': 'system', 'text': 'Esta billetera SMC se creó en otro aparato. Puedes jugar, pero no emitir monedas con ese nombre.'})
        return {'ok': False, 'reason': 'wallet', 'smh': 0}
    profile = account_profile(sender)
    if proof:
        result = SUP.redeem(
            ECON, profile, action, context, proof,
            want_smh=want_smh, room_smh=room_smh, exact=exact, counts_as_mint=counts_as_mint,
        )
        save_econ()
        if not result.get('ok'):
            return fail_claim(sender, result.get('reason') or 'signature', channel='smelt' if action == 'fundicion' else 'system')
        return result
    opened = SUP.open_challenge(ECON, profile, action, context)
    save_econ()
    if not opened.get('ok'):
        return fail_claim(sender, opened.get('reason') or 'guest', channel='smelt' if action == 'fundicion' else 'system')
    sender.pow_challenge = opened['challenge']
    view = opened.get('view') or {}
    view['owedSubs'] = int((ECON.get('questOwed') or {}).get(getattr(sender, 'name', '') or '') or 0)
    send(sender, {'t': 'pow_challenge', 'challenge': opened['challenge'], 'resume': resume, 'supply': view})
    if action == 'fundicion':
        send(sender, {'t': 'smelt_result', 'ok': False, 'needPow': True, 'reason': 'Calculando la prueba de trabajo. El mineral sigue en la mochila.', 'supply': view})
    return {'ok': False, 'pending': True, 'smh': 0}

def revert_issue(name, granted):
    if granted <= 0:
        return
    ECO.debit(ECON, name, granted)
    ECON['minedSmh'] = max(0, int(ECON.get('minedSmh') or 0) - int(granted))
    mem = ECON.get('mempool') or []
    if mem and mem[-1].get('to') == name and int(mem[-1].get('amountSubs') or 0) == int(granted):
        mem.pop()

def emitir(sender, smh, note, kind, foundry, tile, location):
    profile = account_profile(sender)
    granted = ECO.issue(ECON, sender.name, smh, note, kind)
    if granted <= 0:
        SUP.restore(ECON, profile['account'], smh, minted=True, undo_claim=True)
        save_econ()
        return 0, None, None
    if granted < int(smh):
        SUP.restore(ECON, profile['account'], int(smh) - granted, minted=True, undo_claim=False)
    pub = anotar_emision(sender.name, granted, location)
    if not pub:
        revert_issue(sender.name, granted)
        SUP.restore(ECON, profile['account'], granted, minted=True, undo_claim=True)
        save_econ()
        return 0, None, None
    token = certify(sender.name, granted, foundry, tile)
    kept, pooled = PLATA.apartar(ECON, sender.name, granted)
    if pooled:
        try:
            anotar_pase(sender.name, PLATA.POOL, pooled, 'Aporte al fondo de cambio')
            ECO.append_tx(ECON, {
                'type': 'pool', 'from': sender.name, 'to': PLATA.POOL,
                'amountSubs': pooled, 'note': 'Un quinto al fondo de cambio',
            })
        except (LIBRO.LibroError, persist_duplicate):
            PLATA.devolver(ECON, sender.name, pooled)
            pooled = 0
            kept = granted
    sender.kept_smh = kept
    sender.pool_smh = pooled
    sender.activity_tiles = 0
    save_econ()
    broadcast_econ()
    return granted, token, pub

def mint_for(sender, node_id, proof=None):
    if not getattr(sender, 'wallet_ok', False):
        return send(sender, {'t': 'system', 'text': 'Esta billetera SMC se creó en otro aparato. Puedes jugar, pero no emitir monedas con ese nombre.'})
    if getattr(sender, 'zone', 'city') != 'city':
        return send(sender, {'t': 'system', 'text': 'Las SMC sólo se emiten al lavar oro en el río, fuera de la casa.'})
    node = gold_node_for(sender.x, sender.y, node_id)
    if not node:
        return send(sender, {'t': 'system', 'text': 'Hay que estar junto a la arena de oro del río para emitir SMC.'})
    now = time.time()
    if now < NODE_READY.get(node['id'], 0):
        return send(sender, {'t': 'system', 'text': 'Esa arena ya se lavó. El río trae más dentro de un rato.'})
    bind_wallet(sender.name, getattr(sender, 'wallet_token', ''))
    room = min(ECO.issuance_room(ECON), LIBRO.cupo_subs(LIBRO_CHAIN))
    result = take_proof(
        sender, 'mint', node['id'], proof,
        {'t': 'mint', 'node': node['id']},
        room_smh=room,
    )
    if not result.get('ok'):
        return
    lugar = river_label(node)
    granted, token, libro_pub = emitir(
        sender, result['smh'], 'Emisión por prueba de trabajo en el río', 'mint',
        'rio', f"{node['x']},{node['y']}", lugar,
    )
    if granted <= 0:
        return send(sender, {'t': 'system', 'text': 'Se alcanzó el tope minable de SMC.'})
    NODE_READY[node['id']] = time.time() + (float(node.get('respawnMs') or 30000) / 1000.0)
    kept = int(getattr(sender, 'kept_smh', granted) or 0)
    pooled = int(getattr(sender, 'pool_smh', 0) or 0)
    if pooled:
        send(sender, {'t': 'system', 'text': f'Se acuñaron {ECO.format_pair(granted)}. Tu billetera recibe {ECO.format_pair(kept)} y el fondo de cambio aparta {ECO.format_pair(pooled)}. No es dinero real.'})
    else:
        send(sender, {'t': 'system', 'text': f'Se acuñaron {ECO.format_pair(granted)}. Es una simulación: no es dinero real.'})
    send(sender, {'t': 'issued', 'amountSmh': kept, 'mintedSmh': granted, 'pooledSmh': pooled, 'amountText': ECO.format_pair(kept), 'kind': 'mint', 'certificate': token, 'libro': libro_pub, 'supply': result.get('view')})

def fail_plata(sender, code):
    text = PLATA.reason_text(code)
    try:
        view = PLATA.public_view(ECON, account_profile(sender))
    except Exception:
        view = {}
    if isinstance(view, dict):
        view['balanceSph'] = PLATA.balance_of(ECON, getattr(sender, 'name', '') or '')
    send(sender, {'t': 'plata_result', 'ok': False, 'reason': text, 'code': code, 'plata': view, 'coin': 'SMP'})
    send(sender, {'t': 'system', 'text': text})
    return {'ok': False, 'reason': code, 'sph': 0}


def mint_plata(sender, proof=None):
    if getattr(sender, 'bot', False):
        return fail_plata(sender, 'guest')
    if not getattr(sender, 'wallet_ok', False):
        return fail_plata(sender, 'wallet')
    profile = account_profile(sender)
    if proof:
        result = PLATA.redeem(ECON, profile, 'plata', 'libre', proof)
        save_econ()
        if not result.get('ok'):
            return fail_plata(sender, result.get('reason') or 'signature')
        sender.activity_tiles = 0
        save_econ()
        broadcast_econ()
        sph = int(result.get('sph') or 0)
        text = f'Se minaron {PLATA.format_pair(sph)}. Es una simulación: no es dinero real.'
        send(sender, {'t': 'system', 'text': text})
        send(sender, {'t': 'issued', 'coin': 'SMP', 'amountSph': sph, 'amountText': PLATA.format_pair(sph), 'kind': 'plata', 'plata': result.get('view')})
        send(sender, {'t': 'plata_result', 'ok': True, 'reason': text, 'amountSph': sph, 'amountText': PLATA.format_pair(sph), 'plata': result.get('view'), 'coin': 'SMP'})
        return result
    opened = PLATA.open_challenge(ECON, profile, 'plata', 'libre')
    save_econ()
    if not opened.get('ok'):
        return fail_plata(sender, opened.get('reason') or 'guest')
    sender.pow_challenge = opened['challenge']
    send(sender, {'t': 'pow_challenge', 'challenge': opened['challenge'], 'resume': {'t': 'mint_plata'}, 'plata': opened.get('view'), 'coin': 'SMP'})
    return {'ok': False, 'pending': True, 'sph': 0}


def exchange_plata(sender, sph=None):
    if getattr(sender, 'bot', False):
        return fail_plata(sender, 'guest')
    if not getattr(sender, 'wallet_ok', False):
        return fail_plata(sender, 'wallet')
    profile = account_profile(sender)
    result = PLATA.exchange(ECON, profile, sph)
    if not result.get('ok'):
        save_econ()
        return fail_plata(sender, result.get('reason') or 'pool')
    smh = int(result.get('smh') or 0)
    spent = int(result.get('sph') or 0)
    try:
        anotar_pase(PLATA.POOL, sender.name, smh, 'Cambio de Plata por SMC')
    except (LIBRO.LibroError, persist_duplicate):
        PLATA.undo_exchange(ECON, profile, smh, spent)
        save_econ()
        return fail_plata(sender, 'pool')
    ECO.append_tx(ECON, {
        'type': 'exchange', 'from': PLATA.POOL, 'to': sender.name,
        'amountSubs': smh, 'spentSph': spent, 'note': 'Cambio de plata por oro',
    })
    sender.activity_tiles = 0
    save_econ()
    broadcast_econ()
    text = f'Cambiaste {PLATA.format_pair(spent)} por {ECO.format_pair(smh)}. La Plata se quemó y el SMC salió del fondo. No es dinero real.'
    view = PLATA.public_view(ECON, profile)
    view['balanceSph'] = PLATA.balance_of(ECON, sender.name)
    send(sender, {'t': 'system', 'text': text})
    send(sender, {'t': 'exchange_result', 'ok': True, 'spentSph': spent, 'gotSmh': smh, 'amountText': ECO.format_pair(smh), 'plataText': PLATA.format_pair(spent), 'reason': text, 'plata': view, 'coin': 'SMP'})
    return result


def wallet_ready(sender):
    if not getattr(sender, 'wallet_ok', False):
        send(sender, {'t': 'system', 'text': 'Esta billetera SMC se creó en otro aparato. Puedes jugar, pero no mover esas monedas.'})
        return False
    bind_wallet(sender.name, getattr(sender, 'wallet_token', ''))
    return True

def smelt_for(sender, ore, batches, proof=None):
    recipe = FOUNDRY.get(str(ore or ''))
    if not recipe or getattr(sender, 'zone', 'city') != 'mine':
        return send(sender, {'t': 'smelt_result', 'ok': False, 'reason': 'Hay que fundir dentro de la cantera.'})
    try:
        batches = int(batches)
    except (TypeError, ValueError):
        batches = 0
    if batches < 1 or batches > 30:
        return send(sender, {'t': 'smelt_result', 'ok': False, 'reason': 'La cantidad de lotes no es válida.'})
    if not wallet_ready(sender):
        return send(sender, {'t': 'smelt_result', 'ok': False, 'reason': 'Billetera de otro aparato.'})
    _ore, coins = recipe
    want = ECO.smc_to_smh(coins * batches)
    context = f'{ore}:{batches}'
    result = take_proof(
        sender, 'fundicion', context, proof,
        {'t': 'smelt', 'ore': ore, 'batches': batches},
        want_smh=want, exact=True,
        room_smh=min(ECO.issuance_room(ECON), LIBRO.cupo_subs(LIBRO_CHAIN)),
    )
    if not result.get('ok'):
        return
    granted, token, libro_pub = emitir(
        sender, result['smh'], f'Fundición de {ore} en la cantera', 'fundicion',
        'fundidora', 'horno_cantera', 'Fundidora de la cantera',
    )
    if granted <= 0:
        return send(sender, {'t': 'smelt_result', 'ok': False, 'reason': 'Se alcanzó el tope de 21.000.000 SMC.', 'grantedSmh': 0})
    kept = int(getattr(sender, 'kept_smh', granted) or 0)
    pooled = int(getattr(sender, 'pool_smh', 0) or 0)
    note = f'La fundidora acreditó {ECO.format_pair(kept)} a tu billetera.'
    if pooled:
        note += f' El fondo de cambio apartó {ECO.format_pair(pooled)}.'
    send(sender, {'t': 'smelt_result', 'ok': True, 'grantedSmh': kept, 'mintedSmh': granted, 'pooledSmh': pooled, 'amountText': ECO.format_pair(kept), 'ore': ore, 'batches': batches, 'certificate': token, 'libro': libro_pub, 'supply': result.get('view')})
    send(sender, {'t': 'system', 'text': note})

def swing_for(sender, mineral, proof=None):
    mineral = str(mineral or '')
    if mineral not in ('cobre', 'plata') or getattr(sender, 'zone', '') != 'mine':
        return
    if not wallet_ready(sender):
        return
    if not proof and not getattr(sender, 'shift_ready', False):
        now = time.time()
        if now - getattr(sender, 'last_swing', 0) < 1:
            return
        sender.last_swing = now
        note_motion(sender, 1)
        sender.swings = getattr(sender, 'swings', 0) + 1
        if sender.swings < SHIFT_SWINGS:
            return send(sender, {'t': 'shift', 'swings': sender.swings, 'need': SHIFT_SWINGS, 'left': SHIFT_SWINGS - sender.swings})
        sender.shift_ready = True
    if not getattr(sender, 'shift_ready', False):
        return
    result = take_proof(
        sender, 'mina', mineral, proof,
        {'t': 'swing', 'mineral': mineral},
        want_smh=ECO.smc_to_smh(SHIFT_PAY),
        room_smh=min(ECO.issuance_room(ECON), LIBRO.cupo_subs(LIBRO_CHAIN)),
    )
    if not result.get('ok'):
        return
    granted, token, _pub = emitir(
        sender, result['smh'], 'Turno del capataz en la cantera (cobre o plata)', 'mina',
        'mina', 'cantera', 'Cantera · turno',
    )
    sender.swings = 0
    sender.shift_ready = False
    try:
        PAYOUT.ADAPTER.payout(sender.name, granted, 'USDT')
    except RuntimeError:
        pass
    kept = int(getattr(sender, 'kept_smh', granted) or 0)
    pooled = int(getattr(sender, 'pool_smh', 0) or 0)
    shift_note = 'El turno paga sólo lo que cabe en el tope de hoy. No hay retiro a OnePay ni a USDT.'
    if pooled:
        shift_note = f'El turno acredita {ECO.format_pair(kept)}. El fondo de cambio aparta {ECO.format_pair(pooled)}. ' + shift_note
    send(sender, {'t': 'shift', 'swings': 0, 'need': SHIFT_SWINGS, 'paidSmh': kept, 'mintedSmh': granted, 'pooledSmh': pooled, 'amountText': ECO.format_pair(kept), 'certificate': token,
                  'note': shift_note, 'supply': result.get('view')})

def migration_left(sender, amount):
    prior = (ECON.get('migrations') or {}).get(sender.name)
    if isinstance(prior, dict) and prior.get('done', True):
        return 0
    if isinstance(prior, dict):
        return max(0, int(prior.get('requested') or 0) - int(prior.get('credited') or 0))
    try:
        if isinstance(amount, str):
            amount = ECO.parse_amount(amount) // ECO.SUBS
        requested = ECO.smc_to_smh(amount or 0)
    except (TypeError, ValueError, ECO.AmountError):
        requested = 0
    return max(0, requested)

def migrate_for(sender, amount, proof=None):
    if not wallet_ready(sender):
        return send(sender, {'t': 'migrate_result', 'ok': False})
    left = migration_left(sender, amount)
    if left <= 0:
        return send(sender, {'t': 'migrate_result', 'ok': True, 'already': True, 'credited': 0, 'rate': 1,
                             'note': '1 moneda antigua del Jardín = 1 SMC. El SAI ya guardado sigue 1:1 y no se vuelve a convertir.'})
    result = take_proof(
        sender, 'migrate', 'migrate', proof,
        {'t': 'migrate', 'amount': amount or 0},
        want_smh=left,
        room_smh=min(ECO.issuance_room(ECON), LIBRO.cupo_subs(LIBRO_CHAIN)),
    )
    if not result.get('ok'):
        return
    converted = ECO.migrate_monedas(ECON, sender.name, amount or 0, limit_smh=result['smh'])
    credited = int(converted.get('credited') or 0)
    if credited < int(result['smh']):
        SUP.restore(ECON, account_profile(sender)['account'], int(result['smh']) - credited, minted=True, undo_claim=credited <= 0)
    if credited:
        anotar_emision(sender.name, credited, 'Conversión de monedas antiguas')
        _kept, pooled = PLATA.apartar(ECON, sender.name, credited)
        if pooled:
            try:
                anotar_pase(sender.name, PLATA.POOL, pooled, 'Aporte al fondo de cambio')
                ECO.append_tx(ECON, {
                    'type': 'pool', 'from': sender.name, 'to': PLATA.POOL,
                    'amountSubs': pooled, 'note': 'Un quinto al fondo de cambio',
                })
            except (LIBRO.LibroError, persist_duplicate):
                PLATA.devolver(ECON, sender.name, pooled)
    else:
        save_econ()
    token = certify(sender.name, credited, 'migracion', 'jardin') if credited else None
    if credited:
        sender.activity_tiles = 0
        save_econ()
        broadcast_econ()
    send(sender, {'t': 'migrate_result', 'ok': True, 'rate': converted['rate'], 'credited': credited,
                  'already': converted['already'], 'certificate': token, 'supply': result.get('view'),
                  'note': '1 moneda antigua del Jardín = 1 SMC. Si no cupo hoy, el resto espera al próximo día.'})

def quest_for(sender, quest_id, proof=None):
    quest_id = str(quest_id or '')
    amount = QUEST_GRANTS.get(quest_id)
    owed = int((ECON.get('questOwed') or {}).get(sender.name) or 0)
    done = quest_id in SUP.quest_ids(ECON, sender.name)
    if not wallet_ready(sender):
        return
    if (not amount and owed <= 0) or (done and owed <= 0):
        return send(sender, {'t': 'quest_result', 'ok': True, 'already': True, 'amountSmh': 0})
    want = owed if done else ECO.smc_to_smh(amount)
    treasury = int((ECON.get('wallets') or {}).get('tesoro_genesis') or 0)
    result = take_proof(
        sender, 'quest', quest_id, proof,
        {'t': 'quest', 'id': quest_id},
        want_smh=min(want, treasury), exact=False, counts_as_mint=False, room_smh=treasury,
    )
    if not result.get('ok'):
        return
    smh = int(result['smh'])
    if smh <= 0 or not ECO.debit(ECON, 'tesoro_genesis', smh):
        SUP.restore(ECON, account_profile(sender)['account'], smh, minted=False, undo_claim=True)
        save_econ()
        return send(sender, {'t': 'quest_result', 'ok': False, 'reason': 'La reserva de misiones no alcanza.'})
    ECO.credit(ECON, sender.name, smh)
    ECO.append_tx(ECON, {'type': 'grant', 'from': 'tesoro_genesis', 'to': sender.name, 'amountSubs': smh, 'note': quest_id})
    try:
        anotar_pase('tesoro_genesis', sender.name, smh, quest_id)
    except (LIBRO.LibroError, persist_duplicate):
        pass
    if not done and amount:
        SUP.mark_quest(ECON, sender.name, quest_id)
        ECON.setdefault('questOwed', {})[sender.name] = max(0, ECO.smc_to_smh(amount) - smh)
    else:
        ECON.setdefault('questOwed', {})[sender.name] = max(0, owed - smh)
    sender.activity_tiles = 0
    save_econ()
    broadcast_econ()
    send(sender, {'t': 'quest_result', 'ok': True, 'already': False, 'amountSmh': smh, 'amountText': ECO.format_pair(smh),
                  'owedSubs': int(ECON['questOwed'].get(sender.name) or 0), 'supply': result.get('view')})

def vault_for(sender):
    if not wallet_ready(sender):
        return
    box = VAULT.account(VAULT_STATE, sender.name)
    try:
        plata = PLATA.public_view(ECON, account_profile(sender))
        plata['balanceSph'] = PLATA.balance_of(ECON, sender.name)
    except Exception:
        plata = {}
    send(sender, {'t': 'vault', 'account': VAULT.public_account(box), 'plata': plata,
                  'note': 'El banquito y el baúl de la casa son el mismo depósito. No se pierde al morir: sólo la mochila que llevas encima puede caerse.'})

def deposit_smc(sender, amount):
    if not wallet_ready(sender):
        return
    try:
        smh = int(amount)
    except (TypeError, ValueError):
        return
    if smh <= 0 or not ECO.debit(ECON, sender.name, smh):
        return send(sender, {'t': 'system', 'text': 'No hay SMC suficientes en la billetera para depositar.'})
    VAULT.add_smc(VAULT.account(VAULT_STATE, sender.name), smh)
    ECO.append_tx(ECON, {'type': 'bank', 'from': sender.name, 'to': 'deposito', 'amountSubs': smh, 'note': 'Depósito en el banquito'})
    try:
        anotar_pase(sender.name, 'deposito:' + sender.name, smh, 'Depósito en el banquito')
    except (LIBRO.LibroError, persist_duplicate):
        pass
    save_econ(); save_vault(); broadcast_econ(); vault_for(sender)

def withdraw_smc(sender, amount):
    if not wallet_ready(sender):
        return
    try:
        smh = int(amount)
    except (TypeError, ValueError):
        return
    box = VAULT.account(VAULT_STATE, sender.name)
    if smh <= 0 or not VAULT.take_smc(box, smh):
        return send(sender, {'t': 'system', 'text': 'El depósito no tiene tantas SMC.'})
    ECO.credit(ECON, sender.name, smh)
    ECO.append_tx(ECON, {'type': 'bank', 'from': 'deposito', 'to': sender.name, 'amountSubs': smh, 'note': 'Retiro del banquito'})
    try:
        anotar_pase('deposito:' + sender.name, sender.name, smh, 'Retiro del banquito')
    except (LIBRO.LibroError, persist_duplicate):
        pass
    save_econ(); save_vault(); broadcast_econ(); vault_for(sender)

def leer_sph(message):
    """Lee platicas (SPH). Un entero ya está en SPH; «1 SMP» son 100.000.000 SPH."""
    if isinstance(message, int):
        return PLATA.parse_sph(message)
    if not isinstance(message, dict):
        return PLATA.parse_sph(message)
    if message.get('sph') is not None:
        return PLATA.parse_sph(message.get('sph'))
    return PLATA.parse_sph(message.get('amount'))


def _anotar_plata_banco(sender, sph, incoming):
    sph = int(sph)
    if incoming:
        origin, dest, note = sender.name, 'deposito', 'Depósito de Plata en el banquito'
    else:
        origin, dest, note = 'deposito', sender.name, 'Retiro de Plata del banquito'
    ECO.append_tx(ECON, {
        'type': 'bank', 'coin': 'SMP', 'from': origin, 'to': dest,
        'amountSubs': 0, 'amountSph': sph, 'note': note,
    })


def deposit_smp(sender, sph):
    """Guarda Plata en el depósito. No acuña SMP ni SMC."""
    if not wallet_ready(sender):
        return
    try:
        sph = int(sph)
    except (TypeError, ValueError):
        return
    if sph <= 0 or not PLATA.park(ECON, sender.name, sph):
        return send(sender, {'t': 'system', 'text': 'No hay Plata suficiente en la billetera para guardar.'})
    VAULT.add_smp(VAULT.account(VAULT_STATE, sender.name), sph)
    _anotar_plata_banco(sender, sph, True)
    save_econ(); save_vault(); broadcast_econ(); vault_for(sender)


def withdraw_smp(sender, sph):
    """Saca Plata del depósito a la billetera. No acuña."""
    if not wallet_ready(sender):
        return
    try:
        sph = int(sph)
    except (TypeError, ValueError):
        return
    box = VAULT.account(VAULT_STATE, sender.name)
    if sph <= 0 or not VAULT.take_smp(box, sph):
        return send(sender, {'t': 'system', 'text': 'El depósito no tiene tanta Plata.'})
    if not PLATA.unpark(ECON, sender.name, sph):
        VAULT.add_smp(box, sph)
        return send(sender, {'t': 'system', 'text': 'No se pudo devolver la Plata a la billetera.'})
    _anotar_plata_banco(sender, sph, False)
    save_econ(); save_vault(); broadcast_econ(); vault_for(sender)


def deposit_item(sender, item, qty):
    if not wallet_ready(sender):
        return
    item = clean(item, 32)
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        qty = 0
    if not item or qty < 1 or qty > 999:
        return
    VAULT.add_item(VAULT.account(VAULT_STATE, sender.name), item, qty)
    save_vault()
    send(sender, {'t': 'vault_item', 'op': 'deposit', 'item': item, 'qty': qty})
    vault_for(sender)

def withdraw_item(sender, item, qty):
    if not wallet_ready(sender):
        return
    item = clean(item, 32)
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        qty = 0
    box = VAULT.account(VAULT_STATE, sender.name)
    if not item or qty < 1 or not VAULT.take_item(box, item, qty):
        return send(sender, {'t': 'system', 'text': 'El depósito no tiene esa cantidad.'})
    save_vault()
    send(sender, {'t': 'vault_item', 'op': 'withdraw', 'item': item, 'qty': qty})
    vault_for(sender)

clients = {}      # id -> Client
next_id = 1

class Client:
    def __init__(self, writer, bot=False):
        global next_id
        self.id = next_id; next_id += 1
        self.w = writer; self.bot = bot
        self.name = f'Jugador{self.id}'; self.color = 'azul'; self.clan = 'LIFE INC'; self.group = ''
        self.x, self.y, self.dir, self.moving = float(SPAWN[0]), float(SPAWN[1]), 'down', False
        self.level = 1; self.hello = False; self.stamps = []; self.zone = 'city'
    def public(self):
        return {'id': self.id, 'avatar_id': ('avatar_' + self.user['id']) if getattr(self, 'user', None) else None, 'name': self.name, 'color': self.color, 'clan': self.clan, 'group': self.group,
                'x': round(self.x, 2), 'y': round(self.y, 2), 'dir': self.dir, 'moving': self.moving, 'level': self.level, 'bot': self.bot, 'zone': self.zone}

def clean(s, n):
    s = re.sub(r'[\x00-\x1f\x7f<>]', '', str(s or '')).strip()
    return s[:n]

# ---------------- WebSocket mínimo (RFC 6455) ----------------
def frame(text):
    data = text.encode('utf-8'); n = len(data)
    if n < 126: head = struct.pack('!BB', 0x81, n)
    elif n < 65536: head = struct.pack('!BBH', 0x81, 126, n)
    else: head = struct.pack('!BBQ', 0x81, 127, n)
    return head + data

async def read_frame(reader):
    b1, b2 = await reader.readexactly(2)
    op = b1 & 0x0F; masked = b2 & 0x80; n = b2 & 0x7F
    if n == 126: n = struct.unpack('!H', await reader.readexactly(2))[0]
    elif n == 127: n = struct.unpack('!Q', await reader.readexactly(8))[0]
    if n > 65536: raise ConnectionError('frame demasiado grande')
    mask = await reader.readexactly(4) if masked else b'\0\0\0\0'
    payload = bytearray(await reader.readexactly(n))
    for i in range(n): payload[i] ^= mask[i % 4]
    return op, bytes(payload)

def send(c, obj):
    if c.bot or c.w is None: return
    try: c.w.write(frame(json.dumps(obj, ensure_ascii=False)))
    except Exception: pass

def broadcast(obj, who=None, exclude=None):
    for c in list(clients.values()):
        if c is exclude or not c.hello: continue
        if who is None or who(c): send(c, obj)

def broadcast_econ():
    for c in list(clients.values()):
        if c.hello and not c.bot:
            send(c, econ_msg(c.name, locked=not getattr(c, 'wallet_ok', False), profile=account_profile(c)))

def dist(a, b):
    if a is b: return 0
    if getattr(a, 'zone', 'city') == 'casa' or getattr(b, 'zone', 'city') == 'casa': return 1e9
    return max(abs(a.x - b.x), abs(a.y - b.y))

def unique_name(name, me):
    if PLATA.reserved_name(name):
        name = 'Viajero'
    if not getattr(me, 'user', None) and ACC.reserved_nickname(ACCOUNTS, name):
        name = 'Invitado'
    if getattr(me, 'user', None):
        return me.user.get('wallet_name') or me.user['name']
    base = name or f'Jugador{me.id}'; n = base; k = 2
    while ACC.reserved_nickname(ACCOUNTS, n) or any(c is not me and ACC.name_key(c.name) == ACC.name_key(n) for c in clients.values()): n = f'{base[:12]}{k}'; k += 1
    return n

def chat(sender, channel, text):
    now = time.time()
    sender.stamps = [t for t in sender.stamps if now - t < 5]
    if len(sender.stamps) >= 6 and not sender.bot:
        return send(sender, {'t': 'system', 'text': 'Vas muy rápido: espera unos segundos.'})
    sender.stamps.append(now)
    text = clean(text, MAX_TEXT)
    if not text: return
    if text.startswith('/'):
        raw = text[1:].strip()
        cmd, _, rest = raw.partition(' ')
        cmd = cmd.lower()
        if cmd == 'pagar':
            parts = rest.split()
            if len(parts) < 2:
                return send(sender, {'t': 'system', 'text': 'Uso: /pagar <jugador> <monto>  (SMC o SMH, sólo en el juego)'})
            if parts[-1].lower() in ('smc', 'smh', 'simonchi', 'simonchis'):
                if len(parts) < 3:
                    return send(sender, {'t': 'system', 'text': 'El monto no es válido.'})
                dest, monto_s = ' '.join(parts[:-2]), parts[-2] + ' ' + parts[-1]
            else:
                dest, monto_s = ' '.join(parts[:-1]), parts[-1]
            try:
                smh = ECO.parse_amount(monto_s)
            except ECO.AmountError:
                return send(sender, {'t': 'system', 'text': 'El monto no es válido. Usa SMC (hasta 8 decimales) o SMH enteros.'})
            return pagar(sender, dest, smh)
        arg = clean(rest, 24)
        if cmd == 'grupo':
            sender.group = arg
            send(sender, {'t': 'system', 'text': f'Ahora estás en el grupo «{arg}».' if arg else 'Saliste del grupo.'})
            return broadcast({'t': 'player', 'player': sender.public()})
        if cmd == 'clan':
            sender.clan = arg
            send(sender, {'t': 'system', 'text': f'Tu clan ahora es «{sender.clan}».' if arg else 'Saliste del clan.'})
            return broadcast({'t': 'player', 'player': sender.public()})
        return send(sender, {'t': 'system', 'text': 'Comandos: /grupo <nombre> · /clan <nombre> · /pagar <jugador> <monto>'})
    if channel not in CHANNELS: channel = 'proximidad'
    msg = {'t': 'chat', 'channel': channel, 'from': sender.name, 'fromId': sender.id, 'clan': sender.clan, 'text': text,
           'ts': time.strftime('%H:%M'), 'bot': sender.bot}
    if channel == 'global': broadcast(msg)
    elif channel == 'proximidad': broadcast(msg, lambda c: dist(c, sender) <= PROX_TILES)
    elif channel == 'clan': broadcast(msg, lambda c: c.clan.lower() == sender.clan.lower())
    elif channel == 'grupo':
        if not sender.group: return send(sender, {'t': 'system', 'text': 'No estás en un grupo. Escribe /grupo <nombre> para crear o unirte a uno.'})
        broadcast(msg, lambda c: c.group and c.group.lower() == sender.group.lower())

def arrival_position(resume=None):
    # Start within the same connected spawn area, on an unoccupied walkable tile.
    occupied = [(c.x, c.y) for c in clients.values() if c.hello]
    if isinstance(resume, dict):
        try:
            x, y = float(resume['x']), float(resume['y'])
            if walkable(int(x), int(y)) and x >= 0 and y >= 0:
                return x, y
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
    seen = {SPAWN}; queue = [SPAWN]
    for x, y in queue:
        if walkable(x, y) and all(abs(x-ox) >= 0.9 or abs(y-oy) >= 0.9 for ox, oy in occupied):
            return float(x), float(y)
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            tile = (x+dx,y+dy)
            if tile not in seen and walkable(*tile):
                seen.add(tile); queue.append(tile)
    return float(SPAWN[0]), float(SPAWN[1])

TRAVEL_GATE = VIAJES.Gate()

def travel_for(sender, dest_id):
    """Lleva al jugador a un municipio o punto conocido. El servidor elige la casilla."""
    now = time.time()
    try:
        dest = VIAJES.resolve(WORLD, clean(dest_id, 32).lower())
    except VIAJES.ViajeError as exc:
        return send(sender, {'t': 'travel_result', 'ok': False, 'reason': str(exc)})
    if not TRAVEL_GATE.allow(sender.id, now):
        return send(sender, {'t': 'travel_result', 'ok': False, 'reason': 'Espera un momento para volver a viajar.'})
    was_hidden = sender.zone != 'city'
    sender.zone = 'city'
    sender.x, sender.y = float(dest['x']), float(dest['y'])
    sender.moving = False
    if was_hidden:
        broadcast({'t': 'join', 'player': sender.public()}, exclude=sender)
    else:
        broadcast({'t': 'move', 'id': sender.id, 'x': sender.x, 'y': sender.y, 'dir': sender.dir, 'moving': False, 'level': sender.level, 'zone': 'city'}, exclude=sender)
    send(sender, {'t': 'travel_result', 'ok': True, 'id': dest['id'], 'name': dest['name'], 'x': dest['x'], 'y': dest['y']})

async def handle_ws(reader, writer, cookie='', ip=''):
    c = Client(writer); clients[c.id] = c
    c.ip = ip or ''
    c.user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
    try:
        while True:
            op, data = await asyncio.wait_for(read_frame(reader), 45)  # el cliente hace ping cada 3 s
            if op == 8: break
            if op == 9: writer.write(struct.pack('!BB', 0x8A, len(data)) + data); continue
            if op != 1: continue
            try: m = json.loads(data.decode('utf-8'))
            except Exception: continue
            t = m.get('t')
            if t == 'hello':
                if c.hello: continue
                c.zone = m.get('zone') if m.get('zone') in ('casa', 'mine', 'banco', 'city') else 'city'
                if c.zone == 'casa': c.x, c.y = float(SPAWN[0]), float(SPAWN[1])
                else: c.x, c.y = arrival_position(m.get('resume'))
                asked = c.user.get('wallet_name') if getattr(c, 'user', None) else m.get('name')
                token_src = c.user.get('wallet_token') if getattr(c, 'user', None) else m.get('walletToken')
                c.name = unique_name(clean(asked, 16), c)
                c.color = m.get('color') if m.get('color') in COLORS else random.choice(COLORS)
                c.clan = clean(m.get('clan'), 24); c.group = clean(m.get('group'), 24)
                c.level = int(m.get('level') or 1);                 c.hello = True
                presented = clean(token_src, 64)
                owned = bind_wallet(c.name, presented)
                c.wallet_ok = bool(owned)
                c.wallet_token = owned or ''
                send(c, {'t': 'welcome', 'id': c.id, 'you': c.public(), 'players': [o.public() for o in clients.values() if o.hello and o is not c and o.zone != 'casa'],
                         'proximityTiles': PROX_TILES, 'serverId': SERVER_ID, 'worldBuild': WORLD.get('build')})
                if c.zone != 'casa':
                    broadcast({'t': 'join', 'player': c.public()}, exclude=c)
                    broadcast({'t': 'system', 'text': f'{c.name} entró a El Jardín.'}, exclude=c)
                send(c, econ_msg(c.name, reveal_token=owned, locked=not c.wallet_ok, profile=account_profile(c)))
                if c.wallet_ok:
                    send(c, {'t': 'playtime', **play_for(c.name, active=True)})
                if not c.wallet_ok:
                    send(c, {'t': 'system', 'text': 'Ese nombre ya tiene una billetera SMC en otro aparato. Puedes entrar, pero no gastar ni emitir esas monedas.'})
            elif t == 'travel' and c.hello:
                travel_for(c, m.get('id'))
            elif t == 'move' and c.hello:
                zone = m.get('zone')
                if zone in ('casa', 'mine', 'banco'):
                    if c.zone == 'city' and zone != 'city':
                        broadcast({'t': 'leave', 'id': c.id}, exclude=c)
                    c.zone = zone
                    continue
                was_casa = c.zone != 'city'
                c.zone = 'city'
                try:
                    nx = max(0.0, min(WORLD['width'] - 1.0, float(m['x']))); ny = max(0.0, min(WORLD['height'] - 1.0, float(m['y'])))
                except Exception: continue
                step = max(abs(nx - c.x), abs(ny - c.y))
                c.x, c.y = nx, ny
                note_motion(c, step)
                c.dir = m.get('dir') if m.get('dir') in ('up', 'down', 'left', 'right') else c.dir
                c.moving = bool(m.get('moving')); c.level = int(m.get('level') or c.level)
                if was_casa: broadcast({'t': 'join', 'player': c.public()}, exclude=c)
                else: broadcast({'t': 'move', 'id': c.id, 'x': round(c.x, 2), 'y': round(c.y, 2), 'dir': c.dir, 'moving': c.moving, 'level': c.level, 'zone': 'city'}, exclude=c)
            elif t == 'ping':
                send(c, {'t': 'pong', 'c': m.get('c')})
            elif t == 'chat' and c.hello:
                chat(c, str(m.get('channel', 'proximidad')).lower(), m.get('text'))
            elif t == 'mint' and c.hello:
                mint_for(c, clean(m.get('node'), 40), m.get('proof'))
            elif t == 'mint_plata' and c.hello:
                mint_plata(c, m.get('proof'))
            elif t == 'exchange_plata' and c.hello:
                try:
                    if m.get('max'):
                        exchange_plata(c, None)
                    elif m.get('sph') is not None:
                        exchange_plata(c, m.get('sph'))
                    elif m.get('amount') is not None:
                        exchange_plata(c, m.get('amount'))
                    else:
                        fail_plata(c, 'dust')
                except (TypeError, ValueError, ECO.AmountError):
                    fail_plata(c, 'dust')
            elif t == 'ledger' and c.hello:
                try:
                    before = int(m.get('before'))
                except (TypeError, ValueError):
                    before = None
                send(c, econ_msg(c.name, before=before, locked=not c.wallet_ok, profile=account_profile(c)))
            elif t == 'pay' and c.hello:
                try:
                    smh = leer_smh(m)
                except (TypeError, ValueError, ECO.AmountError):
                    continue
                pagar(c, m.get('to'), smh, clean(m.get('note') or 'Pago', 80) or 'Pago')
            elif t == 'smelt' and c.hello:
                smelt_for(c, m.get('ore'), m.get('batches'), m.get('proof'))
            elif t == 'swing' and c.hello:
                swing_for(c, m.get('mineral'), m.get('proof'))
            elif t == 'migrate' and c.hello:
                migrate_for(c, m.get('amount'), m.get('proof'))
            elif t == 'quest' and c.hello:
                quest_for(c, m.get('id'), m.get('proof'))
            elif t == 'heartbeat' and c.hello and c.wallet_ok:
                send(c, {'t': 'playtime', **play_for(c.name, active=bool(m.get('active')))})
            elif t == 'vault' and c.hello:
                vault_for(c)
            elif t == 'deposit_smc' and c.hello:
                try:
                    deposit_smc(c, leer_smh(m))
                except (TypeError, ValueError, ECO.AmountError):
                    pass
            elif t == 'withdraw_smc' and c.hello:
                try:
                    withdraw_smc(c, leer_smh(m))
                except (TypeError, ValueError, ECO.AmountError):
                    pass
            elif t == 'deposit_smp' and c.hello:
                try:
                    deposit_smp(c, leer_sph(m))
                except (TypeError, ValueError, ECO.AmountError):
                    send(c, {'t': 'system', 'text': 'Monto de Plata no válido. Ejemplo: 1 SMP o 100000000 SPH.'})
            elif t == 'withdraw_smp' and c.hello:
                try:
                    withdraw_smp(c, leer_sph(m))
                except (TypeError, ValueError, ECO.AmountError):
                    send(c, {'t': 'system', 'text': 'Monto de Plata no válido. Ejemplo: 1 SMP o 100000000 SPH.'})
            elif t == 'deposit_item' and c.hello:
                deposit_item(c, m.get('item'), m.get('qty'))
            elif t == 'withdraw_item' and c.hello:
                withdraw_item(c, m.get('item'), m.get('qty'))
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionError, OSError, asyncio.TimeoutError):
        pass
    finally:
        clients.pop(c.id, None)
        if c.hello:
            broadcast({'t': 'leave', 'id': c.id}); broadcast({'t': 'system', 'text': f'{c.name} salió.'})
        try: writer.close()
        except Exception: pass

def public_base(headers):
    env = os.environ.get('PUBLIC_URL', '').strip().rstrip('/')
    if env:
        return env
    proto = headers.get('x-forwarded-proto', 'http')
    host = headers.get('x-forwarded-host') or headers.get('host') or '127.0.0.1'
    return f'{proto}://{host}'


def secure_cookie(headers):
    return headers.get('x-forwarded-proto') == 'https' or bool(os.environ.get('RENDER'))


def settle_wallet(user, link_name, link_token):
    if link_token and link_name:
        owned = bind_wallet(link_name, link_token)
        if owned:
            ACC.link_wallet(user, link_name, owned)
            return
    if not user.get('wallet_token'):
        token = bind_wallet(user.get('wallet_name') or user['name'], user.get('wallet_token') or '')
        if token:
            ACC.link_wallet(user, user.get('wallet_name') or user['name'], token)


def auth_response(status, body, headers, extra_headers=()):
    raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
    lines = [f'HTTP/1.1 {status}\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(raw)}\r\n']
    for item in extra_headers:
        lines.append(item + '\r\n')
    lines.append('Connection: close\r\n\r\n')
    return ''.join(lines).encode() + raw


def redirect(location, headers, cookies):
    raw = b''
    parts = [f'HTTP/1.1 302 Found\r\nLocation: {location}\r\nContent-Length: 0\r\n']
    for item in cookies:
        parts.append('Set-Cookie: ' + item + '\r\n')
    parts.append('Connection: close\r\n\r\n')
    return ''.join(parts).encode()


def juego_vuelta(raw):
    """Sólo /play/ o el modo móvil. Evita una redirección abierta."""
    text = urllib.parse.unquote(raw or '').strip()
    if text in ('/play/?movil=1', '/movil', '/movil/', '/movil/index.html'):
        return '/play/?movil=1'
    return '/play/'


def vuelta_pedida(query, cookie):
    asked = (query.get('vuelta') or [''])[0]
    if not asked:
        asked = ACC.read_cookie(cookie, 'life_return')
    return juego_vuelta(asked)


async def try_auth(method, path, target, headers, body, remote_ip=None):
    if not path.startswith('/auth'):
        return None
    query = urllib.parse.parse_qs(urllib.parse.urlparse(target).query)
    secure = secure_cookie(headers)
    base = public_base(headers)
    cookie = headers.get('cookie', '')
    try:
        payload = json.loads(body.decode() or '{}') if body else {}
    except Exception:
        payload = {}
    if path == '/auth/providers' and method == 'GET':
        return auth_response('200 OK', ACC.providers(), headers)
    if path == '/auth/sesion' and method == 'GET':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        return auth_response('200 OK', {'user': ACC.public_user(user) if user else None}, headers)
    if path == '/auth/google' and method == 'GET':
        if not ACC.providers()['google']:
            return auth_response('404 Not Found', {'error': 'Google no está configurado.'}, headers)
        state = ACC.start_oauth(ACCOUNTS, 'google')
        save_accounts()
        back = vuelta_pedida(query, cookie)
        loc = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
            'client_id': os.environ['GOOGLE_CLIENT_ID'], 'redirect_uri': base + '/auth/google/callback',
            'response_type': 'code', 'scope': 'openid email profile', 'state': state,
        })
        return redirect(loc, headers, [ACC.cookie('oauth_state', state, 600, secure), ACC.cookie('life_return', urllib.parse.quote(back, safe=''), 600, secure)])
    if path == '/auth/facebook' and method == 'GET':
        if not ACC.providers()['facebook']:
            return auth_response('404 Not Found', {'error': 'Facebook no está configurado.'}, headers)
        state = ACC.start_oauth(ACCOUNTS, 'facebook')
        save_accounts()
        back = vuelta_pedida(query, cookie)
        loc = 'https://www.facebook.com/v19.0/dialog/oauth?' + urllib.parse.urlencode({
            'client_id': os.environ['FACEBOOK_APP_ID'], 'redirect_uri': base + '/auth/facebook/callback',
            'state': state, 'scope': 'email',
        })
        return redirect(loc, headers, [ACC.cookie('oauth_state', state, 600, secure), ACC.cookie('life_return', urllib.parse.quote(back, safe=''), 600, secure)])
    if path in ('/auth/google/callback', '/auth/facebook/callback') and method == 'GET':
        provider = 'google' if 'google' in path else 'facebook'
        state = (query.get('state') or [''])[0]
        code = (query.get('code') or [''])[0]
        back = vuelta_pedida(query, cookie)
        fallo = '/play/?movil=1&auth=error' if back.endswith('movil=1') else '/play/?auth=error'
        try:
            profile = ACC.exchange_google(code, base + '/auth/google/callback') if provider == 'google' else ACC.exchange_facebook(code, base + '/auth/facebook/callback')
            result = ACC.finish_oauth(ACCOUNTS, provider, state, ACC.read_cookie(cookie, 'oauth_state'), profile)
            user = next(u for u in ACCOUNTS['users'] if u['id'] == result['user']['id'])
            link = urllib.parse.unquote(ACC.read_cookie(cookie, 'life_link'))
            link_name, _, link_token = link.partition('|')
            settle_wallet(user, link_name, link_token)
            save_accounts()
            maybe_fuse()
        except (ACC.AuthError, urllib.error.URLError, TimeoutError, OSError):
            return redirect(fallo, headers, [ACC.cookie('life_return', '', 0, secure)])
        return redirect(back, headers, [ACC.cookie('life_session', result['token'], result['max_age'], secure), ACC.cookie('oauth_state', '', 0, secure), ACC.cookie('life_return', '', 0, secure)])
    if path == '/auth/entrar' and method == 'POST':
        try:
            result = ACC.login_password(ACCOUNTS, payload.get('email'), payload.get('password'), client_ip=remote_ip)
            save_accounts()
        except ACC.AuthError as exc:
            save_accounts()
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True, 'user': result['user']}, headers,
                             ['Set-Cookie: ' + ACC.cookie('life_session', result['token'], result['max_age'], secure)])
    if path == '/auth/registro' and method == 'POST':
        try:
            ACC.begin_signup(ACCOUNTS, payload.get('name'), payload.get('email'), payload.get('phone'), payload.get('password') or '', ACC.send_email, ACC.start_sms)
            save_accounts()
        except ACC.AuthError as exc:
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True}, headers)
    if path == '/auth/verificar' and method == 'POST':
        try:
            result = ACC.verify_signup(ACCOUNTS, payload.get('email'), payload.get('email_code'), payload.get('phone_code'), ACC.check_sms)
            user = next(u for u in ACCOUNTS['users'] if u['id'] == result['user']['id'])
            settle_wallet(user, payload.get('name') or user['name'], payload.get('walletToken') or '')
            save_accounts()
            maybe_fuse()
        except ACC.AuthError as exc:
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True, 'user': ACC.public_user(user)}, headers, [ 'Set-Cookie: ' + ACC.cookie('life_session', result['token'], result['max_age'], secure)])
    if path == '/auth/salir' and method == 'POST':
        token = ACC.read_cookie(cookie, 'life_session')
        ACCOUNTS['sessions'].pop(token, None)
        save_accounts()
        return auth_response('200 OK', {'ok': True}, headers, ['Set-Cookie: ' + ACC.cookie('life_session', '', 0, secure)])
    return auth_response('404 Not Found', {'error': 'no existe'}, headers)


def legal_page(path):
    """Páginas públicas, sin sesión: /privacidad y /terminos."""
    rel = LEGAL_PAGES.get('/' + path.strip('/'))
    if not rel:
        return None
    full = os.path.join(ROOT, rel)
    if not os.path.isfile(full):
        return None
    with open(full, 'rb') as handle:
        return handle.read()


# ---------------- HTTP estático ----------------
async def handle(reader, writer):
    try:
        req = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 15)
    except Exception:
        writer.close(); return
    lines = req.decode('latin-1').split('\r\n')
    try: method, target, _ = lines[0].split(' ', 2)
    except ValueError: writer.close(); return
    headers = {k.strip().lower(): v.strip() for k, _, v in (l.partition(':') for l in lines[1:] if l)}
    path = urllib.parse.unquote(urllib.parse.urlparse(target).path)
    body = b''
    if method == 'POST' and path.startswith('/auth'):
        try:
            length = min(int(headers.get('content-length') or 0), 20000)
        except ValueError:
            length = 0
        if length:
            body = await reader.readexactly(length)
    answered = await try_auth(method, path, target, headers, body, client_ip(headers, writer))
    if answered is not None:
        writer.write(answered)
        await writer.drain(); writer.close(); return
    if path == '/ws' and headers.get('upgrade', '').lower() == 'websocket':
        key = headers.get('sec-websocket-key', '')
        acc = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        writer.write(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                      f'Sec-WebSocket-Accept: {acc}\r\n\r\n').encode())
        await writer.drain()
        return await handle_ws(reader, writer, headers.get('cookie', ''), client_ip(headers, writer))
    if path == '/healthz' and method in ('GET', 'HEAD'):
        body = b'ok'
        writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: 2\r\nConnection: close\r\n\r\n')
        if method == 'GET': writer.write(body)
        await writer.drain(); writer.close(); return
    if path == '/session.json' and method in ('GET', 'HEAD'):
        body = json.dumps({'serverId': SERVER_ID, 'worldBuild': WORLD.get('build'),
                           'revision': os.environ.get('RENDER_GIT_COMMIT') or None,
                           'playersOnline': sum(c.hello and not c.bot for c in clients.values())}).encode()
        writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nCache-Control: no-store\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
        if method == 'GET': writer.write(body)
        await writer.drain(); writer.close(); return
    if path.startswith('/api/libro') and method in ('GET', 'HEAD'):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(target).query)
        status, payload = LIBRO.api_get(path, query, LIBRO_CHAIN)
        body = json.dumps(payload, ensure_ascii=False).encode()
        code = '200 OK' if status == 200 else '404 Not Found'
        writer.write(f'HTTP/1.1 {code}\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
        if method == 'GET':
            writer.write(body)
        await writer.drain(); writer.close(); return
    if path.startswith('/api/jugador') and method in ('GET', 'HEAD'):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(target).query)
        name = clean((query.get('nombre') or [''])[0], 16)
        token = headers.get('x-wallet-token', '')
        stored = (ECON.get('walletTokens') or {}).get(name)
        if not name or not token_matches(stored, token):
            body = '{"error":"solo el propio jugador"}'.encode()
            writer.write(f'HTTP/1.1 403 Forbidden\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
            if method == 'GET': writer.write(body)
            await writer.drain(); writer.close(); return
        box = PLAY.ensure(PLAYERS, name)
        body = json.dumps(PLAY.public(box), ensure_ascii=False).encode()
        writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
        if method == 'GET': writer.write(body)
        await writer.drain(); writer.close(); return
    if path.startswith('/api/nft') and method in ('GET', 'HEAD'):
        if path in ('/api/nft/pubkey', '/api/nft/pubkey/'):
            body = json.dumps({'pubkey': NFT_PUB.hex(), 'alg': 'Ed25519'}).encode()
        elif path in ('/api/nft/list', '/api/nft/list/'):
            body = json.dumps({'tokens': [NFT.public_token(t) for t in NFT_CHAIN.get('tokens') or []], 'pubkey': NFT_PUB.hex()}).encode()
        else:
            ident = path.rstrip('/').split('/')[-1]
            found = None
            for token in NFT_CHAIN.get('tokens') or []:
                if str(token.get('id')) == ident or token.get('code') == ident:
                    found = token
                    break
            if not found:
                body = b'{"error":"no existe"}'
                writer.write(f'HTTP/1.1 404 Not Found\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
                if method == 'GET': writer.write(body)
                await writer.drain(); writer.close(); return
            body = json.dumps(NFT.metadata(found), ensure_ascii=False).encode()
        writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
        if method == 'GET': writer.write(body)
        await writer.drain(); writer.close(); return
    if method in ('GET', 'HEAD'):
        page = legal_page(path)
        if page is not None:
            writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nCache-Control: no-cache\r\nContent-Length: {len(page)}\r\nConnection: close\r\n\r\n'.encode())
            if method == 'GET': writer.write(page)
            await writer.drain(); writer.close(); return
    if path in ('/', ''):
        writer.write(b'HTTP/1.1 302 Found\r\nLocation: /play/\r\nContent-Length: 0\r\n\r\n'); await writer.drain(); writer.close(); return
    if path.endswith('/'): path += 'index.html'
    full = os.path.realpath(os.path.join(ROOT, path.lstrip('/')))
    ok = full.startswith(ROOT + os.sep) and os.path.isfile(full) and not any(path.startswith(b) for b in BLOCKED) and method in ('GET', 'HEAD')
    if not ok:
        body = b'404'; writer.write(b'HTTP/1.1 404 Not Found\r\nContent-Length: 3\r\nConnection: close\r\n\r\n' + body)
    else:
        with open(full, 'rb') as f: body = f.read()
        ctype = mimetypes.guess_type(full)[0] or 'application/octet-stream'
        if ctype.startswith('text/') or ctype in ('application/javascript', 'application/json'): ctype += '; charset=utf-8'
        writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: {ctype}\r\nContent-Length: {len(body)}\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n'.encode())
        if method == 'GET': writer.write(body)
    try:
        await writer.drain(); writer.close()
    except Exception: pass

# ---------------- aldeanos de demostración (bots) ----------------
BOT_LINES = [
    ('proximidad', '¿Alguien para lavar oro en el río? Llevo batea.'),
    ('proximidad', 'Los mangos del sur ya están maduros.'),
    ('global', '¿Quién tiene semillas de coco? Cambio por trucha.'),
    ('proximidad', 'Cuidado con el venado, corre rápido.'),
    ('global', 'Voy a la cantera por plata, ¿vienen?'),
    ('proximidad', 'El capataz da tareas en la plaza.'),
    ('clan', 'Reunión del clan junto a la fuente.'),
]
def walkable(x, y): return 0 <= x < WORLD['width'] and 0 <= y < WORLD['height'] and COLL[y][x] == 0
async def bots_loop(n):
    names = [('Brisa', 'verde'), ('Tomás', 'rojo'), ('Nelo', 'amarillo'), ('Luz', 'morado')][:n]
    bots = []
    for nm, col in names:
        b = Client(None, bot=True); b.name = nm + ' (bot)'; b.color = col; b.hello = True; b.level = random.randint(3, 12)
        b.x, b.y = float(PLAZA_C[0] + random.randint(-4, 4)), float(PLAZA_C[1] + random.randint(-2, 3))
        while not walkable(int(b.x), int(b.y)): b.x, b.y = float(PLAZA_C[0] + random.randint(-4, 4)), float(PLAZA_C[1] + random.randint(-2, 3))
        clients[b.id] = b; bots.append(b)
    while True:
        await asyncio.sleep(1.2)
        for b in bots:
            if random.random() < 0.45:
                dx, dy = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
                nx, ny = int(b.x) + dx, int(b.y) + dy
                if walkable(nx, ny) and abs(nx - PLAZA_C[0]) <= 6 and abs(ny - PLAZA_C[1]) <= 6:
                    b.x, b.y = float(nx), float(ny); b.dir = {(1,0):'right',(-1,0):'left',(0,1):'down',(0,-1):'up'}[(dx, dy)]
                    broadcast({'t': 'move', 'id': b.id, 'x': b.x, 'y': b.y, 'dir': b.dir, 'moving': True, 'level': b.level})
            if random.random() < 0.012:
                ch, line = random.choice(BOT_LINES); chat(b, ch, line)

async def main():
    ap = argparse.ArgumentParser(description='Servidor local LIFE INC · El Jardín')
    ap.add_argument('--port', type=int, default=None, help='puerto; si se omite, usa la variable PORT o 8765')
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--sin-bots', action='store_true', help='no crear aldeanos de demostración')
    ap.add_argument('--bots', type=int, default=3)
    a = ap.parse_args()
    if a.port is None:
        raw = os.environ.get('PORT', '').strip()
        try:
            a.port = int(raw) if raw else 8765
        except ValueError:
            raise SystemExit(f'PORT no es un entero válido: {raw}')
    hosts = [a.host]
    # Chrome resuelve localhost a ::1 primero; si sólo escuchamos IPv4, la pestaña da ERR_CONNECTION_REFUSED.
    if a.host in ('0.0.0.0', '127.0.0.1', ''):
        hosts.append('::1')
    servers = []
    for host in hosts:
        try:
            servers.append(await asyncio.start_server(handle, host, a.port))
        except OSError as e:
            print(f'(aviso) no se pudo escuchar en [{host}]:{a.port}: {e}')
    if not servers:
        raise SystemExit(f'No se pudo abrir el puerto {a.port}')
    print(f'LIFE INC · El Jardín  →  http://localhost:{a.port}/play/   (también http://127.0.0.1:{a.port}/play/)')
    print(f'chat WebSocket: ws://<host>:{a.port}/ws')
    print('Ctrl+C para detener.')
    if not a.sin_bots and a.bots > 0: asyncio.create_task(bots_loop(min(4, a.bots)))
    async def ledger_loop():
        while True:
            await asyncio.sleep(5)
            if ECO.seal_if_due(ECON):
                save_econ()
                broadcast(econ_msg())
    asyncio.create_task(ledger_loop())
    async def _serve(srv):
        async with srv:
            await srv.serve_forever()
    await asyncio.gather(*(_serve(srv) for srv in servers))

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: print('\nServidor detenido.')
