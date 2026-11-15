# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reloj único de Saimon City.

El día cero es el 1 de enero de 1777. Cada 20 minutos reales son un día
de juego. El ancla es un instante del servidor, el mismo para todos.
No usa el reloj de cada navegador.
"""
import os
from datetime import datetime, timedelta, timezone

START = datetime(1777, 1, 1, tzinfo=timezone.utc)
REAL_SECONDS_PER_DAY = 20 * 60
# Instante de este despliegue. GAME_CLOCK_EPOCH, si es un entero válido, lo sustituye.
DEPLOY_EPOCH = 1794714051
MESES = (
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
)


def _positive(raw):
    try:
        number = int(str(raw).strip())
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


def resolve_epoch(saved=None, env=None):
    """Elige un ancla fija. Una variable vacía o ilegible no mueve el reloj."""
    for raw in (env, saved, DEPLOY_EPOCH):
        number = _positive(raw)
        if number:
            return number
    return DEPLOY_EPOCH


def anchor(state, env=None):
    """Guarda el ancla en el estado del servidor. Devuelve (época, cambió)."""
    if env is None:
        env = os.environ.get('GAME_CLOCK_EPOCH')
    chosen = resolve_epoch(state.get('relojEpoch'), env)
    changed = int(state.get('relojEpoch') or 0) != chosen
    state['relojEpoch'] = chosen
    return chosen, changed


def describe(now, epoch):
    """Fecha y hora de juego a partir del reloj del servidor."""
    elapsed = max(0.0, float(now) - float(epoch))
    moment = START + timedelta(seconds=elapsed * 86400.0 / REAL_SECONDS_PER_DAY)
    fecha = f'{moment.day} de {MESES[moment.month - 1]} de {moment.year}'
    hora = f'{moment.hour:02d}:{moment.minute:02d}'
    return {
        'epoch': int(epoch),
        'serverNow': int(now),
        'fecha': fecha,
        'hora': hora,
        'label': f'{fecha} · {hora}',
    }


def payload(state, now=None):
    import time
    now = time.time() if now is None else now
    epoch, _changed = anchor(state)
    return describe(now, epoch)
