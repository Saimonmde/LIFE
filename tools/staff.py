# SPDX-License-Identifier: AGPL-3.0-or-later
"""Personal del juego. El dueño es sólo el fundador. El staff lo nombra él.

SIMON_STAFF, si existe, es una lista de correos separada por comas. Sirve
para el primer arranque. No guarda contraseñas ni crea monedas. Quitar el
papel desde la cuenta del dueño permanece aunque el correo siga en esa lista.

Formato exacto de la variable (sin comillas):
    SIMON_STAFF=correo1@ejemplo.com,correo2@ejemplo.com
Los espacios alrededor de cada correo se ignoran. Mayúsculas y minúsculas
cuentan como el mismo correo. Un solo correo también vale.
"""
import os
import time

import accounts as ACC

AUDIT_CAP = 200


def emails():
    """Correos del arranque. Vacío si la variable no está."""
    raw = str(os.environ.get('SIMON_STAFF') or '')
    found = []
    for part in raw.split(','):
        email = part.strip().lower()
        if email and '@' in email and email not in found:
            found.append(email)
    return tuple(found)


def _email(user):
    return str((user or {}).get('email') or '').strip().lower()


def role_of(user):
    """Papel efectivo. Nadie se vuelve dueño escribiendo el campo role."""
    if not isinstance(user, dict):
        return 'player'
    if ACC.is_owner(user):
        return 'owner'
    stored = str(user.get('role') or 'player')
    if stored == 'staff':
        return 'staff'
    if stored == 'owner':
        return 'player'
    email = _email(user)
    if email and email in emails() and not user.get('staffRevoked'):
        return 'staff'
    if stored in ('player', 'admin', 'simon'):
        return stored
    return 'player'


def remember_email(user, email):
    """Guarda el correo del proveedor en minúsculas.

    No pisa un correo distinto que la cuenta ya tenga. El mismo correo escrito
    con mayúsculas se normaliza para coincidir con SIMON_STAFF.
    """
    if not isinstance(user, dict):
        return False
    email = str(email or '').strip().lower()
    if not email or '@' not in email:
        return False
    current = str(user.get('email') or '').strip().lower()
    if current and current != email:
        return False
    if user.get('email') == email:
        return False
    user['email'] = email
    return True


def apply_bootstrap(user):
    """Si el correo está en SIMON_STAFF y nadie le quitó el papel, lo deja en la cuenta.

    Sirve igual para una cuenta que ya existía y para una creada después de
    fijar la variable. La comparación no distingue mayúsculas.
    """
    if not isinstance(user, dict) or ACC.is_owner(user):
        return False
    email = _email(user)
    if not email or email not in emails() or user.get('staffRevoked'):
        return False
    if user.get('role') == 'staff':
        return False
    user['role'] = 'staff'
    return True


def row(user):
    return {
        'id': str((user or {}).get('id') or ''),
        'nick': str((user or {}).get('wallet_name') or (user or {}).get('name') or '')[:16],
        'email': _email(user),
        'role': role_of(user),
    }


def _users(doc):
    return [user for user in (doc or {}).get('users') or [] if isinstance(user, dict)]


def find(doc, ident):
    key = str(ident or '').strip()
    if not key:
        return None
    lowered = key.lower()
    for user in _users(doc):
        if str(user.get('id') or '') == key or _email(user) == lowered:
            return user
    nick = ACC.name_key(key)
    if not nick:
        return None
    for user in _users(doc):
        if ACC.name_key(user.get('wallet_name') or user.get('name')) == nick:
            return user
    return None


def search(doc, query):
    raw = str(query or '').strip().lower()
    if len(raw) < 2:
        return []
    nick = ACC.name_key(raw)
    hits = []
    for user in _users(doc):
        email = _email(user)
        name = str(user.get('wallet_name') or user.get('name') or '').lower()
        if raw in email or raw in name or (nick and ACC.name_key(name) == nick):
            hits.append(row(user))
        if len(hits) >= 12:
            break
    return hits


def list_staff(doc):
    rows = [row(user) for user in _users(doc) if role_of(user) == 'staff']
    rows.sort(key=lambda item: (item['nick'].lower(), item['email']))
    return rows


def recent(doc, limit=12):
    rows = [item for item in (doc or {}).get('staffAudit') or [] if isinstance(item, dict)]
    return rows[-int(limit):]


def note(doc, actor, action, target='', now=None):
    """Una línea: cuenta, acción y hora. Sin claves ni textos largos."""
    if not isinstance(doc, dict):
        return None
    stamp = int(time.time() if now is None else now)
    item = {
        'at': stamp,
        'account': str((actor or {}).get('id') or ''),
        'nick': str((actor or {}).get('wallet_name') or (actor or {}).get('name') or '')[:16],
        'action': str(action or '')[:80],
        'target': str(target or '')[:80],
    }
    box = doc.setdefault('staffAudit', [])
    box.append(item)
    del box[:-AUDIT_CAP]
    return item


def set_staff(doc, actor, ident, grant, now=None):
    """Sólo el dueño. No cambia al dueño y no acuña."""
    if role_of(actor) != 'owner':
        raise PermissionError('Sólo el dueño nombra al personal.')
    target = find(doc, ident)
    if not target:
        raise PermissionError('No encuentro esa cuenta.')
    if ACC.is_owner(target):
        raise PermissionError('El dueño no se puede cambiar.')
    if grant:
        target['role'] = 'staff'
        target['staffRevoked'] = False
        action = 'otorgar_staff'
    else:
        if target.get('role') == 'staff':
            target['role'] = 'player'
        target['staffRevoked'] = True
        action = 'quitar_staff'
    note(doc, actor, action, target.get('id'), now)
    return row(target)


def handle(doc, actor, payload, now=None):
    """Respuesta del panel. 403 si no es el dueño."""
    payload = payload if isinstance(payload, dict) else {}
    if role_of(actor) != 'owner':
        return {'ok': False, 'status': '403 Forbidden', 'error': 'Sólo el dueño nombra al personal.'}
    if payload.get('id') is not None and 'grant' in payload:
        try:
            shown = set_staff(doc, actor, payload.get('id'), bool(payload.get('grant')), now)
        except PermissionError as exc:
            return {'ok': False, 'status': '403 Forbidden', 'error': str(exc)}
        return {'ok': True, 'user': shown, 'staff': list_staff(doc), 'audit': recent(doc)}
    return {
        'ok': True,
        'results': search(doc, payload.get('q') if payload.get('q') is not None else payload.get('query')),
        'staff': list_staff(doc),
        'audit': recent(doc),
    }
