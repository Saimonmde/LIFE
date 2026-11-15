# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cadena de series de las tres monedas. Sólo se añade. El tope no se puede subir.

Cada lote acuñado lleva un rango de series, la cuenta que acuñó, la hora real,
la fecha del juego y un hash que encadena el lote anterior.
"""
import hashlib
import threading

GENESIS = '0' * 64
LOCK = threading.Lock()

# Topes fijos. No hay función que los cambie.
CAPS = {
    'simoncoin': 21_000_000 * 100_000_000,
    'simonplata': 84_000_000 * 100_000_000,
    'simonchis': 333_000_000,
}
PREFIX = {'simoncoin': 'SMC', 'simonplata': 'SMP', 'simonchis': 'SCH'}


class SerieError(Exception):
    pass


def _box(state):
    box = state.get('serie')
    if not isinstance(box, dict):
        box = {'entries': [], 'cursor': {}}
        state['serie'] = box
    box.setdefault('entries', [])
    box.setdefault('cursor', {})
    return box


def _canon(entry):
    return '|'.join((
        entry['id'], entry['coin'], str(entry['serialFrom']), str(entry['serialTo']),
        entry['minter'], str(entry['ts']), entry['gameDate'], entry['prev'],
    ))


def _digest(entry):
    return hashlib.sha256(_canon(entry).encode('utf-8')).hexdigest()


def record(state, coin, qty, minter, now, game_date):
    """Anota un lote. `qty` va en la unidad mínima (SMH, SPH o Simonchis enteros)."""
    coin = str(coin or '')
    if coin not in CAPS:
        raise SerieError('esa moneda no existe')
    if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1:
        raise SerieError('la cantidad no es válida')
    minter = str(minter or '').strip()[:64]
    if not minter:
        raise SerieError('falta la cuenta que acuña')
    game_date = str(game_date or '').strip()[:80]
    now = int(now)
    with LOCK:
        box = _box(state)
        cursor = int(box['cursor'].get(coin) or 0)
        start = cursor + 1
        end = cursor + qty
        if end > CAPS[coin]:
            raise SerieError('ese lote pasaría el tope')
        prev = box['entries'][-1]['hash'] if box['entries'] else GENESIS
        entry = {
            'id': f'{PREFIX[coin]}-{start}',
            'coin': coin,
            'serialFrom': start,
            'serialTo': end,
            'minter': minter,
            'ts': now,
            'gameDate': game_date,
            'prev': prev,
        }
        entry['hash'] = _digest(entry)
        if any(item.get('id') == entry['id'] for item in box['entries']):
            raise SerieError('esa serie ya existe')
        box['entries'].append(entry)
        box['cursor'][coin] = end
        return dict(entry)


def undo_last(state, ident):
    """Quita el último lote si es el que se acaba de anotar y el resto falló."""
    with LOCK:
        box = _box(state)
        entries = box['entries']
        if not entries or entries[-1].get('id') != ident:
            return False
        last = entries.pop()
        coin = last['coin']
        box['cursor'][coin] = int(last['serialFrom']) - 1
        if box['cursor'][coin] <= 0:
            box['cursor'].pop(coin, None)
        return True


def lookup(state, coin, serial):
    coin = str(coin or '')
    serial = int(serial)
    for entry in _box(state)['entries']:
        if entry['coin'] == coin and entry['serialFrom'] <= serial <= entry['serialTo']:
            return dict(entry)
    return None


def lookup_id(state, ident):
    for entry in _box(state)['entries']:
        if entry.get('id') == ident:
            return dict(entry)
    return None


def intact(state):
    """True si cada hash encadena con el anterior y ninguna serie se pisa o pasa el tope."""
    entries = _box(state)['entries']
    prev = GENESIS
    seen = set()
    cursors = {coin: 0 for coin in CAPS}
    for entry in entries:
        ident = entry.get('id')
        if not ident or ident in seen or entry.get('coin') not in CAPS:
            return False
        seen.add(ident)
        if entry.get('prev') != prev or entry.get('hash') != _digest(entry):
            return False
        start, end = int(entry['serialFrom']), int(entry['serialTo'])
        coin = entry['coin']
        if start != cursors[coin] + 1 or end < start or end > CAPS[coin]:
            return False
        cursors[coin] = end
        prev = entry['hash']
    return True
