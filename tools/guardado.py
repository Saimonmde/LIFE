#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""La partida de una cuenta, organizada.

La identidad es el id de la cuenta (la misma sesión del login: nick,
contraseña o Google). El navegador no elige ese id y no puede sumar
monedas al volver a sincronizar.
"""
import partida


def saldos(econ, name):
    """Lee las tres monedas que ya están en el libro. No acuña."""
    econ = econ if isinstance(econ, dict) else {}
    name = str(name or '')
    oro = int((econ.get('wallets') or {}).get(name) or 0)
    plata = int(((econ.get('plata') or {}).get('wallets') or {}).get(name) or 0)
    cobre = int(((econ.get('simonchis') or {}).get('wallets') or {}).get(name) or 0)
    return {'simoncoin': oro, 'simonplata': plata, 'simonchis': cobre}


def recall(user, econ=None):
    shown = partida.recall(user)
    shown['monedas'] = saldos(econ, user.get('wallet_name') or user.get('name') if isinstance(user, dict) else '')
    shown['finquita'] = 'en la cuenta'
    return shown


def remember(user, raw, econ=None):
    """Guarda y devuelve la partida. No escribe en el libro de monedas."""
    partida.remember(user, raw)
    return recall(user, econ)
