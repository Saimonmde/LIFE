# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lingotes del Banco Central. Un jugador no los acuña.

Cada alta queda en el registro propio del banco, aparte del libro de las monedas.
"""
import hmac
import os
import secrets

BANK = 'Banco Central de Saimon City'
METALS = ('oro', 'plata', 'cobre')


class BancoError(Exception):
    pass


def autorizado(token_header, user=None):
    """El token de admin o la cuenta creadora. Nadie más."""
    expected = os.environ.get('SIMON_ADMIN_TOKEN', '').strip()
    presented = str(token_header or '')
    if expected and len(presented) == len(expected) and hmac.compare_digest(presented, expected):
        return True
    if not isinstance(user, dict):
        return False
    role = str(user.get('role') or '')
    if user.get('creator') or role in ('creator', 'admin'):
        return True
    email = os.environ.get('SIMON_CREATOR_EMAIL', '').strip().lower()
    return bool(email and str(user.get('email') or '').strip().lower() == email)


def crear_lingotes(state, metal, qty, actor, now, game_date):
    metal = str(metal or '').strip().lower()
    if metal not in METALS:
        raise BancoError('El banco sólo hace lingotes de oro, plata o cobre.')
    if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1 or qty > 10000:
        raise BancoError('La cantidad de lingotes no es válida.')
    actor = str(actor or '').strip()[:64] or 'admin'
    item = 'lingote_' + metal
    import monedas as MONEDAS
    MONEDAS.anotar_lingotes(state, BANK, item, qty)
    book = state.get('bancoCentral')
    if not isinstance(book, dict):
        book = {'name': BANK, 'ingots': []}
        state['bancoCentral'] = book
    book['name'] = BANK
    book.setdefault('ingots', [])
    entry = {
        'id': 'LNG-' + secrets.token_hex(8),
        'item': item,
        'metal': metal,
        'qty': qty,
        'account': BANK,
        'actor': actor,
        'ts': int(now),
        'gameDate': str(game_date or '')[:80],
    }
    book['ingots'].append(entry)
    return dict(entry)
