# SPDX-License-Identifier: AGPL-3.0-or-later
"""Filomancia: hacer fuego y, al final, fuegos artificiales.

La fogata gasta una madera y dura un minuto. El encendedor no se gasta.
Los fuegos artificiales solo se lanzan en el nivel maestro.
"""
DURACION = 60
BRASAS = 8
ALCANCE = 48
XP_FOGATA = 8
XP_FUEGOS = 12
MAESTRO = 5
RANGOS = (
    (1, 'Hacer fuego'),
    (2, 'Mantener la llama'),
    (3, 'Brasas'),
    (4, 'Chispa alta'),
    (5, 'Fuegos artificiales'),
)


def nivel(xp):
    return int((max(0, int(xp)) / 25) ** 0.5) + 1


def rango(xp):
    nombre = RANGOS[0][1]
    actual = nivel(xp)
    for umbral, titulo in RANGOS:
        if actual >= umbral:
            nombre = titulo
    return nombre


def puede_fuegos(xp):
    return nivel(xp) >= MAESTRO


def preparar(tiene_encendedor, madera, ya_arde):
    if not tiene_encendedor:
        return None, 'Te falta el encendedor.'
    if int(madera or 0) < 1:
        return None, 'Te falta madera cortada.'
    if ya_arde:
        return None, 'Ya hay una fogata tuya ardiendo.'
    return {'madera': 1, 'segundos': DURACION, 'xp': XP_FOGATA}, ''


def lanzar(xp):
    if not puede_fuegos(xp):
        return None, 'Los fuegos artificiales son el nivel maestro de Filomancia.'
    return {'segundos': 8, 'xp': XP_FUEGOS}, ''


def fase(restante):
    if restante <= 0:
        return 'apagada'
    if restante <= BRASAS:
        return 'brasas'
    return 'llama'


def ve(ox, oy, oz, fx, fy, fz):
    if oz != fz:
        return False
    return (float(ox) - float(fx)) ** 2 + (float(oy) - float(fy)) ** 2 <= ALCANCE ** 2
