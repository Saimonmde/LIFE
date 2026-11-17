# SPDX-License-Identifier: AGPL-3.0-or-later
"""Topes diarios y cuántos metales hacen una moneda.

Los números salen de aquí. Una variable de entorno los cambia sin tocar
el resto del juego. Los topes mundiales (21, 84 y 333 millones) no se mueven.

Oro: 10 minerales de oro = 1 Simoncoin (0,1 SMC cada uno). MINT_ORO_POR_MONEDA.
Plata: 4 minerales de plata = 1 Simonplata. MINT_PLATA_POR_MONEDA.
Cobre: 3 minerales de cobre = 1 Simonchis. MINT_COBRE_POR_MONEDA.

El tope de Simoncoin empieza en 0,25 al día y puede llegar a 6,25.
El de Simonplata empieza en 5. El de Simonchis es 200, sin crecimiento.
Se reinicia a las 00:00 UTC, las 7:00 p. m. en Bogotá.
"""
import os

import economy as _eco

# SPH por SMP. El oro usa economy.SMH_PER_SMC (100). No mezclar las dos escalas.
SUBS = 100_000_000
DAY = 86400
RESET_LABEL = '7:00 p. m. Bogotá (00:00 UTC)'

DEFAULT_ORO_POR_MONEDA = 10
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
# Segundos que tarda una veta picada en volver. El cliente usa los mismos milisegundos.
VEIN_ORO_S = 32
VEIN_PLATA_S = 18
VEIN_COBRE_S = 18

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
    return int(round(float(smc) * _eco.SMH_PER_SMC))


def _sph(smp):
    return int(round(float(smp) * SUBS))


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
    base = _sph(_float_env('MINT_SIMONPLATA_BASE_SMP', DEFAULT_SIMONPLATA_BASE))
    age = _sph(_float_env('MINT_SIMONPLATA_AGE_SMP', DEFAULT_SIMONPLATA_AGE))
    play = _sph(_float_env('MINT_SIMONPLATA_PLAY_SMP', DEFAULT_SIMONPLATA_PLAY))
    quest = _sph(_float_env('MINT_SIMONPLATA_QUEST_SMP', DEFAULT_SIMONPLATA_QUEST))
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


def _cantidad(number):
    number = float(number)
    if abs(number - round(number)) < 1e-6:
        whole = int(round(number))
        return f'{whole:,}'.replace(',', '.')
    text = f'{number:.2f}'.rstrip('0').rstrip('.')
    whole, frac = text.split('.')
    return f'{int(whole):,}'.replace(',', '.') + ',' + frac


def _techo_simoncoin():
    days = _int_env('MINT_AGE_DAYS', DEFAULT_AGE_DAYS)
    hours = _int_env('MINT_PLAY_HOURS', DEFAULT_PLAY_HOURS)
    quests = _int_env('MINT_QUEST_CAP', DEFAULT_QUEST_CAP)
    return simoncoin_daily_smh(days * DAY, hours * 3600, quests) / _eco.SMH_PER_SMC


def _techo_simonplata():
    days = _int_env('MINT_AGE_DAYS', DEFAULT_AGE_DAYS)
    hours = _int_env('MINT_PLAY_HOURS', DEFAULT_PLAY_HOURS)
    quests = _int_env('MINT_QUEST_CAP', DEFAULT_QUEST_CAP)
    return simonplata_daily_sph(days * DAY, hours * 3600, quests) / SUBS


def siguiente(age_seconds, play_seconds, quests):
    """El próximo peldaño del tope, con los mismos días, horas y misiones de _growth."""
    age_seconds = max(0, int(age_seconds or 0))
    play_seconds = max(0, int(play_seconds or 0))
    quests = max(0, int(quests or 0))
    days, hours, done = _growth(age_seconds, play_seconds, quests)
    max_days = _int_env('MINT_AGE_DAYS', DEFAULT_AGE_DAYS)
    max_hours = _int_env('MINT_PLAY_HOURS', DEFAULT_PLAY_HOURS)
    max_quests = _int_env('MINT_QUEST_CAP', DEFAULT_QUEST_CAP)
    now_smc = simoncoin_daily_smh(age_seconds, play_seconds, quests) / _eco.SMH_PER_SMC
    now_smp = simonplata_daily_sph(age_seconds, play_seconds, quests) / SUBS
    steps = []

    def add(kind, wait, future_age, future_play, future_quests, when):
        smc = simoncoin_daily_smh(future_age, future_play, future_quests) / _eco.SMH_PER_SMC - now_smc
        smp = simonplata_daily_sph(future_age, future_play, future_quests) / SUBS - now_smp
        steps.append({
            'kind': kind,
            'wait': wait,
            'simoncoin': smc,
            'simonplata': smp,
            'text': when + ' Sumas ' + _cantidad(smc) + ' de Simoncoin y ' + _cantidad(smp) + ' de Simonplata al tope del día.',
        })

    if days < max_days:
        wait = DAY - (age_seconds % DAY)
        add('edad', wait, age_seconds + wait, play_seconds, quests, 'El siguiente peldaño llega con un día más de cuenta.')
    if hours < max_hours:
        wait = 3600 - (play_seconds % 3600)
        add('juego', wait, age_seconds, play_seconds + wait, quests, 'El siguiente peldaño llega con una hora más de juego.')
    if done < max_quests:
        add('mision', None, age_seconds, play_seconds, quests + 1, 'El siguiente peldaño llega al completar una misión más.')
    if not steps:
        steps.append({
            'kind': 'listo',
            'wait': None,
            'simoncoin': 0,
            'simonplata': 0,
            'text': 'Ya llegaste al tope de recompensas de Simoncoin y Simonplata.',
        })
    return steps


def hoy(coins):
    """'Hoy te quedan X' a partir de los cupos ya calculados. Sin números fijos."""
    lines = []
    for coin in ('simoncoin', 'simonplata', 'simonchis'):
        row = (coins or {}).get(coin) or {}
        if 'left' not in row:
            continue
        lines.append('Hoy te quedan ' + _cantidad(row['left']) + ' ' + row.get('name', coin) + '.')
    return lines


def letrero(age_seconds=0, play_seconds=0, quests=0, now=None):
    """Texto del letrero de la mina. Los números salen de estas funciones."""
    import time as _time
    import economy
    import plata
    import cobre
    now = int(_time.time() if now is None else now)
    oro = rate('simoncoin')
    plata_rate = rate('simonplata')
    cobre_rate = rate('simonchis')
    oro_base = simoncoin_daily_smh(0, 0, 0) / _eco.SMH_PER_SMC
    oro_top = _techo_simoncoin()
    plata_base = simonplata_daily_sph(0, 0, 0) / SUBS
    plata_top = _techo_simonplata()
    chis = simonchis_daily()
    bono_dia = _float_env('MINT_SIMONPLATA_AGE_SMP', DEFAULT_SIMONPLATA_AGE)
    bono_hora = _float_env('MINT_SIMONPLATA_PLAY_SMP', DEFAULT_SIMONPLATA_PLAY)
    bono_mision = _float_env('MINT_SIMONPLATA_QUEST_SMP', DEFAULT_SIMONPLATA_QUEST)
    lines = [
        'Bienvenido. Acá se pica el mineral y se acuñan las monedas del juego. No son dinero real.',
        (
            f'Picar no tiene tope. Podés picar las veces que quieras. El mineral queda en la mochila y picar no crea monedas. '
            f'Si una veta de oro se agota, vuelve en {_cantidad(VEIN_ORO_S)} segundos. '
            f'La plata vuelve en {_cantidad(VEIN_PLATA_S)} segundos y el cobre en {_cantidad(VEIN_COBRE_S)} segundos.'
        ),
        f'{_cantidad(oro)} minerales de oro hacen 1 Simoncoin (cada uno vale 0,1 SMC). El servidor aplica un piso de 50 SMC al día; la fórmula sola iría de {_cantidad(oro_base)} a {_cantidad(oro_top)}.',
        (
            f'{_cantidad(plata_rate)} de plata cruda hacen 1 Simonplata. Hasta {_cantidad(plata_base)} Simonplata al día, más bonos: '
            f'{_cantidad(bono_dia)} por día de cuenta, {_cantidad(bono_hora)} por hora de juego y {_cantidad(bono_mision)} por misión. '
            f'Con esos bonos sube hasta {_cantidad(plata_top)}.'
        ),
        f'{_cantidad(cobre_rate)} de cobre crudo hacen 1 Simonchis. El tope es {_cantidad(chis)} al día.',
        'Para acuñar tenés que entrar con tu apodo. El cupo se reinicia a las ' + RESET_LABEL + '.',
        (
            f'Hay tres monedas y el total ya está fijo: {_cantidad(economy.MAX_SUPPLY)} de Simoncoin, '
            f'{_cantidad(plata.MAX_SUPPLY)} de Simonplata y {_cantidad(cobre.MAX_SUPPLY)} de Simonchis. '
            'No se puede crear más ni copiarlas. Si el mundo ya llegó al máximo, el horno se detiene.'
        ),
    ]
    return {
        'lines': lines,
        'veins': {'oro': VEIN_ORO_S, 'plata': VEIN_PLATA_S, 'cobre': VEIN_COBRE_S},
        'reset': RESET_LABEL,
        'rates': {'simoncoin': oro, 'simonplata': plata_rate, 'simonchis': cobre_rate},
        'daily': {'simoncoin': oro_base, 'simoncoinMax': oro_top, 'simonplata': plata_base, 'simonplataMax': plata_top, 'simonchis': chis},
        'supply': {'simoncoin': economy.MAX_SUPPLY, 'simonplata': plata.MAX_SUPPLY, 'simonchis': cobre.MAX_SUPPLY},
        'resetAt': next_reset(now),
        'steps': siguiente(age_seconds, play_seconds, quests),
    }
