# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mueve todo el SMC de un jugador entre su billetera y su banco.

No acuña, no toca la plata ni el cobre, y no sale del juego.
Si la billetera o el banco no existen, se crean vacíos.
"""
import economy as eco
import vault


def trasladar(econ, vault_state, name, dest):
    """Pasa el saldo entero. La segunda vez, con el origen ya en cero, no duplica."""
    name = str(name or '').strip()
    if not name:
        return {'ok': False, 'reason': 'Falta el nombre de la cuenta.', 'smh': 0}
    dest = 'banco' if str(dest or '') in ('banco', 'bank') else 'billetera'
    wallets = econ.setdefault('wallets', {})
    wallets.setdefault(name, 0)
    box = vault.account(vault_state, name)
    if dest == 'banco':
        smh = int(wallets.get(name) or 0)
        if smh <= 0:
            return {'ok': False, 'reason': 'No hay SMC en la billetera para transferir.', 'smh': 0, 'dest': dest}
        if not eco.debit(econ, name, smh):
            return {'ok': False, 'reason': 'No hay SMC en la billetera para transferir.', 'smh': 0, 'dest': dest}
        vault.add_smc(box, smh)
        note = 'Transferir todo al banco'
        origin, target = name, 'deposito'
    else:
        smh = vault.smh_of(box)
        if smh <= 0 or not vault.take_smc(box, smh):
            return {'ok': False, 'reason': 'No hay SMC en el banco para transferir.', 'smh': 0, 'dest': dest}
        eco.credit(econ, name, smh)
        note = 'Transferir todo a la billetera'
        origin, target = 'deposito', name
    eco.append_tx(econ, {
        'type': 'bank', 'from': origin, 'to': target, 'amountSubs': int(smh), 'note': note,
    })
    return {
        'ok': True,
        'smh': int(smh),
        'dest': dest,
        'from': origin if origin != 'deposito' else 'deposito:' + name,
        'to': target if target != 'deposito' else 'deposito:' + name,
        'note': note,
        'walletSmh': int(wallets.get(name) or 0),
        'bankSmh': vault.smh_of(box),
    }
