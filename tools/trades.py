# SPDX-License-Identifier: AGPL-3.0-or-later
"""Intercambio entre dos personas. Todo ocurre en el hilo del servidor.

API para otros oficios (café, cacao y cualquiera que acredite objetos)
--------------------------------------------------------------------------
No hace falta otro módulo de intercambio. Se usa este.

1. Acreditar la mochila del servidor, no el inventario del navegador::

       import purses
       purses.credit(vault_state, nombre_visible, 'bolsa_cafe', 1)
       purses.credit(vault_state, nombre_visible, 'bolsa_cacao', 1)

   Ids acordados: ``bolsa_cafe``, ``bolsa_cacao``. También vale cualquier
   ``^[a-z][a-z0-9_]{0,31}$``. Guardar el vault con el mismo ``save`` que
   ya usa el depósito. El mensaje ``economy`` incluye ``purse`` de esa persona.

2. Oferta canónica (enteros; SMC y SMP van en la unidad mínima)::

       {'smc': 0, 'smp': 0, 'cobre': 0, 'items': {'bolsa_cafe': 1}}

   ``smc`` son Simonchis de oro (SMH). ``smp`` son platicas (SPH).
   ``cobre`` son Simonchis de cobre, enteras. ``amountSmh`` sigue valiendo
   como alias de ``smc`` para un cliente que sólo manda oro.

3. WebSocket, sólo entre las dos conexiones (el libro público no lleva nombres)::

       {t:'trade_start', peer:<id de la otra conexión>}
       {t:'trade_offer', id, revision, offer:{...}}
       {t:'trade_accept', id, revision}
       {t:'trade_confirm', id, revision}
       {t:'trade_cancel', id}

   Respuestas: ``trade_state``, ``trade_error``, ``trade_end``.
   Hace falta billetera desbloqueada, las dos en la ciudad o las dos en la
   mina, a 15 casillas (30 m) o menos, una sola sesión por persona, 180 s
   de inactividad. La casa y el banco no sirven. No hay puesto ni comisión.
   Cambiar la oferta sube ``revision`` y borra las aceptaciones.
   Primero aceptan las dos; después confirman las dos. Con esas cuatro
   respuestas se mueve el saldo. No se reserva saldo entre medias.

``balances(name)`` devuelve ``{smc, smp, cobre, items}``.
``commit(name_a, name_b, offer_a, offer_b, trade_id)`` persiste o lanza.
"""
import re
import time
import uuid

import cobre
import economy
import libro
import mochila
import plata
import purses

PROXIMITY_TILES = 15
TIMEOUT_S = 180
MAX_SMH = economy.MAX_SMH
MAX_SPH = plata.MAX_SUPPLY * plata.SUBS
MAX_COBRE = cobre.MAX_SUPPLY
MAX_ITEM = 999
ITEM_OK = re.compile(r'^[a-z][a-z0-9_]{0,31}$')


class TradeError(ValueError):
    pass


def empty_offer():
    return {'smc': 0, 'smp': 0, 'cobre': 0, 'items': {}}


def _whole(value, limit, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TradeError(label + ' tiene que ser un entero.')
    if value < 0 or value > limit:
        raise TradeError(label + ' no es válido.')
    return value


def normalize_offer(raw):
    """Oferta canónica. ``amountSmh`` cuenta como SMC si no viene ``smc``."""
    if raw is None:
        raw = {}
    if isinstance(raw, bool) or isinstance(raw, int):
        raw = {'smc': raw}
    if not isinstance(raw, dict):
        raise TradeError('La oferta no es válida.')
    if 'smc' in raw:
        smc_raw = raw.get('smc')
    elif 'amountSmh' in raw:
        smc_raw = raw.get('amountSmh')
    else:
        smc_raw = 0
    smc = _whole(smc_raw, MAX_SMH, 'La Simoncoin')
    smp = _whole(raw.get('smp', 0), MAX_SPH, 'La Simonplata')
    copper = _whole(raw.get('cobre', 0), MAX_COBRE, 'El cobre')
    items_raw = raw.get('items') or {}
    if not isinstance(items_raw, dict):
        raise TradeError('Los objetos de la oferta no son válidos.')
    items = {}
    for key, qty in items_raw.items():
        if not isinstance(key, str) or not ITEM_OK.match(key):
            raise TradeError('Hay un objeto que no se puede intercambiar.')
        count = _whole(qty, MAX_ITEM, 'La cantidad de ' + key)
        if count:
            items[key] = count
    return {'smc': smc, 'smp': smp, 'cobre': copper, 'items': items}


def offer_empty(offer):
    return not offer['smc'] and not offer['smp'] and not offer['cobre'] and not offer['items']


def public_legs(offer):
    """Lados que pueden verse en el libro. Sin nombres."""
    legs = []
    if offer['smc']:
        legs.append({'asset': 'smc', 'amount': offer['smc']})
    if offer['smp']:
        legs.append({'asset': 'smp', 'amount': offer['smp']})
    if offer['cobre']:
        legs.append({'asset': 'cobre', 'amount': offer['cobre']})
    for item, qty in sorted(offer['items'].items()):
        legs.append({'asset': 'item', 'item': item, 'amount': qty})
    return legs


def _covers(balance, offer):
    if offer['smc'] > int(balance.get('smc') or 0):
        return False
    if offer['smp'] > int(balance.get('smp') or 0):
        return False
    if offer['cobre'] > int(balance.get('cobre') or 0):
        return False
    have = balance.get('items') or {}
    return all(qty <= int(have.get(item) or 0) for item, qty in offer['items'].items())


def _take_smp(econ, name, sph):
    if sph <= 0:
        return True
    plata.ensure(econ)
    wallets = econ['plata'].setdefault('wallets', {})
    have = int(wallets.get(name) or 0)
    if have < sph:
        return False
    wallets[name] = have - sph
    return True


def _give_smp(econ, name, sph):
    if sph <= 0:
        return
    plata.ensure(econ)
    wallets = econ['plata'].setdefault('wallets', {})
    wallets[name] = int(wallets.get(name) or 0) + sph


def _take_cobre(econ, name, qty):
    if qty <= 0:
        return True
    box = cobre.ensure(econ)
    have = int((box.get('wallets') or {}).get(name) or 0)
    if have < qty:
        return False
    box['wallets'][name] = have - qty
    return True


def _give_cobre(econ, name, qty):
    if qty <= 0:
        return
    cobre.credit_named(econ, name, qty)


def apply_exchange(econ, vault, chain, seed, name_a, name_b, offer_a, offer_b, trade_id):
    """Mueve las dos ofertas en copias. El libro público no lleva los nombres.

    Lanza TradeError y no debe persistirse si algo no alcanza. Las SMC que
    salen de una billetera quedan anotadas en el libro madre como
    ``intercambio``: la firma conserva las cuentas y la vista pública las omite.
    """
    offer_a = normalize_offer(offer_a)
    offer_b = normalize_offer(offer_b)
    if offer_empty(offer_a) and offer_empty(offer_b):
        raise TradeError('Añade algo antes de aceptar.')
    if name_a == name_b or not name_a or not name_b:
        raise TradeError('Hacen falta dos personas distintas.')

    def holdings(name):
        return {
            'smc': int((econ.get('wallets') or {}).get(name) or 0),
            'smp': plata.balance_of(econ, name),
            'cobre': cobre.balance_of(econ, name),
            'items': purses.inventory(vault, name),
        }

    balance_a, balance_b = holdings(name_a), holdings(name_b)
    if not _covers(balance_a, offer_a) or not _covers(balance_b, offer_b):
        raise TradeError('Saldo insuficiente')
    # Validate final quantities, including the space released by the recipient's
    # own offer. purses.credit caps a stack and would silently discard excess.
    for balance, outgoing, incoming in (
        (balance_a, offer_a, offer_b), (balance_b, offer_b, offer_a),
    ):
        for item, qty in incoming['items'].items():
            final = int(balance['items'].get(item) or 0) - outgoing['items'].get(item, 0) + qty
            if final > purses.MAX_STACK:
                raise TradeError('No hay espacio para todos los objetos. Ajusten las ofertas.')
        projected = {
            key: int(balance['items'].get(key) or 0) - int(outgoing['items'].get(key) or 0)
            for key in set(balance['items']) | set(outgoing['items'])
        }
        projected = {key: qty for key, qty in projected.items() if qty > 0}
        for item, qty in incoming['items'].items():
            if not mochila.fits(projected, item, qty):
                raise TradeError(mochila.FULL)
            projected[item] = int(projected.get(item) or 0) + int(qty)
    for name, offer in ((name_a, offer_a), (name_b, offer_b)):
        if offer['smc'] and not economy.debit(econ, name, offer['smc']):
            raise TradeError('Saldo insuficiente')
    economy.credit(econ, name_a, offer_b['smc'])
    economy.credit(econ, name_b, offer_a['smc'])
    if not _take_smp(econ, name_a, offer_a['smp']) or not _take_smp(econ, name_b, offer_b['smp']):
        raise TradeError('Saldo insuficiente')
    _give_smp(econ, name_a, offer_b['smp'])
    _give_smp(econ, name_b, offer_a['smp'])
    if not _take_cobre(econ, name_a, offer_a['cobre']) or not _take_cobre(econ, name_b, offer_b['cobre']):
        raise TradeError('Saldo insuficiente')
    _give_cobre(econ, name_a, offer_b['cobre'])
    _give_cobre(econ, name_b, offer_a['cobre'])
    for item, qty in offer_a['items'].items():
        if not purses.debit(vault, name_a, item, qty):
            raise TradeError('Saldo insuficiente')
    for item, qty in offer_b['items'].items():
        if not purses.debit(vault, name_b, item, qty):
            raise TradeError('Saldo insuficiente')
    # Remove both offers before crediting either side: a simultaneous exchange
    # must not overflow temporarily when both stacks started at capacity.
    for item, qty in offer_a['items'].items():
        purses.credit(vault, name_b, item, qty)
    for item, qty in offer_b['items'].items():
        purses.credit(vault, name_a, item, qty)
    records = []
    for origin, dest, amount in (
        (name_a, name_b, offer_a['smc']),
        (name_b, name_a, offer_b['smc']),
    ):
        if not amount:
            continue
        records.append(libro.intercambiar(chain, seed, origin, dest, amount))
    economy.append_tx(econ, {
        'type': 'trade',
        'tradeId': trade_id,
        'legs': public_legs(offer_a) + public_legs(offer_b),
        'note': 'Intercambio entre dos personas',
    })
    return records


class Trades:
    def __init__(self, clients, send, balances, commit, clock=time.monotonic):
        self.clients = clients
        self.send = send
        self.balances = balances
        self.commit = commit
        self.clock = clock
        self.sessions = {}
        self.by_player = {}

    def ready(self, client):
        return bool(client and client.hello and not client.bot and client.wallet_ok)

    def _spot(self, person):
        if getattr(person, 'zone', 'city') == 'mine':
            return float(getattr(person, 'zx', person.x) or 0), float(getattr(person, 'zy', person.y) or 0)
        return float(person.x), float(person.y)

    def _near(self, a, b):
        """30 m en la ciudad o en la mina. La casa y el banco quedan fuera."""
        zone_a = getattr(a, 'zone', 'city') or 'city'
        zone_b = getattr(b, 'zone', 'city') or 'city'
        if zone_a != zone_b or zone_a not in ('city', 'mine'):
            return False
        world_a = getattr(a, 'world', None)
        world_b = getattr(b, 'world', None)
        if world_a and world_b and world_a != world_b:
            return False
        ax, ay = self._spot(a)
        bx, by = self._spot(b)
        return (ax - bx) ** 2 + (ay - by) ** 2 <= PROXIMITY_TILES ** 2

    def cancel(self, player_id, reason='Intercambio cancelado.'):
        key = self.by_player.get(player_id)
        session = self.sessions.pop(key, None)
        if not session:
            return
        for pid in session['players']:
            self.by_player.pop(pid, None)
            if pid in self.clients:
                self.send(self.clients[pid], {'t': 'trade_end', 'id': key, 'ok': False, 'reason': reason})

    def expire(self):
        for session in list(self.sessions.values()):
            if self.clock() - session['updated'] > TIMEOUT_S:
                self.cancel(session['players'][0], 'Intercambio vencido por inactividad.')

    def publish(self, session):
        body = {
            't': 'trade_state',
            'id': session['id'],
            'revision': session['revision'],
            'offers': session['offers'],
            'accepted': list(session['accepted']),
            'confirmed': list(session['confirmed']),
            'players': [
                {'id': pid, 'name': self.clients[pid].name}
                for pid in session['players'] if pid in self.clients
            ],
        }
        for pid in session['players']:
            if pid in self.clients:
                self.send(self.clients[pid], body)

    def _touch(self, session):
        session['updated'] = self.clock()
        self.publish(session)

    def handle(self, client, message):
        self.expire()
        action = message.get('t')
        if action == 'trade_cancel':
            session = self.sessions.get(self.by_player.get(client.id))
            if session and message.get('id') == session['id']:
                self.cancel(client.id)
            return
        if not self.ready(client):
            raise TradeError('Se necesita una billetera desbloqueada y conexión al servidor.')
        if action == 'trade_start':
            peer_id = message.get('peer')
            peer = self.clients.get(peer_id) if type(peer_id) is int else None
            if not self.ready(peer) or peer.id == client.id or peer.name == client.name:
                raise TradeError('Elige otra persona conectada con una billetera desbloqueada.')
            if client.id in self.by_player or peer.id in self.by_player:
                raise TradeError('Una de las personas ya tiene un intercambio abierto.')
            if not self._near(client, peer):
                raise TradeError('Acércate a la otra persona (máximo 30 m).')
            session = {
                'id': uuid.uuid4().hex,
                'players': [client.id, peer.id],
                'offers': {str(client.id): empty_offer(), str(peer.id): empty_offer()},
                'revision': 0,
                'accepted': [],
                'confirmed': [],
                'updated': self.clock(),
            }
            self.sessions[session['id']] = session
            for pid in session['players']:
                self.by_player[pid] = session['id']
            self.publish(session)
            return
        session = self.sessions.get(self.by_player.get(client.id))
        if not session or message.get('id') != session['id']:
            raise TradeError('Este intercambio ya no está activo.')
        if type(message.get('revision')) is not int or message['revision'] != session['revision']:
            self.publish(session)
            raise TradeError('La oferta cambió. Revisa la nueva versión antes de aceptar.')
        a, b = [self.clients.get(pid) for pid in session['players']]
        if not self.ready(a) or not self.ready(b) or not self._near(a, b):
            self.cancel(client.id, 'Una persona se desconectó, se bloqueó o se alejó.')
            return
        if action == 'trade_offer':
            offer = normalize_offer(message.get('offer') if message.get('offer') is not None else message)
            balance = self.balances(client.name)
            if not _covers(balance, offer):
                raise TradeError('Cantidad inválida o saldo insuficiente en la billetera.')
            session['offers'][str(client.id)] = offer
            session['revision'] += 1
            session['accepted'] = []
            session['confirmed'] = []
        elif action in ('trade_accept', 'trade_confirm'):
            left = session['offers'][str(a.id)]
            right = session['offers'][str(b.id)]
            if offer_empty(left) and offer_empty(right):
                raise TradeError('Añade algo antes de aceptar.')
            if not _covers(self.balances(a.name), left) or not _covers(self.balances(b.name), right):
                session['accepted'] = []
                session['confirmed'] = []
                self.publish(session)
                raise TradeError('Un saldo cambió. Ajusten las ofertas y acepten de nuevo.')
            if action == 'trade_accept':
                if client.id not in session['accepted']:
                    session['accepted'].append(client.id)
            else:
                if len(session['accepted']) != 2:
                    raise TradeError('Ambas personas deben aceptar primero la oferta.')
                if client.id not in session['confirmed']:
                    session['confirmed'].append(client.id)
                if len(session['confirmed']) == 2:
                    try:
                        self.commit(a.name, b.name, left, right, session['id'])
                    except TradeError as err:
                        self.cancel(client.id, str(err))
                        return
                    except Exception:
                        self.cancel(client.id, 'No se pudo guardar el intercambio. No se aplicaron cambios en memoria; reconecta para comprobar el saldo.')
                        return
                    self.sessions.pop(session['id'], None)
                    for person in (a, b):
                        self.by_player.pop(person.id, None)
                        box = self.balances(person.name) or {}
                        smc = int(box.get('smc') or 0)
                        sph = int(box.get('smp') or 0)
                        chis = int(box.get('cobre') or 0)
                        self.send(person, {
                            't': 'trade_end',
                            'id': session['id'],
                            'ok': True,
                            'balances': {'smc': smc, 'smp': sph, 'cobre': chis},
                            'reason': (
                                'Intercambiaste. Saldo: '
                                f'{economy.format_smc(smc)}, {plata.format_smp(sph)}, {chis} de cobre.'
                            ),
                        })
                    return
        else:
            raise TradeError('Acción de intercambio no reconocida.')
        self._touch(session)
