# SPDX-License-Identifier: AGPL-3.0-or-later
"""Amigos, chat moderado, feedback y el poste del Parque de Envigado.

Los papeles son player, staff, admin y simon. Hoy sólo simon responde el poste
y lee el feedback. staff y admin existen para sumarlos después sin cambiar el esquema.
El cambio de nick queda marcado como acción de pago: la red no cobra ni renombra.
"""
import hmac
import os
import re
import time
import unicodedata

import accounts as ACC
import mascotas
import muebles
import mundos

ROLES = ('player', 'staff', 'admin', 'simon')
# Hoy estas acciones piden el papel simon. Mañana se agrega 'admin' o 'staff' a la tupla.
ACTIONS = {
    'see_feedback': ('simon',),
    'answer_note': ('simon',),
    'hide_note': ('simon',),
    'close_poll': ('simon',),
}
_BANNED = (
    'puta', 'puto', 'mierda', 'gonorrea', 'hijueputa', 'malparido',
    'fuck', 'shit', 'bitch',
)
_BANNED_RX = re.compile(r'\b(?:' + '|'.join(_BANNED) + r')\b')


def empty():
    return {'v': 1, 'pets': {}, 'homes': {}, 'friends': {}, 'dms': {}, 'feedback': [], 'notes': [], 'polls': []}


def normalize(doc):
    base = empty()
    if not isinstance(doc, dict):
        return base
    for key in base:
        if key == 'v':
            continue
        value = doc.get(key)
        if isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = value
        elif isinstance(base[key], list) and isinstance(value, list):
            base[key] = value
    return base


def limits():
    raw = mundos.catalog().get('limits') or {}
    return {
        'chat': int(raw.get('chat') or 160),
        'note': int(raw.get('note') or 240),
        'feedback': int(raw.get('feedback') or 400),
        'pollQuestion': int(raw.get('pollQuestion') or 80),
        'pollOption': int(raw.get('pollOption') or 24),
        'nick': int(raw.get('nick') or 16),
    }


def _fold(text):
    text = unicodedata.normalize('NFKD', str(text or '').casefold())
    return ''.join(ch for ch in text if not unicodedata.combining(ch))


def mask(text, limit):
    """Recorta y tapa palabrotas. No rechaza el mensaje entero."""
    cleaned = re.sub(r'[\x00-\x1f\x7f<>]', '', str(text or '')).strip()
    cleaned = cleaned[: int(limit)]
    parts = re.split(r'(\s+)', cleaned)
    masked = []
    for part in parts:
        if part and _BANNED_RX.search(_fold(part)):
            masked.append('···')
        else:
            masked.append(part)
    return ''.join(masked).strip()


def allow(stamps, now, burst, window):
    now = float(now)
    stamps[:] = [stamp for stamp in stamps if now - stamp < window]
    if len(stamps) >= burst:
        return False
    stamps.append(now)
    return True


def identity_of(client):
    user = getattr(client, 'user', None)
    if user and user.get('id'):
        return 'acct:' + str(user['id'])
    nick = getattr(client, 'name', '') or 'viajero'
    return 'guest:' + (ACC.name_key(nick) or 'viajero')


def visible_account_nick(user):
    email = str(user.get('email') or '').strip().lower()
    wallet = str(user.get('wallet_name') or '').strip()
    if wallet and '@' not in wallet and wallet.lower() != email:
        return ACC.game_name(wallet) or 'Viajero'
    return ACC.game_name(user.get('name') or '') or 'Viajero'


def find_account(doc, nick):
    key = ACC.name_key(nick)
    if not key or not isinstance(doc, dict):
        return None
    for user in doc.get('users') or []:
        keys = {
            ACC.name_key(user.get('name')),
            ACC.name_key(user.get('wallet_name')),
            ACC.name_key(visible_account_nick(user)),
        }
        if key in keys:
            return user
    return None


def _bucket(state, key):
    box = state['friends'].setdefault(key, {'friends': [], 'in': [], 'out': []})
    for field in ('friends', 'in', 'out'):
        box.setdefault(field, [])
    return box


def search_nick(doc, nick, online_keys):
    user = find_account(doc, nick)
    if not user:
        return None
    key = 'acct:' + str(user['id'])
    return {'key': key, 'nick': visible_account_nick(user), 'online': key in set(online_keys or [])}


def request_friend(state, me, other_key):
    if not other_key or other_key == me or not str(other_key).startswith('acct:'):
        return {'ok': False, 'error': 'Ese nick no es una cuenta.'}
    mine = _bucket(state, me)
    theirs = _bucket(state, other_key)
    if other_key in mine['friends']:
        return {'ok': True, 'status': 'amigos'}
    if other_key in mine['in']:
        mine['in'].remove(other_key)
        theirs['out'] = [item for item in theirs['out'] if item != me]
        if other_key not in mine['friends']:
            mine['friends'].append(other_key)
        if me not in theirs['friends']:
            theirs['friends'].append(me)
        return {'ok': True, 'status': 'amigos'}
    if other_key not in mine['out']:
        mine['out'].append(other_key)
    if me not in theirs['in']:
        theirs['in'].append(me)
    return {'ok': True, 'status': 'pedido'}


def accept_friend(state, me, other_key):
    mine = _bucket(state, me)
    if other_key not in mine['in']:
        return {'ok': False, 'error': 'No hay un pedido de esa cuenta.'}
    return request_friend(state, me, other_key)


def are_friends(state, a, b):
    return b in _bucket(state, a)['friends']


def quote_nick(doc, user, new_name):
    """No cambia el nick. Si está libre, deja el gancho de pago."""
    if not user:
        return {'ok': False, 'changed': False, 'payment_required': False, 'error': 'Entra con tu cuenta para reservar un nick.'}
    name = ACC.game_name(new_name)
    if not name or len(name) < 3:
        return {'ok': False, 'changed': False, 'payment_required': False, 'error': 'El nick necesita al menos 3 letras.'}
    if ACC.name_key(name) in {ACC.name_key(user.get('name')), ACC.name_key(user.get('wallet_name'))}:
        return {'ok': False, 'changed': False, 'payment_required': False, 'error': 'Ese ya es tu nick.'}
    if not ACC.name_available(doc, name, user_id=user.get('id')):
        return {'ok': False, 'changed': False, 'payment_required': False, 'error': 'Ese nick ya pertenece a otra cuenta.'}
    return {
        'ok': False,
        'changed': False,
        'payment_required': True,
        'flag': 'nick_change_paid',
        'name': name,
        'note': 'El cambio de nick queda apartado como acción de pago. Todavía no hay cobro y el nombre no cambia.',
    }


def grant_paid_nick(doc, user, new_name):
    """Gancho para un cobro futuro. La red del juego no lo llama ni marca el flag."""
    if not user or not user.get('nick_change_paid'):
        return {'ok': False, 'changed': False, 'payment_required': True, 'flag': 'nick_change_paid'}
    quoted = quote_nick(doc, user, new_name)
    if quoted.get('error'):
        return quoted
    name = quoted['name']
    old = ACC.name_key(user.get('name'))
    wallet = ACC.name_key(user.get('wallet_name'))
    user['name'] = name
    if not user.get('wallet_name') or wallet == old:
        user['wallet_name'] = name
    user['nick_change_paid'] = False
    return {'ok': True, 'changed': True, 'payment_required': False, 'name': name}


def admin_ok(header):
    expected = os.environ.get('SIMON_ADMIN_TOKEN', '').strip()
    got = str(header or '')
    if not expected or len(got) != len(expected):
        return False
    return hmac.compare_digest(got, expected)


def role_of(user, admin_header=''):
    if admin_ok(admin_header):
        return 'simon'
    if not user:
        return 'player'
    owner = os.environ.get('SIMON_OWNER_EMAIL', '').strip().lower()
    email = str(user.get('email') or '').strip().lower()
    if owner and email and email == owner:
        return 'simon'
    role = user.get('role') or 'player'
    if role not in ROLES:
        return 'player'
    return role


def allows(role, action):
    return role in ACTIONS.get(action, ())


def pet_for(state, key):
    pet = (state.get('pets') or {}).get(key)
    return dict(pet) if isinstance(pet, dict) else None


def save_pet(state, key, raw):
    pet = mascotas.validate(raw)
    if not pet:
        return None
    state['pets'][key] = pet
    return dict(pet)


def home_for(state, key):
    raw = (state.get('homes') or {}).get(key)
    if not isinstance(raw, dict):
        return None
    return muebles.sanitize(raw)


def save_home(state, key, raw):
    layout = muebles.sanitize(raw)
    state['homes'][key] = layout
    return layout


def _online_map(clients):
    found = {}
    for client in clients or []:
        if not getattr(client, 'hello', False) or getattr(client, 'bot', False):
            continue
        key = getattr(client, 'identity', '') or identity_of(client)
        found[key] = client
    return found


def friend_view(state, me, doc, clients):
    online = _online_map(clients)
    box = _bucket(state, me)

    def row(key):
        user = None
        if key.startswith('acct:'):
            ident = key.split(':', 1)[1]
            user = next((item for item in (doc or {}).get('users') or [] if item.get('id') == ident), None)
        nick = visible_account_nick(user) if user else key
        return {'key': key, 'nick': nick, 'online': key in online}

    return {
        'friends': [row(key) for key in box['friends']],
        'in': [row(key) for key in box['in']],
        'out': [row(key) for key in box['out']],
    }


def remember_dm(state, a, b, message):
    pair = '|'.join(sorted((a, b)))
    thread = state['dms'].setdefault(pair, [])
    thread.append(message)
    if len(thread) > 30:
        del thread[:-30]
    return thread


def private_message(state, sender_key, sender_nick, target_nick, text, doc, now=None):
    user = find_account(doc, target_nick)
    if not user:
        return {'ok': False, 'error': 'No hay una cuenta con ese nick.'}
    target = 'acct:' + str(user['id'])
    if not are_friends(state, sender_key, target):
        return {'ok': False, 'error': 'El chat privado es sólo entre amigos.'}
    body = mask(text, limits()['chat'])
    if not body:
        return {'ok': False, 'error': 'El mensaje quedó vacío.'}
    now = int(now if now is not None else time.time())
    message = {
        't': 'chat',
        'channel': 'privado',
        'from': sender_nick,
        'fromKey': sender_key,
        'to': visible_account_nick(user),
        'toKey': target,
        'text': body,
        'ts': time.strftime('%H:%M', time.localtime(now)),
    }
    remember_dm(state, sender_key, target, message)
    return {'ok': True, 'message': message, 'targets': [sender_key, target]}


def add_feedback(state, nick, text, world, place, now=None):
    body = mask(text, limits()['feedback'])
    if len(body) < 4:
        return {'ok': False, 'error': 'Cuéntanos un poco más.'}
    now = int(now if now is not None else time.time())
    row = {
        'id': f'fb{now % 100000000:08d}{len(state["feedback"]):03d}',
        'nick': nick or 'Viajero',
        'text': body,
        'world': world,
        'place': place,
        'ts': now,
    }
    state['feedback'].append(row)
    if len(state['feedback']) > 500:
        del state['feedback'][:-500]
    return {'ok': True, 'feedback': {k: row[k] for k in ('id', 'ts')}}


def public_notes(state):
    notes = []
    for row in state.get('notes') or []:
        if row.get('hidden'):
            continue
        notes.append({k: row.get(k) for k in ('id', 'nick', 'text', 'place', 'world', 'ts', 'answer')})
    polls = []
    for row in state.get('polls') or []:
        if row.get('hidden'):
            continue
        votes = row.get('votes') or {}
        counts = []
        for option in row.get('options') or []:
            counts.append({'id': option['id'], 'text': option['text'], 'votes': sum(1 for pick in votes.values() if pick == option['id'])})
        polls.append({
            'id': row.get('id'), 'nick': row.get('nick'), 'question': row.get('question'),
            'options': counts, 'closed': bool(row.get('closed')), 'answer': row.get('answer') or '',
            'ts': row.get('ts'), 'voters': len(votes),
        })
    return {'notes': notes[-80:], 'polls': polls[-40:]}


def add_note(state, nick, key, text, place, world, now=None):
    body = mask(text, limits()['note'])
    if len(body) < 4:
        return {'ok': False, 'error': 'La nota es muy corta.'}
    now = int(now if now is not None else time.time())
    row = {
        'id': f'n{now % 100000000:08d}{len(state["notes"]):03d}',
        'nick': nick or 'Viajero', 'key': key, 'text': body,
        'place': place, 'world': world, 'ts': now, 'hidden': False, 'answer': '',
    }
    state['notes'].append(row)
    if len(state['notes']) > 200:
        del state['notes'][:-200]
    return {'ok': True, 'board': public_notes(state)}


def add_poll(state, nick, key, question, options, place, world, now=None):
    cap = limits()
    title = mask(question, cap['pollQuestion'])
    clean = []
    for raw in options or []:
        text = mask(raw, cap['pollOption'])
        if text and text not in clean:
            clean.append(text)
    if len(title) < 4 or not 2 <= len(clean) <= 4:
        return {'ok': False, 'error': 'La encuesta necesita una pregunta y de 2 a 4 opciones.'}
    now = int(now if now is not None else time.time())
    row = {
        'id': f'p{now % 100000000:08d}{len(state["polls"]):03d}',
        'nick': nick or 'Viajero', 'key': key, 'question': title,
        'options': [{'id': f'o{i}', 'text': text} for i, text in enumerate(clean)],
        'votes': {}, 'closed': False, 'hidden': False, 'answer': '',
        'place': place, 'world': world, 'ts': now,
    }
    state['polls'].append(row)
    return {'ok': True, 'board': public_notes(state)}


def vote_poll(state, key, poll_id, option_id):
    row = next((item for item in state.get('polls') or [] if item.get('id') == poll_id and not item.get('hidden')), None)
    if not row or row.get('closed'):
        return {'ok': False, 'error': 'Esa encuesta no recibe votos.'}
    if option_id not in {option['id'] for option in row.get('options') or []}:
        return {'ok': False, 'error': 'Esa opción no existe.'}
    row.setdefault('votes', {})[key] = option_id
    return {'ok': True, 'board': public_notes(state)}


def moderate(state, role, kind, ident, action, text=''):
    if kind == 'note' and action == 'answer' and not allows(role, 'answer_note'):
        return {'ok': False, 'error': 'Por ahora sólo la cuenta principal de Simon responde el poste.'}
    if kind == 'note' and action == 'hide' and not allows(role, 'hide_note'):
        return {'ok': False, 'error': 'Por ahora sólo la cuenta principal de Simon modera el poste.'}
    if kind == 'poll' and action in ('answer', 'close', 'hide') and not allows(role, 'close_poll' if action == 'close' else 'answer_note' if action == 'answer' else 'hide_note'):
        return {'ok': False, 'error': 'Por ahora sólo la cuenta principal de Simon modera el poste.'}
    pile = state['notes'] if kind == 'note' else state['polls']
    row = next((item for item in pile if item.get('id') == ident), None)
    if not row:
        return {'ok': False, 'error': 'No está en el poste.'}
    if action == 'hide':
        row['hidden'] = True
    elif action == 'close' and kind == 'poll':
        row['closed'] = True
    elif action == 'answer':
        reply = mask(text, limits()['note'])
        if len(reply) < 2:
            return {'ok': False, 'error': 'La respuesta es muy corta.'}
        row['answer'] = reply
    else:
        return {'ok': False, 'error': 'Esa acción no existe.'}
    return {'ok': True, 'board': public_notes(state)}


def thread_for(state, a, b):
    pair = '|'.join(sorted((a, b)))
    return list(state.get('dms', {}).get(pair) or [])


def hello_extra(state, client, doc, clients, boxes):
    key = getattr(client, 'identity', '') or identity_of(client)
    presence = mundos.counts(clients.values() if hasattr(clients, 'values') else clients)
    world = getattr(client, 'world', 1)
    return {
        'role': role_of(getattr(client, 'user', None)),
        'pet': pet_for(state, key),
        'home': home_for(state, key),
        'social': friend_view(state, key, doc, clients.values() if hasattr(clients, 'values') else clients),
        'presence': presence,
        'placeName': mundos.place_name(getattr(client, 'place', 'valle'), boxes),
        'worldName': f'Mundo {world}',
        'dms': {},
    }
