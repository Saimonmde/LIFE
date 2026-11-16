# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cuentas: Google, Facebook o correo + teléfono. Sin proveedores, el nombre libre sigue valiendo.

Las contraseñas salen con hashlib.scrypt. Los códigos caducan. La sesión es una
cookie httpOnly. El estado vive en el mismo almacén que el resto (Postgres o JSON).
"""
import hashlib
import os
import re
import secrets
import smtplib
import time
import unicodedata
import urllib.parse
import urllib.request
from email.message import EmailMessage

CODE_TTL = 600
LINK_TTL = 60 * 60 * 24
RESET_TTL = 60 * 60
SESSION_TTL = 60 * 60 * 24 * 30
OTP_PER_HOUR = 5
MAX_ATTEMPTS = 5
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PHONE_RE = re.compile(r'^\+[1-9][0-9]{7,14}$')


class AuthError(Exception):
    pass


def empty():
    return {'users': [], 'sessions': {}, 'pending': {}, 'states': {}, 'rates': {}, 'resets': {}}


def load(path):
    import persist
    doc = persist.load_named('accounts', path)
    if not isinstance(doc, dict):
        doc = empty()
        save(path, doc)
    base = empty()
    for key, value in base.items():
        doc.setdefault(key, value)
    return doc


def save(path, doc):
    import persist
    persist.save_named('accounts', path, doc)


def providers():
    return {
        'google': bool(os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET')),
        'facebook': bool(os.environ.get('FACEBOOK_APP_ID') and os.environ.get('FACEBOOK_APP_SECRET')),
        'registro': email_ready(),
        'email_login': True,
        'reset': email_ready(),
        'sms': sms_ready(),
        'guest': False,
    }


def email_ready():
    if os.environ.get('RESEND_API_KEY') and os.environ.get('EMAIL_FROM'):
        return True
    return bool(os.environ.get('SMTP_HOST') and os.environ.get('SMTP_FROM'))


def sms_ready():
    return bool(os.environ.get('TWILIO_ACCOUNT_SID') and os.environ.get('TWILIO_AUTH_TOKEN') and os.environ.get('TWILIO_VERIFY_SERVICE_SID'))


def hash_password(password, salt=None):
    if not isinstance(password, str) or not 8 <= len(password) <= 1024:
        raise AuthError('La contraseña necesita entre 8 y 1024 caracteres.')
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return 'scrypt$' + salt.hex() + '$' + digest.hex()


def verify_password(password, stored):
    try:
        kind, salt_hex, digest_hex = stored.split('$')
        if kind != 'scrypt':
            return False
        salt = bytes.fromhex(salt_hex)
        expect = bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False
    digest = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return secrets.compare_digest(digest, expect)


def _now(now):
    return int(now if now is not None else time.time())


def _prune_rates(doc, key, now):
    recent = [t for t in doc['rates'].get(key, []) if now - t < 3600]
    doc['rates'][key] = recent
    return recent


def _hit_rate(doc, key, now):
    recent = _prune_rates(doc, key, now)
    if len(recent) >= OTP_PER_HOUR:
        raise AuthError('Demasiados códigos. Espera un rato.')
    recent.append(now)
    doc['rates'][key] = recent


def game_name(text):
    cleaned = re.sub(r'[^0-9A-Za-zÁÉÍÓÚáéíóúÑñ ]', '', unicodedata.normalize('NFKC', str(text or ''))).strip()
    return cleaned[:16]


def _user_by(doc, **query):
    for user in doc['users']:
        if all(user.get(k) == v for k, v in query.items()):
            return user
    return None


def name_key(name):
    return ' '.join(unicodedata.normalize('NFKC', str(name or '')).casefold().split())


_SIMON_LEET = str.maketrans({'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '@': 'a', '$': 's', '!': 'i'})


def simon_key(text):
    """Forma plana: sin acentos, sin símbolos, con los números que imitan letras."""
    raw = unicodedata.normalize('NFKD', str(text or ''))
    raw = ''.join(ch for ch in raw if not unicodedata.combining(ch))
    raw = raw.casefold().translate(_SIMON_LEET)
    return re.sub(r'[^a-z]', '', raw)


def simon_reserved(text):
    return simon_key(text) == 'simon'


def is_owner(user):
    import fusion
    email = str((user or {}).get('email') or '').strip().lower()
    return bool(email) and email == fusion.owner_email()


def name_available(doc, name, email=None, user_id=None, now=None):
    key = name_key(name)
    if not key:
        return False
    if any(name_key(u.get('name')) == key and u.get('id') != user_id for u in doc['users']):
        return False
    return not any(name_key(p.get('name')) == key and owner != email and p.get('exp', 0) >= _now(now)
                   for owner, p in doc['pending'].items())


def reserved_nickname(doc, name):
    key = name_key(name)
    return any(key in (name_key(u.get('name')), name_key(u.get('wallet_name'))) for u in doc['users'])


def login_password(doc, email, password, now=None, client_ip=None):
    now = _now(now)
    email = str(email or '').strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254 or not isinstance(password, str) or len(password) > 1024:
        raise AuthError('Correo o contraseña incorrectos.')
    if client_ip:
        key = 'login-ip:' + hashlib.sha256(str(client_ip).encode()).hexdigest()
        recent = _prune_rates(doc, key, now)
        if len(recent) >= 30:
            raise AuthError('Demasiados intentos. Espera un rato.')
        recent.append(now)
    _hit_rate(doc, 'login:' + email, now)
    pending = doc.get('pending', {}).get(email)
    if pending and pending.get('password_hash') and verify_password(password, pending['password_hash']):
        raise AuthError('Confirma el enlace del correo antes de entrar. Puedes pedir otro enlace.')
    user = _user_by(doc, email=email)
    stored = (user or {}).get('password_hash') or ('scrypt$' + '00' * 16 + '$' + '00' * 32)
    verified = verify_password(password, stored)
    if not user or not user.get('password_hash') or not verified:
        raise AuthError('Correo o contraseña incorrectos.')
    if user.get('verified') is False:
        raise AuthError('Confirma el enlace del correo antes de entrar. Puedes pedir otro enlace.')
    doc['rates'].pop('login:' + email, None)
    return open_session(doc, user, now)


def _dummy_hash():
    return 'scrypt$' + '00' * 16 + '$' + '00' * 32


def _login_bucket(doc, key, now, client_ip):
    if client_ip:
        ip_key = 'login-ip:' + hashlib.sha256(str(client_ip).encode()).hexdigest()
        recent = _prune_rates(doc, ip_key, now)
        if len(recent) >= 30:
            raise AuthError('Demasiados intentos. Espera un rato.')
        recent.append(now)
        doc['rates'][ip_key] = recent
    _hit_rate(doc, key, now)


def _nick_user(doc, nick):
    key = name_key(game_name(nick))
    if not key:
        return None
    for item in doc['users']:
        if name_key(item.get('name')) == key or name_key(item.get('wallet_name')) == key:
            return item
    return None


def nick_preview(doc, nick):
    """Dice si ese nickname todavía no tiene cuenta. No crea nada."""
    cleaned = game_name(nick)
    if not cleaned or simon_reserved(cleaned):
        return {'nuevo': False, 'reservado': bool(cleaned) and simon_reserved(cleaned)}
    return {'nuevo': _nick_user(doc, cleaned) is None, 'reservado': False}


def enter_or_create(doc, nick, password, now=None, client_ip=None):
    """Entra si el nickname existe. Si no existe, crea la cuenta con scrypt y entra.

    Una clave equivocada no reescribe el hash. Simon sigue reservado.
    """
    now = _now(now)
    cleaned = game_name(nick)
    if not cleaned:
        raise AuthError('Escribe un nickname de hasta 16 letras.')
    if not isinstance(password, str) or len(password) > 1024:
        raise AuthError('Contraseña incorrecta')
    _login_bucket(doc, 'login-nick:' + (name_key(cleaned) or 'vacio'), now, client_ip)
    user = _nick_user(doc, cleaned)
    if user:
        stored = user.get('password_hash') or _dummy_hash()
        before = user.get('password_hash')
        verified = bool(password) and bool(before) and verify_password(password, stored)
        if not verified:
            raise AuthError('Contraseña incorrecta')
        doc['rates'].pop('login-nick:' + name_key(cleaned), None)
        return open_session(doc, user, now)
    if simon_reserved(cleaned):
        raise AuthError('Ese apodo está reservado.')
    user = {
        'id': secrets.token_hex(8),
        'name': cleaned,
        'email': '',
        'phone': '',
        'password_hash': hash_password(password),
        'providers': {},
        'wallet_name': cleaned,
        'wallet_token': '',
        'createdAt': now,
        'verified': True,
    }
    doc['users'].append(user)
    doc['rates'].pop('login-nick:' + name_key(cleaned), None)
    return open_session(doc, user, now)


def login_nick(doc, nick, password, now=None, client_ip=None):
    """Entra con el apodo. El error es el mismo si el apodo no existe o la clave no sirve."""
    now = _now(now)
    nick = game_name(nick)
    if not isinstance(password, str) or len(password) > 1024:
        raise AuthError('Apodo o contraseña incorrectos.')
    _login_bucket(doc, 'login-nick:' + (name_key(nick) or 'vacio'), now, client_ip)
    user = None
    key = name_key(nick)
    if key:
        for item in doc['users']:
            if name_key(item.get('name')) == key or name_key(item.get('wallet_name')) == key:
                user = item
                break
    stored = (user or {}).get('password_hash') or _dummy_hash()
    verified = verify_password(password, stored) if password else False
    if not user or not user.get('password_hash') or not verified:
        raise AuthError('Apodo o contraseña incorrectos.')
    doc['rates'].pop('login-nick:' + key, None)
    return open_session(doc, user, now)


def set_nick_and_password(doc, user, nick, password, confirm, now=None):
    """Primera vez: apodo único y contraseña. El hash es el scrypt de siempre.

    TODO: frase secreta de 12 palabras. Mostrarla una sola vez y guardar sólo
    su hash lento. Todavía no está en este flujo.
    """
    now = _now(now)
    if not user:
        raise AuthError('Entra otra vez.')
    _hit_rate(doc, 'clave:' + user['id'], now)
    if user.get('password_hash'):
        raise AuthError('Esta cuenta ya tiene contraseña.')
    if simon_reserved(nick):
        if not is_owner(user):
            raise AuthError('Ese apodo está reservado.')
        nick = 'Simon'
    else:
        nick = game_name(nick)
    if not nick:
        raise AuthError('Escribe un apodo de hasta 16 letras.')
    if simon_reserved(nick) and not is_owner(user):
        raise AuthError('Ese apodo está reservado.')
    if not isinstance(password, str) or password != confirm:
        raise AuthError('Las contraseñas no coinciden.')
    key = name_key(nick)
    for other in doc['users']:
        if other.get('id') == user['id']:
            continue
        if name_key(other.get('name')) == key or name_key(other.get('wallet_name')) == key:
            raise AuthError('Ese apodo ya pertenece a otra cuenta.')
    if not name_available(doc, nick, user_id=user['id'], now=now):
        raise AuthError('Ese apodo ya pertenece a otra cuenta.')
    user['password_hash'] = hash_password(password)
    user['name'] = 'Simon' if is_owner(user) and simon_reserved(nick) else nick
    user['wallet_name'] = user['name']
    return public_user(user)


def claim_simon(doc, user, now=None):
    """El fundador toma el apodo Simon gratis. No crea ni guarda una contraseña."""
    now = _now(now)
    if not user or not is_owner(user):
        raise AuthError('Ese apodo está reservado.')
    _hit_rate(doc, 'simon:' + user['id'], now)
    for other in doc['users']:
        if other.get('id') == user['id']:
            continue
        if simon_key(other.get('name')) == 'simon' or simon_key(other.get('wallet_name')) == 'simon':
            raise AuthError('Ese apodo ya pertenece a otra cuenta.')
    user['name'] = 'Simon'
    user['wallet_name'] = 'Simon'
    return public_user(user)


def begin_signup(doc, name, email, phone, password, send_email, start_sms, now=None):
    now = _now(now)
    if simon_reserved(name):
        raise AuthError('Ese apodo está reservado.')
    name = game_name(name)
    email = str(email or '').strip().lower()
    phone = str(phone or '').strip().replace(' ', '')
    if simon_reserved(name):
        raise AuthError('Ese apodo está reservado.')
    if not name:
        raise AuthError('Escribe un nombre de hasta 16 letras.')
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise AuthError('El correo no parece válido.')
    if phone and not PHONE_RE.match(phone):
        raise AuthError('El teléfono va en formato internacional, por ejemplo +573001112233.')
    if _user_by(doc, email=email) or (phone and _user_by(doc, phone=phone)):
        raise AuthError('Ese correo o teléfono ya tiene cuenta.')
    if not name_available(doc, name, email=email, now=now):
        raise AuthError('Ese nombre ya pertenece a otra cuenta o está reservado por un registro pendiente.')
    _hit_rate(doc, 'email:' + email, now)
    if phone:
        _hit_rate(doc, 'phone:' + phone, now)
    code = f'{secrets.randbelow(1_000_000):06d}'
    doc['pending'][email] = {
        'name': name, 'email': email, 'phone': phone,
        'password_hash': hash_password(password),
        'email_hash': hashlib.sha256(code.encode()).hexdigest(),
        'exp': now + CODE_TTL, 'attempts': 0,
    }
    send_email(email, code)
    if phone:
        start_sms(phone)
    return {'email': email, 'phone': phone, 'exp': now + CODE_TTL}


def verify_signup(doc, email, email_code, phone_code, check_sms, now=None):
    now = _now(now)
    email = str(email or '').strip().lower()
    pending = doc['pending'].get(email)
    if not pending or pending['exp'] < now:
        raise AuthError('El código caducó. Pide otro.')
    pending['attempts'] = int(pending.get('attempts') or 0) + 1
    if pending['attempts'] > MAX_ATTEMPTS:
        doc['pending'].pop(email, None)
        raise AuthError('Demasiados intentos. Pide un código nuevo.')
    digest = hashlib.sha256(str(email_code or '').encode()).hexdigest()
    if not secrets.compare_digest(digest, pending['email_hash']):
        raise AuthError('El código del correo no coincide.')
    if pending['phone'] and not check_sms(pending['phone'], str(phone_code or '')):
        raise AuthError('El código del teléfono no coincide.')
    if _user_by(doc, email=email) or (pending['phone'] and _user_by(doc, phone=pending['phone'])):
        raise AuthError('Esa identidad ya tiene una cuenta.')
    if not name_available(doc, pending['name'], email=email, now=now):
        raise AuthError('Ese nombre ya no está disponible. Elige otro y pide un código nuevo.')
    doc['pending'].pop(email, None)
    user = {
        'id': secrets.token_hex(8),
        'name': pending['name'],
        'email': email,
        'phone': pending['phone'],
        'password_hash': pending['password_hash'],
        'providers': {},
        'wallet_name': pending['name'],
        'wallet_token': '',
        'createdAt': now,
    }
    doc['users'].append(user)
    return open_session(doc, user, now)


def ensure_owner_favorite(user):
    """Si la cuenta del fundador aún no tiene favorito, queda el mundo 5. No toca la contraseña."""
    import mundos
    if not user or not is_owner(user):
        return False
    if mundos.normalize(user.get('favorite_world')):
        return False
    user['favorite_world'] = mundos.OWNER_FAVORITE_WORLD
    return True


def set_favorite_world(doc, user, world):
    """Guarda el mundo favorito en la cuenta. No crea monedas ni cambia la clave."""
    import mundos
    number = mundos.normalize(world)
    if not number:
        raise AuthError('Ese mundo no está abierto.')
    user['favorite_world'] = number
    return public_user(user)


def open_session(doc, user, now=None):
    now = _now(now)
    ensure_owner_favorite(user)
    token = secrets.token_urlsafe(32)
    doc['sessions'][token] = {'user_id': user['id'], 'exp': now + SESSION_TTL}
    return {'token': token, 'user': public_user(user), 'max_age': SESSION_TTL}


def public_user(user):
    import casa_cuenta
    import caballo_cuenta
    shown = casa_cuenta.view(user)
    return {
        'id': user['id'], 'name': user['name'], 'email': user.get('email') or '',
        'wallet_name': user.get('wallet_name') or '',
        'needsPassword': not bool(user.get('password_hash')),
        'canClaimSimon': is_owner(user) and simon_key(user.get('wallet_name') or user.get('name')) != 'simon',
        'avatar_id': 'avatar_' + user['id'],
        'municipio': shown['municipio'],
        'favoriteWorld': __import__('mundos').normalize(user.get('favorite_world')),
        'favoritePlace': __import__('lugares').get(user.get('favorite_place')) and user.get('favorite_place') or '',
        'casa': shown,
        'caballo': caballo_cuenta.view(user),
        'role': __import__('social').role_of(user),
    }


def set_favorite_place(doc, user, place_id):
    """Guarda el lugar donde esta cuenta aparece. No toca la contraseña ni crea monedas."""
    import lugares
    import casa_cuenta
    item = lugares.get(place_id)
    if not item:
        raise AuthError('Ese lugar no está en el valle.')
    user['favorite_place'] = item['id']
    if item.get('municipio'):
        try:
            casa_cuenta.apply(user, {'municipio': item['municipio']})
        except casa_cuenta.CasaError as exc:
            raise AuthError(str(exc)) from exc
    return public_user(user)


def set_municipio(doc, user, municipio):
    """Guarda el municipio dentro de la casa de la cuenta."""
    import casa_cuenta
    try:
        casa_cuenta.apply(user, {'municipio': municipio})
    except casa_cuenta.CasaError as exc:
        raise AuthError(str(exc)) from exc
    return public_user(user)


def set_caballo(user, coat):
    import caballo_cuenta
    try:
        caballo_cuenta.apply(user, coat)
    except caballo_cuenta.CoatError as exc:
        raise AuthError(str(exc)) from exc
    return public_user(user)


def save_casa(user, payload, migrate=False):
    import casa_cuenta
    try:
        casa_cuenta.apply(user, payload, migrate=migrate)
    except casa_cuenta.CasaError as exc:
        raise AuthError(str(exc)) from exc
    return public_user(user)


def session_user(doc, token, now=None):
    now = _now(now)
    if not token:
        return None
    row = doc['sessions'].get(token)
    if not row or row['exp'] < now:
        doc['sessions'].pop(token, None)
        return None
    return _user_by(doc, id=row['user_id'])


def start_oauth(doc, provider, now=None):
    now = _now(now)
    state = secrets.token_urlsafe(24)
    doc['states'][state] = {'provider': provider, 'exp': now + CODE_TTL}
    return state


def finish_oauth(doc, provider, state, cookie_state, profile, now=None):
    now = _now(now)
    saved = doc['states'].get(state or '')
    if not state or state != cookie_state or not saved or saved.get('provider') != provider or saved['exp'] < now:
        raise AuthError('La vuelta del proveedor no coincide. Entra otra vez.')
    doc['states'].pop(state, None)
    sub = str(profile.get('sub') or '')
    if not sub:
        raise AuthError('El proveedor no entregó una identidad.')
    user = None
    for item in doc['users']:
        if (item.get('providers') or {}).get(provider) == sub:
            user = item
            break
    email = str(profile.get('email') or '').strip().lower()
    if user is None and email:
        user = _user_by(doc, email=email)
        if user:
            user.setdefault('providers', {})[provider] = sub
    if user is None:
        name = game_name(profile.get('name') or email.split('@')[0] or 'Jugador') or 'Jugador'
        if (simon_reserved(profile.get('name')) or simon_reserved(name)) and not is_owner({'email': email}):
            name = 'Jugador'
        base = name
        n = 2
        while not name_available(doc, name, email=email, now=now):
            name = (base[:12] + str(n))[:16]
            n += 1
        user = {
            'id': secrets.token_hex(8), 'name': name, 'email': email, 'phone': '',
            'password_hash': '', 'providers': {provider: sub},
            'wallet_name': name, 'wallet_token': '', 'createdAt': now, 'verified': True,
        }
        doc['users'].append(user)
    return open_session(doc, user, now)


def link_wallet(user, name, token):
    """Conserva la billetera que el jugador ya tenía con ese nombre y token."""
    if token:
        user['wallet_name'] = game_name(name) or user['name']
        user['wallet_token'] = token
    elif not user.get('wallet_token'):
        user['wallet_name'] = user.get('wallet_name') or user['name']
    return user


def cookie(name, value, max_age, secure=False):
    bits = [f'{name}={value}', 'Path=/', 'HttpOnly', 'SameSite=Lax', f'Max-Age={int(max_age)}']
    if secure:
        bits.append('Secure')
    return '; '.join(bits)


def read_cookie(header, name):
    for part in str(header or '').split(';'):
        key, _, val = part.strip().partition('=')
        if key == name:
            return val
    return ''


def _token():
    return secrets.token_urlsafe(32)


def _token_hash(raw):
    return hashlib.sha256(str(raw or '').encode('utf-8')).hexdigest()


def begin_email_account(doc, name, email, password, send_link, now=None):
    """Crea un registro pendiente. La cuenta no existe hasta abrir el enlace."""
    now = _now(now)
    if simon_reserved(name):
        raise AuthError('Ese apodo está reservado.')
    name = game_name(name)
    email = str(email or '').strip().lower()
    if simon_reserved(name):
        raise AuthError('Ese apodo está reservado.')
    if not name:
        raise AuthError('Escribe un apodo de hasta 16 letras.')
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise AuthError('El correo no parece válido.')
    if _user_by(doc, email=email):
        raise AuthError('Ese correo ya tiene cuenta. Entra o restablece la contraseña.')
    if not name_available(doc, name, email=email, now=now):
        raise AuthError('Ese apodo ya pertenece a otra cuenta.')
    _hit_rate(doc, 'email:' + email, now)
    raw = _token()
    doc['pending'][email] = {
        'name': name, 'email': email, 'phone': '',
        'password_hash': hash_password(password),
        'link_hash': _token_hash(raw),
        'exp': now + LINK_TTL, 'attempts': 0,
    }
    try:
        send_link(email, raw)
    except AuthError:
        doc['pending'].pop(email, None)
        raise
    except Exception:
        doc['pending'].pop(email, None)
        raise AuthError('No se pudo enviar el correo. Intenta más tarde.')
    return {'email': email, 'exp': now + LINK_TTL}


def _pending_by_link(doc, raw):
    digest = _token_hash(raw)
    if not raw or not digest:
        return None, None
    for email, row in doc.get('pending', {}).items():
        stored = str(row.get('link_hash') or '')
        if stored and secrets.compare_digest(stored, digest):
            return email, row
    return None, None


def confirm_email_link(doc, raw, now=None):
    """Gasta el enlace una sola vez y abre la sesión. Un segundo uso no sirve."""
    now = _now(now)
    email, pending = _pending_by_link(doc, raw)
    if not pending or int(pending.get('exp') or 0) < now:
        raise AuthError('El enlace caducó o ya se usó. Pide otro.')
    doc['pending'].pop(email, None)
    if _user_by(doc, email=email):
        raise AuthError('Esa identidad ya tiene una cuenta.')
    if not name_available(doc, pending['name'], email=email, now=now):
        raise AuthError('Ese apodo ya no está disponible. Elige otro y pide un enlace nuevo.')
    user = {
        'id': secrets.token_hex(8),
        'name': pending['name'],
        'email': email,
        'phone': '',
        'password_hash': pending['password_hash'],
        'providers': {},
        'wallet_name': pending['name'],
        'wallet_token': '',
        'createdAt': now,
        'verified': True,
    }
    doc['users'].append(user)
    return open_session(doc, user, now)


def resend_verification(doc, email, send_link, now=None):
    now = _now(now)
    email = str(email or '').strip().lower()
    if not EMAIL_RE.match(email):
        return
    _hit_rate(doc, 'resend:' + email, now)
    pending = doc.get('pending', {}).get(email)
    if not pending:
        return
    raw = _token()
    pending['link_hash'] = _token_hash(raw)
    pending['exp'] = now + LINK_TTL
    pending['attempts'] = 0
    send_link(email, raw)


def request_password_reset(doc, email, send_link, now=None):
    now = _now(now)
    email = str(email or '').strip().lower()
    if not EMAIL_RE.match(email):
        return
    _hit_rate(doc, 'reset:' + email, now)
    user = _user_by(doc, email=email)
    if not user or not user.get('password_hash'):
        return
    raw = _token()
    resets = doc.setdefault('resets', {})
    for key, row in list(resets.items()):
        if row.get('email') == email:
            resets.pop(key, None)
    resets[_token_hash(raw)] = {'email': email, 'exp': now + RESET_TTL}
    send_link(email, raw)


def reset_password(doc, raw, password, now=None):
    now = _now(now)
    resets = doc.setdefault('resets', {})
    digest = _token_hash(raw)
    row = None
    found = None
    for key, item in list(resets.items()):
        if secrets.compare_digest(key, digest):
            found = key
            row = item
            break
    if found:
        resets.pop(found, None)
    if not row or int(row.get('exp') or 0) < now:
        raise AuthError('El enlace caducó o ya se usó. Pide otro.')
    user = _user_by(doc, email=row['email'])
    if not user:
        raise AuthError('Esa cuenta ya no está.')
    user['password_hash'] = hash_password(password)
    user['verified'] = True
    for token, session in list(doc.get('sessions', {}).items()):
        if session.get('user_id') == user['id']:
            doc['sessions'].pop(token, None)
    return {'ok': True, 'email': user['email']}


def send_email(email, code):
    subject = 'Tu código de Saimon City'
    text = f'Tu código es {code}. Caduca en 10 minutos. Si no pediste entrar, ignora este mensaje.'
    send_message(email, subject, text)


def send_message(email, subject, text):
    sender = os.environ.get('EMAIL_FROM') or os.environ.get('SMTP_FROM') or ''
    if os.environ.get('RESEND_API_KEY'):
        payload = json_dumps({'from': sender, 'to': [email], 'subject': subject, 'text': text})
        req = urllib.request.Request(
            'https://api.resend.com/emails', data=payload, method='POST',
            headers={'Authorization': 'Bearer ' + os.environ['RESEND_API_KEY'], 'Content-Type': 'application/json'},
        )
        urllib.request.urlopen(req, timeout=15).read()
        return
    host = os.environ.get('SMTP_HOST')
    if not host:
        raise AuthError('No hay correo configurado.')
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = email
    msg['Subject'] = subject
    msg.set_content(text)
    with smtplib.SMTP(host, int(os.environ.get('SMTP_PORT') or 587), timeout=15) as smtp:
        if os.environ.get('SMTP_USER'):
            smtp.starttls()
            smtp.login(os.environ['SMTP_USER'], os.environ.get('SMTP_PASSWORD') or '')
        smtp.send_message(msg)


def json_dumps(doc):
    import json
    return json.dumps(doc).encode('utf-8')


def exchange_google(code, redirect_uri):
    form = urllib.parse.urlencode({
        'code': code, 'client_id': os.environ['GOOGLE_CLIENT_ID'],
        'client_secret': os.environ['GOOGLE_CLIENT_SECRET'],
        'redirect_uri': redirect_uri, 'grant_type': 'authorization_code',
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=form)
    import json
    token = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    info_req = urllib.request.Request('https://openidconnect.googleapis.com/v1/userinfo', headers={'Authorization': 'Bearer ' + token['access_token']})
    info = json.loads(urllib.request.urlopen(info_req, timeout=15).read().decode())
    return {'sub': info.get('sub'), 'email': info.get('email') or '', 'name': info.get('name') or ''}


def exchange_facebook(code, redirect_uri):
    query = urllib.parse.urlencode({
        'client_id': os.environ['FACEBOOK_APP_ID'], 'client_secret': os.environ['FACEBOOK_APP_SECRET'],
        'redirect_uri': redirect_uri, 'code': code,
    })
    import json
    token = json.loads(urllib.request.urlopen('https://graph.facebook.com/v19.0/oauth/access_token?' + query, timeout=15).read().decode())
    me = json.loads(urllib.request.urlopen('https://graph.facebook.com/me?fields=id,name,email&access_token=' + urllib.parse.quote(token['access_token']), timeout=15).read().decode())
    return {'sub': me.get('id'), 'email': me.get('email') or '', 'name': me.get('name') or ''}


def start_sms(phone):
    _twilio(phone, None)


def check_sms(phone, code):
    return _twilio(phone, code)


def _twilio(phone, code):
    sid = os.environ.get('TWILIO_ACCOUNT_SID')
    token = os.environ.get('TWILIO_AUTH_TOKEN')
    service = os.environ.get('TWILIO_VERIFY_SERVICE_SID')
    if not (sid and token and service):
        raise AuthError('No hay SMS configurado.')
    import base64
    auth = base64.b64encode(f'{sid}:{token}'.encode()).decode()
    if code is None:
        url = f'https://verify.twilio.com/v2/Services/{service}/Verifications'
        form = urllib.parse.urlencode({'To': phone, 'Channel': 'sms'}).encode()
    else:
        url = f'https://verify.twilio.com/v2/Services/{service}/VerificationCheck'
        form = urllib.parse.urlencode({'To': phone, 'Code': code}).encode()
    req = urllib.request.Request(url, data=form, headers={'Authorization': 'Basic ' + auth})
    raw = urllib.request.urlopen(req, timeout=15).read()
    import json
    data = json.loads(raw.decode())
    if code is None:
        return True
    return data.get('status') == 'approved'
