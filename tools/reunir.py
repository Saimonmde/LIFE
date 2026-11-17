# SPDX-License-Identifier: AGPL-3.0-or-later
"""Junta las llaves partidas de una misma cuenta. No acuña.

La llave canónica es el id de la cuenta, no el apodo. El dueño se reconoce
por el correo verificado. Dave, Cristóbal y cualquiera con el mismo nombre
partido quedan en la suya. El libro, si alcanza, anota una transferencia.
"""
import accounts as acc
import billetera

RESERVADAS = {
    'tesoro_genesis', 'fondo_cambio', 'puesto_frutas', 'casa_de_contratacion',
}
DUENO = ('saimon', 'Simon', 'Saimon', 'Saimon2', 'Saimon888')
DUENO_IGUAL = {name.casefold() for name in DUENO}


def canon(user):
    return 'id:' + str((user or {}).get('id') or '')


def _llaves(econ, vault):
    found = set()
    for key in ((econ or {}).get('wallets') or {}):
        found.add(str(key))
    box = (vault or {}).get('accounts') or {}
    for key in box:
        found.add(str(key))
    for key in ((vault or {}).get('purses') or {}):
        found.add(str(key))
    return found


def _token(name):
    parts = acc.name_key(name).split(' ')
    return parts[0] if parts else ''


def _dueños_de(users, econ, vault):
    """Cada llave suelta apunta a un solo id, o a nadie si es ambigua."""
    claims = {}

    def reclamar(key, uid):
        if not key or key in RESERVADAS or str(key).startswith('id:') or str(key).startswith('deposito:'):
            return
        prev = claims.get(key)
        if prev is None:
            claims[key] = uid
        elif prev != uid:
            claims[key] = ''

    for user in users:
        uid = str(user.get('id') or '')
        if not uid:
            continue
        for raw in (user.get('wallet_name'), user.get('name')):
            if raw:
                reclamar(str(raw), uid)
    tokens = {}
    for user in users:
        uid = str(user.get('id') or '')
        token = _token(user.get('wallet_name') or user.get('name') or '')
        if len(token) < 4 or not uid:
            continue
        tokens.setdefault(token, set()).add(uid)
    unicos = {token: next(iter(ids)) for token, ids in tokens.items() if len(ids) == 1}
    for key in _llaves(econ, vault):
        token = _token(key)
        uid = unicos.get(token)
        if uid:
            reclamar(key, uid)
    # El correo del dueño gana estas llaves aunque otro apodo las haya pedido.
    for user in users:
        if not acc.is_owner(user):
            continue
        uid = str(user.get('id') or '')
        if not uid:
            continue
        for raw in DUENO:
            claims[raw] = uid
        for key in _llaves(econ, vault):
            if str(key).casefold() in DUENO_IGUAL:
                claims[key] = uid
    return {key: uid for key, uid in claims.items() if uid}


def _smh_baul(box):
    if not isinstance(box, dict):
        return 0
    if box.get('smh') is not None:
        return int(box.get('smh') or 0)
    return int(box.get('smcSubs') or 0)


def _poner_baul(box, smh):
    box['smh'] = int(smh)
    box['smcSubs'] = int(smh)


def planear(econ, vault, accounts):
    users = [user for user in (accounts or {}).get('users') or [] if isinstance(user, dict) and user.get('id')]
    claims = _dueños_de(users, econ, vault)
    grupos = {}
    for key, uid in claims.items():
        grupos.setdefault(uid, []).append(key)
    movimientos = []
    for user in users:
        uid = str(user['id'])
        destino = canon(user)
        origenes = [key for key in grupos.get(uid, []) if key != destino]
        if not origenes and destino not in ((econ or {}).get('wallets') or {}):
            continue
        movimientos.append({
            'id': uid,
            'correo': billetera.correo_corto(user.get('email')),
            'dueno': acc.is_owner(user),
            'destino': destino,
            'origenes': sorted(origenes),
        })
    return movimientos


def _sumar_items(dest, src):
    for item, qty in list((src or {}).items()):
        amount = int(qty or 0)
        if amount <= 0:
            continue
        dest[item] = int(dest.get(item) or 0) + amount
        src[item] = 0
    vacios = [item for item, qty in src.items() if int(qty or 0) <= 0]
    for item in vacios:
        src.pop(item, None)


def aplicar(econ, vault, accounts, libro=None, seed=None, ahora=0):
    """Mueve saldos y objetos. La segunda pasada no cambia nada ni acuña."""
    econ.setdefault('wallets', {})
    vault.setdefault('accounts', {})
    vault.setdefault('purses', {})
    antes = int(econ.get('minedSmh') or 0)
    hechos = []
    asientos = []
    for move in planear(econ, vault, accounts):
        destino = move['destino']
        origenes = [key for key in move['origenes'] if key != destino]
        if not origenes:
            continue
        wallet_mov = 0
        baul_mov = 0
        movio_objetos = False
        for key in origenes:
            smh = int(econ['wallets'].get(key) or 0)
            if smh > 0:
                econ['wallets'][destino] = int(econ['wallets'].get(destino) or 0) + smh
                econ['wallets'][key] = 0
                wallet_mov += smh
                asientos.append((key, destino, smh, 'Reasignación de la billetera'))
            box = vault['accounts'].get(key)
            if isinstance(box, dict):
                bank = _smh_baul(box)
                dest_box = vault['accounts'].setdefault(destino, {'items': {}, 'smh': 0, 'smcSubs': 0})
                if bank > 0:
                    _poner_baul(dest_box, _smh_baul(dest_box) + bank)
                    _poner_baul(box, 0)
                    baul_mov += bank
                    asientos.append(('deposito:' + key, 'deposito:' + destino, bank, 'Reasignación del baúl'))
                src_items = box.setdefault('items', {})
                if any(int(qty or 0) > 0 for qty in src_items.values()):
                    movio_objetos = True
                dest_items = dest_box.setdefault('items', {})
                _sumar_items(dest_items, src_items)
            bag = vault['purses'].get(key)
            if isinstance(bag, dict) and any(int(qty or 0) > 0 for qty in bag.values()):
                movio_objetos = True
                dest_bag = vault['purses'].setdefault(destino, {})
                _sumar_items(dest_bag, bag)
        if wallet_mov or baul_mov or movio_objetos:
            hechos.append({
                'id': move['id'],
                'correo': move['correo'],
                'dueno': move['dueno'],
                'llave': destino,
                'smhBilletera': int(econ['wallets'].get(destino) or 0),
                'smhBaul': _smh_baul(vault['accounts'].get(destino)),
                'objetos': _contar(vault, destino),
                'movidoBilletera': wallet_mov,
                'movidoBaul': baul_mov,
            })
    escritos = []
    if libro is not None and seed is not None:
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
    changed = bool(hechos)
    if int(econ.get('minedSmh') or 0) != antes:
        econ['minedSmh'] = antes
    return {
        'changed': changed,
        'cuentas': hechos,
        'asientos': escritos,
        'minedSmh': int(econ.get('minedSmh') or 0),
    }


def _contar(vault, name):
    total = 0
    box = (vault.get('accounts') or {}).get(name) or {}
    if isinstance(box, dict):
        total += sum(int(qty or 0) for qty in (box.get('items') or {}).values())
    bag = (vault.get('purses') or {}).get(name) or {}
    if isinstance(bag, dict):
        total += sum(int(qty or 0) for qty in bag.values())
    return total


def informe(econ, vault, accounts):
    """Lo que vería el diagnóstico: llave, SMC y objetos. Sin correos completos."""
    rows = []
    for user in (accounts or {}).get('users') or []:
        if not isinstance(user, dict) or not user.get('id'):
            continue
        key = canon(user)
        box = (vault.get('accounts') or {}).get(key) or {}
        rows.append({
            'id': str(user['id']),
            'correo': billetera.correo_corto(user.get('email')),
            'dueno': acc.is_owner(user),
            'llave': key,
            'smhBilletera': int(((econ or {}).get('wallets') or {}).get(key) or 0),
            'smhBaul': _smh_baul(box),
            'objetos': _contar(vault, key),
        })
    return rows
