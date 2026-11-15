# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fichas y medallas físicas con QR. Prototipo apagado por defecto.

No acuña Simoncoin, Simonplata ni Simonchis. Al emitir se aparta saldo ya
existente en reserva_fichas. Un pase cambia de titular; la reserva no se mueve.
Una lectura del QR sólo abre la ficha y deja una intención. No la transfiere.
"""
import hashlib
import hmac
import os
import secrets
import time

import cobre
import economy
import plata

RESERVA = 'reserva_fichas'
METALES = ('simoncoin', 'simonplata', 'simonchis')
ESTADOS = ('circulando', 'perdida', 'robada', 'revocada', 'retirada')
VENTANA_LECTURA = 600


class FichaError(ValueError):
    pass


def activas():
    """La web pública no ofrece fichas físicas salvo FICHAS_FISICAS=1."""
    return os.environ.get('FICHAS_FISICAS', '').strip() == '1'


def _box(econ):
    box = econ.setdefault('fichas', {})
    box.setdefault('piezas', {})
    box.setdefault('intenciones', {})
    box.setdefault('libro', [])
    return box


def _spendable(econ, metal, name):
    if metal == 'simoncoin':
        return int((econ.get('wallets') or {}).get(name) or 0)
    if metal == 'simonplata':
        return plata.balance_of(econ, name)
    if metal == 'simonchis':
        return cobre.balance_of(econ, name)
    raise FichaError('Metal desconocido.')


def _debit(econ, metal, name, amount):
    amount = int(amount)
    if amount <= 0:
        return False
    if metal == 'simoncoin':
        return economy.debit(econ, name, amount)
    if metal == 'simonplata':
        plata.ensure(econ)
        wallets = econ['plata'].setdefault('wallets', {})
        have = int(wallets.get(name) or 0)
        if have < amount:
            return False
        wallets[name] = have - amount
        return True
    if metal == 'simonchis':
        box = cobre.ensure(econ)
        have = int((box.get('wallets') or {}).get(name) or 0)
        if have < amount:
            return False
        box['wallets'][name] = have - amount
        return True
    return False


def _credit(econ, metal, name, amount):
    amount = int(amount)
    if amount <= 0 or not name:
        return
    if metal == 'simoncoin':
        economy.credit(econ, name, amount)
        return
    if metal == 'simonplata':
        plata.ensure(econ)
        wallets = econ['plata'].setdefault('wallets', {})
        wallets[name] = int(wallets.get(name) or 0) + amount
        return
    if metal == 'simonchis':
        cobre.credit_named(econ, name, amount)


def _mac(key, ident):
    return hmac.new(bytes.fromhex(key), ident.encode('utf-8'), hashlib.sha256).hexdigest()


def _anotar(econ, piece, hecho, amount):
    """Libro de la ficha y un apunte público sin nombres."""
    box = _box(econ)
    row = {
        'ts': int(time.time()),
        'pieza': piece['id'],
        'hecho': hecho,
        'metal': piece['metal'],
        'cantidad': int(amount),
    }
    box['libro'].append(row)
    economy.append_tx(econ, {
        'type': 'ficha',
        'piece': piece['id'],
        'metal': piece['metal'],
        'amountSubs': int(amount) if piece['metal'] == 'simoncoin' else 0,
        'note': 'Ficha coleccionable. Las partes no se publican.',
    })


def emitir(econ, account, metal, amount, peso_g, serie, ahora=None, segundo=None):
    """Aparta saldo ya existente. Si no alcanza, no crea la ficha."""
    if not account or not isinstance(account, str):
        raise FichaError('Hace falta una cuenta.')
    if metal not in METALES:
        raise FichaError('Metal desconocido.')
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise FichaError('La cantidad no es válida.')
    if _spendable(econ, metal, account) < amount:
        raise FichaError('No hay saldo suficiente. No se crea ninguna ficha.')
    if not _debit(econ, metal, account, amount):
        raise FichaError('No hay saldo suficiente. No se crea ninguna ficha.')
    _credit(econ, metal, RESERVA, amount)
    ident = 'FIC-' + secrets.token_hex(4).upper()
    key = secrets.token_hex(32)
    piece = {
        'id': ident,
        'serie': str(serie or 'colección')[:40],
        'metal': metal,
        'cantidad': amount,
        'peso_g': str(peso_g or '')[:20],
        'acuñada': int(ahora if ahora is not None else time.time()),
        'estado': 'circulando',
        'titular': account,
        'clave': key,
        'segundo': hashlib.sha256(str(segundo).encode('utf-8')).hexdigest() if segundo else '',
        'alerta': '',
        'pases': 0,
    }
    _box(econ)['piezas'][ident] = piece
    _anotar(econ, piece, 'emision', amount)
    return {'id': ident, 'url': '/ficha/' + ident + '?m=' + _mac(key, ident)}


def _pieza(econ, ident):
    return _box(econ)['piezas'].get(ident)


def comprobar(piece, mac):
    if not piece or not isinstance(mac, str) or not mac:
        return False
    expected = _mac(piece['clave'], piece['id'])
    return hmac.compare_digest(expected, mac)


def vista_publica(econ, ident, mac):
    """Sin nombres, correos ni identificadores de cuenta. Sin el mac no confirma la pieza."""
    piece = _pieza(econ, ident)
    if not comprobar(piece, mac):
        return {'comprobada': False, 'aviso': 'No se puede comprobar esta ficha.'}
    historia = [
        {'n': index + 1, 'hecho': row['hecho'], 'ts': row['ts']}
        for index, row in enumerate(_box(econ)['libro'])
        if row.get('pieza') == ident
    ]
    return {
        'comprobada': True,
        'id': piece['id'],
        'serie': piece['serie'],
        'metal': piece['metal'],
        'peso_g': piece['peso_g'],
        'acuñada': piece['acuñada'],
        'estado': piece['estado'],
        'pases': piece['pases'],
        'alerta': piece['alerta'],
        'historia': historia,
        'aviso': 'Ficha o medalla coleccionable. No es dinero de curso legal.',
    }


def leer(econ, ident, mac, lugar='', ahora=None):
    """Una lectura no cambia de titular."""
    piece = _pieza(econ, ident)
    if not comprobar(piece, mac):
        return vista_publica(econ, ident, mac)
    ahora = int(ahora if ahora is not None else time.time())
    sitio = str(lugar or '').strip()[:40]
    recientes = piece.setdefault('lecturas', [])
    recientes.append({'ts': ahora, 'lugar': sitio})
    del recientes[:-20]
    otras = [row for row in recientes if ahora - int(row['ts']) <= VENTANA_LECTURA and row['lugar'] and row['lugar'] != sitio]
    if sitio and otras:
        piece['alerta'] = 'Lecturas seguidas en sitios distintos.'
    intent = secrets.token_hex(8)
    _box(econ)['intenciones'][intent] = {
        'id': intent,
        'pieza': ident,
        'ts': ahora,
        'vendedor': '',
        'comprador': '',
        'aceptada': [],
        'confirmada': [],
    }
    page = vista_publica(econ, ident, mac)
    page['intencion'] = intent
    page['transferencia'] = False
    return page


def _intencion(econ, intent, piece_id):
    row = _box(econ)['intenciones'].get(intent)
    if not row or row['pieza'] != piece_id:
        raise FichaError('Esta lectura ya no sirve para un pase.')
    return row


def aceptar(econ, account, intent):
    if not account:
        raise FichaError('Entra con tu cuenta.')
    row = _box(econ)['intenciones'].get(intent)
    if not row:
        raise FichaError('Esta lectura ya no sirve para un pase.')
    piece = _pieza(econ, row['pieza'])
    if not piece or piece['estado'] != 'circulando':
        raise FichaError('Esta ficha no está en circulación.')
    if piece['alerta']:
        raise FichaError('La ficha tiene lecturas en sitios distintos. No se inicia el pase.')
    if account == piece['titular']:
        row['vendedor'] = account
    elif row['vendedor'] and account != row['vendedor']:
        row['comprador'] = account
    else:
        raise FichaError('Primero tiene que aceptar quien tiene la ficha.')
    if account not in row['aceptada']:
        row['aceptada'].append(account)
    row['confirmada'] = [item for item in row['confirmada'] if item == account]
    return {'id': row['id'], 'aceptada': len(row['aceptada']), 'confirmada': len(row['confirmada'])}


def confirmar(econ, account, intent):
    if not account:
        raise FichaError('Entra con tu cuenta.')
    row = _box(econ)['intenciones'].get(intent)
    if not row:
        raise FichaError('Esta lectura ya no sirve para un pase.')
    piece = _pieza(econ, row['pieza'])
    if not piece or piece['estado'] != 'circulando':
        raise FichaError('Esta ficha no está en circulación.')
    if piece['titular'] != row['vendedor'] or not row['comprador'] or row['comprador'] == row['vendedor']:
        raise FichaError('Tienen que aceptar las dos cuentas antes de confirmar.')
    if len(row['aceptada']) < 2 or account not in (row['vendedor'], row['comprador']):
        raise FichaError('Tienen que aceptar las dos cuentas antes de confirmar.')
    if account not in row['confirmada']:
        row['confirmada'].append(account)
    if len(row['confirmada']) < 2:
        return {'ok': False, 'confirmada': len(row['confirmada']), 'transferencia': False}
    seller, buyer = row['vendedor'], row['comprador']
    if piece['titular'] != seller:
        raise FichaError('La ficha ya no está en esa cuenta. No se movió nada.')
    antes = _spendable(econ, piece['metal'], RESERVA)
    piece['titular'] = buyer
    piece['pases'] = int(piece['pases']) + 1
    if _spendable(econ, piece['metal'], RESERVA) != antes:
        piece['titular'] = seller
        piece['pases'] -= 1
        raise FichaError('La reserva no cuadra. No se dejó el pase aplicado.')
    _anotar(econ, piece, 'pase', piece['cantidad'])
    _box(econ)['intenciones'].pop(intent, None)
    return {'ok': True, 'transferencia': True, 'pases': piece['pases']}


def marcar(econ, account, ident, estado):
    piece = _pieza(econ, ident)
    if not piece or piece['titular'] != account:
        raise FichaError('Sólo quien tiene la ficha puede marcarla.')
    if estado not in ('perdida', 'robada', 'revocada'):
        raise FichaError('Estado desconocido.')
    piece['estado'] = estado
    _anotar(econ, piece, estado, piece['cantidad'])
    return {'id': ident, 'estado': estado}


def retirar(econ, account, ident, segundo=''):
    """Devuelve el saldo apartado a quien tiene la ficha. No acuña."""
    piece = _pieza(econ, ident)
    if not piece or piece['titular'] != account or piece['estado'] != 'circulando':
        raise FichaError('Esta ficha no se puede retirar.')
    if piece['segundo']:
        digest = hashlib.sha256(str(segundo).encode('utf-8')).hexdigest()
        if not hmac.compare_digest(piece['segundo'], digest):
            raise FichaError('Falta el segundo código, el que no va en el QR.')
    amount = int(piece['cantidad'])
    if not _debit(econ, piece['metal'], RESERVA, amount):
        raise FichaError('La reserva no tiene esa cantidad. No se retiró.')
    _credit(econ, piece['metal'], account, amount)
    piece['estado'] = 'retirada'
    _anotar(econ, piece, 'retiro', amount)
    return {'id': ident, 'estado': 'retirada'}


def _esc(text):
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def pagina(vista):
    if not vista.get('comprobada'):
        cuerpo = '<p>No se puede comprobar esta ficha.</p>'
    else:
        filas = ''.join(
            '<li>' + _esc(item['hecho']) + '</li>' for item in vista.get('historia') or []
        )
        cuerpo = (
            '<p>Comprobada.</p>'
            '<ul><li>Serie: ' + _esc(vista['serie']) + '</li>'
            '<li>Metal de juego: ' + _esc(vista['metal']) + '</li>'
            '<li>Peso: ' + _esc(vista['peso_g']) + '</li>'
            '<li>Fecha de emisión: ' + _esc(vista['acuñada']) + '</li>'
            '<li>Estado: ' + _esc(vista['estado']) + '</li>'
            '<li>Pases: ' + _esc(vista['pases']) + '</li></ul>'
            '<ol>' + filas + '</ol>'
            '<p>' + _esc(vista['aviso']) + '</p>'
        )
        if vista.get('alerta'):
            cuerpo += '<p>Aviso: hay lecturas seguidas en sitios distintos. Un pase nuevo queda detenido.</p>'
        if vista.get('intencion'):
            cuerpo += '<p>La lectura quedó registrada. No mueve la ficha. Las dos cuentas tienen que aceptarla y confirmarla.</p>'
    return '<!doctype html><html lang="es"><meta charset="utf-8"><title>Ficha coleccionable</title><h1>Ficha coleccionable</h1>' + cuerpo + '</html>'


def responder(econ, method, path, query, body, account):
    """HTTP mínimo. Si el flag está apagado, responde como si la ruta no existiera."""
    if not activas():
        return 404, {'error': 'no existe'}, 'json'
    ident = ''
    if path.startswith('/ficha/'):
        ident = path.split('/')[2] if len(path.split('/')) > 2 else ''
    if method == 'GET' and path.startswith('/ficha/'):
        mac = (query.get('m') or [''])[0]
        lugar = (query.get('lugar') or [''])[0]
        vista = leer(econ, ident, mac, lugar)
        return 200, pagina(vista), 'html'
    if method != 'POST' or not path.startswith('/api/fichas/'):
        return 404, {'error': 'no existe'}, 'json'
    action = path.rstrip('/').split('/')[-1]
    try:
        if action == 'aceptar':
            return 200, aceptar(econ, account, str(body.get('intencion') or '')), 'json'
        if action == 'confirmar':
            return 200, confirmar(econ, account, str(body.get('intencion') or '')), 'json'
        if action == 'marcar':
            return 200, marcar(econ, account, str(body.get('id') or ''), str(body.get('estado') or '')), 'json'
        if action == 'retirar':
            return 200, retirar(econ, account, str(body.get('id') or ''), body.get('segundo') or ''), 'json'
    except FichaError as exc:
        return 400, {'error': str(exc)}, 'json'
    return 404, {'error': 'no existe'}, 'json'
