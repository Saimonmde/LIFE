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
import ed25519
import libro as LIBRO
import nft as NFT
import payout as PAYOUT
import playtime as PLAY
import vault as VAULT
import accounts as ACC

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
QUEST_GRANTS = {'primeros_pasos': 250}

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

def econ_msg(who=None, before=None, reveal_token=None, locked=False):
    page = block_page(before)
    m = {'t': 'economy', 'state': {
        'minedSmh': int(ECON.get('minedSmh') or 0), 'blocks': page, 'blockCount': len(ECON.get('blocks') or []),
        'mempool': ECON.get('mempool', []), 'disclaimer': (ECON.get('disclaimer') or '') + RESET_NOTE,
        'ledgerResets': True, 'symbol': 'SMC', 'symbolBase': 'SMH', 'unit': 'SaiMonCoin',
        'smallestName': 'Simonchi', 'subunitsPerUnit': ECO.SUBS, 'maxSupply': ECO.MAX_SUPPLY,
        'maxSupplySmh': ECO.MAX_SMH,
    }}
    if who:
        m['balanceSubs'] = 0 if locked else int((ECON.get('wallets') or {}).get(who) or 0)
        m['walletLocked'] = bool(locked)
    if reveal_token:
        m['walletToken'] = reveal_token
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

def mint_for(sender, node_id):
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
    if now - getattr(sender, 'last_mint', 0) < 1:
        return send(sender, {'t': 'system', 'text': 'Espera un momento para volver a batear.'})
    sender.last_mint = now
    bind_wallet(sender.name, getattr(sender, 'wallet_token', ''))
    reward = min(ECO.reward_smh(ECON.get('minedSmh') or 0), LIBRO.cupo_subs(LIBRO_CHAIN))
    if reward <= 0:
        return send(sender, {'t': 'system', 'text': 'Se alcanzó el tope minable de SMC.'})
    NODE_READY[node['id']] = now + (float(node.get('respawnMs') or 30000) / 1000.0)
    granted = ECO.issue(ECON, sender.name, reward, 'Emisión por bateada de oro fluvial', 'mint')
    if granted <= 0:
        return send(sender, {'t': 'system', 'text': 'Se alcanzó el tope minable de SMC.'})
    lugar = river_label(node)
    libro_pub = anotar_emision(sender.name, granted, lugar)
    if not libro_pub:
        ECO.debit(ECON, sender.name, granted)
        ECON['minedSmh'] = int(ECON.get('minedSmh') or 0) - granted
        mem = ECON.get('mempool') or []
        if mem and int(mem[-1].get('amountSubs') or 0) == granted:
            mem.pop()
        return send(sender, {'t': 'system', 'text': 'Se alcanzó el tope minable de SMC.'})
    save_econ()
    token = certify(sender.name, granted, 'rio', f"{node['x']},{node['y']}")
    broadcast_econ()
    send(sender, {'t': 'system', 'text': f'Se acuñaron {ECO.format_pair(granted)}. Es una simulación: no es dinero real.'})
    send(sender, {'t': 'issued', 'amountSmh': granted, 'amountText': ECO.format_pair(granted), 'kind': 'mint', 'certificate': token, 'libro': libro_pub})

def wallet_ready(sender):
    if not getattr(sender, 'wallet_ok', False):
        send(sender, {'t': 'system', 'text': 'Esta billetera SMC se creó en otro aparato. Puedes jugar, pero no mover esas monedas.'})
        return False
    bind_wallet(sender.name, getattr(sender, 'wallet_token', ''))
    return True

def smelt_for(sender, ore, batches):
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
    now = time.time()
    if now - getattr(sender, 'last_smelt', 0) < 1:
        return send(sender, {'t': 'smelt_result', 'ok': False, 'reason': 'Espera un momento para volver a fundir.'})
    sender.last_smelt = now
    _ore, coins = recipe
    granted = ECO.issue(ECON, sender.name, ECO.smc_to_smh(coins * batches), f'Fundición de {ore} en la cantera', 'fundicion')
    libro_pub = anotar_emision(sender.name, granted, 'Fundidora de la cantera') if granted else None
    save_econ()
    token = certify(sender.name, granted, 'fundidora', 'horno_cantera') if granted else None
    broadcast_econ()
    if granted <= 0:
        return send(sender, {'t': 'smelt_result', 'ok': False, 'reason': 'Se alcanzó el tope de 21.000.000 SMC.', 'grantedSmh': 0})
    send(sender, {'t': 'smelt_result', 'ok': True, 'grantedSmh': granted, 'amountText': ECO.format_pair(granted), 'ore': ore, 'batches': batches, 'certificate': token, 'libro': libro_pub})
    send(sender, {'t': 'system', 'text': f'La fundidora acreditó {ECO.format_pair(granted)} a tu billetera. No hace falta reclamarlas.'})

def swing_for(sender, mineral):
    mineral = str(mineral or '')
    if mineral not in ('cobre', 'plata') or getattr(sender, 'zone', '') != 'mine':
        return
    if not wallet_ready(sender):
        return
    now = time.time()
    if now - getattr(sender, 'last_swing', 0) < 1:
        return
    sender.last_swing = now
    sender.swings = getattr(sender, 'swings', 0) + 1
    left = SHIFT_SWINGS - sender.swings
    if sender.swings < SHIFT_SWINGS:
        return send(sender, {'t': 'shift', 'swings': sender.swings, 'need': SHIFT_SWINGS, 'left': left})
    sender.swings = 0
    granted = ECO.issue(ECON, sender.name, ECO.smc_to_smh(SHIFT_PAY), 'Turno del capataz en la cantera (cobre o plata)', 'mina')
    if granted:
        anotar_emision(sender.name, granted, 'Cantera · turno')
    save_econ()
    token = certify(sender.name, granted, 'mina', 'cantera') if granted else None
    broadcast_econ()
    try:
        PAYOUT.ADAPTER.payout(sender.name, granted, 'USDT')
    except RuntimeError:
        pass
    send(sender, {'t': 'shift', 'swings': 0, 'need': SHIFT_SWINGS, 'paidSmh': granted, 'amountText': ECO.format_pair(granted), 'certificate': token,
                  'note': 'El turno paga SMC del juego. No hay retiro a OnePay ni a USDT. SMC no tiene valor real.'})

def migrate_for(sender, amount):
    if not wallet_ready(sender):
        return send(sender, {'t': 'migrate_result', 'ok': False})
    try:
        if isinstance(amount, str):
            amount = ECO.parse_amount(amount) // ECO.SUBS
    except (TypeError, ValueError, ECO.AmountError):
        amount = 0
    result = ECO.migrate_monedas(ECON, sender.name, amount or 0)
    if result['credited']:
        anotar_emision(sender.name, result['credited'], 'Conversión de monedas antiguas')
    save_econ()
    token = certify(sender.name, result['credited'], 'migracion', 'jardin') if result['credited'] else None
    broadcast_econ()
    send(sender, {'t': 'migrate_result', 'ok': True, 'rate': result['rate'], 'credited': result['credited'],
                  'already': result['already'], 'certificate': token,
                  'note': '1 moneda antigua del Jardín = 1 SMC. El SAI ya guardado sigue 1:1 y no se vuelve a convertir.'})

def quest_for(sender, quest_id):
    amount = QUEST_GRANTS.get(str(quest_id or ''))
    if not amount or not wallet_ready(sender):
        return
    done = ECON.setdefault('questGrants', {})
    if sender.name in done:
        return send(sender, {'t': 'quest_result', 'ok': True, 'already': True, 'amount': 0})
    smh = ECO.smc_to_smh(amount)
    if not ECO.debit(ECON, 'tesoro_genesis', smh):
        return send(sender, {'t': 'quest_result', 'ok': False, 'reason': 'La reserva de misiones no alcanza.'})
    ECO.credit(ECON, sender.name, smh)
    ECO.append_tx(ECON, {'type': 'grant', 'from': 'tesoro_genesis', 'to': sender.name, 'amountSubs': smh, 'note': 'Primeros Pasos'})
    try:
        anotar_pase('tesoro_genesis', sender.name, smh, 'Primeros Pasos')
    except (LIBRO.LibroError, persist_duplicate):
        pass
    done[sender.name] = str(quest_id)
    save_econ()
    broadcast_econ()
    send(sender, {'t': 'quest_result', 'ok': True, 'already': False, 'amount': amount})

def vault_for(sender):
    if not wallet_ready(sender):
        return
    box = VAULT.account(VAULT_STATE, sender.name)
    send(sender, {'t': 'vault', 'account': VAULT.public_account(box),
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
        return {'id': self.id, 'name': self.name, 'color': self.color, 'clan': self.clan, 'group': self.group,
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
            send(c, econ_msg(c.name, locked=not getattr(c, 'wallet_ok', False)))

def dist(a, b):
    if a is b: return 0
    if getattr(a, 'zone', 'city') == 'casa' or getattr(b, 'zone', 'city') == 'casa': return 1e9
    return max(abs(a.x - b.x), abs(a.y - b.y))

def unique_name(name, me):
    base = name or f'Jugador{me.id}'; n = base; k = 2
    while any(c is not me and c.name.lower() == n.lower() for c in clients.values()): n = f'{base}{k}'; k += 1
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

async def handle_ws(reader, writer, cookie=''):
    c = Client(writer); clients[c.id] = c
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
                send(c, econ_msg(c.name, reveal_token=owned, locked=not c.wallet_ok))
                if c.wallet_ok:
                    send(c, {'t': 'playtime', **play_for(c.name, active=True)})
                if not c.wallet_ok:
                    send(c, {'t': 'system', 'text': 'Ese nombre ya tiene una billetera SMC en otro aparato. Puedes entrar, pero no gastar ni emitir esas monedas.'})
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
                    c.x = max(0.0, min(WORLD['width'] - 1.0, float(m['x']))); c.y = max(0.0, min(WORLD['height'] - 1.0, float(m['y'])))
                except Exception: continue
                c.dir = m.get('dir') if m.get('dir') in ('up', 'down', 'left', 'right') else c.dir
                c.moving = bool(m.get('moving')); c.level = int(m.get('level') or c.level)
                if was_casa: broadcast({'t': 'join', 'player': c.public()}, exclude=c)
                else: broadcast({'t': 'move', 'id': c.id, 'x': round(c.x, 2), 'y': round(c.y, 2), 'dir': c.dir, 'moving': c.moving, 'level': c.level, 'zone': 'city'}, exclude=c)
            elif t == 'ping':
                send(c, {'t': 'pong', 'c': m.get('c')})
            elif t == 'chat' and c.hello:
                chat(c, str(m.get('channel', 'proximidad')).lower(), m.get('text'))
            elif t == 'mint' and c.hello:
                mint_for(c, clean(m.get('node'), 40))
            elif t == 'ledger' and c.hello:
                try:
                    before = int(m.get('before'))
                except (TypeError, ValueError):
                    before = None
                send(c, econ_msg(c.name, before=before, locked=not c.wallet_ok))
            elif t == 'pay' and c.hello:
                try:
                    smh = leer_smh(m)
                except (TypeError, ValueError, ECO.AmountError):
                    continue
                pagar(c, m.get('to'), smh, clean(m.get('note') or 'Pago', 80) or 'Pago')
            elif t == 'smelt' and c.hello:
                smelt_for(c, m.get('ore'), m.get('batches'))
            elif t == 'swing' and c.hello:
                swing_for(c, m.get('mineral'))
            elif t == 'migrate' and c.hello:
                migrate_for(c, m.get('amount'))
            elif t == 'quest' and c.hello:
                quest_for(c, m.get('id'))
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


async def try_auth(method, path, target, headers, body):
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
    if path == '/auth/google' and method == 'GET':
        if not ACC.providers()['google']:
            return auth_response('404 Not Found', {'error': 'Google no está configurado.'}, headers)
        state = ACC.start_oauth(ACCOUNTS, 'google')
        save_accounts()
        loc = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
            'client_id': os.environ['GOOGLE_CLIENT_ID'], 'redirect_uri': base + '/auth/google/callback',
            'response_type': 'code', 'scope': 'openid email profile', 'state': state,
        })
        return redirect(loc, headers, [ACC.cookie('oauth_state', state, 600, secure)])
    if path == '/auth/facebook' and method == 'GET':
        if not ACC.providers()['facebook']:
            return auth_response('404 Not Found', {'error': 'Facebook no está configurado.'}, headers)
        state = ACC.start_oauth(ACCOUNTS, 'facebook')
        save_accounts()
        loc = 'https://www.facebook.com/v19.0/dialog/oauth?' + urllib.parse.urlencode({
            'client_id': os.environ['FACEBOOK_APP_ID'], 'redirect_uri': base + '/auth/facebook/callback',
            'state': state, 'scope': 'email',
        })
        return redirect(loc, headers, [ACC.cookie('oauth_state', state, 600, secure)])
    if path in ('/auth/google/callback', '/auth/facebook/callback') and method == 'GET':
        provider = 'google' if 'google' in path else 'facebook'
        state = (query.get('state') or [''])[0]
        code = (query.get('code') or [''])[0]
        try:
            profile = ACC.exchange_google(code, base + '/auth/google/callback') if provider == 'google' else ACC.exchange_facebook(code, base + '/auth/facebook/callback')
            result = ACC.finish_oauth(ACCOUNTS, provider, state, ACC.read_cookie(cookie, 'oauth_state'), profile)
            user = next(u for u in ACCOUNTS['users'] if u['id'] == result['user']['id'])
            link = urllib.parse.unquote(ACC.read_cookie(cookie, 'life_link'))
            link_name, _, link_token = link.partition('|')
            settle_wallet(user, link_name, link_token)
            save_accounts()
        except ACC.AuthError as exc:
            return redirect('/play/?auth=error', headers, [])
        return redirect('/play/', headers, [ACC.cookie('life_session', result['token'], result['max_age'], secure), ACC.cookie('oauth_state', '', 0, secure)])
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
    answered = await try_auth(method, path, target, headers, body)
    if answered is not None:
        writer.write(answered)
        await writer.drain(); writer.close(); return
    if path == '/ws' and headers.get('upgrade', '').lower() == 'websocket':
        key = headers.get('sec-websocket-key', '')
        acc = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        writer.write(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                      f'Sec-WebSocket-Accept: {acc}\r\n\r\n').encode())
        await writer.drain()
        return await handle_ws(reader, writer, headers.get('cookie', ''))
    if path == '/healthz' and method in ('GET', 'HEAD'):
        body = b'ok'
        writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: 2\r\nConnection: close\r\n\r\n')
        if method == 'GET': writer.write(body)
        await writer.drain(); writer.close(); return
    if path == '/session.json' and method in ('GET', 'HEAD'):
        body = json.dumps({'serverId': SERVER_ID, 'worldBuild': WORLD.get('build'),
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
