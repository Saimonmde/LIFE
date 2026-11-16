# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pasa SMC ya minado al banco de Jay. No se ejecuta solo y no toca producción.

Por defecto es un ensayo: imprime lo que movería y no escribe nada.
El destino es siempre el banco (el depósito), nunca la billetera.

  python3 tools/mover_al_banco.py
  python3 tools/mover_al_banco.py --scope all
  python3 tools/mover_al_banco.py --scope jay --apply

--scope jay mueve sólo la billetera del personaje de Jay.
--scope all mueve las billeteras de los jugadores (no la reserva ni el puesto).
Si DATABASE_URL está puesta, el programa se niega: esa base puede ser la de producción.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import economy as eco
import fusion
import vault

RESERVE = {'tesoro_genesis', 'puesto_frutas', 'fondo_cambio', 'casa_de_contratacion'}


def founder_name(accounts, wallets=None):
    user = fusion.find_founder(accounts or {})
    name = fusion.wallet_of(user)
    if name:
        return name
    wallets = wallets or {}
    folded = {str(key).casefold(): key for key in wallets}
    for candidate in ('jay', 'simon'):
        if candidate in folded:
            return folded[candidate]
    return 'Jay'


def plan(econ, vault_state, accounts, scope='jay', dest=None):
    """Lista lo que se movería. No escribe."""
    scope = 'all' if str(scope or '') == 'all' else 'jay'
    wallets = (econ or {}).get('wallets') or {}
    dest = str(dest or founder_name(accounts, wallets) or 'Jay')
    if scope == 'jay':
        names = [dest]
    else:
        names = [name for name in wallets if name not in RESERVE]
        if dest not in names:
            names.append(dest)
    rows = []
    for name in names:
        if name in RESERVE:
            continue
        smh = int(wallets.get(name) or 0)
        if smh <= 0:
            continue
        rows.append({
            'from': name,
            'bank': dest,
            'smh': smh,
            'smc': eco.format_smc(smh),
            'where': 'billetera → banco de ' + dest,
        })
    return {'scope': scope, 'dest': dest, 'rows': rows, 'dryRun': True}


def apply_plan(econ, vault_state, accounts, scope='jay', dest=None):
    """Mueve cada billetera al banco de Jay y lo anota en el libro mayor. No acuña."""
    planned = plan(econ, vault_state, accounts, scope=scope, dest=dest)
    done = []
    bank = vault.account(vault_state, planned['dest'])
    for row in planned['rows']:
        before_wallet = int((econ.get('wallets') or {}).get(row['from']) or 0)
        before_bank = vault.smh_of(bank)
        smh = int(row['smh'])
        if not eco.debit(econ, row['from'], smh):
            print(f"[banco] {row['from']}: no se pudo debitar {smh} SMH. No se movió.", flush=True)
            continue
        vault.add_smc(bank, smh)
        eco.append_tx(econ, {
            'type': 'bank',
            'from': row['from'],
            'to': 'deposito:' + planned['dest'],
            'amountSubs': smh,
            'note': 'SMC minado al banco de Jay',
        })
        after_bank = vault.smh_of(bank)
        print(
            f"[banco] {row['from']}: antes billetera {before_wallet} SMH, banco {before_bank} SMH; "
            f"después billetera {int((econ.get('wallets') or {}).get(row['from']) or 0)} SMH, "
            f"banco {after_bank} SMH ({eco.format_smc(smh)} al banco, no a la billetera).",
            flush=True,
        )
        done.append(dict(row, bankSmh=after_bank))
    return {'scope': planned['scope'], 'dest': planned['dest'], 'rows': done, 'dryRun': False}


def _load_local(root):
    import persist
    eco_path = os.path.join(root, 'state', 'economy.json')
    vault_path = os.path.join(root, 'state', 'vault.json')
    accounts_path = os.path.join(root, 'state', 'accounts.json')
    econ = persist.load_named('economy', eco_path) or eco.empty_state()
    box = persist.load_named('vault', vault_path) or vault.empty()
    accounts = persist.load_named('accounts', accounts_path) or {'users': []}
    return econ, box, accounts, eco_path, vault_path


def main(argv=None):
    parser = argparse.ArgumentParser(description='Mover SMC minado al banco de Jay (ensayo por defecto).')
    parser.add_argument('--scope', choices=('jay', 'all'), default='jay')
    parser.add_argument('--dest', default='', help='Nombre de la billetera de Jay, si no es la del fundador.')
    parser.add_argument('--apply', action='store_true', help='Escribe el ensayo. Sin esto no se mueve nada.')
    parser.add_argument('--state-dir', default='', help='Carpeta con state/. Por defecto, la raíz del juego.')
    args = parser.parse_args(argv)
    if os.environ.get('DATABASE_URL', '').strip():
        print('DATABASE_URL está puesta. No se lee ni se escribe esa base. Quítala para usar sólo el JSON local.', flush=True)
        return 2
    root = args.state_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    econ, box, accounts, eco_path, vault_path = _load_local(root)
    planned = plan(econ, box, accounts, scope=args.scope, dest=args.dest or None)
    print(f"Ensayo. Alcance: {planned['scope']}. Banco de: {planned['dest']}.", flush=True)
    if not planned['rows']:
        print('No hay SMC en billetera para mover.', flush=True)
    for row in planned['rows']:
        print(f"  {row['from']}: {row['smc']} ({row['smh']} SMH) {row['where']}", flush=True)
    if not args.apply:
        print('Ensayo solamente. No se escribió nada. Para mover: --apply', flush=True)
        return 0
    apply_plan(econ, box, accounts, scope=args.scope, dest=args.dest or None)
    import persist
    persist.save_named('economy', eco_path, econ)
    persist.save_named('vault', vault_path, box)
    print('Listo. El SMC quedó en el banco, no en la billetera.', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
