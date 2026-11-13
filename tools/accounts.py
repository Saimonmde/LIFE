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
SESSION_TTL = 60 * 60 * 24 * 30
OTP_PER_HOUR = 5
MAX_ATTEMPTS = 5
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PHONE_RE = re.compile(r'^\+[1-9][0-9]{7,14}$')


class AuthError(Exception):
    pass


def empty():
    return {'users': [], 'sessions': {}, 'pending': {}, 'states': {}, 'rates': {}}


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
        'sms': sms_ready(),
        'guest': True,
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
    cleaned = re.sub(r'[^0-9A-Za-zÁÉÍÓÚáéíóúÑñ ]', '', str(text or '')).strip()
    return cleaned[:16]


def _user_by(doc, **query):
    for user in doc['users']:
        if all(user.get(k) == v for k, v in query.items()):
            return user
    return None


def name_key(name):
    return ' '.join(unicodedata.normalize('NFKC', str(name or '')).casefold().split())


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
    user = _user_by(doc, email=email)
    stored = (user or {}).get('password_hash') or ('scrypt$' + '00' * 16 + '$' + '00' * 32)
    verified = verify_password(password, stored)
    if not user or not user.get('password_hash') or not verified:
        raise AuthError('Correo o contraseña incorrectos.')
    doc['rates'].pop('login:' + email, None)
    return open_session(doc, user, now)


def begin_signup(doc, name, email, phone, password, send_email, start_sms, now=None):
    now = _now(now)
    name = game_name(name)
    email = str(email or '').strip().lower()
    phone = str(phone or '').strip().replace(' ', '')
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


def open_session(doc, user, now=None):
    now = _now(now)
    token = secrets.token_urlsafe(32)
    doc['sessions'][token] = {'user_id': user['id'], 'exp': now + SESSION_TTL}
    return {'token': token, 'user': public_user(user), 'max_age': SESSION_TTL}


def public_user(user):
    return {
        'id': user['id'], 'name': user['name'], 'email': user.get('email') or '',
        'wallet_name': user.get('wallet_name') or user['name'],
        'avatar_id': 'avatar_' + user['id'],
    }


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
        base = name
        n = 2
        while not name_available(doc, name, email=email, now=now):
            name = (base[:12] + str(n))[:16]
            n += 1
        user = {
            'id': secrets.token_hex(8), 'name': name, 'email': email, 'phone': '',
            'password_hash': '', 'providers': {provider: sub},
            'wallet_name': name, 'wallet_token': '', 'createdAt': now,
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


def send_email(email, code):
    subject = 'Tu código de Saimon City'
    text = f'Tu código es {code}. Caduca en 10 minutos. Si no pediste entrar, ignora este mensaje.'
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
