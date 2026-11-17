# SPDX-License-Identifier: AGPL-3.0-or-later
"""Puma y caída de la mochila. El servidor manda: un bulto, un dueño, una vez.

El puma (Puma concolor) anda por pasto o monte. No entra al Parque de
Envigado, al skate, a los parques ni a los pueblos. Al morir, el jugador
suelta sólo la mochila. El equipo, la experiencia, la billetera y el libro
no pasan por aquí.
"""
from __future__ import annotations

import math
import os
import re
import secrets
import time

GREEN = ('grass', 'grass_flowers', 'grass_worn')
# Casillas que el pedido deja fuera, además de parques y pueblos del mapa.
# El skate vivo del parque (origen 81,255 + dx 3, dy 18) y el rectángulo pedido.
EXTRA_BOXES = (
    (98, 264, 1, 1),      # casilla de aparición del Parque de Envigado
    (90, 260, 28, 22),    # bloque del parque en el catálogo
    (92, 210, 14, 10),    # skate pedido: x 92-105, y 210-219
    (84, 273, 3, 2),      # zona skate que está en el mundo
)
TOWN_AREAS = ('plaza', 'pueblo')
KEEP_AREAS = ('jardin',)  # el pueblo tutorial; el puma no se mete en la prueba
PROTECTED_ITEMS = ('smc', 'simoncoin', 'libro', 'xp', 'wallet', 'libro_mayor')
ITEM_RE = re.compile(r'^[a-z][a-z0-9_]{0,31}$')
DROP_TTL = 30 * 60
STALK = 18.0
WARN = 8.0
CHARGE = 5.5
BITE = 1.35
LEASH = 24.0
HIT = 26
PUMA_HP = 100
LANZA_HIT = 34
FIST_HIT = 10
WARN_S = 1.7
BITE_EVERY = 1.15


class FaunaError(ValueError):
    pass


def drop_ttl(raw=None):
    if raw is None:
        raw = os.environ.get('FAUNA_DROP_SECONDS', '')
    try:
        value = float(raw) if str(raw).strip() else DROP_TTL
    except (TypeError, ValueError):
        value = DROP_TTL
    if value < 30:
        value = 30.0
    if value > 24 * 3600:
        value = 24 * 3600.0
    return value


def gear_ids(world):
    found = set()
    items = (world or {}).get('items') or {}
    for key, spec in items.items():
        if isinstance(spec, dict) and spec.get('category') == 'tool':
            found.add(str(key))
    return found


def _qty(raw):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    if value < 1 or value > 9999:
        return 0
    return value


def _item(raw):
    text = str(raw or '').strip().lower()
    if text in PROTECTED_ITEMS or not ITEM_RE.match(text):
        return ''
    return text


def stack_items(rows):
    """Suma montones del mismo objeto. Ignora el equipo y lo que no es un ítem."""
    totals = {}
    order = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        item = _item(row.get('item'))
        qty = _qty(row.get('qty'))
        if not item or qty < 1:
            continue
        if item not in totals:
            order.append(item)
        totals[item] = min(9999, totals.get(item, 0) + qty)
    return [{'item': item, 'qty': totals[item]} for item in order]


def split_pack(slots, gear):
    """Separa la mochila del equipo. No toca experiencia, saldo ni libro."""
    gear = set(gear or ())
    kept = []
    lost_rows = []
    for row in slots or []:
        if not isinstance(row, dict):
            continue
        item = _item(row.get('item'))
        qty = _qty(row.get('qty'))
        if not item or qty < 1:
            continue
        if item in gear:
            kept.append({'item': item, 'qty': qty})
        else:
            lost_rows.append({'item': item, 'qty': qty})
    return kept, stack_items(lost_rows)


def _box(x, y, w, h, pad=0):
    return (int(x) - pad, int(y) - pad, int(w) + pad * 2, int(h) + pad * 2)


def forbidden_boxes(world, places=None):
    boxes = []
    for area in (world or {}).get('areas') or []:
        aid = str(area.get('id') or '')
        if aid in TOWN_AREAS or aid.startswith('parque_'):
            boxes.append(_box(area['x'], area['y'], area['w'], area['h'], 2))
    for region in (world or {}).get('regions') or []:
        rid = str(region.get('id') or '')
        if rid in KEEP_AREAS or rid == 'envigado':
            boxes.append(_box(region['x'], region['y'], region['w'], region['h'], 1))
    for raw in places or []:
        if str(raw.get('id') or '') == 'parque-envigado':
            boxes.append(_box(raw['x'], raw['y'], raw['w'], raw['h'], 1))
    for x, y, w, h in EXTRA_BOXES:
        boxes.append((x, y, w, h))
    return boxes


def inside_box(x, y, boxes):
    ix, iy = int(math.floor(x)), int(math.floor(y))
    for bx, by, bw, bh in boxes:
        if bx <= ix < bx + bw and by <= iy < by + bh:
            return True
    return False


class Range:
    """Mapa de pasto donde el puma puede pisar."""

    def __init__(self, world, places=None):
        self.width = int(world['width'])
        self.height = int(world['height'])
        self.boxes = forbidden_boxes(world, places)
        tiles = world['tiles']
        ground = world['ground']
        coll = world['collision']
        self.ok = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                if coll[y][x] != 0:
                    row.append(False)
                    continue
                spec = tiles[str(ground[y][x])] if isinstance(tiles, dict) else tiles[ground[y][x]]
                kind = spec.get('kind')
                row.append(kind in GREEN and not inside_box(x, y, self.boxes))
            self.ok.append(row)
        self.homes = self._homes()

    def allowed(self, x, y):
        ix, iy = int(math.floor(x)), int(math.floor(y))
        if iy < 0 or ix < 0 or iy >= self.height or ix >= self.width:
            return False
        return bool(self.ok[iy][ix])

    def _homes(self):
        found = []
        margin = 16
        for y in range(margin, max(margin, self.height - margin), 7):
            for x in range(margin, max(margin, self.width - margin), 7):
                if self.allowed(x, y):
                    found.append((x, y))
        if not found:
            return []
        picked = [found[0]]
        while len(picked) < 3 and len(picked) < len(found):
            best = None
            best_d = -1
            for spot in found:
                dist = min(math.hypot(spot[0] - px, spot[1] - py) for px, py in picked)
                if dist > best_d:
                    best_d = dist
                    best = spot
            if best is None or best in picked:
                break
            picked.append(best)
        return picked

    def spawn_pumas(self):
        pumas = []
        for i, (x, y) in enumerate(self.homes):
            pumas.append({
                'id': 'puma-%d' % (i + 1),
                'name': 'Puma',
                'species': 'puma_concolor',
                'x': float(x), 'y': float(y),
                'homeX': float(x), 'homeY': float(y),
                'dir': 'down',
                'mode': 'wander',
                'hp': PUMA_HP,
                'growl': False,
                'until': 0.0,
                'nextHit': 0.0,
                'goalX': float(x), 'goalY': float(y),
                'goalAt': 0.0,
                'target': '',
            })
        return pumas


def _dir(dx, dy, fallback):
    if abs(dx) < 0.05 and abs(dy) < 0.05:
        return fallback or 'down'
    if abs(dx) > abs(dy):
        return 'right' if dx > 0 else 'left'
    return 'down' if dy > 0 else 'up'


def _slide(puma, nx, ny, allowed):
    if allowed(nx, ny):
        puma['x'], puma['y'] = nx, ny
        return True
    if allowed(nx, puma['y']):
        puma['x'] = nx
        return True
    if allowed(puma['x'], ny):
        puma['y'] = ny
        return True
    return False


def _toward(puma, tx, ty, speed, dt, allowed):
    dx, dy = tx - puma['x'], ty - puma['y']
    dist = math.hypot(dx, dy)
    if dist < 1e-4:
        return 0.0
    step = min(dist, max(0.0, speed) * dt)
    nx = puma['x'] + dx / dist * step
    ny = puma['y'] + dy / dist * step
    if _slide(puma, nx, ny, allowed):
        puma['dir'] = _dir(dx, dy, puma.get('dir'))
    return dist


def _nearest(puma, players):
    best = None
    best_d = 1e9
    for player in players or []:
        try:
            px, py = float(player['x']), float(player['y'])
        except (KeyError, TypeError, ValueError):
            continue
        if inside_box(px, py, puma.get('_safe') or ()):
            continue
        dist = math.hypot(px - puma['x'], py - puma['y'])
        if dist < best_d:
            best_d = dist
            best = player
    return best, best_d


def step_puma(puma, players, allowed, safe_boxes, now, dt, rng):
    """Un paso. `allowed(x,y)` es el pasto. `safe_boxes` es donde no caza."""
    puma['_safe'] = safe_boxes
    puma['growl'] = False
    if puma.get('hp', PUMA_HP) <= 0:
        if now >= float(puma.get('until') or 0):
            puma['hp'] = PUMA_HP
            puma['x'], puma['y'] = float(puma['homeX']), float(puma['homeY'])
            puma['mode'] = 'wander'
            puma['target'] = ''
        return None
    player, dist = _nearest(puma, players)
    mode = puma.get('mode') or 'wander'
    event = None
    if mode == 'wander':
        if player and dist <= STALK:
            puma['mode'] = 'stalk'
            puma['target'] = str(player.get('id') or player.get('name') or '')
        else:
            if now >= float(puma.get('goalAt') or 0):
                ang = rng.random() * math.tau
                rad = 3 + rng.random() * 7
                puma['goalX'] = puma['homeX'] + math.cos(ang) * rad
                puma['goalY'] = puma['homeY'] + math.sin(ang) * rad
                puma['goalAt'] = now + 3.5 + rng.random() * 3
            _toward(puma, puma['goalX'], puma['goalY'], 1.15, dt, allowed)
            if math.hypot(puma['x'] - puma['homeX'], puma['y'] - puma['homeY']) > 14:
                _toward(puma, puma['homeX'], puma['homeY'], 1.4, dt, allowed)
    elif mode == 'stalk':
        if not player or dist > LEASH:
            puma['mode'] = 'wander'
            puma['target'] = ''
        elif dist <= WARN:
            puma['mode'] = 'warn'
            puma['until'] = now + WARN_S
            puma['growl'] = True
        else:
            _toward(puma, float(player['x']), float(player['y']), 1.7, dt, allowed)
    elif mode == 'warn':
        puma['growl'] = True
        if player:
            puma['dir'] = _dir(float(player['x']) - puma['x'], float(player['y']) - puma['y'], puma.get('dir'))
        if now >= float(puma.get('until') or 0):
            if player and dist <= LEASH:
                puma['mode'] = 'charge'
            else:
                puma['mode'] = 'wander'
                puma['target'] = ''
    elif mode == 'charge':
        if not player or dist > LEASH:
            puma['mode'] = 'wander'
            puma['target'] = ''
        else:
            _toward(puma, float(player['x']), float(player['y']), 4.4, dt, allowed)
            dist = math.hypot(float(player['x']) - puma['x'], float(player['y']) - puma['y'])
            if dist <= BITE:
                puma['mode'] = 'attack'
                puma['nextHit'] = now
    elif mode == 'attack':
        if not player or dist > 3.2:
            puma['mode'] = 'charge' if player and dist <= LEASH else 'wander'
        elif now >= float(puma.get('nextHit') or 0):
            puma['nextHit'] = now + BITE_EVERY
            puma['growl'] = True
            event = {
                'id': player.get('id'),
                'name': player.get('name') or '',
                'amount': HIT,
                'puma': puma['id'],
            }
    else:
        puma['mode'] = 'wander'
    puma.pop('_safe', None)
    return event


def strike(puma, x, y, armed, now):
    """El jugador responde. La lanza pega más. Hace falta estar al lado."""
    if not puma or int(puma.get('hp') or 0) <= 0:
        return 0
    if puma.get('mode') not in ('warn', 'charge', 'attack', 'stalk'):
        return 0
    try:
        dist = math.hypot(float(x) - float(puma['x']), float(y) - float(puma['y']))
    except (TypeError, ValueError):
        return 0
    if dist > 2.4:
        return 0
    if now < float(puma.get('swingAt') or 0):
        return 0
    dmg = LANZA_HIT if armed else FIST_HIT
    puma['hp'] = max(0, int(puma.get('hp') or PUMA_HP) - dmg)
    puma['swingAt'] = now + 0.55
    if puma['hp'] <= 0:
        puma['mode'] = 'flee'
        puma['until'] = now + 50
        puma['x'], puma['y'] = float(puma['homeX']), float(puma['homeY'])
    else:
        puma['mode'] = 'warn'
        puma['until'] = now + 0.8
        puma['growl'] = True
    return dmg


def public_puma(puma):
    return {
        'id': puma['id'],
        'name': 'Puma',
        'x': round(float(puma['x']), 2),
        'y': round(float(puma['y']), 2),
        'dir': puma.get('dir') or 'down',
        'mode': puma.get('mode') or 'wander',
        'hp': int(puma.get('hp') or 0),
        'growl': bool(puma.get('growl')),
    }


def empty_state():
    return {'v': 1, 'drops': [], 'seen': {}, 'pumas': []}


def dump(state):
    """Sólo el bulto vive en disco. El puma vuelve a su monte al reiniciar."""
    raw = normalize(state)
    return {'v': 1, 'drops': raw['drops'], 'seen': raw['seen']}


def normalize(doc):
    raw = doc if isinstance(doc, dict) else {}
    drops = []
    for row in raw.get('drops') or []:
        if not isinstance(row, dict) or not row.get('id'):
            continue
        drops.append({
            'id': str(row['id']),
            'owner': str(row.get('owner') or ''),
            'token': str(row.get('token') or ''),
            'x': float(row.get('x') or 0),
            'y': float(row.get('y') or 0),
            'items': stack_items(row.get('items')),
            'purse': {k: int(v) for k, v in (row.get('purse') or {}).items() if _item(k) and _qty(v)},
            'created': float(row.get('created') or 0),
            'expires': float(row.get('expires') or 0),
        })
    seen = {}
    for key, value in (raw.get('seen') or {}).items():
        if key and value:
            seen[str(key)] = str(value)
    return {'v': 1, 'drops': drops, 'seen': seen, 'pumas': list(raw.get('pumas') or [])}


class Book:
    """Bultos en el suelo. Un dueño, una recogida, sin copia."""

    def __init__(self, state=None, gear=(), ttl=None, purse_state=None):
        self.state = normalize(state)
        self.gear = set(gear or ())
        self.ttl = drop_ttl(ttl if ttl is not None else DROP_TTL)
        self.purse_state = purse_state if isinstance(purse_state, dict) else {'purses': {}}

    def _purse(self, owner):
        purses = self.purse_state.setdefault('purses', {})
        bag = purses.setdefault(str(owner or ''), {})
        return bag

    def _reserved(self, owner):
        totals = {}
        for drop in self.state['drops']:
            if drop['owner'] != owner:
                continue
            for row in drop['items']:
                totals[row['item']] = totals.get(row['item'], 0) + row['qty']
        return totals

    def _find_token(self, owner, token):
        key = owner + ':' + token
        drop_id = self.state['seen'].get(key)
        if not drop_id:
            return None
        for drop in self.state['drops']:
            if drop['id'] == drop_id:
                return drop
        return None

    def commit(self, owner, x, y, slots, token, now=None):
        """Pasa la mochila al bulto. El mismo token no crea otro."""
        owner = str(owner or '')
        token = str(token or '')[:80]
        if not owner or not token:
            raise FaunaError('falta el dueño o la marca')
        now = time.time() if now is None else float(now)
        previous = self._find_token(owner, token)
        if previous:
            return previous
        kept, lost = split_pack(slots, self.gear)
        reserved = self._reserved(owner)
        fresh = []
        for row in lost:
            room = row['qty'] - int(reserved.get(row['item']) or 0)
            if room > 0:
                fresh.append({'item': row['item'], 'qty': room})
        if not fresh:
            raise FaunaError('no hay nada nuevo que soltar')
        bag = self._purse(owner)
        purse_taken = {}
        for row in fresh:
            have = int(bag.get(row['item']) or 0)
            take = min(have, row['qty'])
            if take > 0:
                left = have - take
                if left:
                    bag[row['item']] = left
                else:
                    bag.pop(row['item'], None)
                purse_taken[row['item']] = take
        drop = {
            'id': secrets.token_hex(8),
            'owner': owner,
            'token': token,
            'x': float(x),
            'y': float(y),
            'items': fresh,
            'purse': purse_taken,
            'created': now,
            'expires': now + self.ttl,
        }
        self.state['drops'].append(drop)
        self.state['seen'][owner + ':' + token] = drop['id']
        if len(self.state['seen']) > 400:
            self.state['seen'] = dict(list(self.state['seen'].items())[-200:])
        view = dict(drop)
        view['kept'] = kept
        return view

    def expire(self, now=None):
        now = time.time() if now is None else float(now)
        alive = []
        gone = []
        for drop in self.state['drops']:
            if float(drop.get('expires') or 0) <= now:
                gone.append(drop)
            else:
                alive.append(drop)
        self.state['drops'] = alive
        return gone

    def pickup(self, owner, drop_id, now=None):
        """Sólo el dueño. La segunda vez no devuelve nada."""
        owner = str(owner or '')
        now = time.time() if now is None else float(now)
        self.expire(now)
        found = None
        for drop in self.state['drops']:
            if drop['id'] == str(drop_id or ''):
                found = drop
                break
        if not found:
            raise FaunaError('ese bulto ya no está')
        if found['owner'] != owner:
            raise FaunaError('esa mochila no es tuya')
        self.state['drops'] = [row for row in self.state['drops'] if row['id'] != found['id']]
        bag = self._purse(owner)
        for item, qty in (found.get('purse') or {}).items():
            bag[item] = int(bag.get(item) or 0) + int(qty)
        return {'id': found['id'], 'owner': owner, 'items': list(found['items']), 'x': found['x'], 'y': found['y']}

    def for_owner(self, owner, now=None):
        now = time.time() if now is None else float(now)
        self.expire(now)
        return [self.public_drop(row, full=row['owner'] == owner) for row in self.state['drops'] if row['owner'] == owner or True]

    def public_drop(self, drop, full=False):
        view = {
            'id': drop['id'],
            'owner': drop['owner'],
            'x': round(float(drop['x']), 2),
            'y': round(float(drop['y']), 2),
            'expires': drop['expires'],
            'label': 'Tu mochila' if full else 'Mochila',
        }
        if full:
            view['items'] = list(drop['items'])
        return view


def ensure_pumas(state, land):
    if state.get('pumas'):
        return state['pumas']
    state['pumas'] = land.spawn_pumas()
    return state['pumas']


def step_world(state, land, players, now, dt, rng):
    ensure_pumas(state, land)
    events = []
    for puma in state['pumas']:
        event = step_puma(puma, players, land.allowed, land.boxes, now, dt, rng)
        if event:
            events.append(event)
    return events
