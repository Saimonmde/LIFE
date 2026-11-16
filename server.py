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
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server'))
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
import apartment_api as APARTMENT_API
import simon_api as SIMON_API
import reloj as RELOJ
import cobre as COBRE
import monedas as MONEDAS
import lingotes as LINGOTES
import finca as FINCA
import persist as PERSIST
import purses as PURSES
import mochila as MOCHILA
import trades as TRADE
import cambio_simple as CAMBIO
import bridge4sur
import mundos as MUNDOS
import social as SOCIAL
import seguir as SEGUIR
import topes as TOPES
import crudo as CRUDO
import vida_api as VIDA_API
import hogar as HOGAR
import casa_cuenta as CASA
import caballo_cuenta as CABALLO
import gallos as GALLOS
import guardado as GUARDADO
import partida as PARTIDA
import world_edits as EDITS

ROOT = os.path.dirname(os.path.abspath(__file__))
GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
BLOCKED = ('/references', '/tools', '/server.py', '/state', '/.git', '/.env', '/tests')
LEGAL_PAGES = {
    '/privacidad': 'legal/privacidad.html',
    '/terminos': 'legal/terminos.html',
}
PROX_TILES = 15           # 30 m con 2 m por casilla
MAX_TEXT = 160
CHANNELS = ('global', 'proximidad', 'clan', 'grupo', 'lugar')
SERVER_ID = uuid.uuid4().hex[:12]

with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as f:
    WORLD = json.load(f)
bridge4sur.install(WORLD)
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
VIDA_PATH = os.path.join(ROOT, 'state', 'vida.json')
VIDA = SOCIAL.normalize(PERSIST.load_named('vida', VIDA_PATH))
FINCA_PATH = os.path.join(ROOT, 'state', 'finca.json')
FINCA_CONFIG = FINCA.load_config()
FINCA_STATE = FINCA.load(FINCA_PATH)
PLACES = MUNDOS.boxes(WORLD)
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

if RELOJ.anchor(ECON)[1]:
    save_econ()

def save_nft():
    NFT.save_chain(NFT_PATH, NFT_CHAIN)

def save_vault():
    VAULT.save(VAULT_PATH, VAULT_STATE)

if ECO.migrate_vault_smc(ECON, VAULT_STATE, log=print):
    save_econ()
    save_vault()

def save_play():
    PLAY.save(PLAY_PATH, PLAYERS)

def save_vida():
    PERSIST.save_named('vida', VIDA_PATH, VIDA)

def save_finca():
    FINCA.save(FINCA_PATH, FINCA_STATE)

def save_accounts():
    ACC.save(ACCOUNTS_PATH, ACCOUNTS)

WORLD_EDITS_PATH = os.path.join(ROOT, 'state', EDITS.storage_filename())
WORLD_EDITS = EDITS.normalize(PERSIST.load_named(EDITS.storage_name(), WORLD_EDITS_PATH), env=EDITS.env_name())

def save_world_edits():
    PERSIST.save_named(EDITS.storage_name(), WORLD_EDITS_PATH, WORLD_EDITS)

def world_edit_packet(user):
    return EDITS.packet(WORLD_EDITS, user, role_of=SOCIAL.role_of)

def world_edit_request(user, message, save=True, announce=True):
    """Escribe la capa de ediciones. Un no-admin recibe code 403 y no cambia nada."""
    global WORLD_EDITS
    result = EDITS.apply_request(WORLD_EDITS, user, message, role_of=SOCIAL.role_of)
    if result.get('ok') and result.get('changed'):
        WORLD_EDITS = result['stored']
        if save:
            save_world_edits()
        if announce:
            broadcast({'t': 'world_edits', 'worldEdits': EDITS.packet(WORLD_EDITS)})
    return result

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
        print('[fusion] pendiente hasta que entre ' + FUSION.owner_email(), flush=True)
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
    view['copperDailySmc'] = SUP.COPPER_DAILY_SMC
    rivers_rest = bool(GOLD_NODES) and all(time.time() < NODE_READY.get(n.get('id'), 0) for n in GOLD_NODES)
    gold_done = bool(profile and profile.get('account') and int(view.get('remainingSubs') or 0) <= 0)
    view['copperOpen'] = rivers_rest or gold_done
    view['copperNote'] = SUP.COPPER_NOTE if view['copperOpen'] else ''
    m['supply'] = view
    plata_profile = dict(profile or {})
    if who and not locked:
        plata_profile['name'] = who
    pview = PLATA.public_view(ECON, plata_profile)
    pview['balanceSph'] = 0 if locked or not who else PLATA.balance_of(ECON, who)
    m['plata'] = pview
    m['balanceSph'] = pview['balanceSph']
    m['reloj'] = RELOJ.payload(ECON)
    m['walletName'] = '' if locked else (who or '')
    m['ledger'] = MONEDAS.ledger(ECON, name=None if locked else who, account=(profile or {}).get('account'))
    m['cupos'] = cupos_public(profile)
    if who and not locked:
        import acunar_credito as ACU
        m['purse'] = ACU.vista(VAULT_STATE, ECON, who, (profile or {}).get('account'))
    else:
        m['purse'] = {'items': {}, 'catalog': dict(PURSES.CATALOG), 'monedas': {}}
    m['puestoSmh'] = int((ECON.get('wallets') or {}).get('puesto_frutas') or 0)
    return m

def token_matches(stored, presented):
    if not stored or not presented or len(stored) != len(str(presented)):
        return False
    return secrets.compare_digest(stored, str(presented))

def _sumar_clave(box, old, new):
    """Pasa un saldo de un nombre a otro. La suma no cambia."""
    if not isinstance(box, dict) or old not in box:
        return False
    box[new] = int(box.get(new) or 0) + int(box.pop(old) or 0)
    return True


def mover_billetera(old, new):
    """El apodo nuevo se queda con las monedas del nombre anterior.

    Si el nombre nuevo ya tenía saldo, se suma. No se acuña ni se pierde.
    """
    old, new = str(old or ''), str(new or '')
    if not old or not new or old == new:
        return
    wallets = ECON.setdefault('wallets', {})
    tokens = ECON.setdefault('walletTokens', {})
    moved = _sumar_clave(wallets, old, new)
    if old in tokens and new not in tokens:
        tokens[new] = tokens.pop(old)
        moved = True
    elif old in tokens:
        tokens.pop(old, None)
    plata = ECON.get('plata') if isinstance(ECON.get('plata'), dict) else None
    if plata:
        moved = _sumar_clave(plata.get('wallets'), old, new) or moved
    chis = ECON.get('simonchis') if isinstance(ECON.get('simonchis'), dict) else None
    if chis:
        moved = _sumar_clave(chis.get('wallets'), old, new) or moved
    purses = VAULT_STATE.setdefault('purses', {})
    if old in purses:
        dest = purses.setdefault(new, {})
        for item, qty in (purses.pop(old) or {}).items():
            dest[item] = int(dest.get(item) or 0) + int(qty or 0)
        moved = True
    if moved:
        save_econ()
        save_vault()


def bind_wallet(name, presented, owner=False):
    """Crea la billetera o reconoce a quien guarda el token. No revela el secreto ajeno.

    Quien ya entró con su cuenta es el dueño de ese nombre: la cookie basta.
    Un invitado sin token no puede acuñar con el nombre de otro.
    """
    wallets = ECON.setdefault('wallets', {})
    tokens = ECON.setdefault('walletTokens', {})
    if name not in wallets:
        wallets[name] = 0
    if name not in tokens:
        token = secrets.token_hex(16)
        tokens[name] = token
        save_econ()
        return token
    if token_matches(tokens[name], presented) or owner:
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
    broadcast({'t': 'system', 'text': f'{visible_nick(sender)} pagó {ECO.format_pair(smh)} a {nick_de(hit)}. Sólo es una simulación, sin valor real.'})

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
    seconds = None
    if code == 'cooldown':
        profile = account_profile(sender)
        acc = ((ECON.get('supply') or {}).get('accounts') or {}).get(profile.get('account') or '') or {}
        last = int(acc.get('lastClaim') or 0)
        seconds = max(0, SUP.CLAIM_COOLDOWN - (int(time.time()) - last))
    text = SUP.reason_text(code, seconds)
    try:
        view = SUP.public_view(ECON, account_profile(sender))
    except Exception:
        view = {}
    name = getattr(sender, 'name', '') or ''
    if isinstance(view, dict):
        view['owedSubs'] = int((ECON.get('questOwed') or {}).get(name) or 0)
    send(sender, {'t': 'pow_result', 'ok': False, 'reason': text, 'code': code, 'supply': view})
    if channel == 'acunar':
        send(sender, {'t': 'acunar_result', 'ok': False, 'reason': text, 'code': code, 'supply': view})
    elif channel == 'smelt':
        send(sender, {'t': 'smelt_result', 'ok': False, 'needPow': False, 'reason': text, 'code': code, 'supply': view})
    else:
        send(sender, {'t': 'system', 'text': text})
    return {'ok': False, 'reason': code, 'smh': 0}

def take_proof(sender, action, context, proof, resume, want_smh=None, exact=False, counts_as_mint=True, room_smh=None, pay_request=False, kind='gold'):
    if getattr(sender, 'bot', False):
        return fail_claim(sender, 'guest', channel='acunar' if action == 'acunar' else ('smelt' if action == 'fundicion' else 'system'))
    if not getattr(sender, 'wallet_ok', False):
        text = SUP.reason_text('wallet')
        if action == 'acunar':
            send(sender, {'t': 'acunar_result', 'ok': False, 'reason': text, 'code': 'wallet'})
        else:
            send(sender, {'t': 'system', 'text': text})
        return {'ok': False, 'reason': 'wallet', 'smh': 0}
    profile = account_profile(sender)
    if proof:
        result = SUP.redeem(
            ECON, profile, action, context, proof,
            want_smh=want_smh, room_smh=room_smh, exact=exact, counts_as_mint=counts_as_mint,
            pay_request=pay_request, kind=kind,
        )
        save_econ()
        if not result.get('ok'):
            return fail_claim(sender, result.get('reason') or 'signature', channel='acunar' if action == 'acunar' else ('smelt' if action == 'fundicion' else 'system'))
        return result
    opened = SUP.open_challenge(ECON, profile, action, context)
    save_econ()
    if not opened.get('ok'):
        return fail_claim(sender, opened.get('reason') or 'guest', channel='acunar' if action == 'acunar' else ('smelt' if action == 'fundicion' else 'system'))
    sender.pow_challenge = opened['challenge']
    view = opened.get('view') or {}
    view['owedSubs'] = int((ECON.get('questOwed') or {}).get(getattr(sender, 'name', '') or '') or 0)
    send(sender, {'t': 'pow_challenge', 'challenge': opened['challenge'], 'resume': resume, 'supply': view})
    if action == 'fundicion':
        send(sender, {'t': 'smelt_result', 'ok': False, 'needPow': True, 'reason': 'Calculando la prueba de trabajo. El mineral sigue en la mochila.', 'supply': view})
    if action == 'acunar':
        send(sender, {'t': 'acunar_result', 'ok': False, 'pending': True, 'reason': 'Calculando prueba…', 'supply': view})
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

def oro_agotado(sender=None):
    """El río no da más oro: el cupo de oro de hoy se acabó, o todas las vetas están en descanso."""
    profile = account_profile(sender) if sender is not None else {}
    try:
        view = SUP.public_view(ECON, profile)
    except Exception:
        view = {}
    if int(view.get('remainingSubs') or 0) <= 0 and profile.get('account'):
        return True
    if GOLD_NODES and all(time.time() < NODE_READY.get(n.get('id'), 0) for n in GOLD_NODES):
        return True
    return False


def nota_cobre(sender=None):
    if not oro_agotado(sender):
        return ''
    return SUP.COPPER_NOTE


def mint_cobre_for(sender, proof=None):
    """El cobre paga SMC sólo cuando el oro del río ya no da. El tope es COPPER_DAILY_SMC."""
    if getattr(sender, 'zone', '') != 'mine':
        return send(sender, {'t': 'system', 'text': 'El cobre se pica en la mina. El oro sigue saliendo sólo del río.'})
    if not oro_agotado(sender):
        return send(sender, {'t': 'system', 'text': 'El oro del río todavía da SMC. El cobre paga SMC cuando ese oro se agota.'})
    if not getattr(sender, 'wallet_ok', False):
        return send(sender, {'t': 'system', 'text': 'Esta billetera se creó en otro aparato. Puedes picar, pero no recibir SMC.'})
    result = take_proof(
        sender, 'mint_cobre', 'cobre', proof, {'t': 'mint_cobre'},
        want_smh=SUP.copper_daily_smh(), kind='copper',
    )
    if not result.get('ok'):
        return
    granted, _token, _pub = emitir(
        sender, result['smh'], 'Emisión por cobre cuando el oro del río no da más', 'mint',
        'mina', 'cobre', 'Mina de cobre',
    )
    if granted <= 0:
        return send(sender, {'t': 'system', 'text': 'Se alcanzó el tope minable de SMC.'})
    send(sender, {'t': 'system', 'text': f'Se acuñaron {ECO.format_pair(granted)} con cobre. {SUP.COPPER_NOTE}'})
    send(sender, {'t': 'issued', 'amountSmh': int(getattr(sender, 'kept_smh', granted) or 0), 'mintedSmh': granted, 'kind': 'mint_cobre', 'amountText': ECO.format_pair(int(getattr(sender, 'kept_smh', granted) or 0)), 'supply': result.get('view')})


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


def cambio_simple_msg(sender, message):
    """Mueve metal por SMC del puesto, o plata por oro del fondo. No acuña."""
    give = str((message or {}).get('give') or '')
    receive = str((message or {}).get('receive') or '')
    try:
        qty = int((message or {}).get('qty') or 0)
    except (TypeError, ValueError):
        qty = 0
    if give == 'simonplata' and receive == 'simoncoin':
        have = PLATA.balance_of(ECON, sender.name)
        fondo = int((ECON.get('plata') or {}).get('smcPoolSmh') or 0)
        quoted = CAMBIO.quote('simonplata', 'simoncoin', qty, have, fondo_smh=fondo)
        if not quoted.get('ok'):
            return send(sender, {'t': 'cambio_result', 'ok': False, 'reason': quoted.get('texto') or 'No se movió nada.'})
        result = exchange_plata(sender, f"{quoted['das']} smp")
        ok = bool(isinstance(result, dict) and result.get('ok'))
        return send(sender, {'t': 'cambio_result', 'ok': ok, 'give': give, 'das': quoted['das'] if ok else 0, 'recibes': quoted['recibes'] if ok else 0, 'reason': quoted['texto'] if ok else 'No se movió nada.'})
    if give not in CAMBIO.MINERALES or receive != 'simoncoin':
        return send(sender, {'t': 'cambio_result', 'ok': False, 'reason': 'Eso crearía monedas o metal nuevo. No se movió nada.'})
    have = PURSES.count(VAULT_STATE, sender.name, give)
    puesto = int((ECON.get('wallets') or {}).get('puesto_frutas') or 0)
    quoted = CAMBIO.quote(give, 'simoncoin', qty, have, puesto_smh=puesto)
    if not quoted.get('ok'):
        return send(sender, {'t': 'cambio_result', 'ok': False, 'reason': quoted.get('texto') or 'No se movió nada.'})
    if not PURSES.debit(VAULT_STATE, sender.name, give, quoted['das']):
        return send(sender, {'t': 'cambio_result', 'ok': False, 'reason': 'Ese metal no está en la cuenta. No se movió nada.'})
    try:
        CAMBIO.mover_mineral(ECON, sender.name, quoted['das'])
    except ValueError as exc:
        PURSES.credit(VAULT_STATE, sender.name, give, quoted['das'])
        return send(sender, {'t': 'cambio_result', 'ok': False, 'reason': str(exc)})
    ECO.append_tx(ECON, {
        'type': 'trade', 'from': 'puesto_frutas', 'to': sender.name,
        'amountSubs': quoted['das'] * CAMBIO.MINERAL_SMH, 'note': 'Cambio de metal por Simoncoin ya existente',
    })
    save_econ()
    save_vault()
    broadcast_econ()
    send(sender, {'t': 'cambio_result', 'ok': True, 'give': give, 'das': quoted['das'], 'recibes': quoted['recibes'], 'reason': quoted['texto'], 'purse': PURSES.public(VAULT_STATE, sender.name)})


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

COIN_QTY = {'mineral_cobre': 4, 'mineral_plata': 3, 'mineral_oro': 2, 'pepita_oro': 2}
METAL = {'mineral_cobre': 'cobre', 'mineral_plata': 'plata', 'mineral_oro': 'oro', 'pepita_oro': 'oro'}

def _lotes(batches):
    try:
        batches = int(batches)
    except (TypeError, ValueError):
        return 0
    if batches < 1 or batches > 30:
        return 0
    return batches

def _en_la_mina(sender):
    if getattr(sender, 'zone', 'city') != 'mine':
        return False
    sender.activity_tiles = max(int(getattr(sender, 'activity_tiles', 0) or 0), 8)
    sender.last_activity_at = time.time()
    return True

def _smelt_fail(sender, reason):
    send(sender, {'t': 'smelt_result', 'ok': False, 'reason': reason, 'ledger': MONEDAS.ledger(ECON, sender.name, (account_profile(sender) or {}).get('account'))})

def _dia(account, box):
    epoch = int(time.time()) // TOPES.DAY
    acc = (box or {}).get(account or '') or {}
    if int(acc.get('epoch') or -1) != epoch:
        return 0
    return int(acc.get('earned') or 0)

def cupos_public(profile=None):
    profile = profile or {}
    age, play, quests = profile.get('age') or 0, profile.get('play') or 0, profile.get('quests') or 0
    account = profile.get('account') or ''
    oro_cap = TOPES.simoncoin_daily_smh(age, play, quests) / ECO.SUBS
    oro_earned = _dia(account, (ECON.get('supply') or {}).get('accounts')) / ECO.SUBS
    plata_cap = TOPES.simonplata_daily_sph(age, play, quests) / ECO.SUBS
    plata_earned = _dia(account, (ECON.get('plata') or {}).get('accounts')) / ECO.SUBS
    chis_cap = TOPES.simonchis_daily()
    key = f'{account}:{int(time.time()) // TOPES.DAY}'
    chis_earned = int(((ECON.get('simonchis') or {}).get('earnedDay') or {}).get(key) or 0)
    coins = {}
    for coin, cap, earned, room in (
        ('simoncoin', max(oro_cap, SUP.loose_daily_smc()), oro_earned, ECO.issuance_room(ECON) / ECO.SUBS),
        ('simonplata', plata_cap, plata_earned, PLATA.issuance_room(ECON) / ECO.SUBS),
        ('simonchis', chis_cap, chis_earned, COBRE.room(ECON)),
    ):
        spec = TOPES.metal(coin)
        coins[coin] = {
            'name': spec['name'], 'metal': spec['metal'], 'item': spec['item'],
            'items': list(spec.get('items') or (spec['item'],)), 'rate': spec['rate'],
            'cap': cap, 'left': max(0, cap - earned), 'room': room,
        }
    return {'reset': TOPES.RESET_LABEL, 'coins': coins}

def _reglas_mina(headers):
    now = time.time()
    user = ACC.session_user(ACCOUNTS, ACC.read_cookie(headers.get('cookie', ''), 'life_session')) or {}
    name = str(user.get('wallet_name') or user.get('name') or '')
    age = play = quests = 0
    if user:
        age = max(0, int(now - int(user.get('createdAt') or now)))
        if name:
            box = PLAY.ensure(PLAYERS, name, now=int(now)) or {}
            play = int(box.get('playtime') or 0)
            quests = SUP.quest_count(ECON, name)
    payload = TOPES.letrero(age, play, quests, now)
    if user.get('id'):
        payload['hoy'] = TOPES.hoy(cupos_public({
            'account': user['id'], 'age': age, 'play': play, 'quests': quests,
        })['coins'])
    return payload

def _acunar_fail(sender, reason, code=''):
    send(sender, {'t': 'acunar_result', 'ok': False, 'reason': reason, 'code': code})

def acunar_for(sender, coin, pieces, proof=None):
    coin = str(coin or '')
    if 'lingote' in coin or coin in ('ingot', 'ingots'):
        reason = 'Los lingotes no se acuñan en esta ventanilla.'
        LINGOTES.anotar_rechazo('acunar', SOCIAL.role_of(getattr(sender, 'user', None)), getattr(sender, 'zone', ''), reason)
        return _acunar_fail(sender, reason, 'coin')
    spec = TOPES.metal(coin)
    if not spec:
        return _acunar_fail(sender, 'Esa moneda no se acuña aquí.', 'coin')
    if not _en_la_mina(sender):
        return _acunar_fail(sender, 'Ve al horno de la mina.', 'zone')
    if not getattr(sender, 'wallet_ok', False):
        return _acunar_fail(sender, SUP.reason_text('wallet'), 'wallet')
    profile = account_profile(sender)
    if not profile.get('account'):
        return _acunar_fail(sender, SUP.reason_text('guest'), 'guest')
    try:
        pieces = float(pieces or 0)
    except (TypeError, ValueError):
        pieces = 0.0
    row = cupos_public(profile)['coins'].get(str(coin))
    if not row:
        return _acunar_fail(sender, 'Esa moneda no se acuña aquí.', 'coin')
    items = CRUDO.items_for(coin)
    stock = CRUDO.total(ECON, profile['account'], items)
    import acunar_credito as ACU
    falta = ACU.motivo(stock, row['rate'], row['left'], row['room'], row['metal'], row['name'])
    if falta:
        code = 'metal' if stock < row['rate'] else ('cap' if row['left'] <= 0 else 'supply')
        return _acunar_fail(sender, falta, code)
    quote = TOPES.cotizar(stock, row['rate'], row['left'], row['room'], min(pieces, stock) if pieces else None, whole=(coin == 'simonchis'))
    if quote['recibes'] <= 0:
        detail = ACU.explicar(stock, row['rate'], row['metal'], whole=(coin == 'simonchis'))
        code = 'metal' if stock < row['rate'] else ('cap' if row['left'] <= 0 else 'supply')
        return _acunar_fail(sender, detail or falta or 'Hoy no alcanza para acuñar más.', code)
    whole = coin == 'simonchis'
    if coin == 'simoncoin':
        want = int(round(quote['recibes'] * ECO.SUBS))
        result = take_proof(
            sender, 'acunar', f'{coin}:{pieces}', proof,
            {'t': 'acunar', 'coin': coin, 'pieces': pieces},
            want_smh=want, pay_request=True,
        )
        if not result or not result.get('ok'):
            return
        granted, _token, pub = emitir(
            sender, result['smh'], 'Acuñación de Simoncoin con oros crudos', 'fundicion',
            'fundidora', 'horno', 'Horno',
        )
        if granted <= 0:
            return _acunar_fail(sender, 'No se pudo anotar el registro único. No se creó Simoncoin.', 'registry')
        got = granted / ECO.SUBS
        sender.registro = pub
    elif coin == 'simonplata':
        want = int(round(quote['recibes'] * ECO.SUBS))
        if not proof:
            opened = PLATA.open_challenge(ECON, profile, 'acunar', f'{coin}:{pieces}')
            save_econ()
            if not opened.get('ok'):
                return _acunar_fail(sender, SUP.reason_text(opened.get('reason') or 'guest'), opened.get('reason') or 'guest')
            send(sender, {'t': 'pow_challenge', 'challenge': opened['challenge'], 'resume': {'t': 'acunar', 'coin': coin, 'pieces': pieces}, 'coin': 'SMP'})
            send(sender, {'t': 'acunar_result', 'ok': False, 'pending': True, 'reason': 'Calculando prueba…'})
            return
        result = PLATA.redeem(ECON, profile, 'acunar', f'{coin}:{pieces}', proof, want_sph=want, pay_request=True)
        save_econ()
        if not result.get('ok'):
            return _acunar_fail(sender, SUP.reason_text(result.get('reason') or 'signature'), result.get('reason') or 'signature')
        got = int(result.get('sph') or 0) / ECO.SUBS
        broadcast_econ()
    else:
        want = int(quote['recibes'])
        if not proof:
            opened = COBRE.open_challenge(ECON, profile.get('account'), f'{coin}:{pieces}')
            save_econ()
            if not opened.get('ok'):
                return _acunar_fail(sender, SUP.reason_text(opened.get('reason') or 'guest'), opened.get('reason') or 'guest')
            send(sender, {'t': 'pow_challenge', 'challenge': opened['challenge'], 'resume': {'t': 'acunar', 'coin': coin, 'pieces': pieces}, 'coin': 'Simonchis'})
            send(sender, {'t': 'acunar_result', 'ok': False, 'pending': True, 'reason': 'Calculando prueba…'})
            return
        result = COBRE.redeem(ECON, profile.get('account'), f'{coin}:{pieces}', proof, want, purse=sender.name)
        save_econ()
        if not result.get('ok'):
            return _acunar_fail(sender, SUP.reason_text(result.get('reason') or 'signature'), result.get('reason') or 'signature')
        got = int(result.get('qty') or 0)
        broadcast_econ()
    done = TOPES.cotizar(quote['gastas'], row['rate'], got, got, quote['gastas'], whole=whole)
    spent = CRUDO.debit(ECON, profile['account'], items, done['gastas'])
    if spent is None:
        return _acunar_fail(sender, 'No hay suficiente metal en la cuenta.', 'metal')
    moneda = ACU.acreditar_mochila(VAULT_STATE, sender.name, coin, got)
    if moneda:
        save_vault()
    if coin == 'simonchis':
        ECO.append_tx(ECON, {
            'type': 'fundicion', 'to': sender.name, 'coin': 'SMCH', 'qty': int(got),
            'amountSubs': 0, 'note': f'Acuñación de {int(got)} Simonchis',
        })
    view = MONEDAS.ledger(ECON, sender.name, profile.get('account'))
    view['historia'] = HISTORIA.filas(ECON)
    save_econ()
    broadcast_econ()
    recibido = done['recibes']
    if coin == 'simoncoin' and getattr(sender, 'kept_smh', None) is not None:
        recibido = sender.kept_smh / ECO.SUBS
    saldos = view.get('balances') or {}
    razon = (
        f'Se acuñó {recibido} {row["name"]}. '
        f'Saldo: {ECO.format_smc(saldos.get("simoncoin") or 0)}, '
        f'{PLATA.format_smp(saldos.get("simonplata") or 0)}, '
        f'{int(saldos.get("simonchis") or 0)} Simonchis. '
        f'Se gastaron {done["gastas"]} {row["metal"]}.'
    )
    registro = getattr(sender, 'registro', None) if coin == 'simoncoin' else None
    send(sender, {
        't': 'acunar_result', 'ok': True, 'coin': coin, 'name': row['name'],
        'item': row['item'], 'spent': done['gastas'], 'spentItems': spent, 'recibes': recibido,
        'balanceSubs': int(saldos.get('simoncoin') or 0),
        'balanceSph': int(saldos.get('simonplata') or 0),
        'registro': registro,
        'moneda': moneda, 'purse': ACU.vista(VAULT_STATE, ECON, sender.name, profile.get('account')),
        'walletName': sender.name,
        'reason': razon,
        'ledger': view, 'cupos': cupos_public(profile),
        'crudo': {item: CRUDO.nuggets(ECON, profile['account'], item) for item in CRUDO.CAPS},
    })

def fundir_lingotes(sender, ore, batches):
    reason = 'Los lingotes no se funden en el horno.'
    LINGOTES.anotar_rechazo('horno', SOCIAL.role_of(getattr(sender, 'user', None)), getattr(sender, 'zone', ''), reason)
    return _smelt_fail(sender, reason)

def zona_pedida(sender, zone):
    """El Banco Central no se abre con un mensaje. El papel se mira aquí."""
    zone = zone if zone in ('casa', 'mine', 'banco', 'central', 'city') else 'city'
    if zone != 'central' or LINGOTES.autorizado(getattr(sender, 'user', None)):
        return zone
    reason = 'El Banco Central es un recinto del personal. Esta cuenta no entra.'
    LINGOTES.anotar_rechazo('puerta', SOCIAL.role_of(getattr(sender, 'user', None)), getattr(sender, 'zone', ''), reason)
    send(sender, {'t': 'central_result', 'ok': False, 'reason': reason})
    send(sender, {'t': 'system', 'text': reason})
    return 'city'

def lingote_for(sender, metal, qty):
    reason = LINGOTES.rechazar(getattr(sender, 'user', None), getattr(sender, 'zone', ''))
    if reason:
        LINGOTES.anotar_rechazo('lingote', SOCIAL.role_of(getattr(sender, 'user', None)), getattr(sender, 'zone', ''), reason)
        return send(sender, {'t': 'lingote_result', 'ok': False, 'reason': reason})
    try:
        done = LINGOTES.fundir(ECON, sender.name, metal, qty, time.time(), autorizado=True)
    except (TypeError, ValueError, PermissionError):
        reason = 'Esa cantidad no se funde.'
        LINGOTES.anotar_rechazo('lingote', SOCIAL.role_of(getattr(sender, 'user', None)), getattr(sender, 'zone', ''), reason)
        return send(sender, {'t': 'lingote_result', 'ok': False, 'reason': reason})
    save_econ()
    view = MONEDAS.ledger(ECON, sender.name)
    send(sender, {'t': 'lingote_result', 'ok': True, 'reason': 'Quedó en la reserva del Banco Central.', 'ledger': view, **done})
    broadcast({'t': 'libro_publico', 'contadores': public_counters()})

def lingote_ver(sender):
    if not LINGOTES.autorizado(getattr(sender, 'user', None)):
        return send(sender, {'t': 'lingote_estado', 'ok': False, 'reason': 'Esta ventanilla no está abierta para esta cuenta.'})
    send(sender, {'t': 'lingote_estado', 'ok': True, **LINGOTES.vista(ECON)})

def fundir_simonchis(sender, ore, batches, proof):
    profile = account_profile(sender)
    if not profile.get('account'):
        return _smelt_fail(sender, 'Entra con una cuenta para acuñar Simonchis.')
    want = COIN_QTY.get(ore, 4) * batches
    context = f'{ore}:{batches}'
    if not proof:
        opened = COBRE.open_challenge(ECON, profile['account'], context)
        save_econ()
        if not opened.get('ok'):
            reason = 'Ya no se pueden crear más Simonchis. El tope es 333.000.000.' if opened.get('reason') == 'supply' else 'No se pudo empezar la acuñación.'
            return _smelt_fail(sender, reason)
        send(sender, {'t': 'pow_challenge', 'challenge': opened['challenge'], 'resume': {'t': 'smelt', 'ore': ore, 'batches': batches, 'mode': 'simonchis'}, 'coin': 'Simonchis'})
        send(sender, {'t': 'smelt_result', 'ok': False, 'needPow': True, 'mode': 'simonchis', 'reason': 'Calculando la prueba. El mineral sigue en la mochila.'})
        return
    result = COBRE.redeem(ECON, profile['account'], context, proof, want, purse=sender.name)
    save_econ()
    if not result.get('ok'):
        if result.get('reason') == 'supply':
            return _smelt_fail(sender, 'Ya no se pueden crear más Simonchis. El tope es 333.000.000.')
        if result.get('reason') == 'cap':
            return _smelt_fail(sender, 'Hoy ya acuñaste las Simonchis de este día.')
        return _smelt_fail(sender, 'La prueba no sirvió. No se acuñó nada.')
    qty = int(result['qty'])
    note = f'Se acuñaron {qty} Simonchis. No es dinero real.'
    view = MONEDAS.ledger(ECON, sender.name, profile['account'])
    broadcast_econ()
    send(sender, {'t': 'smelt_result', 'ok': True, 'mode': 'simonchis', 'ore': ore, 'batches': batches, 'qty': qty, 'coin': 'Simonchis', 'reason': note, 'ledger': view})
    send(sender, {'t': 'system', 'text': note})

def fundir_simonplata(sender, ore, batches, proof):
    """La plata del horno acuña Simonplata. El tope de 84.000.000 lo aplica el libro de plata."""
    result = mint_plata(sender, proof)
    if result and result.get('pending'):
        send(sender, {'t': 'smelt_result', 'ok': False, 'needPow': True, 'mode': 'simonplata', 'ore': ore, 'batches': batches, 'reason': 'Calculando la prueba de Simonplata. El mineral sigue en la mochila.'})
    elif result and result.get('ok'):
        send(sender, {'t': 'smelt_result', 'ok': True, 'mode': 'simonplata', 'ore': ore, 'batches': batches, 'reason': 'Entró Simonplata en tu saldo.', 'ledger': MONEDAS.ledger(ECON, sender.name, (account_profile(sender) or {}).get('account'))})

def smelt_for(sender, ore, batches, proof=None, mode=None):
    if str(mode or '') == 'ingot':
        return fundir_lingotes(sender, ore, batches)
    ore = str(ore or '')
    recipe = FOUNDRY.get(ore)
    if not recipe or not _en_la_mina(sender):
        return _smelt_fail(sender, 'Hay que fundir dentro de la mina.')
    batches = _lotes(batches)
    if not batches:
        return _smelt_fail(sender, 'La cantidad de lotes no es válida.')
    if not wallet_ready(sender):
        return _smelt_fail(sender, 'Esta billetera se creó en otro aparato.')
    mode = str(mode or 'simoncoin')
    if mode == 'simonchis':
        return fundir_simonchis(sender, ore, batches, proof)
    if mode == 'simonplata':
        return fundir_simonplata(sender, ore, batches, proof)
    context = f'{ore}:{batches}'
    result = take_proof(
        sender, 'fundicion', context, proof,
        {'t': 'smelt', 'ore': ore, 'batches': batches, 'mode': 'simoncoin'},
        room_smh=min(ECO.issuance_room(ECON), LIBRO.cupo_subs(LIBRO_CHAIN)),
    )
    if not result.get('ok'):
        return
    granted, token, libro_pub = emitir(
        sender, result['smh'], f'Acuñación de Simoncoin en la mina ({ore})', 'fundicion',
        'fundidora', 'horno_cantera', 'Fundidora de la cantera',
    )
    if granted <= 0:
        return _smelt_fail(sender, 'Ya no se puede crear más Simoncoin. El tope es 21.000.000.')
    kept = int(getattr(sender, 'kept_smh', granted) or 0)
    pooled = int(getattr(sender, 'pool_smh', 0) or 0)
    note = f'Se acuñó {ECO.format_smc(kept).replace(" SMC", " Simoncoin")}.'
    if pooled:
        note += ' Una parte quedó en el fondo de cambio.'
    view = MONEDAS.ledger(ECON, sender.name, (account_profile(sender) or {}).get('account'))
    send(sender, {'t': 'smelt_result', 'ok': True, 'mode': 'simoncoin', 'grantedSmh': kept, 'mintedSmh': granted, 'pooledSmh': pooled, 'amountText': ECO.format_smc(kept), 'ore': ore, 'batches': batches, 'certificate': token, 'libro': libro_pub, 'supply': result.get('view'), 'ledger': view, 'reason': note})
    send(sender, {'t': 'system', 'text': note + ' No es dinero real.'})

def _cuenta(sender):
    return str((getattr(sender, 'user', None) or {}).get('id') or '')

def _avisar_crudo(sender, item):
    account = _cuenta(sender)
    send(sender, {'t': 'crudo', 'item': item, 'total': CRUDO.nuggets(ECON, account, item),
                  'crudo': {key: CRUDO.nuggets(ECON, account, key) for key in CRUDO.CAPS}})

def swing_for(sender, mineral, qty=1):
    """Picar acredita mineral en la cuenta. No acuña ni toca el libro."""
    mineral = str(mineral or '')
    item = {'oro': 'mineral_oro', 'plata': 'mineral_plata', 'cobre': 'mineral_cobre'}.get(mineral)
    if not item or getattr(sender, 'zone', '') != 'mine':
        return
    now = time.time()
    if now - getattr(sender, 'last_swing', 0) < 1:
        return
    account = _cuenta(sender)
    if not account:
        return
    sender.last_swing = now
    note_motion(sender, 1)
    if not recibir(sender, item, qty, 'ore'):
        return
    send(sender, {'t': 'shift', 'swings': 0, 'need': SHIFT_SWINGS, 'paidSmh': 0, 'mintedSmh': 0, 'qty': int(qty or 1),
                  'note': 'El mineral quedó en tu cuenta. Las monedas se acuñan en el horno, con el tope del día.'})
    _avisar_crudo(sender, item)
    if mineral == 'cobre' and oro_agotado(sender):
        send(sender, {'t': 'system', 'text': SUP.COPPER_NOTE})
        mint_cobre_for(sender)

def lavar_for(sender, qty=1):
    """La batea acredita pepitas. Como mucho una por lavada."""
    if getattr(sender, 'zone', '') == 'mine':
        return
    now = time.time()
    if now - getattr(sender, 'last_pan', 0) < 1:
        return
    account = _cuenta(sender)
    if not account:
        return
    sender.last_pan = now
    note_motion(sender, 1)
    if not recibir(sender, 'pepita_oro', 1, 'lavar'):
        return
    send(sender, {'t': 'lavar_result', 'ok': True, 'qty': 1})
    _avisar_crudo(sender, 'pepita_oro')

SELL_SMH = {
    'mineral_oro': 1_000_000,
    'mineral_plata': 1_000_000,
    'mineral_cobre': 1_000_000,
    'pepita_oro': 1_000_000,
    'bolsa_cafe': 5_000_000,
    'bolsa_cacao': 5_000_000,
}


def recibir(sender, item, qty, kind):
    """Mete algo en la mochila del servidor. Si no cabe, no toca nada."""
    try:
        qty = int(qty or 0)
    except (TypeError, ValueError):
        qty = 0
    item = str(item or '')
    qty = max(0, min(qty, 4))
    if not sender.name or not item or qty <= 0:
        return False
    before = PURSES.count(VAULT_STATE, sender.name, item)
    after = PURSES.credit(VAULT_STATE, sender.name, item, qty)
    if after == before:
        sender.pending_pick = {'item': item, 'qty': qty, 'kind': str(kind or '')}
        send(sender, {'t': 'mochila_llena', 'item': item, 'qty': qty, 'reason': MOCHILA.FULL})
        return False
    sender.pending_pick = None
    if item in CRUDO.CAPS:
        account = _cuenta(sender)
        if account:
            CRUDO.credit(ECON, account, item, qty, cap=qty)
            save_econ()
    save_vault()
    return True


def mochila_op(sender, op):
    """Banco, soltar o vender lo que no cupo. No duplica y no lo tira sin querer."""
    pending = getattr(sender, 'pending_pick', None)
    if not pending:
        return send(sender, {'t': 'mochila_op', 'ok': False, 'reason': 'No hay nada esperando. No se perdió nada.'})
    item = pending['item']
    qty = int(pending['qty'])
    op = str(op or '')
    if op == 'soltar':
        sender.pending_pick = None
        return send(sender, {'t': 'mochila_op', 'ok': True, 'op': 'soltar', 'item': item, 'qty': qty, 'reason': 'Lo dejaste donde estaba.'})
    if op == 'banco':
        VAULT.add_item(VAULT.account(VAULT_STATE, sender.name), item, qty)
        sender.pending_pick = None
        save_vault()
        return send(sender, {'t': 'mochila_op', 'ok': True, 'op': 'banco', 'item': item, 'qty': qty, 'reason': 'Quedó en el banco. La mochila no cambió.'})
    if op == 'vender':
        price = int(SELL_SMH.get(item) or 0) * qty
        if price <= 0 or not ECO.debit(ECON, 'puesto_frutas', price):
            return send(sender, {'t': 'mochila_op', 'ok': False, 'op': 'vender', 'item': item, 'qty': qty, 'reason': 'El puesto no tiene monedas para comprar esto. No se perdió nada.'})
        ECO.credit(ECON, sender.name, price)
        ECO.append_tx(ECON, {'type': 'trade', 'from': 'puesto_frutas', 'to': sender.name, 'amountSubs': price, 'note': 'Venta porque la mochila estaba llena'})
        sender.pending_pick = None
        save_econ()
        return send(sender, {'t': 'mochila_op', 'ok': True, 'op': 'vender', 'item': item, 'qty': qty, 'paid': price, 'reason': 'El puesto lo compró. La mochila no cambió.'})
    return send(sender, {'t': 'mochila_op', 'ok': False, 'reason': 'Esa opción no existe. No se perdió nada.'})


def migrar_crudo(sender, counts):
    account = _cuenta(sender)
    if not account:
        return
    CRUDO.migrar(ECON, account, counts if isinstance(counts, dict) else {})
    save_econ()
    send(sender, {'t': 'crudo', 'migrado': True,
                  'crudo': {key: CRUDO.nuggets(ECON, account, key) for key in CRUDO.CAPS}})

def migration_left(sender, amount):
    migrations = ECON.get('migrations') or {}
    lock = migrations.get(ECO.migration_lock(sender.name) or '')
    if isinstance(lock, dict) and lock.get('done', True):
        return 0
    prior = migrations.get(sender.name)
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

def transferir_todo(sender, dest):
    """Pasa todo el SMC a la billetera o al banco. No acuña y no sale del juego."""
    if not wallet_ready(sender):
        return
    import traslado
    result = traslado.trasladar(ECON, VAULT_STATE, sender.name, dest)
    if not result.get('ok'):
        return send(sender, {'t': 'transfer_result', 'ok': False, 'reason': result.get('reason') or 'No se movió nada.', 'dest': result.get('dest') or dest})
    try:
        anotar_pase(result['from'], result['to'], result['smh'], result.get('note') or 'Transferir todo')
    except (LIBRO.LibroError, persist_duplicate):
        pass
    save_econ()
    save_vault()
    broadcast_econ()
    vault_for(sender)
    send(sender, {
        't': 'transfer_result', 'ok': True, 'dest': result['dest'], 'smh': result['smh'],
        'reason': result.get('note') or 'Listo.',
        'balanceSubs': int((ECON.get('wallets') or {}).get(sender.name) or 0),
        'bankSmh': result.get('bankSmh') or 0,
        'walletName': sender.name,
    })


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
        self.world = MUNDOS.DEFAULT_WORLD; self.place = 'valle'; self.pet = None; self.identity = ''
        self.note_stamps = []; self.feedback_stamps = []
    def public(self):
        pet = self.pet if isinstance(self.pet, dict) else None
        if pet:
            pet = {k: pet[k] for k in ('species', 'breed', 'variant', 'name') if k in pet}
        return {'id': self.id, 'avatar_id': ('avatar_' + self.user['id']) if getattr(self, 'user', None) else None, 'name': self.name, 'nick': visible_nick(self), 'color': self.color, 'clan': self.clan, 'group': self.group,
                'x': round(self.x, 2), 'y': round(self.y, 2), 'dir': self.dir, 'moving': self.moving, 'level': self.level, 'bot': self.bot, 'zone': self.zone,
                'world': self.world, 'place': self.place, 'pet': pet}

def clean(s, n):
    s = re.sub(r'[\x00-\x1f\x7f<>]', '', str(s or '')).strip()
    return s[:n]

def clamp_level(value, default=1):
    """Un nivel absurdo o ilegible no tumba la conexión."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        try:
            n = int(default)
        except (TypeError, ValueError):
            n = 1
    if n < 1:
        return 1
    if n > 9999:
        return 9999
    return n

def health_payload():
    return {
        'ok': True,
        'service': 'saimon-city',
        'playersOnline': sum(bool(c.hello and not c.bot) for c in clients.values()),
        'sockets': len(clients),
        'world': WORLD.get('name') or WORLD.get('id'),
        'build': WORLD.get('build'),
        'serverId': SERVER_ID,
    }

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

def _trade_balances(name):
    return {
        'smc': int((ECON.get('wallets') or {}).get(name) or 0),
        'smp': PLATA.balance_of(ECON, name),
        'cobre': COBRE.balance_of(ECON, name),
        'items': PURSES.inventory(VAULT_STATE, name),
    }

def _mover_bultos_del_trueque(state, name_a, name_b, offer_a, offer_b):
    """Pasa las series de los bultos. No crea monedas ni baja los kilos cosechados."""
    offer_a = TRADE.normalize_offer(offer_a)
    offer_b = TRADE.normalize_offer(offer_b)
    now = time.time()
    for src, dst, offer in ((name_a, name_b, offer_a), (name_b, name_a, offer_b)):
        for item, qty in offer['items'].items():
            crop = {'bolsa_cafe': 'cafe', 'bolsa_cacao': 'cacao'}.get(item)
            if not crop or qty <= 0:
                continue
            serials = [
                bag['serial'] for bag in state['bags'].values()
                if bag.get('owner') == src and bag.get('crop') == crop and bag.get('place') == 'mochila'
            ]
            if len(serials) < qty:
                raise TRADE.TradeError('No hay tantos bultos con serie.')
            for serial in serials[:qty]:
                FINCA.handoff_bag(state, serial, src, dst, now)


def commit_trade(name_a, name_b, offer_a, offer_b, trade_id):
    """Las dos patas se escriben juntas. Si el guardado falla, la memoria no cambia."""
    import copy
    candidate = copy.deepcopy(ECON)
    vault = copy.deepcopy(VAULT_STATE)
    chain = copy.deepcopy(LIBRO_CHAIN)
    records = TRADE.apply_exchange(
        candidate, vault, chain, NFT_SEED, name_a, name_b, offer_a, offer_b, trade_id,
    )
    finca_copy = copy.deepcopy(FINCA_STATE)
    _mover_bultos_del_trueque(finca_copy, name_a, name_b, offer_a, offer_b)
    PERSIST.save_bundle(
        [
            ('economy', ECON_PATH, candidate),
            ('libro_madre', LIBRO_PATH, chain),
            ('vault', VAULT_PATH, vault),
        ],
        [record['id'] for record in records],
        os.path.dirname(LIBRO_PATH),
    )
    FINCA.save(FINCA_PATH, finca_copy)
    _volcar(ECON, candidate)
    _volcar(VAULT_STATE, vault)
    _volcar(LIBRO_CHAIN, chain)
    _volcar(FINCA_STATE, finca_copy)
    broadcast_econ()
    broadcast({'t': 'libro_publico', 'contadores': public_counters()})

TRADES = TRADE.Trades(clients, send, _trade_balances, commit_trade)

def dist(a, b):
    if a is b: return 0
    if getattr(a, 'zone', 'city') == 'casa' or getattr(b, 'zone', 'city') == 'casa': return 1e9
    return max(abs(a.x - b.x), abs(a.y - b.y))

def visible_nick(client):
    """Apodo que ven los demás. Si no hay apodo, Viajero. Nunca el correo ni el usuario de la cuenta."""
    user = getattr(client, 'user', None)
    if user:
        raw = str(user.get('wallet_name') or '').strip()
        email = str(user.get('email') or '').strip().lower()
        if not raw or '@' in raw or raw.lower() == email:
            return 'Viajero'
        return ACC.game_name(raw) or 'Viajero'
    raw = str(getattr(client, 'name', '') or '').strip()
    if not raw or '@' in raw:
        return 'Viajero'
    return raw

def nick_de(name):
    key = ACC.name_key(name)
    if key:
        for other in clients.values():
            if other.hello and ACC.name_key(other.name) == key:
                return visible_nick(other)
    text = str(name or '').strip()
    if not text or '@' in text:
        return 'Viajero'
    return text

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

def too_fast(sender):
    now = time.time()
    sender.stamps = [t for t in sender.stamps if now - t < 5]
    if len(sender.stamps) >= 6 and not sender.bot:
        send(sender, {'t': 'system', 'text': 'Vas muy rápido: espera unos segundos.'})
        return True
    sender.stamps.append(now)
    return False

def chat(sender, channel, text):
    if too_fast(sender):
        return
    text = SOCIAL.mask(clean(text, MAX_TEXT), MAX_TEXT)
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
                return send(sender, {'t': 'system', 'text': 'El monto no es válido. Usa SMC (hasta 2 decimales) o SMH enteros.'})
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
    msg = {'t': 'chat', 'channel': channel, 'from': visible_nick(sender), 'fromId': sender.id, 'clan': sender.clan, 'text': text,
           'ts': time.strftime('%H:%M'), 'bot': sender.bot, 'world': sender.world, 'place': sender.place}
    if channel == 'global': broadcast(msg, lambda c: MUNDOS.same_world(c, sender))
    elif channel == 'proximidad': broadcast(msg, lambda c: MUNDOS.same_world(c, sender) and dist(c, sender) <= PROX_TILES)
    elif channel == 'lugar':
        if sender.place in MUNDOS.PRIVATE:
            return send(sender, {'t': 'system', 'text': 'En tu casa ese chat está cerrado.'})
        broadcast(msg, lambda c: MUNDOS.same_room(c, sender))
    elif channel == 'clan': broadcast(msg, lambda c: MUNDOS.same_world(c, sender) and c.clan.lower() == sender.clan.lower())
    elif channel == 'grupo':
        if not sender.group: return send(sender, {'t': 'system', 'text': 'No estás en un grupo. Escribe /grupo <nombre> para crear o unirte a uno.'})
        broadcast(msg, lambda c: MUNDOS.same_world(c, sender) and c.group and c.group.lower() == sender.group.lower())

def arrival_position(resume=None, user=None):
    # Start within the same connected spawn area, on an unoccupied walkable tile.
    occupied = [(c.x, c.y) for c in clients.values() if c.hello]
    home = HOGAR.arrival(user, resume, walkable)
    if home is not None:
        return home
    seen = {SPAWN}; queue = [SPAWN]
    for x, y in queue:
        if walkable(x, y) and all(abs(x-ox) >= 0.9 or abs(y-oy) >= 0.9 for ox, oy in occupied):
            return float(x), float(y)
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            tile = (x+dx,y+dy)
            if tile not in seen and walkable(*tile):
                seen.add(tile); queue.append(tile)
    return float(SPAWN[0]), float(SPAWN[1])

class _Spot:
    def __init__(self, world, place):
        self.world = world
        self.place = place

def presence_msg():
    body = MUNDOS.presence(clients.values(), PLACES)
    for row in body['players']:
        person = clients.get(row['id'])
        if person is not None:
            row['nick'] = visible_nick(person)
    return body

def city_peers(c):
    return [o.public() for o in clients.values() if o.hello and o is not c and MUNDOS.same_sight(c, o)]

def stand_beside(x, y):
    """Una casilla caminable al lado, no encima de otra persona."""
    ix, iy = int(float(x)), int(float(y))
    occupied = {(int(o.x), int(o.y)) for o in clients.values() if o.hello}
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
        nx, ny = ix + dx, iy + dy
        if (nx, ny) in occupied:
            continue
        if VIAJES.walkable(WORLD, nx, ny):
            return float(nx), float(ny)
    try:
        nx, ny = VIAJES.nearest_spawn(WORLD, ix, iy)
        return float(nx), float(ny)
    except VIAJES.ViajeError:
        return float(ix), float(iy)

def meet_point(target):
    """Al lado de quien está en la ciudad. Si está adentro, a la puerta pública."""
    zone = getattr(target, 'zone', 'city')
    if zone == 'city':
        return float(target.x), float(target.y)
    if zone == 'casa':
        return 94.0, 267.0
    saved_x, saved_y = getattr(target, 'city_x', None), getattr(target, 'city_y', None)
    if saved_x is not None and saved_y is not None:
        return float(saved_x), float(saved_y)
    return float(target.x), float(target.y)

def room_shift(c, old_world, old_place):
    """Quien sale de la ciudad deja de verse. En la misma ciudad, se mueve aunque cambie de parque."""
    previous = _Spot(old_world, old_place)
    for other in list(clients.values()):
        if other is c or not other.hello:
            continue
        before = MUNDOS.same_sight(previous, other)
        after = MUNDOS.same_sight(c, other)
        if before and not after:
            send(other, {'t': 'leave', 'id': c.id})
        elif after and not before:
            send(other, {'t': 'join', 'player': c.public()})
        elif after:
            send(other, {'t': 'move', 'id': c.id, 'x': round(c.x, 2), 'y': round(c.y, 2),
                         'dir': c.dir, 'moving': c.moving, 'level': c.level, 'zone': 'city',
                         'pace': getattr(c, 'pace', '') or ('caminando' if c.moving else 'quieto')})
    if old_world != c.world or old_place != c.place:
        broadcast(presence_msg())

def refresh_social(c, other_key=None):
    send(c, {'t': 'social', 'social': SOCIAL.friend_view(VIDA, c.identity, ACCOUNTS, clients.values())})
    if not other_key:
        return
    for other in clients.values():
        if other.hello and getattr(other, 'identity', '') == other_key:
            send(other, {'t': 'social', 'social': SOCIAL.friend_view(VIDA, other.identity, ACCOUNTS, clients.values())})

def vida_privado(c, m):
    if too_fast(c):
        return
    result = SOCIAL.private_message(VIDA, c.identity or SOCIAL.identity_of(c), visible_nick(c), m.get('to'), m.get('text'), ACCOUNTS)
    if not result.get('ok'):
        return send(c, {'t': 'vida_error', 'error': result.get('error')})
    save_vida()
    targets = set(result['targets'])
    for other in clients.values():
        if other.hello and getattr(other, 'identity', '') in targets:
            send(other, result['message'])

def vida_try(c, m, t):
    if not c.hello:
        return False
    key = c.identity or SOCIAL.identity_of(c)
    c.identity = key
    if t == 'adoptar':
        pet = SOCIAL.save_pet(VIDA, key, m.get('pet') or m)
        if not pet:
            send(c, {'t': 'vida_error', 'error': 'Esa mascota no está en el catálogo.'})
            return True
        c.pet = pet
        if getattr(c, 'user', None):
            CASA.apply(c.user, {'pet': pet})
            save_accounts()
        save_vida()
        send(c, {'t': 'pet', 'id': c.id, 'pet': pet})
        broadcast({'t': 'pet', 'id': c.id, 'pet': pet}, who=lambda o: MUNDOS.same_sight(c, o), exclude=c)
        return True
    if t == 'hogar':
        layout = SOCIAL.save_home(VIDA, key, m.get('layout'))
        if getattr(c, 'user', None):
            CASA.apply(c.user, {'layout': layout})
            save_accounts()
        save_vida()
        send(c, {'t': 'hogar', 'layout': layout})
        return True
    if t == 'mundo':
        chosen = MUNDOS.normalize(m.get('id') if m.get('id') is not None else m.get('world'))
        if not chosen:
            send(c, {'t': 'vida_error', 'error': 'Ese mundo no está abierto.'})
            return True
        old_world, old_place = c.world, c.place
        c.world = chosen
        room_shift(c, old_world, old_place)
        payload = presence_msg()
        send(c, {'t': 'mundo', 'world': chosen, 'presence': payload})
        send(c, {'t': 'cerca', 'players': city_peers(c)})
        broadcast(payload)
        return True
    if t == 'amigo_buscar':
        found = SOCIAL.search_nick(ACCOUNTS, m.get('nick'), [getattr(o, 'identity', '') for o in clients.values() if o.hello])
        send(c, {'t': 'amigo', 'found': found, 'error': None if found else 'No hay una cuenta con ese nick.'})
        return True
    if t == 'amigo_pedir':
        SOCIAL.request_friend(VIDA, key, m.get('key'))
        save_vida()
        refresh_social(c, m.get('key'))
        return True
    if t == 'amigo_aceptar':
        SOCIAL.accept_friend(VIDA, key, m.get('key'))
        save_vida()
        refresh_social(c, m.get('key'))
        return True
    if t == 'amigo_rechazar':
        SOCIAL.reject_friend(VIDA, key, m.get('key'))
        save_vida()
        refresh_social(c, m.get('key'))
        return True
    if t == 'amigo_hilo':
        send(c, {'t': 'hilo', 'key': m.get('key'), 'messages': SOCIAL.thread_for(VIDA, key, m.get('key'))})
        return True
    if t == 'nick_cambio':
        send(c, {'t': 'nick_quote', **SOCIAL.quote_nick(ACCOUNTS, getattr(c, 'user', None), m.get('name'))})
        return True
    if t == 'feedback':
        if not SOCIAL.allow(c.feedback_stamps, time.time(), 3, 600):
            send(c, {'t': 'feedback_result', 'ok': False, 'error': 'Espera un poco para enviar otro.'})
            return True
        result = SOCIAL.add_feedback(VIDA, visible_nick(c), m.get('text'), c.world, c.place)
        if result.get('ok'):
            save_vida()
        send(c, {'t': 'feedback_result', **result})
        return True
    if t == 'poste_nota':
        if not SOCIAL.allow(c.note_stamps, time.time(), 4, 60):
            send(c, {'t': 'poste', 'error': 'Vas muy rápido.', **SOCIAL.public_notes(VIDA)})
            return True
        result = SOCIAL.add_note(VIDA, visible_nick(c), key, m.get('text'), c.place, c.world)
        if result.get('ok'):
            save_vida()
        send(c, {'t': 'poste', **(result.get('board') or {}), 'error': result.get('error')})
        return True
    if t == 'poste_encuesta':
        result = SOCIAL.add_poll(VIDA, visible_nick(c), key, m.get('question'), m.get('options'), c.place, c.world)
        if result.get('ok'):
            save_vida()
        send(c, {'t': 'poste', **(result.get('board') or {}), 'error': result.get('error')})
        return True
    if t == 'poste_votar':
        result = SOCIAL.vote_poll(VIDA, key, m.get('id'), m.get('option'))
        if result.get('ok'):
            save_vida()
        send(c, {'t': 'poste', **(result.get('board') or {}), 'error': result.get('error')})
        return True
    if t == 'poste_ver':
        send(c, {'t': 'poste', **SOCIAL.public_notes(VIDA)})
        return True
    if t == 'poste_moderar':
        result = SOCIAL.moderate(VIDA, SOCIAL.role_of(getattr(c, 'user', None)), m.get('kind'), m.get('id'), m.get('action'), m.get('text') or '')
        if result.get('ok'):
            save_vida()
        send(c, {'t': 'poste', **(result.get('board') or SOCIAL.public_notes(VIDA)), 'error': result.get('error')})
        return True
    return False

TRAVEL_GATE = VIAJES.Gate()

def correct_move(sender):
    send(sender, {'t': 'move_correct', 'x': round(sender.x, 2), 'y': round(sender.y, 2), 'zone': getattr(sender, 'zone', 'city')})


def travel_for(sender, dest_id):
    """Lleva al jugador a un municipio o punto conocido. El servidor elige la casilla."""
    now = time.time()
    try:
        dest = VIAJES.resolve(WORLD, clean(dest_id, 32).lower())
    except VIAJES.ViajeError as exc:
        return send(sender, {'t': 'travel_result', 'ok': False, 'reason': str(exc)})
    if not TRAVEL_GATE.allow(sender.id, now):
        return send(sender, {'t': 'travel_result', 'ok': False, 'reason': 'Espera un momento para volver a viajar.'})
    old_world, old_place = sender.world, getattr(sender, 'place', 'valle')
    sender.zone = 'city'
    sender.x, sender.y = float(dest['x']), float(dest['y'])
    sender.moving = False
    sender.move_at = now
    sender.place = MUNDOS.place_of(sender.x, sender.y, 'city', PLACES)
    room_shift(sender, old_world, old_place)
    send(sender, {'t': 'travel_result', 'ok': True, 'id': dest['id'], 'name': dest['name'], 'x': dest['x'], 'y': dest['y']})

async def handle_ws(reader, writer, cookie='', ip=''):
    c = Client(writer); clients[c.id] = c
    c.ip = ip or ''
    c.user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
    try:
        while True:
            op, data = await asyncio.wait_for(read_frame(reader), 45)  # el cliente hace ping cada 3 s
            if op == 8:
                try:
                    writer.write(struct.pack('!BB', 0x88, 0))
                    await writer.drain()
                except Exception:
                    pass
                break
            if op == 9: writer.write(struct.pack('!BB', 0x8A, len(data)) + data); continue
            if op != 1: continue
            try: m = json.loads(data.decode('utf-8'))
            except Exception: continue
            if not isinstance(m, dict):
                continue
            t = m.get('t')
            try:
                handle_client_message(c, m, t)
                await writer.drain()
            except (asyncio.IncompleteReadError, ConnectionError, OSError, asyncio.TimeoutError):
                raise
            except Exception:
                continue
    except (asyncio.IncompleteReadError, ConnectionError, OSError, asyncio.TimeoutError):
        pass
    finally:
        TRADES.cancel(c.id, 'Intercambio cancelado por desconexión.')
        clients.pop(c.id, None)
        if c.hello:
            broadcast({'t': 'leave', 'id': c.id}, who=lambda o: MUNDOS.same_sight(c, o))
            broadcast(presence_msg())
        try: writer.close()
        except Exception: pass

class FincaPurse:
    """Mueve monedas que ya existen. No toca la acuñación ni los lingotes."""

    def balance(self, coin, name):
        if coin == 'simoncoin':
            return int((ECON.get('wallets') or {}).get(name) or 0)
        if coin == 'simonplata':
            return PLATA.balance_of(ECON, name)
        if coin == 'simonchis':
            return COBRE.balance_of(ECON, name)
        return 0

    def move(self, coin, src, dst, amount):
        amount = int(amount)
        if amount <= 0 or src == dst:
            return False
        if coin == 'simoncoin':
            if not ECO.debit(ECON, src, amount):
                return False
            ECO.credit(ECON, dst, amount)
            return True
        if coin == 'simonplata':
            PLATA.ensure(ECON)
            if not PLATA.park(ECON, src, amount):
                return False
            if not PLATA.unpark(ECON, dst, amount):
                PLATA.unpark(ECON, src, amount)
                return False
            return True
        if coin == 'simonchis':
            box = COBRE.ensure(ECON)
            have = int((box.get('wallets') or {}).get(src) or 0)
            if have < amount:
                return False
            box['wallets'][src] = have - amount
            box['wallets'][dst] = int(box['wallets'].get(dst) or 0) + amount
            return True
        return False

    def supply(self):
        COBRE.ensure(ECON)
        plata_box = ECON.get('plata') or {}
        chis = ECON.get('simonchis') or {}
        return {
            'simoncoin': int(ECON.get('minedSmh') or 0),
            'simonplata': int(plata_box.get('minedSph') or 0),
            'simonchis': int(chis.get('minted') or 0),
            'simoncoinSum': sum(int(v or 0) for v in (ECON.get('wallets') or {}).values()),
            'simonplataSum': sum(int(v or 0) for v in (plata_box.get('wallets') or {}).values()),
            'simonchisSum': sum(int(v or 0) for v in (chis.get('wallets') or {}).values()),
            'foundry': dict(((ECON.get('foundry') or {}).get('minted') or {})),
        }


FINCA_PURSE = FincaPurse()


def public_counters():
    return FINCA.attach_public(MONEDAS.ledger(ECON), FINCA_STATE, FINCA_PURSE, FINCA_CONFIG)


def finca_account(sender):
    if getattr(sender, 'wallet_ok', False) and getattr(sender, 'name', ''):
        return sender.name
    return ''


def finca_sync_purse(name):
    """La mochila del intercambio cuenta los bultos en la mano. No crea monedas."""
    if not name:
        return False
    changed = False
    for crop, item in (('cafe', 'bolsa_cafe'), ('cacao', 'bolsa_cacao')):
        want = sum(
            1 for bag in FINCA_STATE['bags'].values()
            if bag.get('owner') == name and bag.get('crop') == crop and bag.get('place') == 'mochila'
        )
        have = PURSES.count(VAULT_STATE, name, item)
        if want > have:
            PURSES.credit(VAULT_STATE, name, item, want - have)
            changed = True
        elif have > want and PURSES.debit(VAULT_STATE, name, item, have - want):
            changed = True
    return changed


def finca_here(sender):
    """La finca está afuera, en Las Palmas. La mina es solo la cantera."""
    zone = getattr(sender, 'zone', 'city')
    if zone != 'city':
        return False
    spot = next((w for w in WORLD.get('waypoints') or [] if w.get('id') == 'las_palmas'), None)
    if not spot:
        return False
    try:
        return max(abs(float(sender.x) - float(spot['x'])), abs(float(sender.y) - float(spot['y']))) <= 30
    except (TypeError, ValueError):
        return False


def finca_msg(sender, message):
    op = str((message or {}).get('op') or 'ver')
    account = finca_account(sender)
    if op != 'ver' and not account:
        if not wallet_ready(sender):
            return
        account = finca_account(sender)
    if op in ('depositar', 'retirar') and getattr(sender, 'zone', '') == 'banco':
        present = True
    else:
        present = op == 'ver' or finca_here(sender)
    result = FINCA.act(FINCA_STATE, FINCA_PURSE, FINCA_CONFIG, account, op, message, time.time(), present=present)
    if result.get('changed'):
        if finca_sync_purse(account):
            save_vault()
        save_finca()
        if result.get('movedCoins'):
            save_econ()
        for row in result.get('exports') or []:
            crop = str(row.get('crop') or '')
            label = 'café excelso' if crop == 'cafe' else 'cacao seco'
            ECO.append_tx(ECON, {
                'type': 'pay', 'from': FINCA_CONFIG.get('buyer') or 'casa_de_contratacion', 'to': account,
                'amountSubs': 0, 'amountSph': int(row.get('amount') or 0), 'coin': 'SMP',
                'note': f'Exportación de {label}. No se acuñó SMC.',
            })
            save_econ()
        broadcast({'t': 'libro_publico', 'contadores': public_counters()})
    send(sender, {'t': 'finca', 'ok': bool(result.get('ok')), 'error': result.get('error') or '', 'note': result.get('note') or '', 'view': result.get('view')})


def handle_client_message(c, m, t):
    if t == 'hello':
        if c.hello: return
        c.zone = zona_pedida(c, m.get('zone'))
        c.world = MUNDOS.normalize(m.get('world')) or MUNDOS.DEFAULT_WORLD
        if c.zone == 'casa':
            door = HOGAR.stand((getattr(c, 'user', None) or {}).get('municipio')) or (94, 267)
            c.city_x, c.city_y = float(door[0]), float(door[1])
            c.x, c.y = float(SPAWN[0]), float(SPAWN[1])
        else:
            c.x, c.y = arrival_position(m.get('resume'), getattr(c, 'user', None))
        asked = c.user.get('wallet_name') if getattr(c, 'user', None) else m.get('name')
        token_src = c.user.get('wallet_token') if getattr(c, 'user', None) else m.get('walletToken')
        c.name = unique_name(clean(asked, 16), c)
        c.color = m.get('color') if m.get('color') in COLORS else random.choice(COLORS)
        c.clan = clean(m.get('clan'), 24); c.group = clean(m.get('group'), 24)
        c.level = clamp_level(m.get('level'), 1); c.hello = True
        c.move_at = time.time()
        c.identity = SOCIAL.identity_of(c)
        c.place = MUNDOS.place_of(c.x, c.y, c.zone, PLACES)
        if getattr(c, 'user', None) and CASA.absorb(c.user, VIDA, c.identity):
            save_accounts()
            save_vida()
        stored = SOCIAL.pet_for(VIDA, c.identity)
        if stored:
            c.pet = stored
        elif m.get('pet'):
            adopted = SOCIAL.save_pet(VIDA, c.identity, m.get('pet'))
            if adopted:
                c.pet = adopted
                save_vida()
        presented = clean(token_src, 64)
        owned = bind_wallet(c.name, presented, owner=bool(getattr(c, 'user', None)))
        c.wallet_ok = bool(owned)
        c.wallet_token = owned or ''
        if owned and getattr(c, 'user', None) is not None and c.user.get('wallet_token') != owned:
            c.user['wallet_token'] = owned
            save_accounts()
        perfil = account_profile(c)
        libro_nombre = c.name if c.wallet_ok else None
        import acunar_credito as ACU
        welcome = {'t': 'welcome', 'id': c.id, 'you': c.public(), 'canMintIngots': LINGOTES.autorizado(getattr(c, 'user', None)), 'players': city_peers(c),
                 'proximityTiles': PROX_TILES, 'serverId': SERVER_ID, 'worldBuild': WORLD.get('build'),
                 'reloj': RELOJ.payload(ECON),
                 'ledger': MONEDAS.ledger(ECON, libro_nombre, perfil.get('account') if libro_nombre else None),
                 'walletName': libro_nombre or '',
                 'purse': ACU.vista(VAULT_STATE, ECON, c.name, perfil.get('account')) if libro_nombre else {'items': {}, 'catalog': dict(PURSES.CATALOG), 'monedas': {}},
                 'contadores': public_counters()}
        welcome.update(SOCIAL.hello_extra(VIDA, c, ACCOUNTS, clients, PLACES))
        welcome['presence'] = presence_msg()
        welcome['worldEdits'] = world_edit_packet(getattr(c, 'user', None))
        send(c, welcome)
        if MUNDOS.outdoors(c):
            broadcast({'t': 'join', 'player': c.public()}, who=lambda o: MUNDOS.same_sight(c, o), exclude=c)
            place = MUNDOS.place_name(c.place, PLACES)
            broadcast({'t': 'system', 'text': f'{visible_nick(c)} entró a {place}.'}, who=lambda o: MUNDOS.same_sight(c, o), exclude=c)
        broadcast(presence_msg())
        send(c, econ_msg(c.name, reveal_token=owned, locked=not c.wallet_ok, profile=account_profile(c)))
        if c.wallet_ok:
            send(c, {'t': 'playtime', **play_for(c.name, active=True)})
        if not c.wallet_ok:
            send(c, {'t': 'system', 'text': 'Ese nombre ya tiene una billetera SMC en otro aparato. Puedes entrar, pero no gastar ni emitir esas monedas.'})
    elif t == 'travel' and c.hello:
        travel_for(c, m.get('id'))
    elif t == 'ir_con' and c.hello:
        try:
            target = clients.get(int(m.get('id')))
        except (TypeError, ValueError):
            target = None
        if target is None or not target.hello or target is c:
            send(c, {'t': 'travel_result', 'ok': False, 'reason': 'Ese jugador ya no está en línea.'})
        else:
            old_world, old_place = c.world, getattr(c, 'place', 'valle')
            tx, ty = meet_point(target)
            c.world = target.world
            c.zone = 'city'
            c.x, c.y = stand_beside(tx, ty)
            c.moving = False
            c.move_at = time.time()
            c.place = MUNDOS.place_of(c.x, c.y, 'city', PLACES)
            room_shift(c, old_world, old_place)
            payload = presence_msg()
            send(c, {'t': 'mundo', 'world': c.world, 'presence': payload})
            send(c, {'t': 'cerca', 'players': city_peers(c)})
            send(c, {'t': 'travel_result', 'ok': True, 'id': 'junto', 'name': visible_nick(target), 'x': c.x, 'y': c.y, 'world': c.world})
            broadcast(payload)
    elif t == 'ir_mina' and c.hello:
        try:
            dest = VIAJES.mine_stand(WORLD)
        except VIAJES.ViajeError as exc:
            send(c, {'t': 'travel_result', 'ok': False, 'reason': str(exc)})
        else:
            old_world, old_place = c.world, getattr(c, 'place', 'valle')
            c.zone = 'city'
            c.x, c.y = float(dest['x']), float(dest['y'])
            c.moving = False
            c.place = MUNDOS.place_of(c.x, c.y, 'city', PLACES)
            room_shift(c, old_world, old_place)
            send(c, {'t': 'travel_result', 'ok': True, 'id': 'mina', 'name': dest['name'], 'x': dest['x'], 'y': dest['y']})
    elif t == 'seguir' and c.hello:
        try:
            target = clients.get(int(m.get('id')))
        except (TypeError, ValueError):
            target = None
        result = SEGUIR.pedir(getattr(target, 'user', None) if target else None, bool(target and target.hello and target is not c), True)
        if not result['ok']:
            send(c, {'t': 'seguir_result', 'ok': False, 'reason': result['reason']})
        else:
            c.following = target.id
            send(c, {'t': 'seguir_result', 'ok': True, 'id': target.id, 'nick': visible_nick(target)})
            send(target, {'t': 'seguir_aviso', 'from': visible_nick(c), 'text': visible_nick(c) + ' te está siguiendo'})
    elif t == 'dejar_seguir' and c.hello:
        c.following = None
        send(c, {'t': 'seguir_result', 'ok': True, 'id': 0})
    elif t == 'move' and c.hello:
        old_world, old_place = c.world, c.place
        zone = m.get('zone')
        now_move = time.time()
        if zone in ('casa', 'mine', 'banco', 'central'):
            zone = zona_pedida(c, zone)
            if zone == 'city':
                return
            if c.zone == 'city':
                c.city_x, c.city_y = c.x, c.y
            c.zone = zone
            c.pace = 'casa' if zone == 'casa' else getattr(c, 'pace', '') or 'quieto'
            c.place = MUNDOS.place_of(c.x, c.y, c.zone, PLACES)
            if (old_world, old_place) != (c.world, c.place):
                room_shift(c, old_world, old_place)
            return
        try:
            nx = max(0.0, min(WORLD['width'] - 1.0, float(m['x']))); ny = max(0.0, min(WORLD['height'] - 1.0, float(m['y'])))
        except Exception: return
        if nx != nx or ny != ny: return
        came_from = c.zone
        if came_from != 'city':
            back = (getattr(c, 'city_x', None), getattr(c, 'city_y', None))
            if not VIAJES.portal_arrival(came_from, nx, ny, back):
                return correct_move(c)
            c.zone = 'city'
            c.x, c.y = nx, ny
            c.move_at = now_move
            note_motion(c, 1)
        else:
            step = max(abs(nx - c.x), abs(ny - c.y))
            elapsed = now_move - float(getattr(c, 'move_at', now_move) or now_move)
            if not VIAJES.step_allowed(step, elapsed):
                return correct_move(c)
            c.move_at = now_move
            c.x, c.y = nx, ny
            note_motion(c, step)
        c.zone = 'city'
        c.dir = m.get('dir') if m.get('dir') in ('up', 'down', 'left', 'right') else c.dir
        c.moving = bool(m.get('moving')); c.level = clamp_level(m.get('level'), c.level)
        c.pace = SEGUIR.pace_of(m.get('pace'), 'city', c.moving)
        c.place = MUNDOS.place_of(c.x, c.y, 'city', PLACES)
        room_shift(c, old_world, old_place)
    elif t == 'ping':
        TRADES.expire()
        send(c, {'t': 'pong', 'c': m.get('c')})
    elif t == 'emote' and c.hello:
        emote = str(m.get('emote') or '')
        if emote not in ('wave', 'bow', 'dance', 'clap', 'laugh', 'sit', 'point', 'bacano'):
            return
        near = lambda o, me=c: o.zone == 'city' and me.zone == 'city' and (o.x - me.x) ** 2 + (o.y - me.y) ** 2 <= 225
        broadcast({'t': 'emote', 'id': c.id, 'emote': emote}, who=near, exclude=c)
    elif isinstance(t, str) and t.startswith('trade_') and c.hello:
        try:
            TRADES.handle(c, m)
        except TRADE.TradeError as err:
            send(c, {'t': 'trade_error', 'reason': str(err)})
    elif t == 'chat' and c.hello:
        if str(m.get('channel', 'proximidad')).lower() == 'privado':
            vida_privado(c, m)
        else:
            chat(c, str(m.get('channel', 'proximidad')).lower(), m.get('text'))
    elif t == 'mint' and c.hello:
        mint_for(c, clean(m.get('node'), 40), m.get('proof'))
    elif t == 'mint_cobre' and c.hello:
        mint_cobre_for(c, m.get('proof'))
    elif t == 'mint_plata' and c.hello:
        mint_plata(c, m.get('proof'))
    elif t == 'cambio_simple' and c.hello:
        cambio_simple_msg(c, m)
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
            return
        pagar(c, m.get('to'), smh, clean(m.get('note') or 'Pago', 80) or 'Pago')
    elif t == 'acunar' and c.hello:
        try:
            acunar_for(c, m.get('coin'), m.get('pieces'), m.get('proof'))
        except Exception:
            send(c, {'t': 'acunar_result', 'ok': False, 'reason': 'No se pudo acuñar. No se creó ninguna moneda nueva.', 'code': 'error'})
    elif t == 'smelt' and c.hello:
        smelt_for(c, m.get('ore'), m.get('batches'), m.get('proof'), m.get('mode'))
    elif t == 'lingote' and c.hello:
        lingote_for(c, m.get('metal'), m.get('qty'))
    elif t == 'lingote_ver' and c.hello:
        lingote_ver(c)
    elif t == 'swing' and c.hello:
        swing_for(c, m.get('mineral'), m.get('qty'))
    elif t == 'recoger' and c.hello:
        item = str(m.get('item') or '')
        if recibir(c, item, m.get('qty'), m.get('kind') or 'recoger'):
            send(c, {'t': 'recoger', 'ok': True, 'item': item, 'qty': int(m.get('qty') or 0)})
            if item == 'mineral_cobre' and oro_agotado(c):
                send(c, {'t': 'system', 'text': SUP.COPPER_NOTE})
                mint_cobre_for(c)
    elif t == 'mochila_op' and c.hello:
        mochila_op(c, m.get('op'))
    elif t == 'lavar' and c.hello:
        lavar_for(c, m.get('qty') or 1)
    elif t == 'metal_migrar' and c.hello:
        migrar_crudo(c, m.get('counts'))
    elif t == 'migrate' and c.hello:
        migrate_for(c, m.get('amount'), m.get('proof'))
    elif t == 'quest' and c.hello:
        quest_for(c, m.get('id'), m.get('proof'))
    elif t == 'heartbeat' and c.hello and c.wallet_ok:
        send(c, {'t': 'playtime', **play_for(c.name, active=bool(m.get('active')))})
    elif t == 'vault' and c.hello:
        vault_for(c)
    elif t == 'transferir_todo' and c.hello:
        transferir_todo(c, m.get('dest') or m.get('to'))
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
    elif t == 'finca' and c.hello:
        finca_msg(c, m)
    elif t == 'world_edit' and c.hello:
        result = world_edit_request(getattr(c, 'user', None), m)
        send(c, {'t': 'world_edit_result', 'ok': result.get('ok'), 'code': result.get('code'),
                 'error': result.get('error') or '', 'worldEdits': result.get('doc'), 'package': result.get('package')})
    elif vida_try(c, m, t):
        return

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
        if ACC.is_owner(user):
            name = user.get('wallet_name') or user.get('name') or link_name
            token = secrets.token_hex(16)
            ECON.setdefault('wallets', {}).setdefault(name, 0)
            ECON.setdefault('walletTokens', {})[name] = token
            ACC.link_wallet(user, name, token)
            save_econ()
            return
    if not user.get('wallet_token'):
        token = bind_wallet(user.get('wallet_name') or user['name'], user.get('wallet_token') or '')
        if token:
            ACC.link_wallet(user, user.get('wallet_name') or user['name'], token)


def _texto_enlace(frase, url):
    return frase + '\n\n' + url + '\n\nSi no pediste este mensaje, ignóralo.'


def _pagina_clave(token, error, done=False):
    import html
    safe = html.escape(token or '', quote=True)
    aviso = html.escape(error or '')
    if done:
        cuerpo = '<p>La contraseña quedó guardada. Ya puedes entrar con el correo.</p><p><a href="/play/">Volver al juego</a></p>'
    else:
        cuerpo = (
            '<p>Elige una contraseña nueva. El enlace sólo sirve una vez.</p>'
            f'<p class="aviso">{aviso}</p>'
            '<form method="post" action="/auth/restablecer">'
            f'<input type="hidden" name="token" value="{safe}">'
            '<label>Contraseña nueva<input type="password" name="password" minlength="8" required autocomplete="new-password"></label>'
            '<button type="submit">Guardar contraseña</button></form>'
        )
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Contraseña · Saimon City</title>'
        '<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#12160f;color:#f7f4ea;'
        'font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}'
        'main{width:min(420px,calc(100vw - 28px));padding:22px;border:1px solid rgba(255,255,255,.28);border-radius:16px;background:#1c2218}'
        'label{display:flex;flex-direction:column;gap:6px;margin:12px 0}input,button{font:inherit;min-height:44px;border-radius:10px}'
        'input{padding:8px 10px;border:1px solid #8d7a48;background:#10140e;color:#fff}'
        'button{background:#2f6b3a;color:#fff;border:0}a{color:#f0d48a}.aviso{color:#ffb4b4}</style></head>'
        f'<body><main><h1>Saimon City</h1>{cuerpo}</main></body></html>'
    )


def auth_html(status, html_text, headers, extra_headers=()):
    raw = html_text.encode('utf-8')
    lines = [f'HTTP/1.1 {status}\r\nContent-Type: text/html; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(raw)}\r\n']
    for item in extra_headers:
        lines.append(item + '\r\n')
    lines.append('Connection: close\r\n\r\n')
    return ''.join(lines).encode() + raw


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


def _volcar(live, new):
    live.clear()
    live.update(new)


def eliminar_cuenta_propia(user, confirm):
    """Borra sólo la cuenta de esta sesión. Una escritura; si falla, el estado vivo no cambia."""
    import copy
    import persist
    import borrar_cuenta as borrar
    accounts = copy.deepcopy(ACCOUNTS)
    economy = copy.deepcopy(ECON)
    vault_state = copy.deepcopy(VAULT_STATE)
    players = copy.deepcopy(PLAYERS)
    nft_chain = copy.deepcopy(NFT_CHAIN)
    libro_chain = copy.deepcopy(LIBRO_CHAIN)
    bundle = {
        'accounts': accounts,
        'economy': economy,
        'vault': vault_state,
        'players': players,
        'nft': nft_chain,
        'libro': libro_chain,
    }
    result = borrar.aplicar(bundle, user, confirm, seed=NFT_SEED, now=int(time.time()))
    if not result.get('ok') or result.get('already'):
        return result
    docs = [
        ('accounts', ACCOUNTS_PATH, accounts),
        ('economy', ECON_PATH, economy),
        ('vault', VAULT_PATH, vault_state),
        ('players', PLAY_PATH, players),
        ('nft', NFT_PATH, nft_chain),
        ('libro_madre', LIBRO_PATH, libro_chain),
    ]
    persist.save_bundle(docs, result.get('new_ids') or [], os.path.dirname(LIBRO_PATH) or '.')
    _volcar(ACCOUNTS, accounts)
    _volcar(ECON, economy)
    _volcar(VAULT_STATE, vault_state)
    _volcar(PLAYERS, players)
    _volcar(NFT_CHAIN, nft_chain)
    _volcar(LIBRO_CHAIN, libro_chain)
    return result


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
        if user and ACC.ensure_owner_favorite(user):
            save_accounts()
        return auth_response('200 OK', {'user': ACC.public_user(user) if user else None}, headers)
    if path == '/auth/mundo-favorito' and method == 'POST':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para guardar el favorito.'}, headers)
        try:
            shown = ACC.set_favorite_world(ACCOUNTS, user, payload.get('id'))
            save_accounts()
        except ACC.AuthError as exc:
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True, 'user': shown}, headers)
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
    if path == '/auth/nick' and method == 'POST':
        return auth_response('200 OK', ACC.nick_preview(ACCOUNTS, payload.get('nick')), headers)
    if path == '/auth/entrar' and method == 'POST':
        try:
            login = payload.get('nick') if payload.get('nick') else payload.get('email')
            if '@' in str(login or ''):
                result = ACC.login_password(ACCOUNTS, login, payload.get('password'), client_ip=remote_ip)
            else:
                result = ACC.enter_or_create(ACCOUNTS, login, payload.get('password'), client_ip=remote_ip)
            save_accounts()
        except ACC.AuthError as exc:
            save_accounts()
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True, 'user': result['user']}, headers,
                             ['Set-Cookie: ' + ACC.cookie('life_session', result['token'], result['max_age'], secure)])
    if path == '/auth/apodo' and method == 'POST':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra otra vez.'}, headers)
        old_wallet = user.get('wallet_name') or ''
        try:
            shown = ACC.set_nick_and_password(
                ACCOUNTS, user, payload.get('nick'), payload.get('password'), payload.get('confirm'),
            )
            mover_billetera(old_wallet, user.get('wallet_name') or '')
            save_accounts()
        except ACC.AuthError as exc:
            save_accounts()
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True, 'user': shown}, headers)
    if path == '/auth/simon' and method == 'POST':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra otra vez.'}, headers)
        old_wallet = user.get('wallet_name') or ''
        try:
            shown = ACC.claim_simon(ACCOUNTS, user)
            mover_billetera(old_wallet, user.get('wallet_name') or '')
            save_accounts()
        except ACC.AuthError as exc:
            save_accounts()
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True, 'user': shown}, headers)
    if path == '/auth/registro' and method == 'POST':
        if not ACC.email_ready():
            return auth_response('503 Service Unavailable', {'error': 'El correo no está configurado. Entra con Google o Facebook.'}, headers)
        try:
            ACC.begin_email_account(
                ACCOUNTS, payload.get('name'), payload.get('email'), payload.get('password') or '',
                lambda email, raw: ACC.send_message(email, 'Confirma tu cuenta de Saimon City', _texto_enlace(
                    'Abre este enlace para activar la cuenta. Caduca en 24 horas y sólo sirve una vez.',
                    base + '/auth/verificar?token=' + urllib.parse.quote(raw),
                )),
            )
            save_accounts()
        except ACC.AuthError as exc:
            save_accounts()
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True}, headers)
    if path == '/auth/reenviar' and method == 'POST':
        if not ACC.email_ready():
            return auth_response('503 Service Unavailable', {'error': 'El correo no está configurado.'}, headers)
        try:
            ACC.resend_verification(
                ACCOUNTS, payload.get('email'),
                lambda email, raw: ACC.send_message(email, 'Confirma tu cuenta de Saimon City', _texto_enlace(
                    'Este enlace nuevo sustituye al anterior. Caduca en 24 horas y sólo sirve una vez.',
                    base + '/auth/verificar?token=' + urllib.parse.quote(raw),
                )),
            )
            save_accounts()
        except ACC.AuthError as exc:
            save_accounts()
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True}, headers)
    if path == '/auth/olvide' and method == 'POST':
        if not ACC.email_ready():
            return auth_response('503 Service Unavailable', {'error': 'El correo no está configurado.'}, headers)
        try:
            ACC.request_password_reset(
                ACCOUNTS, payload.get('email'),
                lambda email, raw: ACC.send_message(email, 'Nueva contraseña de Saimon City', _texto_enlace(
                    'Abre este enlace para elegir una contraseña nueva. Caduca en 1 hora y sólo sirve una vez.',
                    base + '/auth/restablecer?token=' + urllib.parse.quote(raw),
                )),
            )
            save_accounts()
        except ACC.AuthError as exc:
            save_accounts()
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True}, headers)
    if path == '/auth/verificar' and method == 'GET':
        token = (query.get('token') or [''])[0]
        back = vuelta_pedida(query, cookie)
        fallo = '/play/?movil=1&auth=enlace' if back.endswith('movil=1') else '/play/?auth=enlace'
        try:
            result = ACC.confirm_email_link(ACCOUNTS, token)
            user = next(u for u in ACCOUNTS['users'] if u['id'] == result['user']['id'])
            link = urllib.parse.unquote(ACC.read_cookie(cookie, 'life_link'))
            link_name, _, link_token = link.partition('|')
            settle_wallet(user, link_name or user.get('name') or '', link_token)
            save_accounts()
            maybe_fuse()
        except ACC.AuthError:
            save_accounts()
            return redirect(fallo, headers, [])
        return redirect(back, headers, [ACC.cookie('life_session', result['token'], result['max_age'], secure)])
    if path == '/auth/restablecer' and method == 'GET':
        token = (query.get('token') or [''])[0]
        return auth_html('200 OK', _pagina_clave(token, ''), headers)
    if path == '/auth/restablecer' and method == 'POST':
        form = urllib.parse.parse_qs(body.decode('utf-8', 'replace') if body else '')
        token = (form.get('token') or [payload.get('token') if isinstance(payload, dict) else ''])[0]
        password = (form.get('password') or [payload.get('password') if isinstance(payload, dict) else ''])[0]
        try:
            ACC.reset_password(ACCOUNTS, token, password)
            save_accounts()
        except ACC.AuthError as exc:
            save_accounts()
            return auth_html('400 Bad Request', _pagina_clave(token, str(exc)), headers)
        return auth_html('200 OK', _pagina_clave('', '', done=True), headers)
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
    if path == '/auth/municipio' and method == 'POST':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para elegir tu casa.'}, headers)
        try:
            shown = ACC.set_municipio(ACCOUNTS, user, payload.get('municipio'))
            save_accounts()
        except ACC.AuthError as exc:
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        spot = HOGAR.stand(shown['municipio'])
        if shown.get('casa') and shown['casa'].get('pet'):
            CASA.mirror(VIDA, 'acct:' + user['id'], user)
            save_vida()
        return auth_response('200 OK', {'ok': True, 'user': shown, 'home': {'x': spot[0], 'y': spot[1], 'name': HOGAR.NOMBRES[shown['municipio']]}}, headers)
    if path == '/auth/lugar' and method == 'POST':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para elegir el lugar.'}, headers)
        try:
            shown = ACC.set_favorite_place(ACCOUNTS, user, payload.get('id'))
            save_accounts()
        except ACC.AuthError as exc:
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        import lugares as LUGARES
        item = LUGARES.get(shown.get('favoritePlace'))
        home = {'x': item['x'], 'y': item['y'], 'name': item['name'], 'id': item['id']} if item else None
        return auth_response('200 OK', {'ok': True, 'user': shown, 'home': home}, headers)
    if path == '/auth/casa' and method == 'GET':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para ver tu casa.'}, headers)
        return auth_response('200 OK', {'casa': CASA.view(user)}, headers)
    if path == '/auth/casa' and method == 'POST':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para guardar tu casa.'}, headers)
        try:
            shown = ACC.save_casa(user, payload, migrate=bool(payload.get('migrate')))
        except ACC.AuthError as exc:
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        CASA.mirror(VIDA, 'acct:' + user['id'], user)
        save_accounts()
        save_vida()
        return auth_response('200 OK', {'ok': True, 'user': shown, 'casa': shown['casa']}, headers)
    if path == '/auth/partida' and method == 'GET':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para recuperar la partida.'}, headers)
        return auth_response('200 OK', {'partida': GUARDADO.recall(user, ECON)}, headers)
    if path == '/auth/partida' and method == 'POST':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para guardar la partida.'}, headers)
        shown = GUARDADO.remember(user, payload if isinstance(payload, dict) else {}, ECON)
        CASA.mirror(VIDA, 'acct:' + user['id'], user)
        who = user.get('wallet_name') or user.get('name') or ''
        if who:
            before = PURSES.count(VAULT_STATE, who, 'gallo')
            after = GALLOS.sync_purse(VAULT_STATE, who, shown.get('gallos') or 0)
            if after != before:
                save_vault()
        save_accounts()
        save_vida()
        return auth_response('200 OK', {'ok': True, 'partida': shown}, headers)
    if path == '/auth/caballo' and method == 'GET':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para ver tu caballo.'}, headers)
        return auth_response('200 OK', {'caballo': CABALLO.view(user)}, headers)
    if path == '/auth/caballo' and method == 'POST':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para guardar el pelaje.'}, headers)
        try:
            shown = ACC.set_caballo(user, payload.get('coat'))
            save_accounts()
        except ACC.AuthError as exc:
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True, 'user': shown, 'caballo': shown['caballo']}, headers)
    if path == '/auth/salir' and method == 'POST':
        token = ACC.read_cookie(cookie, 'life_session')
        ACC.end_session(ACCOUNTS, token)
        save_accounts()
        return auth_response('200 OK', {'ok': True}, headers, ['Set-Cookie: ' + ACC.cookie('life_session', '', 0, secure)])
    if path == '/auth/salir-todos' and method == 'POST':
        token = ACC.read_cookie(cookie, 'life_session')
        user = ACC.session_user(ACCOUNTS, token)
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra otra vez.'}, headers)
        ACC.end_all_sessions(ACCOUNTS, user['id'])
        save_accounts()
        return auth_response('200 OK', {'ok': True}, headers, ['Set-Cookie: ' + ACC.cookie('life_session', '', 0, secure)])
    if path == '/auth/clave' and method == 'POST':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra otra vez.'}, headers)
        try:
            shown = ACC.change_password(ACCOUNTS, user, payload.get('current'), payload.get('password'))
            save_accounts()
        except ACC.AuthError as exc:
            save_accounts()
            return auth_response('400 Bad Request', {'error': str(exc)}, headers)
        return auth_response('200 OK', {'ok': True, 'user': shown}, headers)
    if path == '/auth/cuenta' and method == 'GET':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para verla.'}, headers)
        import mi_cuenta as MICUENTA
        body = MICUENTA.resumen(user, ECON, (FINCA_STATE.get('accounts') or {}), int(time.time() * 1000), VAULT_STATE)
        body['followable'] = SEGUIR.allow(user)
        social = SOCIAL.friend_view(VIDA, 'acct:' + str(user.get('id') or ''), ACCOUNTS, clients.values())
        body['amigos'] = social.get('friends') or []
        body['pedidos'] = social.get('in') or []
        return auth_response('200 OK', body, headers)
    if path == '/auth/seguir' and method == 'POST':
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(cookie, 'life_session'))
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para cambiar eso.'}, headers)
        user['followable'] = bool(payload.get('on', True))
        save_accounts()
        return auth_response('200 OK', {'ok': True, 'followable': SEGUIR.allow(user)}, headers)
    if path == '/auth/delete-account' and method == 'POST':
        token = ACC.read_cookie(cookie, 'life_session')
        user = ACC.session_user(ACCOUNTS, token)
        if not user:
            return auth_response('401 Unauthorized', {'error': 'Entra con tu cuenta para eliminarla.'}, headers)
        try:
            result = eliminar_cuenta_propia(user, payload.get('confirm'))
        except Exception:
            return auth_response('500 Internal Server Error', {'error': 'No se pudo eliminar la cuenta. No se cambió nada.'}, headers)
        if not result.get('ok'):
            return auth_response(result.get('status') or '400 Bad Request', {'error': result.get('error') or 'No se pudo eliminar la cuenta.'}, headers)
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
    simon_post = method == 'POST' and path.startswith('/api/simon')
    vida_post = method == 'POST' and path.startswith('/api/vida')
    world_post = method == 'POST' and path.startswith('/api/world-edits')
    if method == 'POST' and (path.startswith('/auth') or path in APARTMENT_API.AGENT_PATHS or simon_post or vida_post or world_post):
        try:
            cap = 1500000 if world_post else (80000 if simon_post or path in APARTMENT_API.AGENT_PATHS else 20000)
            length = min(int(headers.get('content-length') or 0), cap)
        except ValueError:
            length = 0
        if length:
            body = await reader.readexactly(length)
    if path.startswith('/api/apartamentos') or path in APARTMENT_API.AGENT_PATHS:
        # El rastreo nunca se ejecuta desde una petición pública ni bloquea el bucle del juego.
        result = await asyncio.to_thread(APARTMENT_API.dispatch, method, path, target, body)
        code, payload = result
        labels = {200: 'OK', 400: 'Bad Request', 404: 'Not Found', 405: 'Method Not Allowed', 503: 'Service Unavailable'}
        encoded = json.dumps(payload, ensure_ascii=False).encode()
        writer.write(f'HTTP/1.1 {code} {labels[code]}\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(encoded)}\r\nConnection: close\r\n\r\n'.encode())
        if method != 'HEAD':
            writer.write(encoded)
        await writer.drain(); writer.close(); return
    if path.startswith('/api/world-edits'):
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(headers.get('cookie', ''), 'life_session'))
        if method == 'GET':
            code, payload = 200, world_edit_packet(user)
        elif method == 'POST':
            try:
                message = json.loads(body.decode() or '{}')
            except Exception:
                message = {}
            result = world_edit_request(user, message if isinstance(message, dict) else {})
            code = int(result.get('code') or (200 if result.get('ok') else 400))
            payload = {'ok': result.get('ok'), 'code': code, 'error': result.get('error') or '',
                       'worldEdits': result.get('doc'), 'package': result.get('package')}
        else:
            code, payload = 405, {'ok': False, 'error': 'Método no permitido.'}
        labels = {200: 'OK', 400: 'Bad Request', 403: 'Forbidden', 404: 'Not Found', 405: 'Method Not Allowed', 409: 'Conflict'}
        encoded = json.dumps(payload, ensure_ascii=False).encode()
        writer.write(f'HTTP/1.1 {code} {labels.get(code, "OK")}\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(encoded)}\r\nConnection: close\r\n\r\n'.encode())
        if method != 'HEAD':
            writer.write(encoded)
        await writer.drain(); writer.close(); return
    if path.startswith('/api/simon'):
        result = await asyncio.to_thread(SIMON_API.dispatch, method, path, target, headers, body)
        code, payload, extra = result
        labels = {200: 'OK', 400: 'Bad Request', 403: 'Forbidden', 404: 'Not Found',
                  405: 'Method Not Allowed', 409: 'Conflict', 503: 'Service Unavailable'}
        encoded = json.dumps(payload, ensure_ascii=False).encode()
        cookie = ('Set-Cookie: ' + extra['Set-Cookie'] + '\r\n') if extra.get('Set-Cookie') else ''
        writer.write(f'HTTP/1.1 {code} {labels.get(code, "OK")}\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\n{cookie}Content-Length: {len(encoded)}\r\nConnection: close\r\n\r\n'.encode())
        if method != 'HEAD':
            writer.write(encoded)
        await writer.drain(); writer.close(); return
    if path == '/api/mundos' or path.startswith('/api/vida'):
        result = VIDA_API.dispatch(method, path, headers, body, {'state': VIDA, 'clients': clients, 'save': save_vida})
        if result is not None:
            code, payload = result
            labels = {200: 'OK', 400: 'Bad Request', 403: 'Forbidden', 404: 'Not Found'}
            encoded = json.dumps(payload, ensure_ascii=False).encode()
            writer.write(f'HTTP/1.1 {code} {labels.get(code, "OK")}\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(encoded)}\r\nConnection: close\r\n\r\n'.encode())
            if method != 'HEAD':
                writer.write(encoded)
            await writer.drain(); writer.close(); return
    answered = await try_auth(method, path, target, headers, body, client_ip(headers, writer))
    if answered is not None:
        writer.write(answered)
        await writer.drain(); writer.close(); return
    if path.rstrip('/') == '/ws' and headers.get('upgrade', '').lower() == 'websocket':
        key = headers.get('sec-websocket-key', '')
        acc = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        writer.write(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                      f'Sec-WebSocket-Accept: {acc}\r\n\r\n').encode())
        await writer.drain()
        return await handle_ws(reader, writer, headers.get('cookie', ''), client_ip(headers, writer))
    if path in ('/healthz', '/healthz/') and method in ('GET', 'HEAD'):
        body = b'ok'
        writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: 2\r\nConnection: close\r\n\r\n')
        if method == 'GET': writer.write(body)
        await writer.drain(); writer.close(); return
    if path in ('/health', '/health/') and method in ('GET', 'HEAD'):
        body = json.dumps(health_payload()).encode()
        writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
        if method == 'GET': writer.write(body)
        await writer.drain(); writer.close(); return
    if path == '/favicon.ico' and method in ('GET', 'HEAD'):
        path = '/graphics/ui/saimon-logo-gold.png'
    if path in ('/releases/saimoncity-fuente.zip', '/releases/saimoncity-fuente.zip/'):
        archive = os.path.join(ROOT, 'releases', 'saimoncity-fuente.zip')
        if not os.path.isfile(archive):
            # El zip no va en git. La fuente correspondiente de la AGPL está en el repositorio público.
            loc = 'https://github.com/Saimonmde/LIFE'
            writer.write(f'HTTP/1.1 302 Found\r\nLocation: {loc}\r\nCache-Control: no-store\r\nContent-Length: 0\r\nConnection: close\r\n\r\n'.encode())
            await writer.drain(); writer.close(); return
    if path in ('/api/reloj', '/api/reloj/') and method in ('GET', 'HEAD'):
        body = json.dumps(RELOJ.payload(ECON), ensure_ascii=False).encode()
        writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
        if method == 'GET': writer.write(body)
        await writer.drain(); writer.close(); return
    if path in ('/api/contadores', '/api/contadores/', '/api/finca', '/api/finca/') and method in ('GET', 'HEAD'):
        body = json.dumps(public_counters(), ensure_ascii=False).encode()
        writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
        if method == 'GET': writer.write(body)
        await writer.drain(); writer.close(); return
    if path in ('/api/finca/privado', '/api/finca/privado/') and method in ('GET', 'HEAD'):
        user = ACC.session_user(ACCOUNTS, ACC.read_cookie(headers.get('cookie', ''), 'life_session')) or {}
        if not FINCA.can_see_private(user.get('email'), user.get('role')):
            body = '{"error":"solo el dueno o cumplimiento"}'.encode()
            writer.write(f'HTTP/1.1 403 Forbidden\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
            if method == 'GET': writer.write(body)
            await writer.drain(); writer.close(); return
        body = json.dumps(FINCA.private_payload(FINCA_STATE), ensure_ascii=False).encode()
        writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
        if method == 'GET': writer.write(body)
        await writer.drain(); writer.close(); return
    if path == '/reglas-mina' and method in ('GET', 'HEAD'):
        body = json.dumps(_reglas_mina(headers), ensure_ascii=False).encode()
        writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
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
        if full.endswith(os.sep + 'play' + os.sep + 'index.html') or full.endswith('/play/index.html'):
            rev = os.environ.get('RENDER_GIT_COMMIT') or ''
            html = body.decode('utf-8')
            if 'name="life-revision"' not in html:
                html = html.replace('<head>', '<head>\n<meta name="life-revision" content="' + rev + '">', 1)
            body = html.encode('utf-8')
        if ctype.startswith('text/') or ctype in ('application/javascript', 'application/json'): ctype += '; charset=utf-8'
        cache = 'no-store' if ctype.startswith('text/html') else 'no-cache'
        writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: {ctype}\r\nContent-Length: {len(body)}\r\nCache-Control: {cache}\r\nConnection: close\r\n\r\n'.encode())
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
        # Otra red puede llegar por IPv6. Si el puerto ya quedó tomado, se avisa y sigue IPv4.
        if a.host == '0.0.0.0':
            hosts.append('::')
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
