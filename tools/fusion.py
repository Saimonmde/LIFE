# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fusión inicial: pasa el SMC ya existente a la cuenta del fundador.

No acuña. No cambia minedSmh, el tope de 21.000.000 ni la reserva génesis
que sigue en tesoro_genesis. No toca la Plata (SMP): ni sus billeteras,
ni lo minado, ni lo quemado. El fondo de cambio guarda SMC ya emitido
(un quinto de cada acuñación); ese oro sí se mueve, la plata no.

Reglas, en SMH enteros (1 SMC = 100.000.000 SMH):

1. Si founderFusion.status ya es «done», no se vuelve a mover nada.
2. La cuenta destino es la de accounts.users cuyo email, sin distinguir
   mayúsculas, es saimon888oficial@gmail.com. La billetera es wallet_name
   o, si falta, name. Si esa cuenta aún no existe, el estado queda
   «pending» y no se mueve un Simonchi.
3. Se debita por completo, y se acredita a esa billetera, cada saldo SMC
   mayor que cero que no sea la reserva ni la propia billetera del fundador:
   - economy.wallets (jugadores, puesto_frutas y cualquier otra cuenta)
   - economy.plata.smcPoolSmh (el fondo de cambio, clave fondo_cambio)
   - vault.accounts[*].smh, salvo el depósito que ya es del fundador
4. La reserva tesoro_genesis no se toca, aunque le quede menos de
   210.000 SMC porque ya se entregó a cuentas. Lo que ya está en una
   cuenta sí entra en el paso 3.
5. Cada pase deja una transacción en el libro mayor, tipo fusion, con la
   nota «Fusión inicial a la cuenta del fundador». El llamador anota el
   mismo pase en el libro madre cuando ese origen tiene saldo ahí.
6. La suma de billeteras + fondo + depósitos no cambia. minedSmh tampoco.
"""
import time

import economy as eco
import vault as VAULT

EMAIL = 'saimon888oficial@gmail.com'
NOTE = 'Fusión inicial a la cuenta del fundador'
RESERVE = 'tesoro_genesis'
POOL = 'fondo_cambio'


def find_founder(accounts, email=EMAIL):
    want = str(email or '').strip().lower()
    if not want:
        return None
    for user in (accounts or {}).get('users') or []:
        if str(user.get('email') or '').strip().lower() == want:
            return user
    return None


def wallet_of(user):
    if not user:
        return ''
    return str(user.get('wallet_name') or user.get('name') or '').strip()


def _record(state):
    rec = state.get('founderFusion')
    if not isinstance(rec, dict):
        rec = {'status': 'pending', 'transfers': [], 'movedSmh': 0, 'email': EMAIL}
        state['founderFusion'] = rec
    rec.setdefault('transfers', [])
    rec.setdefault('movedSmh', 0)
    rec.setdefault('email', EMAIL)
    return rec


def _keys(rec):
    return {(item.get('where'), item.get('from')) for item in rec.get('transfers') or []}


def _sweep_saved_vaults(vault_state, rec):
    """Si el libro ya se guardó y el depósito no, quita ese saldo sin acreditar otra vez."""
    if not isinstance(vault_state, dict):
        return False
    swept = set(vault_state.get('fusionSwept') or [])
    changed = False
    accounts = vault_state.setdefault('accounts', {})
    for item in rec.get('transfers') or []:
        if item.get('where') != 'deposito':
            continue
        name = item.get('from')
        if not name or name in swept:
            continue
        box = accounts.get(name)
        have = VAULT.smh_of(box) if box else 0
        take = min(have, int(item.get('amountSubs') or 0))
        if take > 0 and box is not None and VAULT.take_smc(box, take):
            changed = True
        swept.add(name)
        changed = True
    if changed:
        vault_state['fusionSwept'] = sorted(swept)
    return changed


def apply(econ, accounts, vault_state, now=None):
    """Mueve el SMC circulante. Idempotente. Devuelve status, fresh y changed."""
    now = int(now if now is not None else time.time())
    rec = _record(econ)
    if rec.get('status') == 'done':
        changed = _sweep_saved_vaults(vault_state, rec)
        return {'status': 'done', 'already': not changed, 'fresh': [], 'record': rec, 'changed': changed}

    dest = wallet_of(find_founder(accounts))
    if not dest:
        if rec.get('status') == 'pending' and rec.get('reason'):
            return {'status': 'pending', 'already': True, 'fresh': [], 'record': rec, 'changed': False}
        rec['status'] = 'pending'
        rec['email'] = EMAIL
        rec['wallet'] = ''
        rec['reason'] = 'La cuenta del fundador aún no existe.'
        rec['ts'] = now
        return {'status': 'pending', 'already': False, 'fresh': [], 'record': rec, 'changed': True}

    done = _keys(rec)
    fresh = []
    changed = False

    def remember(where, source, amount, libro_from):
        nonlocal changed
        row = {
            'where': where,
            'from': source,
            'to': dest,
            'amountSubs': int(amount),
            'note': NOTE,
            'libroFrom': libro_from,
        }
        rec['transfers'].append(row)
        rec['movedSmh'] = int(rec.get('movedSmh') or 0) + int(amount)
        fresh.append(row)
        changed = True

    wallets = econ.setdefault('wallets', {})
    for name in list(wallets):
        if name in (RESERVE, dest):
            continue
        key = ('billetera', name)
        amount = int(wallets.get(name) or 0)
        if key in done:
            if amount > 0 and eco.debit(econ, name, amount):
                changed = True
            continue
        if amount <= 0:
            continue
        if not eco.debit(econ, name, amount):
            continue
        eco.credit(econ, dest, amount)
        eco.append_tx(econ, {
            'type': 'fusion', 'from': name, 'to': dest,
            'amountSubs': amount, 'note': NOTE,
        }, now=now)
        remember('billetera', name, amount, name)

    box = econ.get('plata') if isinstance(econ.get('plata'), dict) else None
    if box is not None:
        key = ('fondo', POOL)
        pool = int(box.get('smcPoolSmh') or 0)
        if key in done:
            if pool > 0:
                box['smcPoolSmh'] = 0
                changed = True
        elif pool > 0:
            box['smcPoolSmh'] = 0
            eco.credit(econ, dest, pool)
            eco.append_tx(econ, {
                'type': 'fusion', 'from': POOL, 'to': dest,
                'amountSubs': pool, 'note': NOTE,
            }, now=now)
            remember('fondo', POOL, pool, POOL)

    deposits = (vault_state or {}).get('accounts') or {}
    for name, accbox in list(deposits.items()):
        if name == dest:
            continue
        key = ('deposito', name)
        amount = VAULT.smh_of(accbox)
        if key in done:
            if amount > 0 and VAULT.take_smc(accbox, amount):
                changed = True
            continue
        if amount <= 0:
            continue
        if not VAULT.take_smc(accbox, amount):
            continue
        eco.credit(econ, dest, amount)
        eco.append_tx(econ, {
            'type': 'fusion', 'from': 'deposito:' + name, 'to': dest,
            'amountSubs': amount, 'note': NOTE,
        }, now=now)
        remember('deposito', name, amount, 'deposito:' + name)

    if isinstance(vault_state, dict):
        swept = set(vault_state.get('fusionSwept') or [])
        swept.update(item['from'] for item in rec['transfers'] if item.get('where') == 'deposito')
        vault_state['fusionSwept'] = sorted(swept)
    eco.seal_if_due(econ, now=now, force=True)
    rec['status'] = 'done'
    rec['email'] = EMAIL
    rec['wallet'] = dest
    rec['reason'] = ''
    rec['ts'] = now
    changed = True
    return {'status': 'done', 'already': False, 'fresh': fresh, 'record': rec, 'changed': changed}
