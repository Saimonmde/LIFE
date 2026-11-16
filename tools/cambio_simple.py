# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cambio simple: mueve monedas o metal que ya existen. No acuña."""
import economy as eco

SUBS = eco.SUBS
# 100 Simonplata = 1 Simoncoin. Igual que el fondo de plata.
SMP_POR_SMC = 100
# El puesto ya paga esto por cada mineral. No es una emisión nueva.
MINERAL_SMH = 1_000_000
MINERALES = {
    'mineral_cobre': 'cobre',
    'mineral_plata': 'plata',
    'mineral_oro': 'oro',
}
DAR = ('simonplata',) + tuple(MINERALES)
RECIBIR = ('simoncoin',) + tuple(MINERALES) + ('simonplata', 'simonchis')


def _texto(das, nombre_das, recibes, nombre_recibes, extra=''):
    base = f'Das {das} {nombre_das}. Recibes {recibes} {nombre_recibes}.'
    return (base + (' ' + extra if extra else '')).strip()


def quote(give, receive, qty, have, fondo_smh=0, puesto_smh=0):
    """Calcula el cambio. Si crearía monedas o metal, no se puede."""
    give = str(give or '')
    receive = str(receive or '')
    try:
        qty = int(qty or 0)
        have = int(have or 0)
        fondo_smh = int(fondo_smh or 0)
        puesto_smh = int(puesto_smh or 0)
    except (TypeError, ValueError):
        qty = have = fondo_smh = puesto_smh = 0
    if give == receive:
        return _no('Elige dos cosas distintas.')
    if receive != 'simoncoin':
        return _no('Eso crearía monedas o metal nuevo. Aquí solo se mueve lo que ya existe.')
    if give == 'simonplata':
        fondo = max(0, fondo_smh // SUBS)
        maximo = max(0, min(have // SMP_POR_SMC, fondo))
        usado = max(0, min(max(0, qty) // SMP_POR_SMC, maximo))
        return {
            'ok': usado > 0,
            'das': usado * SMP_POR_SMC,
            'recibes': usado,
            'maximo': maximo * SMP_POR_SMC,
            'texto': _texto(usado * SMP_POR_SMC, 'Simonplata', usado, 'Simoncoin',
                            'El oro sale de monedas que ya existían.'),
        }
    if give in MINERALES:
        precio = MINERAL_SMH
        cabe = max(0, puesto_smh // precio)
        maximo = max(0, min(have, cabe))
        usado = max(0, min(max(0, qty), maximo))
        smh = usado * precio
        return {
            'ok': usado > 0,
            'das': usado,
            'recibes_smh': smh,
            'recibes': smh / SUBS,
            'maximo': maximo,
            'texto': _texto(usado, 'de ' + MINERALES[give], _smc(smh), 'Simoncoin',
                            'El puesto paga con monedas que ya tenía.'),
        }
    return _no('Eso no se puede cambiar.')


def _smc(smh):
    whole = smh // SUBS
    frac = smh % SUBS
    if not frac:
        return str(whole)
    text = f'{whole},{frac:08d}'.rstrip('0')
    return text


def _no(texto):
    return {'ok': False, 'das': 0, 'recibes': 0, 'maximo': 0, 'texto': texto}


def mover_mineral(econ, name, qty):
    """Pasa SMC del puesto al jugador. No cambia la suma de las billeteras."""
    qty = int(qty or 0)
    smh = qty * MINERAL_SMH
    if qty < 1 or smh < 1:
        raise ValueError('Nada que cambiar.')
    if not eco.debit(econ, 'puesto_frutas', smh):
        raise ValueError('El puesto no tiene monedas. No se movió nada.')
    eco.credit(econ, name, smh)
    return smh
