# SPDX-License-Identifier: AGPL-3.0-or-later
"""Junta lo que el #148 dejó fuera: juanescasimon@gmail.com y las llaves sueltas.

El #148 unió una sola sesión cuyo correo enmascarado es ju…n@gmail.com y cuyo
apodo es saimon o simon. En el arranque de lifein ese correo era
juanskasimon@gmail.com. juanescasimon@gmail.com enmascara igual, pero es otra
cuenta: si el apodo no es saimon/simon, o si había más de un candidato, no
entró. Esta pasada la reconoce por el correo, no por el apodo.

No acuña. No reescribe asientos. No toca a Dave, a Cristóbal ni a gamillo2007.
La segunda pasada no mueve nada.
"""
import sys
import unicodedata

import accounts as acc
import billetera
import fusion
import reunir
import saimon_usuario as SU

LLAVE = 'saimon'
FAMILIA = ('saimon', 'Simon', 'Saimon', 'Saimon2', 'Saimon888')
LOCALES = ('juanescasimon', 'juanskasimon')
RESERVADAS = reunir.RESERVADAS
AVISO = 'Reasignación a la cuenta saimon. Simulación educativa. No es dinero real.'


def _plano(text):
    raw = unicodedata.normalize('NFKD', str(text or ''))
    raw = ''.join(ch for ch in raw if not unicodedata.combining(ch))
    return raw.casefold()


def _protegido(user):
    partes = [
        user.get('email'), user.get('name'), user.get('wallet_name'),
        ' '.join(str(item or '') for item in (user.get('aliases') or [])),
    ]
    blob = _plano(' '.join(str(item or '') for item in partes))
    return 'dave' in blob or 'cristobal' in blob or 'gamillo' in blob


def _correos(user):
    found = []
    for raw in (user.get('email'), *(user.get('aliases') or [])):
        email = str(raw or '').strip().lower()
        if email and email not in found:
            found.append(email)
    return found


def _local(email):
    text = str(email or '').strip().lower()
    if '@' not in text:
        return ''
    return text.split('@', 1)[0]


def es_jay(user):
    """La cuenta del dueño o uno de los dos Google de Jay. No un apodo parecido."""
    if not isinstance(user, dict) or not user.get('id') or user.get('mergedInto'):
        return False
    if _protegido(user):
        return False
    if acc.is_owner(user):
        return True
    return any(_local(email) in LOCALES for email in _correos(user))


def _etiqueta(user):
    for email in _correos(user):
        local = _local(email)
        if local in LOCALES:
            return local
    email = str((user or {}).get('email') or '')
    return billetera.correo_corto(email) or str((user or {}).get('id') or '')


def _canon(users):
    vivos = [user for user in users if es_jay(user)]
    oficial = fusion.owner_email()
    for user in vivos:
        if str(user.get('email') or '').strip().lower() == oficial:
            return user
    for user in vivos:
        if acc.is_owner(user):
            return user
    for user in vivos:
        if any(_local(email) == 'juanescasimon' for email in _correos(user)):
            return user
    return vivos[0] if vivos else None


def _reclamadas(users):
    claimed = {}
    for user in users:
        if not isinstance(user, dict) or user.get('mergedInto'):
            continue
        uid = str(user.get('id') or '')
        if not uid:
            continue
        for raw in (user.get('wallet_name'), user.get('name')):
            text = str(raw or '').strip()
            if not text:
                continue
            prev = claimed.get(text)
            if prev is None:
                claimed[text] = uid
            elif prev != uid:
                claimed[text] = ''
    return claimed


def _llaves(econ, vault, users, owner):
    """Llaves de Jay que todavía no son la canónica. Nunca las de otro jugador."""
    keys = set(FAMILIA)
    jay_ids = {str(user.get('id') or '') for user in users if es_jay(user)}
    if owner and owner.get('id'):
        jay_ids.add(str(owner.get('id')))
    for user in users:
        if not es_jay(user):
            continue
        keys.add('id:' + str(user.get('id')))
        for raw in (user.get('wallet_name'), user.get('name')):
            text = str(raw or '').strip()
            if text:
                keys.add(text)
        for email in _correos(user):
            local = _local(email)
            if local:
                keys.add(local)
    claimed = _reclamadas(users)
    familia = {name.casefold() for name in FAMILIA}
    kept = set()
    for key in keys:
        text = str(key or '').strip()
        if not text or text == LLAVE or text in RESERVADAS or text.startswith('deposito:'):
            continue
        if 'dave' in _plano(text) or 'cristobal' in _plano(text) or 'gamillo' in _plano(text):
            continue
        if text.startswith('id:'):
            if text[3:] in jay_ids:
                kept.add(text)
            continue
        dueno = claimed.get(text)
        if dueno and dueno not in jay_ids:
            dueño = next((user for user in users if str(user.get('id') or '') == dueno), None)
            if dueño and _protegido(dueño):
                continue
            if text.casefold() not in familia:
                continue
        kept.add(text)
    return sorted(kept)


def _foto(econ, vault, key):
    wallets = (econ or {}).get('wallets') or {}
    box = ((vault or {}).get('accounts') or {}).get(key)
    bag = ((vault or {}).get('purses') or {}).get(key)
    return {
        'llave': key,
        'billetera': int(wallets.get(key) or 0),
        'baul': SU._smh(box) if isinstance(box, dict) else 0,
        'objetos': reunir._contar(vault, key),
        'bolsa': dict(bag) if isinstance(bag, dict) else {},
        'items': dict((box or {}).get('items') or {}) if isinstance(box, dict) else {},
    }


def _suma(econ, vault):
    total = 0
    for value in ((econ or {}).get('wallets') or {}).values():
        total += int(value or 0)
    for box in ((vault or {}).get('accounts') or {}).values():
        total += SU._smh(box) if isinstance(box, dict) else 0
    return total


def _usuario_publico(user):
    return {
        'id': str((user or {}).get('id') or ''),
        'email': str((user or {}).get('email') or ''),
        'aliases': [str(item or '') for item in ((user or {}).get('aliases') or []) if item],
        'googleSubs': acc.google_subs(user),
        'name': str((user or {}).get('name') or ''),
        'wallet_name': str((user or {}).get('wallet_name') or ''),
    }


def _respaldo(folder, ahora, fuentes, fotos):
    import os
    import persist
    path = os.path.join(folder, 'jay-unido-respaldo.json')
    previo = persist.load_named('jay_unido_respaldo', path)
    if not isinstance(previo, dict):
        previo = {'pasadas': []}
    pasadas = list(previo.get('pasadas') or [])
    pasadas.append({
        'ts': int(ahora or 0),
        'fuentes': fuentes,
        'fotos': fotos,
    })
    previo['pasadas'] = pasadas[-20:]
    persist.save_named('jay_unido_respaldo', path, previo)
    return previo


def _vincular(owner, other):
    subs = acc.google_subs(owner) + acc.google_subs(other)
    owner['googleSubs'] = list(dict.fromkeys(subs))
    owner.setdefault('providers', {})
    if subs and not owner['providers'].get('google'):
        owner['providers']['google'] = subs[0]
    aliases = [str(item or '').strip().lower() for item in (owner.get('aliases') or []) if item]
    for raw in _correos(other):
        if raw and raw != str(owner.get('email') or '').strip().lower() and raw not in aliases:
            aliases.append(raw)
    owner['aliases'] = aliases
    other['mergedInto'] = owner.get('id')
    other['email'] = ''
    other['aliases'] = []
    other['providers'] = {}
    other['googleSubs'] = []
    other['name'] = ('fusion-' + str(other.get('id') or ''))[:16]
    other['wallet_name'] = other['name']


def _promover(owner):
    """Si la única cuenta de Jay no tiene el correo del dueño, ese correo queda y el otro pasa a alias."""
    if acc.is_owner(owner):
        return False
    oficial = fusion.owner_email()
    previo = str(owner.get('email') or '').strip().lower()
    aliases = [str(item or '').strip().lower() for item in (owner.get('aliases') or []) if item]
    if previo and previo != oficial and previo not in aliases:
        aliases.append(previo)
    owner['aliases'] = aliases
    owner['email'] = oficial
    owner['verified'] = True
    return True


def _renombrar(owner):
    changed = False
    if owner.get('name') != LLAVE:
        owner['name'] = LLAVE
        changed = True
    if owner.get('wallet_name') != LLAVE:
        owner['wallet_name'] = LLAVE
        changed = True
    if not owner.get('verified'):
        owner['verified'] = True
        changed = True
    return changed


def _log(line):
    sys.stderr.write(line + '\n')
    sys.stderr.flush()


def _anotar(libro, seed, origen, destino, smh, nota, ts):
    import libro as LIBRO
    if libro is None or seed is None or smh <= 0 or origen == destino:
        return None
    try:
        return LIBRO.transferir(libro, seed, origen, destino, smh, nota, ts=ts)
    except LIBRO.LibroError:
        return LIBRO.ajustar(libro, seed, origen, destino, smh, nota, ts=ts)


def aplicar(econ, vault, accounts, finca=None, libro=None, seed=None, ahora=0, folder=None):
    """Pasa billetera, baúl y objetos a saimon. La suma de SMC no cambia."""
    econ = econ if isinstance(econ, dict) else {}
    vault = vault if isinstance(vault, dict) else {}
    accounts = accounts if isinstance(accounts, dict) else {}
    econ.setdefault('wallets', {})
    vault.setdefault('accounts', {})
    vault.setdefault('purses', {})
    users = [user for user in (accounts.get('users') or []) if isinstance(user, dict)]
    owner = _canon(users)
    antes_oferta = SU._emitido(libro)
    suma_antes = _suma(econ, vault)
    if owner is None:
        return {
            'changed': False, 'motivo': 'sin-dueno', 'antes': [], 'despues': {},
            'sumaAntes': suma_antes, 'sumaDespues': suma_antes,
            'ofertaAntes': antes_oferta, 'ofertaDespues': antes_oferta,
            'asientos': [], 'fuentes': [],
        }
    otros = [user for user in users if es_jay(user) and user.get('id') != owner.get('id')]
    llaves = _llaves(econ, vault, users, owner)
    fotos = [_foto(econ, vault, key) for key in llaves]
    fuentes = [_usuario_publico(user) for user in otros]
    for row in [_usuario_publico(owner)] + fuentes:
        _log('[jay] antes cuenta %s id %s' % (row.get('email') or row.get('id'), row.get('id')))
    for foto in fotos:
        if foto['billetera'] or foto['baul'] or foto['objetos']:
            _log('[jay] antes llave %s billetera %s baul %s objetos %s' % (
                foto['llave'], foto['billetera'], foto['baul'], foto['objetos']))
    movio = False
    if otros or any(foto['billetera'] or foto['baul'] or foto['objetos'] for foto in fotos):
        if folder:
            _respaldo(folder, ahora, [_usuario_publico(owner)] + fuentes, fotos)
    for other in otros:
        _vincular(owner, other)
        SU._sesiones(accounts, other.get('id'), owner.get('id'))
        SU._sumar_crudo(econ, str(owner.get('id')), str(other.get('id')))
        movio = True
    if _promover(owner):
        movio = True
    if _renombrar(owner):
        movio = True
    asientos = []
    for key in llaves:
        wallet = int(econ['wallets'].get(key) or 0)
        box = vault['accounts'].get(key)
        bank = SU._smh(box) if isinstance(box, dict) else 0
        if wallet > 0:
            econ['wallets'][LLAVE] = int(econ['wallets'].get(LLAVE) or 0) + wallet
            econ['wallets'][key] = 0
            asientos.append((key, LLAVE, wallet, 'Reasignación de la billetera. ' + AVISO))
            movio = True
        if isinstance(box, dict):
            dest = vault['accounts'].setdefault(LLAVE, {'items': {}, 'smh': 0, 'smcSubs': 0})
            if bank > 0:
                reunir._poner_baul(dest, SU._smh(dest) + bank)
                reunir._poner_baul(box, 0)
                asientos.append(('deposito:' + key, 'deposito:' + LLAVE, bank, 'Reasignación del baúl. ' + AVISO))
                movio = True
            if any(int(qty or 0) > 0 for qty in (box.get('items') or {}).values()):
                reunir._sumar_items(dest.setdefault('items', {}), box.setdefault('items', {}))
                movio = True
        bag = vault['purses'].get(key)
        if isinstance(bag, dict) and any(int(qty or 0) > 0 for qty in bag.values()):
            reunir._sumar_items(vault['purses'].setdefault(LLAVE, {}), bag)
            movio = True
        finca_accounts = (finca or {}).get('accounts') if isinstance(finca, dict) else None
        if isinstance(finca_accounts, dict) and key in finca_accounts and key != LLAVE:
            src = finca_accounts.get(key) or {}
            if isinstance(src, dict):
                SU._sumar_finca(finca_accounts.setdefault(LLAVE, {'goods': {}, 'plots': {}}), src)
                finca_accounts.pop(key, None)
                movio = True
    escritos = []
    for index, (origen, destino, smh, nota) in enumerate(asientos):
        record = _anotar(libro, seed, origen, destino, smh, nota, int(ahora or 0) + index)
        if record:
            escritos.append(record)
    despues = _foto(econ, vault, LLAVE)
    suma_despues = _suma(econ, vault)
    oferta = SU._emitido(libro)
    _log('[jay] despues llave %s billetera %s baul %s objetos %s suma %s %s oferta %s %s' % (
        LLAVE, despues['billetera'], despues['baul'], despues['objetos'],
        suma_antes, suma_despues, antes_oferta, oferta,
    ))
    for other in otros:
        _log('[jay] despues cuenta %s unida-a %s' % (other.get('id'), owner.get('id')))
    return {
        'changed': bool(movio),
        'motivo': 'unido' if movio else 'ya',
        'id': owner.get('id'),
        'llave': LLAVE,
        'antes': fotos,
        'despues': despues,
        'sumaAntes': suma_antes,
        'sumaDespues': suma_despues,
        'ofertaAntes': antes_oferta,
        'ofertaDespues': oferta,
        'asientos': escritos,
        'fuentes': [str(user.get('id') or '') for user in otros],
        'billetera': despues['billetera'],
        'baul': despues['baul'],
        'objetos': despues['objetos'],
    }
