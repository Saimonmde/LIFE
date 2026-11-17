# SPDX-License-Identifier: AGPL-3.0-or-later
"""Un solo usuario saimon para los dos Google de Jay.

No acuña. No toca a Dave, a Cristóbal ni a ninguna cuenta que no sea
la del correo del dueño o la otra sesión de Google con el mismo apodo.
"""
import accounts as acc
import billetera
import crudo
import reunir

LLAVE = 'saimon'
LLAVES = ('saimon', 'Simon', 'Saimon', 'Saimon2', 'Saimon888')
FOLDS = {name.casefold() for name in LLAVES}
RESERVADAS = reunir.RESERVADAS
# La máscara que mostró el celular: ju…n@gmail.com. El correo completo
# lo confirma la cuenta que ya está en el servidor, no un texto fijo.
MASCARA_OTRA = 'ju\u2026n@gmail.com'


def _smh(box):
    return reunir._smh_baul(box)


def _es_suya(key):
    text = str(key or '')
    if not text or text in RESERVADAS or text.startswith('deposito:'):
        return False
    return text.casefold() in FOLDS


def otra_cuenta(accounts, owner):
    """La otra sesión de Google cuyo correo enmascarado es ju…n@gmail.com."""
    owner_id = str((owner or {}).get('id') or '')
    hits = []
    for user in (accounts or {}).get('users') or []:
        if not isinstance(user, dict) or user.get('mergedInto'):
            continue
        if str(user.get('id') or '') == owner_id:
            continue
        email = str(user.get('email') or '').strip().lower()
        if billetera.correo_corto(email) != MASCARA_OTRA:
            continue
        nick = str(user.get('wallet_name') or user.get('name') or '').casefold()
        if nick not in ('saimon', 'simon'):
            continue
        if not acc.google_subs(user):
            continue
        hits.append(user)
    if len(hits) == 1:
        return hits[0], hits
    return None, hits


def _llaves_de(econ, vault, owner, other):
    keys = set()
    for raw in LLAVES:
        keys.add(raw)
    for key in reunir._llaves(econ, vault):
        if _es_suya(key):
            keys.add(str(key))
    for user in (owner, other):
        if not isinstance(user, dict) or not user.get('id'):
            continue
        keys.add('id:' + str(user['id']))
        for raw in (user.get('wallet_name'), user.get('name')):
            text = str(raw or '').strip()
            if text and text.casefold() in FOLDS:
                keys.add(text)
    keys.discard(LLAVE)
    return sorted(keys)


def _vincular(owner, other):
    subs = acc.google_subs(owner) + acc.google_subs(other)
    owner['googleSubs'] = list(dict.fromkeys(subs))
    owner.setdefault('providers', {})
    if subs and not owner['providers'].get('google'):
        owner['providers']['google'] = subs[0]
    aliases = [str(item or '').strip().lower() for item in (owner.get('aliases') or []) if item]
    for raw in (other.get('email'), *(other.get('aliases') or [])):
        email = str(raw or '').strip().lower()
        if email and email != str(owner.get('email') or '').strip().lower() and email not in aliases:
            aliases.append(email)
    owner['aliases'] = aliases
    owner['name'] = LLAVE
    owner['wallet_name'] = LLAVE
    owner['verified'] = True
    other['mergedInto'] = owner.get('id')
    other['email'] = ''
    other['aliases'] = []
    other['providers'] = {}
    other['googleSubs'] = []
    other['name'] = ('fusion-' + str(other.get('id') or ''))[:16]
    other['wallet_name'] = other['name']


def _sesiones(accounts, old_id, new_id):
    moved = 0
    for row in (accounts.get('sessions') or {}).values():
        if isinstance(row, dict) and str(row.get('user_id') or '') == str(old_id):
            row['user_id'] = new_id
            moved += 1
    return moved


def _sumar_finca(dest, src):
    goods = dest.setdefault('goods', {})
    for key, qty in (src.get('goods') or {}).items():
        goods[key] = int(goods.get(key) or 0) + int(qty or 0)
    plots = dest.setdefault('plots', {})
    for key, row in (src.get('plots') or {}).items():
        if not isinstance(row, dict):
            continue
        planted = int(row.get('plantedAt') or 0)
        have = plots.get(key)
        if not isinstance(have, dict):
            plots[key] = {'crop': row.get('crop') or '', 'plantedAt': planted}
        elif planted and not int(have.get('plantedAt') or 0):
            have['plantedAt'] = planted
    src['goods'] = {}
    for row in (src.get('plots') or {}).values():
        if isinstance(row, dict):
            row['plantedAt'] = 0


def _sumar_crudo(econ, dest_id, src_id):
    box = econ.get('crudo') if isinstance(econ.get('crudo'), dict) else None
    if not box or not src_id or src_id == dest_id:
        return
    src = box.get(src_id) or {}
    if not isinstance(src, dict) or not src:
        return
    dest = box.setdefault(dest_id, {})
    for item, qty in list(src.items()):
        total = int(dest.get(item) or 0) + int(qty or 0)
        cap = crudo.CAPS.get(item)
        if cap:
            total = min(total, int(cap) * crudo.SCALE)
        if total:
            dest[item] = total
    box.pop(src_id, None)


def _emitido(libro):
    if not isinstance(libro, dict):
        return None
    import libro as LIBRO
    return int(LIBRO._emitido(libro))


def aplicar(econ, vault, accounts, finca=None, libro=None, seed=None, ahora=0):
    """Pasa billetera, baúl, objetos y finca al usuario saimon. La segunda vez no mueve nada."""
    econ = econ if isinstance(econ, dict) else {}
    vault = vault if isinstance(vault, dict) else {}
    accounts = accounts if isinstance(accounts, dict) else {}
    econ.setdefault('wallets', {})
    vault.setdefault('accounts', {})
    vault.setdefault('purses', {})
    owner = None
    for user in accounts.get('users') or []:
        if isinstance(user, dict) and acc.is_owner(user) and not user.get('mergedInto'):
            owner = user
            break
    antes = _emitido(libro)
    if owner is None:
        return {
            'changed': False, 'motivo': 'sin-dueno', 'ofertaAntes': antes, 'ofertaDespues': antes,
            'origenes': [], 'asientos': [],
        }
    other, candidatos = otra_cuenta(accounts, owner)
    correo = str(other.get('email') or '') if other else ''
    if other:
        _vincular(owner, other)
        _sesiones(accounts, other.get('id'), owner.get('id'))
    elif len(candidatos) > 1:
        correo = ''
    llaves = _llaves_de(econ, vault, owner, other)
    origenes = []
    asientos = []
    movio = False
    for key in llaves:
        wallet = int(econ['wallets'].get(key) or 0)
        box = vault['accounts'].get(key)
        bank = _smh(box) if isinstance(box, dict) else 0
        bag = vault['purses'].get(key)
        objetos = 0
        if isinstance(box, dict):
            objetos += sum(int(qty or 0) for qty in (box.get('items') or {}).values())
        if isinstance(bag, dict):
            objetos += sum(int(qty or 0) for qty in bag.values())
        if wallet or bank or objetos:
            origenes.append({'llave': key, 'billetera': wallet, 'baul': bank, 'objetos': objetos})
        if wallet > 0:
            econ['wallets'][LLAVE] = int(econ['wallets'].get(LLAVE) or 0) + wallet
            econ['wallets'][key] = 0
            asientos.append((key, LLAVE, wallet, 'Reasignación de la billetera'))
            movio = True
        if isinstance(box, dict):
            dest = vault['accounts'].setdefault(LLAVE, {'items': {}, 'smh': 0, 'smcSubs': 0})
            if bank > 0:
                reunir._poner_baul(dest, _smh(dest) + bank)
                reunir._poner_baul(box, 0)
                asientos.append(('deposito:' + key, 'deposito:' + LLAVE, bank, 'Reasignación del baúl'))
                movio = True
            if any(int(qty or 0) > 0 for qty in (box.get('items') or {}).values()):
                reunir._sumar_items(dest.setdefault('items', {}), box.setdefault('items', {}))
                movio = True
        if isinstance(bag, dict) and any(int(qty or 0) > 0 for qty in bag.values()):
            reunir._sumar_items(vault['purses'].setdefault(LLAVE, {}), bag)
            movio = True
        finca_accounts = (finca or {}).get('accounts') if isinstance(finca, dict) else None
        if isinstance(finca_accounts, dict) and key in finca_accounts and key != LLAVE:
            src = finca_accounts.get(key) or {}
            if isinstance(src, dict):
                _sumar_finca(finca_accounts.setdefault(LLAVE, {'goods': {}, 'plots': {}}), src)
                finca_accounts.pop(key, None)
                movio = True
    if other and other.get('id'):
        _sumar_crudo(econ, str(owner.get('id')), str(other.get('id')))
    escritos = []
    if libro is not None and seed is not None and asientos:
        import libro as LIBRO
        for index, (origen, destino, smh, nota) in enumerate(asientos):
            if smh <= 0 or origen == destino:
                continue
            try:
                record = LIBRO.transferir(libro, seed, origen, destino, smh, nota, ts=int(ahora or 0) + index)
            except LIBRO.LibroError:
                record = None
            if record:
                escritos.append(record)
    despues = _emitido(libro)
    changed = bool(movio or other)
    return {
        'changed': changed,
        'motivo': 'unido' if other else ('ambiguo' if len(candidatos) > 1 else 'solo-dueno'),
        'correo': correo,
        'candidatos': len(candidatos),
        'llave': LLAVE,
        'id': owner.get('id'),
        'billetera': int(econ['wallets'].get(LLAVE) or 0),
        'baul': _smh(vault['accounts'].get(LLAVE)),
        'objetos': reunir._contar(vault, LLAVE),
        'origenes': origenes,
        'asientos': escritos,
        'ofertaAntes': antes,
        'ofertaDespues': despues,
    }
