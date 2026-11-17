# SPDX-License-Identifier: AGPL-3.0-or-later
"""El dueño edita su propio saldo y acuña SMC. Nadie más.

La identidad sale de la cuenta del servidor (el correo del dueño). Un campo
del cliente no convierte a nadie en dueño. Cada acuñación y cada ajuste queda
en el libro madre, firmado y encadenado, con código único. El tope sigue siendo
21.000.000 SMC. El oro del río y los topes diarios de juego no pasan por aquí.
"""
import copy
import time

import accounts as acc
import billetera
import economy as eco
import libro as LIBRO
import vault as VAULT

AVISO = 'Simulación educativa. No es dinero real. No es el oro del río ni el tope diario.'
POR_HORA = 10
AUDITORIA = 200
SINK = 'baja-admin'


class DuenoError(Exception):
    def __init__(self, message, status='400 Bad Request'):
        super().__init__(message)
        self.status = status


def autorizado(user):
    """Sólo la cuenta cuyo correo es el del dueño. mergedInto no cuenta."""
    return isinstance(user, dict) and not user.get('mergedInto') and acc.is_owner(user)


def _llave(user):
    if not autorizado(user):
        raise DuenoError('Sólo el dueño puede editar Simon Coins.', '403 Forbidden')
    return 'saimon'


def _smh(box):
    return VAULT.smh_of(box)


def _caja(vault, key):
    vault.setdefault('accounts', {})
    return VAULT.account(vault, key)


def _leer(value, presente):
    if not presente:
        return None
    try:
        amount = eco.smc_to_smh(value)
    except eco.AmountError as exc:
        raise DuenoError(str(exc)) from exc
    if amount < 0:
        raise DuenoError('El saldo no puede quedar por debajo de cero.')
    return int(amount)


def _razon(text):
    reason = ' '.join(str(text or '').split())
    if not reason:
        raise DuenoError('Escribe el motivo.')
    if len(reason) > 160:
        raise DuenoError('El motivo es demasiado largo.')
    return reason


def _cupo(econ, chain):
    eco_room = eco.issuance_room(econ if isinstance(econ, dict) else {})
    lib_room = LIBRO.cupo_subs(chain) if isinstance(chain, dict) else eco_room
    return max(0, min(int(eco_room), int(lib_room)))


def _ritmo(accounts, user, now):
    doc = accounts if isinstance(accounts, dict) else {}
    rates = doc.setdefault('rates', {})
    key = 'dueno-smc:' + str((user or {}).get('id') or '')
    now = int(now or 0)
    recent = [int(item) for item in (rates.get(key) or []) if now - int(item) < 3600]
    if len(recent) >= POR_HORA:
        rates[key] = recent
        raise DuenoError('Demasiados cambios. Espera un rato.', '429 Too Many Requests')
    recent.append(now)
    rates[key] = recent


def _auditar(accounts, row):
    doc = accounts if isinstance(accounts, dict) else {}
    log = doc.setdefault('duenoAudit', [])
    log.append(row)
    if len(log) > AUDITORIA:
        del log[:-AUDITORIA]


def vista(econ, vault, chain, user):
    key = _llave(user)
    wallets = (econ or {}).get('wallets') or {}
    box = ((vault or {}).get('accounts') or {}).get(key) or {}
    wallet = int(wallets.get(key) or 0)
    bank = _smh(box)
    room = _cupo(econ, chain)
    return {
        'ok': True,
        'dueno': True,
        'llave': key,
        'billeteraSmh': wallet,
        'baulSmh': bank,
        'totalSmh': wallet + bank,
        'billetera': eco.format_smc(wallet),
        'baul': eco.format_smc(bank),
        'total': eco.format_smc(wallet + bank),
        'cupoSmh': room,
        'cupo': eco.format_smc(room),
        'tope': '21.000.000 SMC',
        'aviso': AVISO,
        'correo': billetera.correo_corto((user or {}).get('email')),
    }


def _emitir(econ, vault, chain, seed, key, amount, reason, ahora, bits, presupuesto):
    """Acuña `amount` céntimos en la billetera. Si no cabe, no mueve nada."""
    amount = int(amount or 0)
    if amount <= 0:
        raise DuenoError('La acuñación tiene que ser mayor que cero.')
    if amount > _cupo(econ, chain):
        raise DuenoError('Supera el tope de 21.000.000 SMC.', '409 Conflict')
    if not isinstance(chain, dict) or seed is None:
        raise DuenoError('El libro madre no está listo.')
    nota = reason + ' · ' + AVISO
    record = LIBRO.acuñar(
        chain, seed, key, amount, nota,
        ts=int(ahora or 0), bits=int(bits), presupuesto=float(presupuesto),
        kind=LIBRO.KIND_ADMIN_MINT,
    )
    if record is None:
        raise DuenoError('Supera el tope de 21.000.000 SMC.', '409 Conflict')
    granted = eco.issue(econ, key, amount, nota, LIBRO.KIND_ADMIN_MINT, now=int(ahora or 0))
    if granted != amount:
        LIBRO.revertir(chain, record)
        if granted:
            eco.debit(econ, key, granted)
            econ['minedSmh'] = int(econ.get('minedSmh') or 0) - granted
        raise DuenoError('Supera el tope de 21.000.000 SMC.', '409 Conflict')
    return record


def _bajar(chain, seed, origen, amount, reason, ts):
    nota = reason + ' · Ajuste de administración. ' + AVISO
    return LIBRO.ajustar(chain, seed, origen, SINK, int(amount), nota, ts=ts)


def _mover(chain, seed, origen, destino, amount, reason, ts):
    nota = reason + ' · Ajuste de administración. ' + AVISO
    return LIBRO.ajustar(chain, seed, origen, destino, int(amount), nota, ts=ts)


def _estado(econ, vault, key):
    wallet = int(((econ or {}).get('wallets') or {}).get(key) or 0)
    bank = _smh(((vault or {}).get('accounts') or {}).get(key))
    return wallet, bank


def _captura(econ, vault, chain, key):
    box = ((vault or {}).get('accounts') or {}).get(key)
    return {
        'wallet': int(((econ or {}).get('wallets') or {}).get(key) or 0),
        'tenía': key in ((econ or {}).get('wallets') or {}),
        'mined': int((econ or {}).get('minedSmh') or 0),
        'mempool': copy.deepcopy((econ or {}).get('mempool') or []),
        'bloques': copy.deepcopy((econ or {}).get('blocks') or []),
        'baul': None if not isinstance(box, dict) else _smh(box),
        'n': len((chain or {}).get('blocks') or []),
        'ids': list((chain or {}).get('ids') or []),
    }


def _volver(econ, vault, chain, key, foto):
    wallets = econ.setdefault('wallets', {})
    if foto['tenía']:
        wallets[key] = foto['wallet']
    else:
        wallets.pop(key, None)
    econ['minedSmh'] = foto['mined']
    econ['mempool'] = foto['mempool']
    econ['blocks'] = foto['bloques']
    accounts = vault.setdefault('accounts', {})
    box = accounts.get(key)
    if isinstance(box, dict) and foto['baul'] is not None:
        box['smh'] = foto['baul']
        box['smcSubs'] = foto['baul']
    elif isinstance(box, dict) and foto['baul'] is None:
        box['smh'] = 0
        box['smcSubs'] = 0
    if isinstance(chain, dict):
        chain['blocks'] = (chain.get('blocks') or [])[:foto['n']]
        chain['ids'] = list(foto['ids'])


def acunar(econ, vault, accounts, user, smc, razon, chain, seed, ahora=None, bits=1, presupuesto=0.2):
    key = _llave(user)
    ahora = int(time.time() if ahora is None else ahora)
    reason = _razon(razon)
    amount = _leer(smc, True)
    if amount <= 0:
        raise DuenoError('La acuñación tiene que ser mayor que cero.')
    _ritmo(accounts, user, ahora)
    antes_w, antes_b = _estado(econ, vault, key)
    foto = _captura(econ, vault, chain, key)
    try:
        record = _emitir(econ, vault, chain, seed, key, amount, reason, ahora, bits, presupuesto)
    except Exception:
        _volver(econ, vault, chain, key, foto)
        _devolver_ritmo(accounts, user, ahora)
        raise
    despues_w, despues_b = _estado(econ, vault, key)
    _auditar(accounts, {
        'ts': ahora, 'user': str(user.get('id') or ''), 'op': 'acunar', 'razon': reason,
        'antes': {'billetera': antes_w, 'baul': antes_b},
        'despues': {'billetera': despues_w, 'baul': despues_b},
        'codigos': [record.get('id')], 'ok': True,
    })
    cuerpo = vista(econ, vault, chain, user)
    cuerpo['op'] = 'acunar'
    cuerpo['codigo'] = record.get('id')
    cuerpo['asientos'] = [LIBRO.publico(record)]
    return cuerpo


def _devolver_ritmo(accounts, user, ahora):
    rates = (accounts or {}).get('rates') or {}
    key = 'dueno-smc:' + str((user or {}).get('id') or '')
    recent = [int(item) for item in (rates.get(key) or [])]
    if recent and recent[-1] == int(ahora):
        recent.pop()
    if isinstance(accounts, dict):
        accounts.setdefault('rates', {})[key] = recent


def ajustar(econ, vault, accounts, user, billetera, baul, razon, chain, seed, ahora=None, bits=1, presupuesto=0.2, toca_billetera=True, toca_baul=True):
    """Deja la billetera y el baúl en esas cifras. Lo que sube se acuña; lo que baja queda anotado."""
    key = _llave(user)
    ahora = int(time.time() if ahora is None else ahora)
    reason = _razon(razon)
    if not isinstance(chain, dict) or seed is None:
        raise DuenoError('El libro madre no está listo.')
    old_w, old_b = _estado(econ, vault, key)
    new_w = old_w if not toca_billetera else _leer(billetera, True)
    new_b = old_b if not toca_baul else _leer(baul, True)
    if new_w == old_w and new_b == old_b:
        raise DuenoError('Ese ya es el saldo.')
    delta = (new_w + new_b) - (old_w + old_b)
    if delta > _cupo(econ, chain):
        raise DuenoError('Supera el tope de 21.000.000 SMC.', '409 Conflict')
    _ritmo(accounts, user, ahora)
    foto = _captura(econ, vault, chain, key)
    records = []
    try:
        if delta > 0:
            records.append(_emitir(
                econ, vault, chain, seed, key, delta, reason, ahora, bits, presupuesto,
            ))
        wallet, bank = _estado(econ, vault, key)
        if delta < 0:
            quitar = -delta
            de_wallet = min(wallet, quitar)
            if de_wallet:
                if not eco.debit(econ, key, de_wallet):
                    raise DuenoError('La billetera no alcanza para ese ajuste.')
                records.append(_bajar(chain, seed, key, de_wallet, reason, ahora + len(records)))
                quitar -= de_wallet
            if quitar:
                box = _caja(vault, key)
                if not VAULT.take_smc(box, quitar):
                    raise DuenoError('El baúl no alcanza para ese ajuste.')
                records.append(_bajar(
                    chain, seed, 'deposito:' + key, quitar, reason, ahora + len(records),
                ))
        wallet, bank = _estado(econ, vault, key)
        if bank < new_b:
            mover = new_b - bank
            if not eco.debit(econ, key, mover):
                raise DuenoError('La billetera no alcanza para ese ajuste.')
            VAULT.add_smc(_caja(vault, key), mover)
            records.append(_mover(
                chain, seed, key, 'deposito:' + key, mover, reason, ahora + len(records),
            ))
        elif bank > new_b:
            mover = bank - new_b
            box = _caja(vault, key)
            if not VAULT.take_smc(box, mover):
                raise DuenoError('El baúl no alcanza para ese ajuste.')
            eco.credit(econ, key, mover)
            records.append(_mover(
                chain, seed, 'deposito:' + key, key, mover, reason, ahora + len(records),
            ))
        final_w, final_b = _estado(econ, vault, key)
        if final_w != new_w or final_b != new_b:
            raise DuenoError('El ajuste no cerró.')
    except Exception:
        _volver(econ, vault, chain, key, foto)
        _devolver_ritmo(accounts, user, ahora)
        raise
    _auditar(accounts, {
        'ts': ahora, 'user': str(user.get('id') or ''), 'op': 'ajustar', 'razon': reason,
        'antes': {'billetera': old_w, 'baul': old_b},
        'despues': {'billetera': new_w, 'baul': new_b},
        'codigos': [record.get('id') for record in records], 'ok': True,
    })
    cuerpo = vista(econ, vault, chain, user)
    cuerpo['op'] = 'ajustar'
    cuerpo['codigos'] = [record.get('id') for record in records]
    cuerpo['asientos'] = [LIBRO.publico(record) for record in records]
    return cuerpo
