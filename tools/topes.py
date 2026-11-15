# SPDX-License-Identifier: AGPL-3.0-or-later
"""Topes diarios y cuántos metales hacen una moneda.

Los números salen de aquí. Una variable de entorno los cambia sin tocar
el resto del juego. Los topes mundiales (21, 84 y 333 millones) no se mueven.

Oro: 5 oros crudos (pepitas) = 1 Simoncoin. MINT_ORO_POR_MONEDA.
Plata: 4 minerales de plata = 1 Simonplata. MINT_PLATA_POR_MONEDA.
Cobre: 3 minerales de cobre = 1 Simonchis. MINT_COBRE_POR_MONEDA.

El tope de Simoncoin empieza en 0,25 al día y puede llegar a 6,25.
El de Simonplata empieza en 5. El de Simonchis es 200, sin crecimiento.
Se reinicia a las 00:00 UTC, las 7:00 p. m. en Bogotá.
"""
import os

SUBS = 100_000_000
DAY = 86400
RESET_LABEL = '7:00 p. m. Bogotá (00:00 UTC)'

DEFAULT_ORO_POR_MONEDA = 5
DEFAULT_PLATA_POR_MONEDA = 4
DEFAULT_COBRE_POR_MONEDA = 3

DEFAULT_SIMONCOIN_BASE = 0.25
DEFAULT_SIMONCOIN_AGE = 0.05
DEFAULT_SIMONCOIN_PLAY = 0.05
DEFAULT_SIMONCOIN_QUEST = 0.10
DEFAULT_SIMONPLATA_BASE = 5
DEFAULT_SIMONPLATA_AGE = 1
DEFAULT_SIMONPLATA_PLAY = 1
DEFAULT_SIMONPLATA_QUEST = 2
DEFAULT_SIMONCHIS = 200
DEFAULT_AGE_DAYS = 60
DEFAULT_PLAY_HOURS = 40
DEFAULT_QUEST_CAP = 10

METALES = {
    'simoncoin': {
        'item': 'pepita_oro',
        'items': ('pepita_oro', 'mineral_oro'),
        'env': 'MINT_ORO_POR_MONEDA',
        'default': DEFAULT_ORO_POR_MONEDA,
        'name': 'Simoncoin',
        'metal': 'oros crudos',
    },
    'simonplata': {
        'item': 'mineral_plata',
        'env': 'MINT_PLATA_POR_MONEDA',
        'default': DEFAULT_PLATA_POR_MONEDA,
        'name': 'Simonplata',
        'metal': 'plata cruda',
    },
    'simonchis': {
        'item': 'mineral_cobre',
        'env': 'MINT_COBRE_POR_MONEDA',
        'default': DEFAULT_COBRE_POR_MONEDA,
        'name': 'Simonchis',
        'metal': 'cobre crudo',
    },
}


def _float_env(name, default):
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == '':
        return float(default)
    try:
        return float(str(raw).strip().replace(',', '.'))
    except ValueError:
        return float(default)


def _int_env(name, default):
    number = _float_env(name, default)
    return int(number) if number > 0 else int(default)


def _smh(smc):
    return int(round(float(smc) * SUBS))


def rate(coin):
    spec = METALES.get(coin) or {}
    return _int_env(spec.get('env') or '', spec.get('default') or 1)


def metal(coin):
    spec = METALES.get(coin)
    if not spec:
        return None
    items = tuple(spec.get('items') or (spec['item'],))
    return dict(spec, rate=rate(coin), items=items)


def _growth(age_seconds, play_seconds, quests):
    days = min(_int_env('MINT_AGE_DAYS', DEFAULT_AGE_DAYS), max(0, int(age_seconds)) // DAY)
    hours = min(_int_env('MINT_PLAY_HOURS', DEFAULT_PLAY_HOURS), max(0, int(play_seconds)) // 3600)
    done = min(_int_env('MINT_QUEST_CAP', DEFAULT_QUEST_CAP), max(0, int(quests)))
    return days, hours, done


def simoncoin_daily_smh(age_seconds, play_seconds, quests):
    days, hours, done = _growth(age_seconds, play_seconds, quests)
    base = _smh(_float_env('MINT_SIMONCOIN_BASE_SMC', DEFAULT_SIMONCOIN_BASE))
    age = _smh(_float_env('MINT_SIMONCOIN_AGE_SMC', DEFAULT_SIMONCOIN_AGE))
    play = _smh(_float_env('MINT_SIMONCOIN_PLAY_SMC', DEFAULT_SIMONCOIN_PLAY))
    quest = _smh(_float_env('MINT_SIMONCOIN_QUEST_SMC', DEFAULT_SIMONCOIN_QUEST))
    return base + days * age + hours * play + done * quest


def simonplata_daily_sph(age_seconds, play_seconds, quests):
    days, hours, done = _growth(age_seconds, play_seconds, quests)
    base = _smh(_float_env('MINT_SIMONPLATA_BASE_SMP', DEFAULT_SIMONPLATA_BASE))
    age = _smh(_float_env('MINT_SIMONPLATA_AGE_SMP', DEFAULT_SIMONPLATA_AGE))
    play = _smh(_float_env('MINT_SIMONPLATA_PLAY_SMP', DEFAULT_SIMONPLATA_PLAY))
    quest = _smh(_float_env('MINT_SIMONPLATA_QUEST_SMP', DEFAULT_SIMONPLATA_QUEST))
    return base + days * age + hours * play + done * quest


def simonchis_daily():
    return _int_env('MINT_SIMONCHIS_DAILY', DEFAULT_SIMONCHIS)


def next_reset(now):
    now = int(now)
    return (now // DAY + 1) * DAY


def cotizar(have, rate_n, daily_left, global_left, pieces=None, whole=False):
    """Cuántas monedas salen, sin pasar el día ni el mundo.

    El tope se puede usar entero aunque no sea un número cabal de pepitas:
    0,25 Simoncoin gasta 1,25 oros. Con `whole`, el cobre sigue en monedas enteras.
    """
    have = max(0.0, float(have or 0))
    rate_n = max(1, int(rate_n or 1))
    daily_left = max(0.0, float(daily_left or 0))
    global_left = max(0.0, float(global_left or 0))
    alcanzan = have / rate_n
    techo = min(alcanzan, daily_left, global_left)
    max_pieces = min(have, techo * rate_n)
    if whole:
        max_pieces = (int(max_pieces) // rate_n) * rate_n
    if pieces is None:
        pieces = max_pieces
    else:
        pieces = max(0.0, min(have, float(pieces), max_pieces))
    if whole:
        pieces = (int(pieces) // rate_n) * rate_n
    recibes = pieces / rate_n
    return {
        'tienes': have,
        'rate': rate_n,
        'alcanzan': alcanzan,
        'hoy': daily_left,
        'mundo': global_left,
        'maxPieces': max_pieces,
        'gastas': pieces,
        'recibes': recibes,
        'sobran': have - pieces,
    }
