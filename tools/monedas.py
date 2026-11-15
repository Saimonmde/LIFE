# SPDX-License-Identifier: AGPL-3.0-or-later
"""Las tres monedas y el libro que ve todo el mundo.

Simoncoin: 21.000.000. Simonplata: 84.000.000. Simonchis: 333.000.000.
El libro muestra lo acuñado frente al máximo. Pasado el máximo, no se acuña.
"""
import economy as eco
import plata
import cobre

SIMONCOIN_MAX = eco.MAX_SUPPLY
SIMONPLATA_MAX = plata.MAX_SUPPLY
SIMONCHIS_MAX = cobre.MAX_SUPPLY


def _whole(base, subunits):
    base = int(base or 0)
    whole, frac = divmod(abs(base), subunits)
    if frac == 0:
        return whole
    return whole + frac / subunits


def anotar_lingotes(state, name, item, qty):
    """Guarda lingotes acuñados. No son una de las tres monedas."""
    box = state.get('foundry')
    if not isinstance(box, dict):
        box = {'minted': {}, 'players': {}}
        state['foundry'] = box
    box.setdefault('minted', {})
    box.setdefault('players', {})
    qty = int(qty or 0)
    if qty <= 0 or not item:
        return 0
    box['minted'][item] = int(box['minted'].get(item) or 0) + qty
    player = box['players'].setdefault(str(name or ''), {})
    player[item] = int(player.get(item) or 0) + qty
    return qty


def ledger(state, name=None, account=None):
    """Totales acuñados y, si hay jugador, su saldo. Los topes no se mueven."""
    cobre.ensure(state)
    mined = int(state.get('minedSmh') or 0)
    sph = int((state.get('plata') or {}).get('minedSph') or 0)
    chis = int((state.get('simonchis') or {}).get('minted') or 0)
    coins = [
        {
            'id': 'simoncoin',
            'name': 'Simoncoin',
            'minted': _whole(mined, eco.SUBS),
            'mintedBase': mined,
            'max': SIMONCOIN_MAX,
        },
        {
            'id': 'simonplata',
            'name': 'Simonplata',
            'minted': _whole(sph, plata.SUBS),
            'mintedBase': sph,
            'max': SIMONPLATA_MAX,
        },
        {
            'id': 'simonchis',
            'name': 'Simonchis',
            'minted': chis,
            'mintedBase': chis,
            'max': SIMONCHIS_MAX,
        },
    ]
    out = {'coins': coins, 'foundry': (state.get('foundry') or {}).get('minted') or {}}
    if name:
        chis_name = cobre.balance_of(state, name)
        chis_account = cobre.balance_of(state, account) if account else 0
        out['balances'] = {
            'simoncoin': int((state.get('wallets') or {}).get(name) or 0),
            'simonplata': plata.balance_of(state, name),
            'simonchis': max(chis_name, chis_account),
        }
    return out
