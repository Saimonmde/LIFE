# SPDX-License-Identifier: AGPL-3.0-or-later
"""Qué llave de billetera corresponde a una cuenta.

La fusión dejó el saldo del fundador en ``saimon``. Si la cuenta luego
tomó el apodo Simon, la pantalla buscaba otra llave y mostraba cero.
"""
import accounts as acc


def _nombres(user, fallback=''):
    names = []
    if isinstance(user, dict):
        for key in (user.get('wallet_name'), user.get('name')):
            text = str(key or '').strip()
            if text and text not in names:
                names.append(text)
        if acc.is_owner(user):
            for extra in ('saimon', 'Simon', 'Saimon'):
                if extra not in names:
                    names.append(extra)
    fallback = str(fallback or '').strip()
    if fallback and fallback not in names:
        names.append(fallback)
    return names


def _total(econ, vault, name):
    wallets = (econ or {}).get('wallets') or {}
    box = ((vault or {}).get('accounts') or {}).get(name) or {}
    if not isinstance(box, dict):
        box = {}
    bank = box.get('smh')
    if bank is None:
        bank = box.get('smcSubs') or 0
    return int(wallets.get(name) or 0) + int(bank or 0)


def elegir(econ, vault, user, fallback=''):
    """La llave que de verdad tiene el saldo. No mueve monedas."""
    wallets = (econ or {}).get('wallets') or {}
    vaults = (vault or {}).get('accounts') or {}
    folded = {}
    for key in list(wallets) + list(vaults):
        folded.setdefault(str(key).casefold(), str(key))
    if isinstance(user, dict) and user.get('id'):
        canon = 'id:' + str(user['id'])
        if _total(econ, vault, canon) > 0:
            return canon
    best = ''
    best_n = -1
    for name in _nombres(user, fallback):
        hit = name if name in wallets or name in vaults else folded.get(name.casefold())
        if not hit:
            continue
        total = _total(econ, vault, hit)
        if total > best_n:
            best, best_n = hit, total
    if best:
        return best
    names = _nombres(user, fallback)
    return names[0] if names else ''


def correo_corto(email):
    """Correo enmascarado para saber con qué sesión se entró."""
    text = str(email or '').strip().lower()
    if '@' not in text:
        return ''
    user, _, host = text.partition('@')
    if not user or not host:
        return ''
    if len(user) <= 2:
        shown = user[:1] + '…'
    else:
        shown = user[:2] + '…' + user[-1:]
    return shown + '@' + host
